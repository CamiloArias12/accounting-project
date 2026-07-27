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

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    COMPANY_NIT: str = "900000000-5"
    COMPANY_LEGAL_NAME: str = "Mi Empresa S.A.S."
    COMPANY_ADDRESS: str | None = None
    COMPANY_PHONE: str | None = None
    COMPANY_EMAIL: str | None = None

    UVT_SOURCE: Literal["http", "simulated"] = "http"
    UVT_SOURCE_URL: str = "https://www.gerencie.com/uvt.html"
    UVT_SOURCE_TIMEOUT_SECONDS: float = 10.0

    UVT_SOURCE_FAILURE_RATE: float = 0.0
    UVT_SOURCE_LATENCY_SECONDS: float = 0.0

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "accounting"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    CACHE_TTL_SECONDS: int = 300

    JWT_SECRET: str = "local-development-secret-not-for-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 60

    MIN_SECRET_BYTES: ClassVar[int] = 32

    @model_validator(mode="after")
    def secret_must_be_strong_outside_local(self) -> "Settings":
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
