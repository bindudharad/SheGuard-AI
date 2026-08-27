"""
Threat Fusion Engine - unified risk scoring combining all signals.

Fuses:
- VISION (activity, interaction, temporal)
- FOLLOWING
- APPROACHING
- CHASING
- FLEEING
- CONFRONTATION
- AUDIO (keywords, distress)
- CONTEXT (location, time, environment)
- GRU (temporal classification)
- LOCATION (GPS, camera zone)
- TEMPORAL EVIDENCE (persistence, escalation)

Produces explainable risk score 0-100 with reasons.
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import math


@dataclass
class ThreatContribution:
    """Individual signal contribution to threat score"""
    source: str  # e.g., "vision", "following", "audio", "context"
    factor: str  # e.g., "activity:fall", "following", "distress"
    raw_score: float  # 0-100
    weight: float  # 0-1
    weighted_score: float  # raw * weight
    confidence: float  # 0-1
    evidence: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "factor": self.factor,
            "raw_score": round(self.raw_score, 1),
            "weight": round(self.weight, 2),
            "weighted_score": round(self.weighted_score, 1),
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
        }


@dataclass
class ThreatResult:
    """Final fused threat result"""
    risk_score: float  # 0-100
    risk_level: str    # SAFE, WARNING, HIGH, CRITICAL, EMERGENCY
    behaviors: List[str]
    reasons: List[str]
    contributions: List[ThreatContribution]
    confidence: float  # 0-1
    timestamp: str
    tracks: List[Dict[str, Any]]
    temporal_trend: str  # "escalating", "stable", "de-escalating"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "behaviors": self.behaviors,
            "reasons": self.reasons,
            "contributions": [c.to_dict() for c in self.contributions],
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
            "tracks": self.tracks,
            "temporal_trend": self.temporal_trend,
        }


class ThreatFusionEngine:
    """
    Unified Threat/Risk Engine with explainable scoring and temporal smoothing.
    
    Features:
    - Configurable weights per signal source
    - Explainable contributions
    - Temporal smoothing / hysteresis
    - Risk levels with configurable thresholds
    - No single detector can immediately declare emergency (except explicit rules)
    """
    
    def __init__(
        self,
        # Weights (sum should be ~1.0 for normalization)
        vision_weight: float = 0.25,
        following_weight: float = 0.20,
        approaching_weight: float = 0.10,
        chasing_weight: float = 0.15,
        fleeing_weight: float = 0.10,
        confrontation_weight: float = 0.10,
        audio_weight: float = 0.05,
        context_weight: float = 0.05,
        
        # Risk level thresholds (configurable)
        safe_max: float = 29.0,
        warning_max: float = 54.0,
        high_max: float = 74.0,
        critical_max: float = 89.0,
        emergency_min: float = 90.0,
        
        # Temporal smoothing
        smooth_factor: float = 0.7,  # Higher = more smoothing
        max_increase_per_frame: float = 15.0,  # Max jump per frame
        max_decrease_per_frame: float = 10.0,
        
        # Escalation detection
        escalation_window: int = 30,  # frames
        escalation_threshold: float = 20.0,  # score increase over window
        
        # Special rules
        allow_single_frame_emergency: bool = False,
        emergency_confidence_min: float = 0.95,
    ):
        self.weights = {
            'vision': vision_weight,
            'following': following_weight,
            'approaching': approaching_weight,
            'chasing': chasing_weight,
            'fleeing': fleeing_weight,
            'confrontation': confrontation_weight,
            'audio': audio_weight,
            'context': context_weight,
        }
        
        self.thresholds = {
            'SAFE': safe_max,
            'WARNING': warning_max,
            'HIGH': high_max,
            'CRITICAL': critical_max,
            'EMERGENCY': emergency_min,
        }
        
        self.config = {
            'smooth_factor': smooth_factor,
            'max_increase_per_frame': max_increase_per_frame,
            'max_decrease_per_frame': max_decrease_per_frame,
            'escalation_window': escalation_window,
            'escalation_threshold': escalation_threshold,
            'allow_single_frame_emergency': allow_single_frame_emergency,
            'emergency_confidence_min': emergency_confidence_min,
        }
        
        # State
        self._prev_score = 0.0
        self._score_history = deque(maxlen=300)  # ~10 seconds at 30fps
        self._prev_contributions: Dict[str, float] = {}
    
    def assess(
        self,
        vision_signal: Optional[Dict[str, Any]] = None,
        following_events: Optional[List[Dict[str, Any]]] = None,
        behavior_results: Optional[List[Dict[str, Any]]] = None,
        audio_signal: Optional[Dict[str, Any]] = None,
        context_signal: Optional[Dict[str, Any]] = None,
        gru_result: Optional[Dict[str, Any]] = None,
        location: Optional[Dict[str, float]] = None,
        tracks: Optional[List[Dict[str, Any]]] = None,
        now: Optional[float] = None,
    ) -> ThreatResult:
        """
        Fuse all available signals into a unified threat assessment.
        
        Args:
            vision_signal: VisionAgent output (activity, interaction, temporal)
            following_events: FollowingDetector events
            behavior_results: BehaviorEngine results (approaching, chasing, etc.)
            audio_signal: Audio agent output (keywords, distress)
            context_signal: Context agent output (location, time, zone)
            gru_result: GRU temporal classifier result
            location: GPS location
            tracks: Current tracked persons
            now: Current timestamp
            
        Returns:
            ThreatResult with fused score, level, reasons, and evidence
        """
        if now is None:
            now = time.time()
        
        contributions = []
        reasons = []
        active_behaviors = []
        
        # 1. Vision signal
        if vision_signal:
            vis_score, vis_conf, vis_contrib = self._process_vision(vision_signal)
            if vis_score > 0:
                contributions.append(ThreatContribution(
                    source="vision",
                    factor=f"activity:{vision_signal.get('activity_label', 'unknown')}",
                    raw_score=vis_score,
                    weight=self.weights['vision'],
                    weighted_score=vis_score * self.weights['vision'],
                    confidence=vis_conf,
                    evidence=[f"activity={vision_signal.get('activity_label')}",
                             f"confidence={vision_signal.get('activity_confidence', 0):.2f}"],
                ))
                reasons.append(f"Vision: {vision_signal.get('activity_label', 'unknown')} (conf={vision_signal.get('activity_confidence', 0):.2f})")
                if vision_signal.get('activity_label') not in ('normal', 'warming_up', 'unknown'):
                    active_behaviors.append(vision_signal.get('activity_label'))
        
        # 2. Following
        if following_events:
            for ev in following_events:
                score = ev.get('score', 0)
                conf = min(1.0, score / 100.0 * 1.2)  # Rough confidence from score
                contributions.append(ThreatContribution(
                    source="following",
                    factor="following",
                    raw_score=score,
                    weight=self.weights['following'],
                    weighted_score=score * self.weights['following'],
                    confidence=conf,
                    evidence=ev.get('evidence', []),
                ))
                reasons.append(f"Following: target={ev['target_id']} follower={ev['follower_id']} score={score:.0f}")
                active_behaviors.append("following")
        
        # 3. Other behaviors
        if behavior_results:
            for br in behavior_results:
                btype = br.get('behavior', 'unknown')
                score = br.get('score', 0)
                conf = min(1.0, score / 100.0 * 1.2)
                
                weight_key = btype
                if weight_key not in self.weights:
                    weight_key = 'approaching'  # default fallback
                
                contributions.append(ThreatContribution(
                    source="behavior",
                    factor=btype,
                    raw_score=score,
                    weight=self.weights.get(weight_key, 0.05),
                    weighted_score=score * self.weights.get(weight_key, 0.05),
                    confidence=conf,
                    evidence=br.get('evidence', []),
                ))
                reasons.append(f"{btype.capitalize()}: score={score:.0f} subjects={br.get('subjects', [])}")
                if btype not in active_behaviors:
                    active_behaviors.append(btype)
        
        # 4. Audio
        if audio_signal:
            aud_score, aud_conf, aud_evidence = self._process_audio(audio_signal)
            if aud_score > 0:
                contributions.append(ThreatContribution(
                    source="audio",
                    factor="distress" if audio_signal.get('distress_detected') else "keyword",
                    raw_score=aud_score,
                    weight=self.weights['audio'],
                    weighted_score=aud_score * self.weights['audio'],
                    confidence=aud_conf,
                    evidence=aud_evidence,
                ))
                reasons.append(f"Audio: {'distress' if audio_signal.get('distress_detected') else 'keywords'} (conf={aud_conf:.2f})")
                if audio_signal.get('distress_detected'):
                    active_behaviors.append("audio_distress")
        
        # 5. Context
        if context_signal:
            ctx_score = context_signal.get('context_score', 0)
            ctx_conf = context_signal.get('context_confidence', 0.5)
            if ctx_score > 0:
                contributions.append(ThreatContribution(
                    source="context",
                    factor="context",
                    raw_score=ctx_score,
                    weight=self.weights['context'],
                    weighted_score=ctx_score * self.weights['context'],
                    confidence=ctx_conf,
                    evidence=context_signal.get('reasons', []),
                ))
                reasons.extend(context_signal.get('reasons', []))
        
        # 6. GRU (as additional vision signal)
        if gru_result and gru_result.get('label') not in ('normal', 'unknown'):
            gru_score = gru_result.get('confidence', 0) * 100
            contributions.append(ThreatContribution(
                source="gru",
                factor=f"gru:{gru_result.get('label')}",
                raw_score=gru_score,
                weight=0.1,  # Additional weight
                weighted_score=gru_score * 0.1,
                confidence=gru_result.get('confidence', 0),
                evidence=[f"GRU predicted {gru_result.get('label')} with {gru_result.get('confidence', 0):.2f}"],
            ))
            reasons.append(f"GRU: {gru_result.get('label')} (conf={gru_result.get('confidence', 0):.2f})")
        
        # Compute weighted total
        total_weight = sum(c.weight for c in contributions)
        if total_weight > 0:
            raw_score = sum(c.weighted_score for c in contributions) / total_weight * 100
        else:
            raw_score = 0.0
        
        # Apply temporal smoothing
        smoothed_score = self._apply_temporal_smoothing(raw_score)
        
        # Determine risk level
        risk_level = self._determine_level(smoothed_score)
        
        # Overall confidence
        if contributions:
            total_conf = sum(c.confidence * c.weight for c in contributions)
            total_w = sum(c.weight for c in contributions)
            confidence = total_conf / total_w if total_w > 0 else 0.0
        else:
            confidence = 0.0
        
        # Determine temporal trend
        trend = self._compute_trend(smoothed_score)
        
        # Check for single-frame emergency (if allowed)
        if (self.config['allow_single_frame_emergency'] and 
            risk_level == 'EMERGENCY' and 
            confidence >= self.config['emergency_confidence_min'] and
            len(self._score_history) < 5):
            # Allow single-frame emergency with very high confidence
            pass
        elif risk_level == 'EMERGENCY' and len(self._score_history) < 10:
            # Require some temporal evidence for emergency
            risk_level = 'CRITICAL'
            smoothed_score = min(smoothed_score, self.thresholds['EMERGENCY'] - 1)
            reasons.append("Emergency requires temporal persistence; downgraded to CRITICAL")
        
        # Build track info
        track_info = []
        if tracks:
            for t in tracks:
                track_info.append({
                    "track_id": t.get('track_id'),
                    "center": t.get('center'),
                    "speed": t.get('speed'),
                    "direction": t.get('direction'),
                })
        
        # Update history
        self._score_history.append(smoothed_score)
        self._prev_score = smoothed_score
        
        return ThreatResult(
            risk_score=round(smoothed_score, 1),
            risk_level=risk_level,
            behaviors=active_behaviors,
            reasons=reasons,
            contributions=contributions,
            confidence=round(confidence, 2),
            timestamp=datetime.fromtimestamp(now).isoformat() + 'Z',
            tracks=track_info,
            temporal_trend=trend,
        )
    
    def _process_vision(self, vision: Dict[str, Any]) -> Tuple[float, float, Dict]:
        """Extract score and confidence from vision signal"""
        # Use visual_risk_signal if available (already 0-100 scale from VisionAgent)
        score = vision.get('visual_risk_signal', 0) * 100
        conf = vision.get('activity_confidence', 0.5)
        
        # Cap at 100
        return min(100.0, score), conf, {}
    
    def _process_audio(self, audio: Dict[str, Any]) -> Tuple[float, float, List[str]]:
        """Extract score from audio signal"""
        score = 0.0
        conf = 0.0
        evidence = []
        
        if audio.get('distress_detected'):
            score = max(score, audio.get('distress_confidence', 0) * 100)
            conf = max(conf, audio.get('distress_confidence', 0))
            evidence.append(f"distress:{audio.get('distress_type', 'unknown')}")
        
        if audio.get('keywords'):
            kw_score = max(k.get('confidence', 0) for k in audio['keywords']) * 100
            score = max(score, kw_score)
            conf = max(conf, max(k.get('confidence', 0) for k in audio['keywords']))
            kw_names = [k.get('keyword', '') for k in audio['keywords']]
            evidence.append(f"keywords:{kw_names}")
        
        return score, conf, evidence
    
    def _apply_temporal_smoothing(self, raw_score: float) -> float:
        """Apply temporal smoothing and rate limiting"""
        if not self._score_history:
            return raw_score
        
        prev = self._prev_score
        
        # Rate limiting
        max_inc = self.config['max_increase_per_frame']
        max_dec = self.config['max_decrease_per_frame']
        
        if raw_score > prev + max_inc:
            limited = prev + max_inc
        elif raw_score < prev - max_dec:
            limited = prev - max_dec
        else:
            limited = raw_score
        
        # Exponential smoothing
        alpha = 1.0 - self.config['smooth_factor']
        smoothed = alpha * limited + (1 - alpha) * prev
        
        return smoothed
    
    def _determine_level(self, score: float) -> str:
        """Map score to risk level"""
        if score >= self.thresholds['EMERGENCY']:
            return 'EMERGENCY'
        elif score >= self.thresholds['CRITICAL']:
            return 'CRITICAL'
        elif score >= self.thresholds['HIGH']:
            return 'HIGH'
        elif score >= self.thresholds['WARNING']:
            return 'WARNING'
        else:
            return 'SAFE'
    
    def _compute_trend(self, current: float) -> str:
        """Determine temporal trend"""
        if len(self._score_history) < 5:
            return "stable"
        
        recent = list(self._score_history)[-self.config['escalation_window']:]
        if len(recent) < 2:
            return "stable"
        
        change = recent[-1] - recent[0]
        
        if change > self.config['escalation_threshold']:
            return "escalating"
        elif change < -self.config['escalation_threshold']:
            return "de-escalating"
        else:
            return "stable"
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "current_score": self._prev_score,
            "history_len": len(self._score_history),
            "thresholds": self.thresholds,
        }
    
    def import_time(self):
        import time
        return time

# Need to import time at module level
import time
