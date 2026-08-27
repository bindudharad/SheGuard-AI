"""
Behavior Engine - reusable behavior analysis using tracking infrastructure.

Implements:
1. FOLLOWING
2. APPROACHING
3. CHASING
4. FLEEING
5. CONFRONTATION
6. ISOLATION

Each behavior produces a structured result with score 0-100 and evidence.
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import math
import time

import numpy as np

from agents.vision.pipeline.following_detector import FollowingDetector


@dataclass
class BehaviorResult:
    """Structured behavior result"""
    behavior: str
    score: float  # 0-100
    subjects: List[int]  # track IDs involved
    duration: float  # seconds
    evidence: List[str]
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "behavior": self.behavior,
            "score": round(self.score, 1),
            "subjects": self.subjects,
            "duration": round(self.duration, 1),
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class BehaviorEngine:
    """
    Reusable behavior analysis layer.
    Uses the same tracking infrastructure as following detection.
    """
    
    def __init__(
        self,
        following_config: Optional[dict] = None,
        approaching_distance_threshold: float = 300.0,
        approaching_speed_threshold: float = 15.0,  # px/frame
        approaching_window: int = 10,
        chasing_distance_threshold: float = 250.0,
        chasing_speed_threshold: float = 20.0,
        chasing_relative_velocity_min: float = 15.0,
        fleeing_acceleration_threshold: float = 2.0,
        fleeing_direction_away_min: float = 0.7,
        confrontation_distance_max: float = 150.0,
        confrontation_persistence: float = 2.0,
        isolation_radius: float = 200.0,  # px
        isolation_density_min: float = 0.5,  # persons per 100px
        isolation_persistence: float = 5.0,
        trigger_score: float = 55.0,
        clear_score: float = 40.0,
        smooth_factor: float = 0.6,
    ):
        self.following_detector = FollowingDetector(**(following_config or {}))
        
        self.config = {
            'approaching_distance_threshold': approaching_distance_threshold,
            'approaching_speed_threshold': approaching_speed_threshold,
            'approaching_window': approaching_window,
            'chasing_distance_threshold': chasing_distance_threshold,
            'chasing_speed_threshold': chasing_speed_threshold,
            'chasing_relative_velocity_min': chasing_relative_velocity_min,
            'fleeing_acceleration_threshold': fleeing_acceleration_threshold,
            'fleeing_direction_away_min': fleeing_direction_away_min,
            'confrontation_distance_max': confrontation_distance_max,
            'confrontation_persistence': confrontation_persistence,
            'isolation_radius': isolation_radius,
            'isolation_density_min': isolation_density_min,
            'isolation_persistence': isolation_persistence,
            'trigger_score': trigger_score,
            'clear_score': clear_score,
            'smooth_factor': smooth_factor,
        }
        
        # State for temporal behaviors
        self._approaching_state: Dict[Tuple[int, int], deque] = {}
        self._chasing_state: Dict[Tuple[int, int], deque] = {}
        self._fleeing_state: Dict[int, deque] = {}
        self._confrontation_state: Dict[Tuple[int, int], float] = {}
        self._isolation_state: Dict[int, float] = {}
        
        # Smoothed scores
        self._smoothed_scores: Dict[str, Dict[Tuple, float]] = {
            'approaching': {},
            'chasing': {},
            'fleeing': {},
            'confrontation': {},
            'isolation': {},
        }
    
    def update(self, tracks: List[Any], now: float) -> List[BehaviorResult]:
        """
        Run all behavior detectors.
        Returns list of active behavior results.
        """
        results = []
        
        # 1. Following (delegates to FollowingDetector)
        following_events = self.following_detector.update(tracks, now)
        for ev in following_events:
            results.append(BehaviorResult(
                behavior="following",
                score=ev["score"],
                subjects=[ev["target_id"], ev["follower_id"]],
                duration=ev["duration_seconds"],
                evidence=ev["evidence"],
                timestamp=now,
                details=ev,
            ))
        
        # 2. Approaching
        results.extend(self._detect_approaching(tracks, now))
        
        # 3. Chasing
        results.extend(self._detect_chasing(tracks, now))
        
        # 4. Fleeing
        results.extend(self._detect_fleeing(tracks, now))
        
        # 5. Confrontation
        results.extend(self._detect_confrontation(tracks, now))
        
        # 6. Isolation
        results.extend(self._detect_isolation(tracks, now))
        
        return results
    
    def _detect_approaching(self, tracks, now) -> List[BehaviorResult]:
        """Detect sustained rapid distance reduction between people"""
        results = []
        track_map = {t.track_id: t for t in tracks}
        
        for i, tid_a in enumerate(track_map):
            for tid_b in list(track_map)[i+1:]:
                pair = tuple(sorted([tid_a, tid_b]))
                ta = track_map[tid_a]
                tb = track_map[tid_b]
                dist = self._point_distance(ta.center, tb.center)
                
                if dist > self.config['approaching_distance_threshold']:
                    self._approaching_state[pair] = deque(maxlen=self.config['approaching_window'])
                    continue
                
                # Record distance
                if pair not in self._approaching_state:
                    self._approaching_state[pair] = deque(maxlen=self.config['approaching_window'])
                self._approaching_state[pair].append((now, dist))
                
                if len(self._approaching_state[pair]) < 3:
                    continue
                
                # Check sustained decrease
                distances = [d for _, d in self._approaching_state[pair]]
                total_reduction = distances[0] - distances[-1]
                rate = total_reduction / max(1, len(distances))
                
                # Check combined speed toward each other
                va = getattr(ta, 'speed', 0.0)
                vb = getattr(tb, 'speed', 0.0)
                
                if total_reduction > 50 and (va + vb) > self.config['approaching_speed_threshold']:
                    score = min(100.0, (total_reduction / 100.0) * 50 + (va + vb) * 2)
                    evidence = [
                        f"distance_reduced={total_reduction:.1f}px",
                        f"combined_speed={va + vb:.1f}px/frame",
                        f"rate={rate:.2f}px/frame",
                    ]
                    results.append(BehaviorResult(
                        behavior="approaching",
                        score=score,
                        subjects=[tid_a, tid_b],
                        duration=now - self._approaching_state[pair][0][0],
                        evidence=evidence,
                        timestamp=now,
                        details={"distance": dist, "total_reduction": total_reduction},
                    ))
        
        return results
    
    def _detect_chasing(self, tracks, now) -> List[BehaviorResult]:
        """
        Chasing requires stronger evidence than approaching:
        - A follows B
        - Distance rapidly decreasing
        - High relative velocity
        - Trajectory correlation
        """
        results = []
        track_map = {t.track_id: t for t in tracks}
        
        for i, tid_a in enumerate(track_map):
            for tid_b in list(track_map)[i+1:]:
                pair = tuple(sorted([tid_a, tid_b]))
                ta = track_map[tid_a]
                tb = track_map[tid_b]
                dist = self._point_distance(ta.center, tb.center)
                
                # Pre-conditions
                if dist > self.config['chasing_distance_threshold']:
                    continue
                
                va = getattr(ta, 'speed', 0.0)
                vb = getattr(tb, 'speed', 0.0)
                
                if va < self.config['chasing_speed_threshold'] and vb < self.config['chasing_speed_threshold']:
                    continue
                
                # Relative velocity
                rel_vel = abs(va - vb)
                if rel_vel < self.config['chasing_relative_velocity_min']:
                    continue
                
                # Trajectory correlation (use following detector's trajectory similarity if available)
                traj_sim = self.following_detector._trajectory_similarity(
                    self.following_detector.relationships.get(pair, None)
                ) if pair in self.following_detector.relationships else 0.0
                
                # Distance decreasing
                if pair not in self._chasing_state:
                    self._chasing_state[pair] = deque(maxlen=10)
                self._chasing_state[pair].append((now, dist))
                
                if len(self._chasing_state[pair]) >= 3:
                    distances = [d for _, d in self._chasing_state[pair]]
                    decreasing = distances[-1] < distances[0] * 0.8
                    
                    if decreasing:
                        score = min(100.0,
                            40.0 * (rel_vel / self.config['chasing_relative_velocity_min']) +
                            30.0 * traj_sim +
                            30.0 * (va + vb) / (2 * self.config['chasing_speed_threshold'])
                        )
                        evidence = [
                            f"relative_velocity={rel_vel:.1f}px/frame",
                            f"trajectory_correlation={traj_sim:.2f}",
                            f"distance={dist:.1f}px",
                            f"decreasing={decreasing}",
                        ]
                        results.append(BehaviorResult(
                            behavior="chasing",
                            score=score,
                            subjects=[tid_a, tid_b],
                            duration=now - self._chasing_state[pair][0][0],
                            evidence=evidence,
                            timestamp=now,
                            details={"distance": dist, "relative_velocity": rel_vel},
                        ))
        
        return results
    
    def _detect_fleeing(self, tracks, now) -> List[BehaviorResult]:
        """
        Detect:
        - sudden velocity increase
        - direction away from another person
        - abnormal acceleration
        - relationship with pursuing person
        """
        results = []
        track_map = {t.track_id: t for t in tracks}
        
        for tid, track in track_map.items():
            vel = getattr(track, 'velocity', (0, 0))
            speed = getattr(track, 'speed', 0.0)
            
            # Track acceleration
            if tid not in self._fleeing_state:
                self._fleeing_state[tid] = deque(maxlen=10)
            self._fleeing_state[tid].append((now, speed))
            
            if len(self._fleeing_state[tid]) < 3:
                continue
            
            speeds = [s for _, s in self._fleeing_state[tid]]
            accel = speeds[-1] - speeds[-2]
            
            if accel < self.config['fleeing_acceleration_threshold']:
                continue
            
            # Check direction away from nearest person
            min_dist = float('inf')
            nearest_id = None
            for other_tid, other in track_map.items():
                if other_tid == tid:
                    continue
                d = self._point_distance(track.center, other.center)
                if d < min_dist:
                    min_dist = d
                    nearest_id = other_tid
            
            if nearest_id is None:
                continue
            
            # Direction away from nearest
            away_vec = (track.center[0] - track_map[nearest_id].center[0],
                       track.center[1] - track_map[nearest_id].center[1])
            vel_norm = math.hypot(*vel)
            if vel_norm < 1.0:
                continue
            
            dot = away_vec[0] * vel[0] + away_vec[1] * vel[1]
            away_sim = dot / (vel_norm * math.hypot(*away_vec))
            
            if away_sim >= self.config['fleeing_direction_away_min']:
                score = min(100.0, 30.0 + accel * 10 + away_sim * 40)
                evidence = [
                    f"acceleration={accel:.1f}px/frame^2",
                    f"direction_away={away_sim:.2f}",
                    f"sustained_flee_from_track={nearest_id}",
                ]
                results.append(BehaviorResult(
                    behavior="fleeing",
                    score=score,
                    subjects=[tid, nearest_id],
                    duration=now - self._fleeing_state[tid][0][0],
                    evidence=evidence,
                    timestamp=now,
                    details={"acceleration": accel, "away_similarity": away_sim},
                ))
        
        return results
    
    def _detect_confrontation(self, tracks, now) -> List[BehaviorResult]:
        """
        Combine:
        - close distance
        - opposing movement (moving toward each other)
        - pose/aggression signals (if available)
        - persistence
        - trajectory relationship
        """
        results = []
        track_map = {t.track_id: t for t in tracks}
        
        for i, tid_a in enumerate(track_map):
            for tid_b in list(track_map)[i+1:]:
                pair = tuple(sorted([tid_a, tid_b]))
                ta = track_map[tid_a]
                tb = track_map[tid_b]
                dist = self._point_distance(ta.center, tb.center)
                
                if dist > self.config['confrontation_distance_max']:
                    self._confrontation_state[pair] = 0.0
                    continue
                
                # Opposing movement: velocities point toward each other
                va = getattr(ta, 'velocity', (0, 0))
                vb = getattr(tb, 'velocity', (0, 0))
                
                # Vector from A to B
                ab = (tb.center[0] - ta.center[0], tb.center[1] - ta.center[1])
                # A moving toward B means dot(va, ab) > 0
                va_norm = math.hypot(*va)
                vb_norm = math.hypot(*vb)
                
                opposing = False
                if va_norm > 1.0 and vb_norm > 1.0:
                    dot_a = va[0] * ab[0] + va[1] * ab[1]
                    dot_b = -vb[0] * ab[0] - vb[1] * ab[1]  # B moving toward A
                    opposing = dot_a > 0 and dot_b > 0
                
                # Pose aggression (if pose available)
                aggression = 0.0
                for t in [ta, tb]:
                    pose = getattr(t, 'pose', None)
                    if pose and getattr(pose, 'visible', False):
                        # Simple heuristic: if head below shoulder level
                        if pose.head and pose.shoulder and pose.head[1] > pose.shoulder[1] + 10:
                            aggression += 0.3
                
                if opposing or aggression > 0:
                    self._confrontation_state[pair] = self._confrontation_state.get(pair, 0.0) + 1.0 / 30.0
                    
                    if self._confrontation_state[pair] >= self.config['confrontation_persistence']:
                        score = min(100.0, 30.0 + aggression * 50 + (50.0 if opposing else 0.0))
                        evidence = [
                            f"distance={dist:.1f}px",
                            f"opposing_movement={opposing}",
                            f"aggression_signals={aggression:.2f}",
                            f"persistence={self._confrontation_state[pair]:.1f}s",
                        ]
                        results.append(BehaviorResult(
                            behavior="confrontation",
                            score=score,
                            subjects=[tid_a, tid_b],
                            duration=self._confrontation_state[pair],
                            evidence=evidence,
                            timestamp=now,
                            details={"distance": dist, "opposing": opposing},
                        ))
                else:
                    self._confrontation_state[pair] = max(0.0, self._confrontation_state.get(pair, 0.0) - 2.0 / 30.0)
        
        return results
    
    def _detect_isolation(self, tracks, now) -> List[BehaviorResult]:
        """
        Detect a person who is:
        - isolated from nearby people
        - in a low-density region
        - potentially in unusual context
        
        DO NOT treat isolation alone as emergency - only contextual signal.
        """
        results = []
        track_map = {t.track_id: t for t in tracks}
        
        for tid, track in track_map.items():
            # Count neighbors within isolation radius
            neighbors = 0
            for other_tid, other in track_map.items():
                if other_tid == tid:
                    continue
                d = self._point_distance(track.center, other.center)
                if d < self.config['isolation_radius']:
                    neighbors += 1
            
            density = neighbors / (self.config['isolation_radius'] / 100.0)
            
            if density < self.config['isolation_density_min'] and neighbors == 0:
                self._isolation_state[tid] = self._isolation_state.get(tid, 0.0) + 1.0 / 30.0
                
                if self._isolation_state[tid] >= self.config['isolation_persistence']:
                    # Low score - just contextual signal
                    score = min(40.0, 10.0 + self._isolation_state[tid] * 2)
                    evidence = [
                        f"no_neighbors_within={self.config['isolation_radius']:.0f}px",
                        f"isolation_duration={self._isolation_state[tid]:.1f}s",
                        "CONTEXTUAL_ONLY_NOT_EMERGENCY",
                    ]
                    results.append(BehaviorResult(
                        behavior="isolation",
                        score=score,
                        subjects=[tid],
                        duration=self._isolation_state[tid],
                        evidence=evidence,
                        timestamp=now,
                        details={"neighbors": neighbors, "contextual_signal": True},
                    ))
            else:
                self._isolation_state[tid] = max(0.0, self._isolation_state.get(tid, 0.0) - 1.0 / 30.0)
        
        return results
    
    def _point_distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "following": self.following_detector.get_metrics(),
            "approaching_pairs": len(self._approaching_state),
            "chasing_pairs": len(self._chasing_state),
            "fleeing_tracks": len(self._fleeing_state),
        }
