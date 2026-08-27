from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML is optional in the MVP runtime
    yaml = None


ROOT_DIR = Path(__file__).resolve().parents[2]


DEFAULT_CONFIG: dict[str, Any] = {
    "runtime": {
        "device": "auto",
        "frame_skip": 1,
        "alert_cooldown_seconds": 30,
        "incident_post_seconds": 30,
    },
    "stability": {
        "confidence_window": 8,
        "ema_alpha": 0.35,
        "trigger_confidence": 0.72,
        "clear_confidence": 0.48,
        "persistence_frames": 3,
        "inactivity_seconds": 8,
        "inactivity_motion_threshold": 9.0,
    },
    "threat": {
        "night_start_hour": 20,
        "night_end_hour": 5,
        "critical_threshold": 9,
        "high_threshold": 7,
        "medium_threshold": 4,
    },
    "cloud_ai": {
        "enabled": True,
        "min_confidence": 0.78,
        "min_threat_score": 5,
        "providers": ["groq", "gemini", "openrouter"],
        "timeout_seconds": 15,
    },
    "evidence": {
        "image_dir": "evidence/images",
        "video_dir": "evidence/videos",
        "metadata_dir": "evidence/metadata",
        "pre_event_seconds": 30,
        "post_event_seconds": 30,
        "fps": 20.0,
        "retention_days": 30,
    },
    "security": {
        "jwt_secret_env": "SHEGUARD_JWT_SECRET",
        "jwt_expire_minutes": 1440,
    },
    "logging": {
        "dir": "logs",
        "level": "INFO",
    },
    "cameras": [],
}


@dataclass
class SheGuardConfig:
    data: dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG.copy())

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path | None = None) -> SheGuardConfig:
    config_path = Path(path or os.environ.get("SHEGUARD_CONFIG", ROOT_DIR / "config.yaml"))
    if not config_path.is_absolute():
        config_path = ROOT_DIR / config_path

    data = DEFAULT_CONFIG
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        if config_path.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
            loaded = yaml.safe_load(raw) or {}
        else:
            loaded = json.loads(raw)
        data = deep_merge(DEFAULT_CONFIG, loaded)
    return SheGuardConfig(data=data)


settings = load_config()

