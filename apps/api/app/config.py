from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SimuLearn"
    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    default_language: str = "fr"

    database_url: str = "sqlite+pysqlite:///./simulearn-dev.db"

    keycloak_url: str = ""
    keycloak_realm: str = ""
    keycloak_client_id: str = ""
    # Dev-only: accept "Bearer dev:<email>" tokens. Never enable in production.
    auth_dev_mode: bool = False

    openai_api_key: str = ""
    openai_live_model: str = "gpt-live-1"
    openai_live_voice: str = "sillage"
    openai_base_url: str = "https://api.openai.com"
    voice_provider: str = "openai_live"  # openai_live | mock

    anthropic_api_key: str = ""
    anthropic_evaluation_model: str = "claude-sonnet-5-5"
    anthropic_scenario_model: str = "claude-sonnet-5-5"
    evaluation_provider: str = "claude"  # claude | mock

    simulation_max_duration_minutes: int = 15
    simulation_max_concurrent_per_user: int = 1
    enable_claude_live_delegation: bool = False
    enable_audio_recording: bool = False

    enable_usage_tracking: bool = True
    max_session_estimated_cost_usd: float = 2.00
    org_monthly_session_quota: int = 500
    pricing_config_path: str = "config/pricing.json"

    transcript_retention_days: int = 90

    valkey_url: str = ""

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url.rstrip('/')}/realms/{self.keycloak_realm}"

    def missing_for_voice(self) -> list[str]:
        return [] if self.openai_api_key else ["OPENAI_API_KEY"]

    def missing_for_evaluation(self) -> list[str]:
        return [] if self.anthropic_api_key else ["ANTHROPIC_API_KEY"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
