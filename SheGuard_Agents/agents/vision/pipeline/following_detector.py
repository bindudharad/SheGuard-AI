"""
Real Following Detector using trajectory-based analysis.

Implements genuine following detection based on:
- Distance trend (sustained convergence)
- Velocity similarity
- Direction similarity
- Trajectory similarity
- Turn-matching
- Persistence over time

Distinguishes genuine following from simply walking together.
"""
from typing import Optional, List, Dict, Any, Tuple, Deque
from dataclasses import dataclass, field
from collections import deque
import math
import time

import numpy as np


@dataclass
class TrackRelationship:
    """Relationship state between two tracked persons"""
    target_id: int
    follower_id: int
    first_seen: float
    last_seen: float
    
    # Distance tracking
    distances: Deque[float] = field(default_factory=lambda: deque(maxlen=60))
    distance_timestamps: Deque[float] = field(default_factory=lambda: deque(maxlen=60))
    
    # Velocity tracking
    target_velocities: Deque[Tuple[float, float]] = field(default_factory=lambda: deque(maxlen=30))
    follower_velocities: Deque[Tuple[float, float]] = field(default_factory=lambda: deque(maxlen=30))
    
    # Direction tracking
    target_directions: Deque[str] = field(default_factory=lambda: deque(maxlen=30))
    follower_directions: Deque[str] = field(default_factory=lambda: deque(maxlen=30))
    
    # Trajectory tracking
    target_positions: Deque[Tuple[float, float]] = field(default_factory=lambda: deque(maxlen=60))
    follower_positions: Deque[Tuple[float, float]] = field(default_factory=lambda: deque(maxlen=60))
    
    # Turn tracking
    target_turns: Deque[float] = field(default_factory=lambda: deque(maxlen=30))  # angle changes
    follower_turns: Deque[float] = field(default_factory=lambda: deque(maxlen=30))
    turn_matches: Deque[bool] = field(default_factory=lambda: deque(maxlen=30))
    
    # Per-frame confidence history
    confidence_history: Deque[float] = field(default_factory=lambda: deque(maxlen=60))


class FollowingDetector:
    """
    Detects genuine following behavior using trajectory analysis.
    
    False-positive suppression: Distinguishes following from walking together
    by requiring distance changes, direction changes followed by follower,
    and persistent correlation.
    """
    
    def __init__(
        self,
        # Distance parameters (in pixels)
        suspicious_distance_max: float = 250.0,    # Max distance to consider following
        suspicious_distance_min: float = 20.0,     # Min distance (too close = confrontation)
        convergence_window: int = 10,              # Frames to detect convergence
        convergence_threshold: float = 30.0,       # Min total distance decrease
        distance_stability_tolerance: float = 40.0, # For walking-together detection
        
        # Velocity/direction parameters
        velocity_similarity_min: float = 0.6,      # Cosine similarity threshold
        direction_match_window: int = 8,
        
        # Turn matching
        turn_match_angle_threshold: float = 25.0,  # degrees
        turn_match_delay_tolerance: int = 5,       # frames follower can lag
        
        # Persistence
        min_persistence_seconds: float = 3.0,
        min_persistence_frames: int = 30,
        
        # Scoring
        trigger_score: float = 60.0,
        clear_score: float = 40.0,
        smooth_factor: float = 0.7,  # Temporal smoothing
        
        # Anti-false-positive
        walking_together_score_penalty: float = 0.5,
    ):
        self.config = {
            'suspicious_distance_max': suspicious_distance_max,
            'suspicious_distance_min': suspicious_distance_min,
            'convergence_window': convergence_window,
            'convergence_threshold': convergence_threshold,
            'distance_stability_tolerance': distance_stability_tolerance,
            'velocity_similarity_min': velocity_similarity_min,
            'direction_match_window': direction_match_window,
            'turn_match_angle_threshold': turn_match_angle_threshold,
            'turn_match_delay_tolerance': turn_match_delay_tolerance,
            'min_persistence_seconds': min_persistence_seconds,
            'min_persistence_frames': min_persistence_frames,
            'trigger_score': trigger_score,
            'clear_score': clear_score,
            'smooth_factor': smooth_factor,
            'walking_together_score_penalty': walking_together_score_penalty,
        }
        
        self.relationships: Dict[Tuple[int, int], TrackRelationship] = {}
        self.active_follows: Dict[Tuple[int, int], float] = {}  # (target, follower) -> smoothed score
    
    def update(self, tracks: List[Any], now: float) -> List[Dict[str, Any]]:
        """
        Update following detection with current tracks.
        Returns list of following events (only when score >= trigger).
        """
        results = []
        
        # Build track lookup
        track_map = {t.track_id: t for t in tracks}
        
        # Ensure all pairs have relationship state
        for i, tid_a in enumerate(track_map):
            for tid_b in list(track_map)[i+1:]:
                pair = tuple(sorted([tid_a, tid_b]))
                if pair not in self.relationships:
                    self.relationships[pair] = TrackRelationship(
                        target_id=pair[0],
                        follower_id=pair[1],
                        first_seen=now,
                        last_seen=now,
                    )
        
        # Update each relationship
        active_pairs = set()
        for pair, rel in self.relationships.items():
            tid_a, tid_b = pair
            track_a = track_map.get(tid_a)
            track_b = track_map.get(tid_b)
            
            if track_a is None or track_b is None:
                continue  # One or both not present
                
            active_pairs.add(pair)
            rel.last_seen = now
            
            # Determine which is target (front) and which is follower (behind)
            # Target = ahead in direction of movement
            target, follower = self._determine_target_follower(track_a, track_b)
            rel.target_id = target.track_id
            rel.follower_id = follower.track_id
            
            # Update distance
            dist = self._point_distance(target.center, follower.center)
            rel.distances.append(dist)
            rel.distance_timestamps.append(now)
            
            # Update positions
            rel.target_positions.append(target.center)
            rel.follower_positions.append(follower.center)
            
            # Update velocities and directions
            if hasattr(target, 'velocity'):
                rel.target_velocities.append(target.velocity)
            if hasattr(follower, 'velocity'):
                rel.follower_velocities.append(follower.velocity)
            if target.direction:
                rel.target_directions.append(target.direction)
            if follower.direction:
                rel.follower_directions.append(follower.direction)
            
            # Update turns
            if len(rel.target_positions) >= 2:
                ta = rel.target_positions[-2]
                tb = rel.target_positions[-1]
                prev_vec = (tb[0] - ta[0], tb[1] - ta[1])
                if len(rel.target_positions) >= 3:
                    ta2 = rel.target_positions[-3]
                    prev_vec2 = (ta[0] - ta2[0], ta[1] - ta2[1])
                    turn = self._angle_between_vectors(prev_vec2, prev_vec)
                    rel.target_turns.append(turn)
            
            if len(rel.follower_positions) >= 2:
                fa = rel.follower_positions[-2]
                fb = rel.follower_positions[-1]
                prev_vec = (fb[0] - fa[0], fb[1] - fa[1])
                if len(rel.follower_positions) >= 3:
                    fa2 = rel.follower_positions[-3]
                    prev_vec2 = (fa[0] - fa2[0], fa[1] - fa2[1])
                    turn = self._angle_between_vectors(prev_vec2, prev_vec)
                    rel.follower_turns.append(turn)
            
            # Compute turn matching
            turn_match = self._compute_turn_match(rel)
            rel.turn_matches.append(turn_match)
            
            # Compute following score
            score, evidence = self._compute_score(rel, dist, now)
            rel.confidence_history.append(score)
            
            # Temporal smoothing
            pair_key = (rel.target_id, rel.follower_id)
            prev_smoothed = self.active_follows.get(pair_key, 0.0)
            smoothed = prev_smoothed * self.config['smooth_factor'] + score * (1 - self.config['smooth_factor'])
            self.active_follows[pair_key] = smoothed
            
            # Only emit if above trigger
            if smoothed >= self.config['trigger_score']:
                results.append(self._build_result(rel, smoothed, dist, evidence, now))
        
        # Clean stale relationships
        self._cleanup_stale(now)
        
        return results
    
    def _determine_target_follower(self, track_a, track_b) -> Tuple[Any, Any]:
        """
        Determine which track is the target (front) and which is the follower (behind).
        Uses velocity direction and relative position.
        """
        va = getattr(track_a, 'velocity', (0, 0))
        vb = getattr(track_b, 'velocity', (0, 0))
        
        # If both have velocity, target is the one "ahead"
        va_mag = math.hypot(*va)
        vb_mag = math.hypot(*vb)
        
        if va_mag < 1.0 and vb_mag < 1.0:
            # Both stationary, use track_id as tiebreaker (stable)
            if track_a.track_id < track_b.track_id:
                return track_a, track_b
            return track_b, track_a
        
        # Target = the one moving "forward" relative to the other
        # Simple heuristic: target is the one with larger velocity magnitude
        if va_mag >= vb_mag:
            return track_a, track_b
        return track_b, track_a
    
    def _compute_score(self, rel: TrackRelationship, current_dist: float, now: float) -> Tuple[float, List[str]]:
        """Compute following score 0-100 with evidence"""
        evidence = []
        score_components = []
        
        # 1. Distance convergence check
        convergence_score, conv_evidence = self._check_convergence(rel)
        if convergence_score > 0:
            score_components.append(convergence_score * 0.25)
            evidence.extend(conv_evidence)
        
        # 2. Velocity similarity
        vel_sim = self._velocity_similarity(rel)
        if vel_sim > self.config['velocity_similarity_min']:
            score_components.append(vel_sim * 0.2)
            evidence.append(f"velocity_similarity={vel_sim:.2f}")
        
        # 3. Direction similarity
        dir_sim = self._direction_similarity(rel)
        if dir_sim > 0.6:
            score_components.append(dir_sim * 0.15)
            evidence.append(f"direction_similarity={dir_sim:.2f}")
        
        # 4. Trajectory similarity
        traj_sim = self._trajectory_similarity(rel)
        if traj_sim > 0.5:
            score_components.append(traj_sim * 0.15)
            evidence.append(f"trajectory_similarity={traj_sim:.2f}")
        
        # 5. Turn matching
        turn_match = self._turn_match_score(rel)
        if turn_match > 0.5:
            score_components.append(turn_match * 0.15)
            evidence.append(f"turn_match_score={turn_match:.2f}")
        
        # 6. Persistence
        duration = now - rel.first_seen
        persistence_score = min(1.0, duration / self.config['min_persistence_seconds'])
        if duration >= self.config['min_persistence_seconds']:
            score_components.append(persistence_score * 0.1)
            evidence.append(f"persistence={duration:.1f}s")
        
        # Distance range check (must be in suspicious but not too close range)
        if self.config['suspicious_distance_min'] < current_dist < self.config['suspicious_distance_max']:
            evidence.append(f"distance={current_dist:.1f}px (in range)")
        else:
            # Penalize if out of range
            score_components = [s * 0.5 for s in score_components]
            evidence.append(f"distance={current_dist:.1f}px (out of range)")
        
        # Anti-false-positive: walking together check
        is_walking_together = self._is_walking_together(rel)
        if is_walking_together:
            score_components = [s * self.config['walking_together_score_penalty'] for s in score_components]
            evidence.append("walking_together_pattern_detected (suppressed)")
        
        # Sum and clamp
        raw_score = sum(score_components)
        final_score = min(100.0, max(0.0, raw_score * 100.0))
        
        return final_score, evidence
    
    def _check_convergence(self, rel: TrackRelationship) -> Tuple[float, List[str]]:
        """Check sustained distance convergence"""
        if len(rel.distances) < self.config['convergence_window']:
            return 0.0, []
        
        window = list(rel.distances)[-self.config['convergence_window']:]
        total_change = window[0] - window[-1]  # Positive = getting closer
        
        if total_change >= self.config['convergence_threshold']:
            return min(1.0, total_change / (self.config['convergence_threshold'] * 2)), \
                   [f"distance_convergence={total_change:.1f}px over {len(window)} frames"]
        
        return 0.0, []
    
    def _velocity_similarity(self, rel: TrackRelationship) -> float:
        """Cosine similarity of recent velocities"""
        if len(rel.target_velocities) < 2 or len(rel.follower_velocities) < 2:
            return 0.0
        
        tv = list(rel.target_velocities)[-1]
        fv = list(rel.follower_velocities)[-1]
        
        tv_norm = math.hypot(*tv)
        fv_norm = math.hypot(*fv)
        
        if tv_norm < 1.0 or fv_norm < 1.0:
            return 0.0
        
        dot = tv[0] * fv[0] + tv[1] * fv[1]
        return max(0.0, dot / (tv_norm * fv_norm))
    
    def _direction_similarity(self, rel: TrackRelationship) -> float:
        """Compare recent direction sequences"""
        if len(rel.target_directions) < 3 or len(rel.follower_directions) < 3:
            return 0.0
        
        window = min(len(rel.target_directions), len(rel.follower_directions), 10)
        matches = 0
        for i in range(1, window):
            if rel.target_directions[-i] == rel.follower_directions[-i]:
                matches += 1
        
        return matches / (window - 1) if window > 1 else 0.0
    
    def _trajectory_similarity(self, rel: TrackRelationship) -> float:
        """Compare trajectory shapes over window"""
        if len(rel.target_positions) < 3 or len(rel.follower_positions) < 3:
            return 0.0
        
        window = min(len(rel.target_positions), len(rel.follower_positions), 20)
        tp = list(rel.target_positions)[-window:]
        fp = list(rel.follower_positions)[-window:]
        
        similarities = []
        for i in range(1, window):
            tv = (tp[i][0] - tp[i-1][0], tp[i][1] - tp[i-1][1])
            fv = (fp[i][0] - fp[i-1][0], fp[i][1] - fp[i-1][1])
            
            tv_norm = math.hypot(*tv)
            fv_norm = math.hypot(*fv)
            
            if tv_norm > 1.0 and fv_norm > 1.0:
                dot = tv[0] * fv[0] + tv[1] * fv[1]
                sim = max(0.0, dot / (tv_norm * fv_norm))
                similarities.append(sim)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _turn_match_score(self, rel: TrackRelationship) -> float:
        """Fraction of turns that were matched by follower"""
        if not rel.turn_matches:
            return 0.0
        matches = sum(1 for m in rel.turn_matches if m)
        return matches / len(rel.turn_matches)
    
    def _compute_turn_match(self, rel: TrackRelationship) -> bool:
        """Determine if follower matched target's most recent turn"""
        if len(rel.target_turns) == 0 or len(rel.follower_turns) == 0:
            return False
        
        target_turn = rel.target_turns[-1]
        if abs(target_turn) < self.config['turn_match_angle_threshold']:
            return False  # Not a significant turn
        
        # Check if follower turned similarly within delay tolerance
        for i in range(min(len(rel.follower_turns), self.config['turn_match_delay_tolerance'])):
            f_turn = rel.follower_turns[-(i+1)]
            if abs(f_turn) >= self.config['turn_match_angle_threshold']:
                # Check direction similarity of turn
                if (target_turn > 0 and f_turn > 0) or (target_turn < 0 and f_turn < 0):
                    return True
        
        return False
    
    def _is_walking_together(self, rel: TrackRelationship) -> bool:
        """
        Detect walking-together pattern (false positive for following):
        - Stable distance (small variance)
        - Same direction
        - Coordinated movement
        - NO suspicious convergence pattern
        """
        if len(rel.distances) < 10:
            return False
        
        # Check distance stability
        dist_std = np.std(list(rel.distances)[-10:]) if len(rel.distances) >= 10 else 0.0
        if dist_std > self.config['distance_stability_tolerance']:
            return False  # Distance varies - could be following
        
        # Check if there's convergence (following requires some)
        convergence = self._check_convergence(rel)[0]
        if convergence > 0.3:
            return False  # Has convergence - likely following
        
        # Check direction match
        dir_sim = self._direction_similarity(rel)
        if dir_sim > 0.8:
            return True  # Stable distance + same direction = walking together
        
        return False
    
    def _build_result(
        self,
        rel: TrackRelationship,
        score: float,
        dist: float,
        evidence: List[str],
        now: float
    ) -> Dict[str, Any]:
        """Build structured following event"""
        # Distance trend
        if len(rel.distances) >= 2:
            if rel.distances[-1] < rel.distances[0]:
                trend = "decreasing"
            elif rel.distances[-1] > rel.distances[0]:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        duration = now - rel.first_seen
        
        return {
            "behavior": "following",
            "target_id": rel.target_id,
            "follower_id": rel.follower_id,
            "score": round(score, 1),
            "duration_seconds": round(duration, 1),
            "distance_meters": round(dist / 100.0, 2),  # Approximate pixels -> meters
            "distance_trend": trend,
            "direction_similarity": round(self._direction_similarity(rel), 3),
            "velocity_similarity": round(self._velocity_similarity(rel), 3),
            "trajectory_similarity": round(self._trajectory_similarity(rel), 3),
            "turn_match_score": round(self._turn_match_score(rel), 3),
            "evidence": evidence,
            "timestamp": now,
        }
    
    def _cleanup_stale(self, now: float, stale_seconds: float = 5.0):
        """Remove stale relationships"""
        stale = [
            pair for pair, rel in self.relationships.items()
            if now - rel.last_seen > stale_seconds
        ]
        for pair in stale:
            del self.relationships[pair]
            if pair in self.active_follows:
                del self.active_follows[pair]
    
    def _point_distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    
    def _angle_between_vectors(self, v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
        """Angle in degrees between two vectors"""
        v1_norm = math.hypot(*v1)
        v2_norm = math.hypot(*v2)
        if v1_norm < 1e-6 or v2_norm < 1e-6:
            return 0.0
        dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (v1_norm * v2_norm)
        dot = max(-1.0, min(1.0, dot))
        return math.degrees(math.acos(dot))
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "active_relationships": len(self.relationships),
            "active_follows": len(self.active_follows),
        }
