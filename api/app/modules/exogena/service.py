from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import Account
from app.modules.exogena.errors import GenerationNotFound, ThresholdNeedsUvt
from app.modules.exogena.models import ExogenaGeneration
from app.modules.exogena.report import Filer, Report
from app.modules.exogena.report import Row as ReportRow
from app.modules.exogena.schemas import GenerateRequest
from app.modules.third_parties.documents import dian_code
from app.modules.third_parties.models import ThirdParty
from app.modules.uvt.errors import UvtValueNotFound
from app.modules.uvt.service import UvtService
from app.modules.vouchers.models import Voucher, VoucherLine
from app.modules.vouchers.posting import ZERO, VoucherStatus

logger = logging.getLogger("app.exogena")


class ExogenaService:
    """Building the exógena report out of what is in the books."""
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate(
        self,
        payload: GenerateRequest,
        *,
        nit: str,
        legal_name: str,
        user_id: int | None = None,
    ) -> ExogenaGeneration:
        filer = Filer.of(nit=nit, legal_name=legal_name, year=payload.year)
        threshold = await self._threshold_in_pesos(payload)

        movements = await self._movements(payload.year)
        report, excluded = _assemble(filer, movements, threshold.pesos)

        generation = ExogenaGeneration(
            year=payload.year,
            threshold_uvt=payload.threshold_uvt,
            uvt_value=threshold.uvt,
            threshold_pesos=threshold.pesos,
            filer_nit=filer.nit,
            filer_name=filer.legal_name,
            record_count=report.totals.count,
            total_gross=report.totals.gross,
            total_withheld=report.totals.withheld,
            excluded_count=len(excluded),
            xml=report.to_xml(),
            generated_at=_now(),
            generated_by_user_id=user_id,
        )
        self._session.add(generation)
        await self._session.commit()
        await self._session.refresh(generation)

        for name, document, total in excluded:
            logger.info(
                "excluded from exógena: below the threshold",
                extra={
                    "generation_id": generation.id,
                    "year": payload.year,
                    "third_party": name,
                    "document": document,
                    "total": str(total),
                    "threshold": str(threshold.pesos),
                },
            )

        return generation

    async def history(self, *, limit: int = 50) -> Sequence[ExogenaGeneration]:
        result = await self._session.execute(
            select(ExogenaGeneration).order_by(ExogenaGeneration.id.desc()).limit(limit)
        )
        return result.scalars().all()

    async def get(self, generation_id: int) -> ExogenaGeneration:
        generation = await self._session.get(ExogenaGeneration, generation_id)
        if generation is None:
            raise GenerationNotFound(generation_id)
        return generation


    async def _threshold_in_pesos(self, payload: GenerateRequest) -> _Threshold:
        if payload.threshold_uvt == ZERO:
            return _Threshold(uvt=None, pesos=ZERO)

        try:
            uvt = await UvtService(self._session).value_for(payload.year)
        except UvtValueNotFound as exc:
            raise ThresholdNeedsUvt(payload.year) from exc

        return _Threshold(uvt=uvt, pesos=uvt * payload.threshold_uvt)

    async def _movements(self, year: int) -> Sequence[Row[Any]]:
        return (
            await self._session.execute(
                select(
                    ThirdParty.id,
                    ThirdParty.document_type,
                    ThirdParty.document_number,
                    ThirdParty.first_name,
                    ThirdParty.middle_name,
                    ThirdParty.first_surname,
                    ThirdParty.second_surname,
                    ThirdParty.legal_name,
                    Account.dian_concept,
                    Account.is_withholding,
                    func.sum(VoucherLine.debit - VoucherLine.credit).label("amount"),
                )
                .select_from(VoucherLine)
                .join(Voucher, Voucher.id == VoucherLine.voucher_id)
                .join(Account, Account.code == VoucherLine.account_code)
                .join(ThirdParty, ThirdParty.id == VoucherLine.third_party_id)
                .where(
                    Voucher.status == VoucherStatus.POSTED,
                    Voucher.period_year == year,
                    Account.dian_concept.is_not(None),
                )
                .group_by(
                    ThirdParty.id,
                    ThirdParty.document_type,
                    ThirdParty.document_number,
                    ThirdParty.first_name,
                    ThirdParty.middle_name,
                    ThirdParty.first_surname,
                    ThirdParty.second_surname,
                    ThirdParty.legal_name,
                    Account.dian_concept,
                    Account.is_withholding,
                )
                .order_by(ThirdParty.document_number, Account.dian_concept)
            )
        ).all()


class _Threshold:
    __slots__ = ("pesos", "uvt")

    def __init__(self, *, uvt: Decimal | None, pesos: Decimal) -> None:
        self.uvt = uvt
        self.pesos = pesos


def _assemble(
    filer: Filer,
    movements: Sequence[Row[Any]],
    threshold: Decimal,
) -> tuple[Report, list[tuple[str, str, Decimal]]]:
    buckets: dict[tuple[int, str], list[Decimal]] = {}
    names: dict[int, tuple[str, str, str]] = {}

    for row in movements:
        key = (row.id, row.dian_concept)
        amounts = buckets.setdefault(key, [ZERO, ZERO])
        amounts[1 if row.is_withholding else 0] += abs(row.amount or ZERO)
        names[row.id] = (
            dian_code(row.document_type),
            row.document_number,
            _display_name(row),
        )

    totals_by_party: dict[int, Decimal] = {}
    for (party, _), (gross, _withheld) in buckets.items():
        totals_by_party[party] = totals_by_party.get(party, ZERO) + gross

    report = Report(filer=filer)
    excluded: list[tuple[str, str, Decimal]] = []

    for party, total in totals_by_party.items():
        document_type, document_number, name = names[party]
        if threshold > ZERO and total <= threshold:
            excluded.append((name, document_number, total))

    included = {
        party
        for party, total in totals_by_party.items()
        if threshold == ZERO or total > threshold
    }

    for (party, concept), (gross, withheld) in buckets.items():
        if party not in included:
            continue
        document_type, document_number, name = names[party]
        report.rows.append(
            ReportRow(
                document_type=document_type,
                document_number=document_number,
                name=name,
                concept=concept,
                gross=gross,
                withheld=withheld,
            )
        )

    report.rows.sort(key=lambda row: (row.document_number, row.concept))
    return report, excluded


def _display_name(row: Row[Any]) -> str:
    if row.legal_name:
        return str(row.legal_name)

    parts = (
        row.first_name,
        row.middle_name,
        row.first_surname,
        row.second_surname,
    )
    return " ".join(str(part) for part in parts if part)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
