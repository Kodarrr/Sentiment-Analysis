from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=("settings_",)
    )

    app_name: str = "Smart Customer Feedback & Sentiment Engine"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://feedback:feedback@localhost:5432/feedback"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    rate_limit_per_minute: int = 30

    sentiment_negative_threshold: float = 0.85
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    max_retries: int = 3

    slack_webhook_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
