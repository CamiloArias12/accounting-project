from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import PostgresDsn, RedisDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Accounting API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS: allowed origins
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # The company whose books these are.
    #
    # Configuration, not a table: this deployment keeps one set of books, so the
    # company is the same on every voucher and storing it per row would be a
    # column with one value in it. A voucher shows it; nothing selects it.
    COMPANY_NIT: str = "900000000-0"
    COMPANY_LEGAL_NAME: str = "Mi Empresa S.A.S."
    COMPANY_ADDRESS: str | None = None
    COMPANY_PHONE: str | None = None
    COMPANY_EMAIL: str | None = None

    # Postgres
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "accounting"

    # Connection pool. Total connections per replica is POOL_SIZE +
    # MAX_OVERFLOW; multiply by the replica count and keep it under Postgres
    # `max_connections` (100 by default).
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    #: How long a cached chart of accounts stays valid if nothing invalidates it.
    CACHE_TTL_SECONDS: int = 300

    # Auth. The default is a throwaway for local runs; production refuses it.
    JWT_SECRET: str = "local-development-secret-not-for-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 60

    #: HMAC-SHA256 wants at least this much key material (RFC 7518 §3.2).
    MIN_SECRET_BYTES: ClassVar[int] = 32

    @model_validator(mode="after")
    def secret_must_be_strong_outside_local(self) -> "Settings":
        """Fails at startup rather than shipping a guessable signing key."""
        if self.ENVIRONMENT == "local":
            return self

        if Settings.model_fields["JWT_SECRET"].default == self.JWT_SECRET:
            raise ValueError(
                "JWT_SECRET is still the development default; set a real one "
                f"in {self.ENVIRONMENT}"
            )
        if len(self.JWT_SECRET.encode()) < self.MIN_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET must be at least {self.MIN_SECRET_BYTES} bytes; "
                "generate one with `openssl rand -hex 32`"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> RedisDsn:
        return RedisDsn.build(
            scheme="redis",
            password=self.REDIS_PASSWORD,
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=str(self.REDIS_DB),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
