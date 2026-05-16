from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRETS = frozenset(
    {
        "CHANGE_ME_ACCESS_SECRET_32_CHARS_MIN",
        "CHANGE_ME_REFRESH_SECRET_32_CHARS_MIN",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    REDIS_URL: str
    ACCESS_TOKEN_SECRET: str
    REFRESH_TOKEN_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_ENV: str = "development"
    AUTO_CREATE_TABLES: bool = True
    CORS_ORIGINS: str = (
        "http://localhost:8000,http://127.0.0.1:8000," "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("ACCESS_TOKEN_SECRET", "REFRESH_TOKEN_SECRET")
    @classmethod
    def secrets_must_be_long_enough(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT secrets must be at least 32 characters")
        return value

    @model_validator(mode="after")
    def reject_placeholder_secrets_in_production(self) -> Self:
        if self.APP_ENV.lower() == "production" and (
            self.ACCESS_TOKEN_SECRET in _PLACEHOLDER_SECRETS
            or self.REFRESH_TOKEN_SECRET in _PLACEHOLDER_SECRETS
            or self.ACCESS_TOKEN_SECRET == self.REFRESH_TOKEN_SECRET
        ):
            raise ValueError(
                "Production requires unique, non-placeholder ACCESS_TOKEN_SECRET "
                "and REFRESH_TOKEN_SECRET values"
            )
        return self


settings = Settings()
