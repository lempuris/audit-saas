from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "audit-api"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://audit:audit@localhost:5432/auditsaas"
    cors_origins: str = "http://localhost:3001"
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
