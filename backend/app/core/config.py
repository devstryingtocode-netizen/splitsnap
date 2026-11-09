from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    jwt_secret_key: str = Field(default="", repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    password_hashing_algorithm: str = "argon2"
    database_url: str = "sqlite:///./splitsnap.db"
    ai_api_key: str | None = Field(default=None, repr=False)
    ai_model: str = ""
    paypal_client_id: str | None = Field(default=None, repr=False)
    paypal_client_secret: str | None = Field(default=None, repr=False)
    paypal_base_url: AnyHttpUrl = "https://api-m.sandbox.paypal.com"
    frontend_url: AnyHttpUrl = "http://localhost:3000"

    @field_validator("jwt_algorithm")
    @classmethod
    def require_hs256(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256.")
        return value

    @field_validator("password_hashing_algorithm")
    @classmethod
    def require_argon2(cls, value: str) -> str:
        if value.lower() != "argon2":
            raise ValueError("PASSWORD_HASHING_ALGORITHM must be argon2.")
        return "argon2"

    def validate_production_security(self) -> None:
        if (
            self.app_env.lower() in {"production", "prod"}
            and len(self.jwt_secret_key.strip()) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY must contain at least 32 characters in production."
            )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
