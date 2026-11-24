from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_version: str = "0.1.6"
    log_level: str = "INFO"
    session_ttl_seconds: int = 3600
    casdoor_client_id: str = ""
    casdoor_client_secret: str = ""
    casdoor_issuer: str = ""
    casdoor_internal_issuer: str = ""
    casdoor_redirect_uri: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
