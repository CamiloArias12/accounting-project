"""Account business errors.

They know nothing about HTTP; the web adapter maps them to status codes.
"""

from app.shared.errors import DomainError


class AccountError(DomainError):
    """Base class for account errors."""


class AccountNotFound(AccountError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Account {code} does not exist")
        self.code = code


class AccountAlreadyExists(AccountError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Account {code} already exists")
        self.code = code


class ParentAccountMissing(AccountError):
    def __init__(self, code: str, parent_code: str) -> None:
        super().__init__(
            f"Account {code} requires its parent {parent_code} to exist first"
        )
        self.code = code
        self.parent_code = parent_code


class AccountHasChildren(AccountError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Account {code} cannot be deleted while it has children")
        self.code = code


class AccountNotDeleted(AccountError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Account {code} is not deleted, so it cannot be restored")
        self.code = code


class ParentAccountDeleted(AccountError):
    def __init__(self, code: str, parent_code: str) -> None:
        super().__init__(
            f"Account {code} cannot be restored while its parent {parent_code} "
            "is deleted"
        )
        self.code = code
        self.parent_code = parent_code
