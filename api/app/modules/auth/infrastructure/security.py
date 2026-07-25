"""Concrete hashing and token adapters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.modules.auth.domain.errors import InvalidToken
from app.shared.config import settings


class Argon2PasswordHasher:
    """Argon2id, the current password-hashing recommendation."""

    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    def hash(self, plain: str) -> str:
        return self._hasher.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(plain, hashed)
        except Exception:
            # A malformed stored hash must read as "wrong password", never as a
            # 500 that tells the caller something about the account.
            return False


class JwtTokenIssuer:
    def __init__(
        self,
        secret: str = settings.JWT_SECRET,
        algorithm: str = settings.JWT_ALGORITHM,
        ttl_minutes: int = settings.ACCESS_TOKEN_TTL_MINUTES,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, subject: str) -> str:
        now = datetime.now(UTC)
        payload = {"sub": subject, "iat": now, "exp": now + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def subject_of(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidToken from exc

        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise InvalidToken
        return subject
