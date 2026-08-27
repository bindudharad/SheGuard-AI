"""SheGuard Agents - emergency orchestration layer.

Coordinates App -> Backend -> AI/CCTV -> Dashboard for SOS/HELP emergencies.
"""
from emergency.config import EmergencyConfig, get_emergency_config
from emergency.models import SessionContext, StandardEvent

__all__ = ["EmergencyConfig", "get_emergency_config", "SessionContext", "StandardEvent"]
