from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment variables / .env.

    DEMO_MODE governs whether the API falls back to deterministic mock
    evaluations when no model credentials are configured. It defaults to
    True so the service runs without any secrets.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    demo_mode: bool = True
    allowed_origins: str = "http://localhost:3000"
    max_request_bytes: int = 200_000
    similarity_flag_threshold: float = 0.85

    huggingface_api_token: str | None = None
    openai_api_key: str | None = None

    rate_limit_per_minute: int = 30

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
