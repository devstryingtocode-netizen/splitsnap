from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = Field(default="", repr=False)
    database_url: str = "sqlite:///./splitsnap.db"
    development_owner_id: str = ""
    ai_api_key: str | None = Field(default=None, repr=False)
    ai_model: str = ""
    paypal_client_id: str | None = Field(default=None, repr=False)
    paypal_client_secret: str | None = Field(default=None, repr=False)
    paypal_base_url: AnyHttpUrl = "https://api-m.sandbox.paypal.com"
    frontend_url: AnyHttpUrl = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
