from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Who signs in. Not a third party, and not an accounting account.

    No link to `third_parties` on purpose: a user needs an email and a
    password, a third party needs a document, a check digit and a tax regime.
    The person who happens to be both is rare enough that a foreign key would
    only add a column nobody fills.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
