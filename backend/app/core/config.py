from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Accept Render/Railway postgres URLs and SQLAlchemy's psycopg driver form."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    port: int | None = None
    database_url: str = "postgresql+psycopg://skilllens:skilllens@localhost:5432/skilllens"
    test_database_url: str = (
        "postgresql+psycopg://skilllens:skilllens@localhost:5432/skilllens_test"
    )

    jwt_secret_key: str = "dev-only-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    access_cookie_name: str = "skilllens_access_token"
    refresh_cookie_name: str = "skilllens_refresh_token"
    cookie_samesite: str = "lax"
    cookie_path: str = "/"

    cors_origins: str = ""

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def _normalize_db_urls(cls, value: object) -> object:
        if isinstance(value, str) and value:
            return normalize_database_url(value)
        return value

    @property
    def listen_port(self) -> int:
        return self.port if self.port is not None else self.backend_port

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
