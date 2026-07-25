"""ORM models.

They must be imported here so Alembic registers them in `Base.metadata`
when autogenerating migrations.
"""

from app.db.base import Base
from app.models.account import Account

__all__ = ["Account", "Base"]
