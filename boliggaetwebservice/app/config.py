from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    sample_source_enabled: bool = False


@cache
def get_settings() -> Settings:
    return Settings()
