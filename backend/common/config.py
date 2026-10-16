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

    cors_allowed_origins: str = "http://localhost:3000"

    sentiment_negative_threshold: float = 0.85
    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    bangla_model_id: str = "sm-khalil/banglabert-sentigold"
    hf_token: str = ""
    hf_home: str = "/app/.cache/huggingface"
    sentiment_engine: str = "auto"
    confidence_threshold: float = 0.65
    max_retries: int = 3
    retry_backoff_base_seconds: int = 10

    slack_webhook_url: str = ""

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
