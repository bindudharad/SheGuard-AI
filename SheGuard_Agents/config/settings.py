"""SheGuard Agents Configuration"""
import os
from typing import Optional
from pydantic import BaseModel
from functools import lru_cache

class BackendSettings(BaseModel):
    base_url: str = os.getenv("SHEGUARD_BACKEND_URL", "http://192.168.1.3:8000")
    api_prefix: str = "/api/v1"
    timeout_seconds: int = 30
    service_token: Optional[str] = os.getenv("SHEGUARD_SERVICE_TOKEN")

    @property
    def incidents_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/incidents/create"

    @property
    def emergency_start_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/emergency/start"

    @property
    def emergency_session_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/emergency/session"

    @property
    def locations_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/location/update"

    @property
    def tracking_start_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/tracking/start"

    @property
    def tracking_update_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/tracking/update"

    @property
    def cameras_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/camera/list"

    @property
    def evidence_upload_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}/evidence/upload"

    @property
    def realtime_ws_url(self) -> str:
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}/ws/live"

class AISettings(BaseModel):
    base_url: str = os.getenv("SHEGUARD_AI_URL", "http://127.0.0.1:8001")
    analysis_endpoint: str = "/analyze"
    timeout_seconds: int = 60

    @property
    def analyze_url(self) -> str:
        return f"{self.base_url}{self.analysis_endpoint}"

class DashboardSettings(BaseModel):
    base_url: str = os.getenv("SHEGUARD_DASHBOARD_URL", "http://127.0.0.1:5173")
    ws_url: str = os.getenv("SHEGUARD_DASHBOARD_WS", "ws://127.0.0.1:8000/ws/live")

class AgentSettings(BaseModel):
    help_timeout_seconds: int = 5
    tracking_stale_threshold_seconds: int = 60
    max_active_emergencies_per_user: int = 1
    max_cctv_distance_meters: float = 500.0
    max_cctv_cameras_per_emergency: int = 3
    weight_sos_vs_help: float = 2.0
    weight_ai_confidence: float = 1.5
    weight_cctv_detection: float = 1.2
    weight_tracking_active: float = 1.0
    weight_repeated_alerts: float = 1.3
    weight_duration: float = 0.5
    max_retries: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 30.0
    idempotency_ttl_seconds: int = 3600
    event_queue_max_size: int = 10000
    event_processing_batch_size: int = 100
    event_processing_interval_ms: int = 100

class DatabaseSettings(BaseModel):
    url: str = os.getenv("DATABASE_URL", "sqlite:///./sheguard.db")

class LoggingSettings(BaseModel):
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = os.getenv("LOG_FILE")

class Settings(BaseModel):
    backend: BackendSettings = BackendSettings()
    ai: AISettings = AISettings()
    dashboard: DashboardSettings = DashboardSettings()
    agent: AgentSettings = AgentSettings()
    database: DatabaseSettings = DatabaseSettings()
    logging: LoggingSettings = LoggingSettings()
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
