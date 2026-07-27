from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.errors import InconsistentPlace
from app.modules.locations.models import City, Department
from app.modules.third_parties.documents import (
    DocumentType,
    PersonType,
    compute_check_digit,
    normalize_document,
    requires_check_digit,
    validate_check_digit,
)
from app.modules.third_parties.errors import (
    ThirdPartyAlreadyExists,
    ThirdPartyNotDeleted,
    ThirdPartyNotFound,
)
from app.modules.third_parties.models import ThirdParty
from app.modules.third_parties.schemas import (
    LegalEntityCreate,
    NaturalPersonCreate,
    ThirdPartyUpdate,
)
from app.shared.pagination import count_of

_KEEP_ON_REVIVE = frozenset({"id", "created_at", "updated_at", "deleted_at"})


class ThirdPartyService:
    """Business rules for third parties."""
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get(
        self, third_party_id: int, *, include_deleted: bool = False
    ) -> ThirdParty:
        found = await self._find(third_party_id, include_deleted=include_deleted)
        if found is None:
            raise ThirdPartyNotFound(third_party_id)
        return found

    async def find_many(
        self,
        *,
        person_type: PersonType | None = None,
        document_type: DocumentType | None = None,
        search: str | None = None,
        only_active: bool | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[ThirdParty], int]:
        query = self._visible(include_deleted)

        if person_type is not None:
            query = query.where(ThirdParty.person_type == person_type)
        if document_type is not None:
            query = query.where(ThirdParty.document_type == document_type)
        if only_active is not None:
            query = query.where(ThirdParty.is_active.is_(only_active))
        if search:
            query = query.where(_matching(search))

        total = await count_of(self._session, query)
        result = await self._session.execute(
            query.order_by(ThirdParty.document_number).offset(skip).limit(limit)
        )
        return result.scalars().all(), total


    async def create(
        self, payload: NaturalPersonCreate | LegalEntityCreate
    ) -> ThirdParty:
        candidate = _build(payload)
        await self._check_places(candidate)

        existing = await self._find_by_document(
            candidate.document_type, candidate.document_number
        )
        if existing is not None and not existing.is_deleted:
            raise ThirdPartyAlreadyExists(
                candidate.document_type.value, candidate.document_number
            )

        if existing is None:
            self._session.add(candidate)
            return await self._commit(candidate)

        _copy_onto(existing, candidate)
        existing.restore()
        return await self._commit(existing)

    async def update(
        self, third_party_id: int, payload: ThirdPartyUpdate
    ) -> ThirdParty:
        third_party = await self.get(third_party_id)
        changes = payload.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(third_party, field, value)

        if {"document_type", "document_number", "check_digit"} & changes.keys():
            _renormalize_document(
                third_party, given_check_digit="check_digit" in changes
            )

            clash = await self._find_by_document(
                third_party.document_type, third_party.document_number
            )
            if clash is not None and clash.id != third_party.id:
                raise ThirdPartyAlreadyExists(
                    third_party.document_type.value, third_party.document_number
                )

        await self._check_places(third_party)
        return await self._commit(third_party)

    async def delete(self, third_party_id: int) -> ThirdParty:
        third_party = await self.get(third_party_id)
        third_party.mark_deleted()
        return await self._commit(third_party)

    async def restore(self, third_party_id: int) -> ThirdParty:
        third_party = await self.get(third_party_id, include_deleted=True)

        if not third_party.is_deleted:
            raise ThirdPartyNotDeleted(third_party_id)

        third_party.restore()
        return await self._commit(third_party)


    async def _check_places(self, third_party: ThirdParty) -> None:
        await self._check_place(
            country_id=third_party.country_id,
            department_id=third_party.department_id,
            city_id=third_party.city_id,
            label="address",
        )
        await self._check_place(
            country_id=third_party.birth_country_id,
            department_id=third_party.birth_department_id,
            city_id=third_party.birth_city_id,
            label="birthplace",
        )

    async def _check_place(
        self,
        *,
        country_id: int | None,
        department_id: int | None,
        city_id: int | None,
        label: str,
    ) -> None:
        if city_id is not None and department_id is None:
            raise InconsistentPlace(f"The {label} city needs its department")
        if department_id is not None and country_id is None:
            raise InconsistentPlace(f"The {label} department needs its country")

        if department_id is not None:
            department = await self._session.get(Department, department_id)
            if department is None or department.country_id != country_id:
                raise InconsistentPlace(
                    f"The {label} department does not belong to that country"
                )

        if city_id is not None:
            city = await self._session.get(City, city_id)
            if city is None or city.department_id != department_id:
                raise InconsistentPlace(
                    f"The {label} city does not belong to that department"
                )

    async def _commit(self, third_party: ThirdParty) -> ThirdParty:
        await self._session.commit()
        await self._session.refresh(third_party)
        return third_party

    async def _find(
        self, third_party_id: int, *, include_deleted: bool
    ) -> ThirdParty | None:
        result = await self._session.execute(
            self._visible(include_deleted).where(ThirdParty.id == third_party_id)
        )
        return result.scalar_one_or_none()

    async def _find_by_document(
        self, document_type: DocumentType, document_number: str
    ) -> ThirdParty | None:
        result = await self._session.execute(
            select(ThirdParty).where(
                ThirdParty.document_type == document_type,
                ThirdParty.document_number == document_number,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _visible(include_deleted: bool) -> Select[tuple[ThirdParty]]:
        query = select(ThirdParty)
        return (
            query if include_deleted else query.where(ThirdParty.deleted_at.is_(None))
        )


def _build(payload: NaturalPersonCreate | LegalEntityCreate) -> ThirdParty:
    fields = payload.model_dump(exclude={"person_type"})

    if isinstance(payload, LegalEntityCreate):
        return ThirdParty.legal(**fields)
    return ThirdParty.natural(**fields)


def _copy_onto(target: ThirdParty, source: ThirdParty) -> None:
    for column in ThirdParty.__mapper__.columns:
        if column.key not in _KEEP_ON_REVIVE:
            setattr(target, column.key, getattr(source, column.key))


def _renormalize_document(third_party: ThirdParty, *, given_check_digit: bool) -> None:
    third_party.document_number = normalize_document(
        third_party.document_number, third_party.document_type
    )

    if not requires_check_digit(third_party.document_type):
        third_party.check_digit = None
        return

    if given_check_digit and third_party.check_digit is not None:
        validate_check_digit(third_party.document_number, third_party.check_digit)
        return

    third_party.check_digit = compute_check_digit(third_party.document_number)


def _matching(search: str) -> ColumnElement[bool]:
    pattern = f"%{search.strip()}%"
    return or_(
        ThirdParty.document_number.like(pattern),
        ThirdParty.first_name.ilike(pattern),
        ThirdParty.middle_name.ilike(pattern),
        ThirdParty.first_surname.ilike(pattern),
        ThirdParty.second_surname.ilike(pattern),
        ThirdParty.legal_name.ilike(pattern),
        ThirdParty.trade_name.ilike(pattern),
    )
