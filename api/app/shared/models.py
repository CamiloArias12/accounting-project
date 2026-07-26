"""Registry of every table, imported by Alembic to populate the metadata.

A module's tables are invisible to autogenerate until they are listed here.
"""

from app.modules.accounts.models import Account
from app.modules.auth.models import User
from app.modules.locations.models import City, Country, Department
from app.modules.third_parties.models import ThirdParty
from app.shared.database import Base

__all__ = [
    "Account",
    "Base",
    "City",
    "Country",
    "Department",
    "ThirdParty",
    "User",
]
