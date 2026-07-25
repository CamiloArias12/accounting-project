from app.shared.errors import DomainError


class AuthError(DomainError):
    """Base class for authentication errors."""


class InvalidCredentials(AuthError):
    def __init__(self) -> None:
        # Deliberately vague: saying which half was wrong tells an attacker
        # which emails exist.
        super().__init__("Incorrect email or password")


class InactiveUser(AuthError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User {email} is not active")
        self.email = email


class EmailAlreadyRegistered(AuthError):
    def __init__(self, email: str) -> None:
        super().__init__(f"Email {email} is already registered")
        self.email = email


class InvalidToken(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired token")
