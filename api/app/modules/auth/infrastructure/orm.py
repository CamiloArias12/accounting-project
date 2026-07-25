from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.domain.user import User
from app.shared.database import Base, TimestampMixin


class UserRow(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)


def to_entity(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        full_name=row.full_name,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_row(user: User) -> UserRow:
    return UserRow(
        email=user.email,
        hashed_password=user.hashed_password,
        full_name=user.full_name,
        is_active=user.is_active,
    )
