from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    """A user of the system, not an accounting account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
