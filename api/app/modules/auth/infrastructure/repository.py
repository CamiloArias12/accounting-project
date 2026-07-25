from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.user import User
from app.modules.auth.infrastructure.orm import UserRow, to_entity, to_row


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.email == email)
        )
        row = result.scalar_one_or_none()
        return to_entity(row) if row is not None else None

    async def get_by_id(self, user_id: int) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return to_entity(row) if row is not None else None

    async def add(self, user: User) -> User:
        row = to_row(user)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return to_entity(row)
