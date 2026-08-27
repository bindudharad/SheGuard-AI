from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DetectorSignal:
    name: str
    score: float
    message: str


class WeaponDetectionModule:
    def analyze(self, frame: Any, tracks: list[Any]) -> DetectorSignal:
        return DetectorSignal("weapon", 0.0, "Weapon detector placeholder ready; no weapon model configured.")


class DraggingDetectionModule:
    def analyze(self, tracks: list[Any]) -> DetectorSignal:
        if len(tracks) < 2:
            return DetectorSignal("dragging", 0.0, "Insufficient tracks for dragging analysis.")
        speeds = [float(getattr(track, "speed", 0.0) or 0.0) for track in tracks]
        slow = min(speeds) < 6.0
        fast = max(speeds) > 24.0
        score = 0.65 if slow and fast else 0.0
        return DetectorSignal("dragging", score, "Possible forced movement pattern." if score else "No dragging pattern.")


class RunningAnomalyModule:
    def analyze(self, tracks: list[Any]) -> DetectorSignal:
        if not tracks:
            return DetectorSignal("running_anomaly", 0.0, "No tracks.")
        max_speed = max(float(getattr(track, "speed", 0.0) or 0.0) for track in tracks)
        score = min(max_speed / 70.0, 1.0)
        return DetectorSignal("running_anomaly", score if score >= 0.6 else 0.0, "Abnormal acceleration." if score >= 0.6 else "Motion normal.")


class CrowdAggressionModule:
    def analyze(self, tracks: list[Any]) -> DetectorSignal:
        if len(tracks) >= 4:
            avg_speed = sum(float(getattr(track, "speed", 0.0) or 0.0) for track in tracks) / len(tracks)
            score = min(avg_speed / 50.0, 1.0)
            return DetectorSignal("crowd_aggression", score if score >= 0.55 else 0.0, "Crowd aggression architecture signal.")
        return DetectorSignal("crowd_aggression", 0.0, "Crowd module ready; not enough people.")


class ForcedMovementAnalyzer:
    def __init__(self) -> None:
        self.dragging = DraggingDetectionModule()
        self.running = RunningAnomalyModule()

    def analyze(self, tracks: list[Any]) -> dict[str, float]:
        dragging = self.dragging.analyze(tracks)
        running = self.running.analyze(tracks)
        suspicion = min(1.0, dragging.score * 0.55 + running.score * 0.35)
        return {
            "dragging_score": dragging.score,
            "route_change_score": 0.0,
            "resistance_score": dragging.score,
            "kidnap_suspicion_score": suspicion,
        }

