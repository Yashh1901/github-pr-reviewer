# api/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    github_webhook_secret: str = ""
    github_token: str = ""
    gemini_api_key: str = ""
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    redis_url: str = "redis://localhost:6379"
    app_env: str = "development"
    app_port: int = 8000

    class ConfigDict:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()