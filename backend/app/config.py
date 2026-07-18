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
    allow_dev_queue_submit: bool = False
    allow_dev_participant_auth: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    participant_oauth_return_url: str = "http://localhost:4200/participar"
    youtube_api_keys: str = ""
    youtube_search_max_results: int = 10
    youtube_search_min_query_length: int = 2


def parse_youtube_api_keys(raw: str) -> list[str]:
    return [key.strip() for key in raw.split(",") if key.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
