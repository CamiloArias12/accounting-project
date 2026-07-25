"""Registry of every persistence model.

Alembic imports this to populate `Base.metadata`. A module's tables are
invisible to autogenerate until they are listed here.
"""

from app.modules.accounts.infrastructure.orm import AccountRow
from app.modules.auth.infrastructure.orm import UserRow
from app.shared.database import Base

__all__ = ["AccountRow", "Base", "UserRow"]
