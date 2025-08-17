from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str

    # API Configuration
    api_key: str
    rate_limit_per_minute: int = 60

    # OpenAI
    # openai_api_key: str

    # App Configuration
    log_level: str = "INFO"
    app_env: str = "development"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
