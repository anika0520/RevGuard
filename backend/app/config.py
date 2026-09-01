"""Central configuration. Business rules live here, not scattered as magic numbers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HealthWeights(BaseModel):
    """Weights must sum to 100. Exposed via /api/settings so they can be tuned live."""

    pacing: float = 40.0
    fill_rate: float = 25.0
    error_rate: float = 20.0
    supply_signal: float = 10.0
    data_quality: float = 5.0

    def total(self) -> float:
        return self.pacing + self.fill_rate + self.error_rate + self.supply_signal + self.data_quality


class HealthBands(BaseModel):
    critical_max: float = 30.0
    high_risk_max: float = 50.0
    warning_max: float = 70.0


class AnomalyThresholds(BaseModel):
    z_score_abs: float = 2.5
    pacing_gap_pts: float = -15.0
    fill_deviation_pct: float = -20.0
    error_deviation_pct: float = 100.0
    overdelivery_pacing_pct: float = 130.0
    min_sustained_windows: int = 2
    min_agreeing_signals: int = 2


class RevenueRiskFactors(BaseModel):
    conservative_multiplier: float = 0.65
    worst_case_multiplier: float = 1.35


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Xperi RevGuard"
    version: str = "1.0.0"

    demo_mode: bool = True
    dry_run: bool = True
    random_seed: int = 42

    llm_provider: str = "deterministic"  # deterministic | openai | gemini
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    slack_webhook_url: str = ""
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = "REV"

    campaign_count: int = 247
    history_days: int = 30
    future_hours: int = 24

    current_window_hours: int = 6
    baseline_window_days: int = 7

    data_freshness_sla_minutes: int = 90

    health_weights: HealthWeights = Field(default_factory=HealthWeights)
    health_bands: HealthBands = Field(default_factory=HealthBands)
    anomaly: AnomalyThresholds = Field(default_factory=AnomalyThresholds)
    revenue_risk: RevenueRiskFactors = Field(default_factory=RevenueRiskFactors)

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sim_start() -> datetime:
    """Anchor the simulated world to today at 08:00 UTC so the demo always feels current."""
    today = datetime.now(timezone.utc).replace(hour=8, minute=14, second=0, microsecond=0)
    return today


def world_origin() -> datetime:
    return sim_start() - timedelta(days=get_settings().history_days)
