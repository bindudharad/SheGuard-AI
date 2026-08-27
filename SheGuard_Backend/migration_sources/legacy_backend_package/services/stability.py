from __future__ import annotations

import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


DANGER_LABELS = {"fall", "attack", "fight", "unconscious", "dragging", "weapon", "forced_movement"}


@dataclass
class SignalState:
    label_history: deque = field(default_factory=lambda: deque(maxlen=8))
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=8))
    ema: dict[str, float] = field(default_factory=dict)
    active_label: str = "normal"
    active_since: float | None = None
    last_alert_at: dict[str, float] = field(default_factory=dict)


@dataclass
class InactivityState:
    still_since: float | None = None
    last_motion_score: float = 0.0
    posture_stable_seconds: float = 0.0
    score: float = 0.0


class TemporalStabilityEngine:
    def __init__(
        self,
        window: int = 8,
        ema_alpha: float = 0.35,
        trigger_confidence: float = 0.72,
        clear_confidence: float = 0.48,
        persistence_frames: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.window = window
        self.ema_alpha = ema_alpha
        self.trigger_confidence = trigger_confidence
        self.clear_confidence = clear_confidence
        self.persistence_frames = persistence_frames
        self.cooldown_seconds = cooldown_seconds
        self.states: dict[str, SignalState] = defaultdict(self._new_state)

    def _new_state(self) -> SignalState:
        return SignalState(
            label_history=deque(maxlen=self.window),
            confidence_history=deque(maxlen=self.window),
        )

    def smooth(self, entity_id: str, label: str, confidence: float, probabilities: dict[str, float] | None = None) -> dict[str, Any]:
        now = time.time()
        state = self.states[entity_id]
        probabilities = dict(probabilities or {label: confidence})
        if label not in probabilities:
            probabilities[label] = confidence

        state.label_history.append(label)
        state.confidence_history.append(float(confidence))
        all_labels = set(probabilities) | set(state.ema) | {label, state.active_label, "normal"}
        for item in all_labels:
            observed = float(probabilities.get(item, 0.0))
            previous = state.ema.get(item, observed)
            state.ema[item] = self.ema_alpha * observed + (1.0 - self.ema_alpha) * previous

        averaged_confidence = sum(state.confidence_history) / max(len(state.confidence_history), 1)
        majority_label, majority_count = Counter(state.label_history).most_common(1)[0]
        ema_label = max(state.ema, key=state.ema.get)
        ema_confidence = float(state.ema.get(ema_label, 0.0))

        final_label = state.active_label
        final_confidence = float(state.ema.get(final_label, 0.0))
        if state.active_label != "normal" and state.ema.get(state.active_label, 0.0) >= self.clear_confidence:
            final_label = state.active_label
        elif majority_count >= self.persistence_frames and ema_confidence >= self.trigger_confidence:
            final_label = ema_label
            state.active_label = final_label
            state.active_since = now
        elif state.active_label != "normal" and state.ema.get(state.active_label, 0.0) < self.clear_confidence:
            final_label = "normal"
            state.active_label = "normal"
            state.active_since = None
        else:
            final_label = "normal"

        final_confidence = float(state.ema.get(final_label, averaged_confidence if final_label == label else 0.0))
        return {
            "label": final_label,
            "confidence": max(0.0, min(final_confidence, 1.0)),
            "raw_label": label,
            "raw_confidence": confidence,
            "temporal_confidence": max(0.0, min(ema_confidence, 1.0)),
            "majority_label": majority_label,
            "persistence": majority_count,
            "active_for_seconds": 0.0 if state.active_since is None else now - state.active_since,
            "probabilities": dict(state.ema),
        }

    def should_alert(self, entity_id: str, event_type: str, now: float | None = None) -> bool:
        now = now or time.time()
        state = self.states[entity_id]
        last = state.last_alert_at.get(event_type, 0.0)
        if now - last < self.cooldown_seconds:
            return False
        state.last_alert_at[event_type] = now
        return True


class InactivityAnalyzer:
    def __init__(self, inactivity_seconds: float = 8.0, motion_threshold: float = 9.0) -> None:
        self.inactivity_seconds = inactivity_seconds
        self.motion_threshold = motion_threshold
        self.states: dict[int, InactivityState] = defaultdict(InactivityState)

    def update(self, track: Any, now: float) -> dict[str, float | bool]:
        state = self.states[int(track.track_id)]
        motion_score = float(getattr(track, "speed", 0.0) or 0.0)
        if motion_score > self.motion_threshold:
            state.still_since = now
            state.posture_stable_seconds = 0.0
        else:
            if state.still_since is None:
                state.still_since = now
            state.posture_stable_seconds = now - state.still_since
        state.last_motion_score = motion_score
        state.score = min(1.0, state.posture_stable_seconds / max(self.inactivity_seconds, 1.0))
        return {
            "motion_score": motion_score,
            "inactivity_score": state.score,
            "inactive_seconds": state.posture_stable_seconds,
            "is_inactive": state.score >= 1.0,
        }


def fuse_signals(
    base_confidence: float,
    temporal_confidence: float = 0.0,
    pose_confidence: float = 1.0,
    motion_score: float = 0.0,
    inactivity_score: float = 0.0,
    label: str = "normal",
) -> float:
    motion_factor = min(float(motion_score) / 60.0, 1.0)
    if label in {"fall", "unconscious"}:
        fused = 0.40 * base_confidence + 0.30 * temporal_confidence + 0.15 * pose_confidence + 0.15 * inactivity_score
    elif label in {"attack", "fight", "dragging", "forced_movement"}:
        fused = 0.38 * base_confidence + 0.34 * temporal_confidence + 0.14 * pose_confidence + 0.14 * motion_factor
    else:
        fused = 0.55 * base_confidence + 0.30 * temporal_confidence + 0.15 * pose_confidence
    return max(0.0, min(float(fused), 1.0))

