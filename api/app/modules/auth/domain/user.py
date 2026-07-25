from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    """An account holder of the system, not an accounting account."""

    id: int | None
    email: str
    hashed_password: str
    full_name: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def register(cls, *, email: str, hashed_password: str, full_name: str) -> User:
        return cls(
            id=None,
            email=email.strip().lower(),
            hashed_password=hashed_password,
            full_name=full_name.strip(),
        )
