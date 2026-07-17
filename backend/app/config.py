from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JUKEBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://jukebox:jukebox@localhost:5432/jukebox"
    cors_allow_origins: str = "http://localhost:8080,http://localhost:4200"
    operator_username: str = ""
    operator_password: str = ""
    session_secret: str = "dev-only-change-me-in-production"
    cookie_secure: bool = False
    frame_ancestors: str = "'none'"


@lru_cache
def get_settings() -> Settings:
    return Settings()
