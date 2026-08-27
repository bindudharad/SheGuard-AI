from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time
import asyncio
import cv2
import numpy as np

from core.agent import BaseAgent, AgentMessage, AgentStatus
from core.event_bus import EventBus, AgentRegistry
from agents.vision.schemas import (
    VisionConfig, VisionOutput, Detection, TrackingData, 
    PoseData, PoseLandmark, InteractionData, ActivityData, TemporalData, VideoSourceType
)
from agents.vision.config import get_vision_config
from agents.vision.pipeline.video_source import VideoSource, VideoSourceError, VideoFrame
from agents.vision.pipeline.detector import YOLODetector, YOLODetection
from agents.vision.pipeline.tracker import PersonTracker, TrackedPerson
from agents.vision.pipeline.pose_estimator import MediaPipePoseEstimator, PoseResult
from agents.vision.pipeline.temporal_buffer import TemporalBuffer
from agents.vision.pipeline.activity_classifier import ActivityClassifier
from agents.vision.pipeline.interaction_detector import InteractionDetector
from agents.vision.pipeline.following_detector import FollowingDetector
from agents.vision.pipeline.event_queue import BackendEventQueue, EventPriority, get_event_queue, set_event_queue

# Import behavior engine if available
try:
    from agents.vision.pipeline.behavior_engine import BehaviorEngine
    BEHAVIOR_ENGINE_AVAILABLE = True
except ImportError:
    BEHAVIOR_ENGINE_AVAILABLE = False
    print("[VisionAgent] BehaviorEngine not available")


class VisionAgent(BaseAgent):
    def __init__(self, config: Optional[VisionConfig] = None):
        super().__init__("vision_agent", "2.0.0")
        self.config = config or get_vision_config()
        self.video_source: Optional[VideoSource] = None
        self.detector: Optional[YOLODetector] = None
        self.tracker: Optional[PersonTracker] = None
        self.pose_estimator: Optional[MediaPipePoseEstimator] = None
        self.activity_classifier: Optional[ActivityClassifier] = None
        self.interaction_detector: Optional[InteractionDetector] = None
        self.following_detector: Optional[FollowingDetector] = None
        self.behavior_engine: Optional['BehaviorEngine'] = None
        self.event_queue: Optional[BackendEventQueue] = None
        
        self.frame_id = 0
        self.last_frame: Optional[np.ndarray] = None
        self.running = False
        self._process_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self.metrics = {
            'frames_processed': 0,
            'yolo_inferences': 0,
            'tracker_frames': 0,
            'mediapipe_invocations': 0,
            'optical_flow_invocations': 0,
            'gru_invocations': 0,
            'backend_queue_size': 0,
            'backend_latency': 0.0,
            'dropped_low_priority': 0,
            'fps': 0.0,
            'last_metrics_log': 0.0,
        }
        self._frame_times = []
        self._last_yolo_frame = -999999
        
    async def _initialize(self) -> None:
        # Initialize video source
        self.video_source = VideoSource(self.config)
        if not self.video_source.open():
            self._set_status(AgentStatus.ERROR)
            raise RuntimeError("Failed to open video source")
        
        # Initialize detector
        self.detector = YOLODetector(self.config)
        if not self.detector.load():
            self._set_status(AgentStatus.ERROR)
            raise RuntimeError("Failed to load YOLO model")
        self._health.component_status["yolo"] = "READY"
        
        # Initialize tracker
        self.tracker = PersonTracker(self.config)
        self._health.component_status["tracking"] = "READY"
        
        # Initialize pose estimator
        self.pose_estimator = MediaPipePoseEstimator(self.config)
        if not self.pose_estimator.initialize():
            self._health.component_status["mediapipe"] = "ERROR"
            # Continue without pose - degraded mode
        else:
            self._health.component_status["mediapipe"] = "READY"
        
        # Initialize activity classifier
        self.activity_classifier = ActivityClassifier(self.config)
        self.activity_classifier.initialize()
        if self.activity_classifier.gru_loaded:
            self._health.component_status["gru"] = "READY"
        else:
            self._health.component_status["gru"] = "NOT_LOADED"
        
        # Initialize interaction detector
        self.interaction_detector = InteractionDetector(self.config)
        
        # Initialize following detector
        self.following_detector = FollowingDetector()
        self._health.component_status["following"] = "READY"
        
        # Initialize behavior engine
        if BEHAVIOR_ENGINE_AVAILABLE:
            self.behavior_engine = BehaviorEngine()
            self._health.component_status["behavior_engine"] = "READY"
        
        # Initialize async event queue
        self.event_queue = BackendEventQueue(worker_count=2)
        await self.event_queue.start()
        set_event_queue(self.event_queue)
        self._health.component_status["event_queue"] = "READY"
        
        self._health.component_status["video_source"] = "CONNECTED"
        self._set_status(AgentStatus.READY)
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        # Process single frame request
        if message.event_type == "PROCESS_FRAME":
            result = await self._process_single_frame()
            # Also publish to event bus for orchestrator
            await EventBus.publish_event(
                event_type="FRAME_PROCESSED",
                data=result.to_dict(),
                agent=self.name,
                incident_id=message.incident_id,
                trace_id=message.trace_id,
                confidence=result.visual_risk_signal
            )
            return AgentMessage.create(
                agent=self.name,
                event_type="FRAME_PROCESSED",
                data=result.to_dict(),
                incident_id=message.incident_id,
                trace_id=message.trace_id,
                confidence=result.visual_risk_signal
            )
        
        # Start continuous processing
        elif message.event_type == "START_PROCESSING":
            await self._start_continuous_processing()
            return AgentMessage.create(
                agent=self.name,
                event_type="PROCESSING_STARTED",
                data={"status": "started"},
                trace_id=message.trace_id
            )
        
        # Stop continuous processing
        elif message.event_type == "STOP_PROCESSING":
            await self._stop_continuous_processing()
            return AgentMessage.create(
                agent=self.name,
                event_type="PROCESSING_STOPPED",
                data={"status": "stopped"},
                trace_id=message.trace_id
            )
        
        # Get current state
        elif message.event_type == "GET_STATE":
            return AgentMessage.create(
                agent=self.name,
                event_type="STATE_RESPONSE",
                data=self._get_current_state(),
                trace_id=message.trace_id
            )
        
        return None
    
    async def _process_single_frame(self) -> VisionOutput:
        start_time = time.time()
        
        # Read frame
        frame_data = self.video_source.read()
        if frame_data is None:
            return VisionOutput(
                frame_id=self.frame_id,
                source=self.config.video_source,
                visual_risk_signal=0.0,
                evidence=["No frame available"]
            )
        
        frame = frame_data.frame
        self.frame_id = frame_data.frame_id
        self.metrics['frames_processed'] += 1
        
        now = time.time()
        
        # === PHASE A: Hierarchical processing ===
        # Check if YOLO detection needed
        should_detect = self.tracker._should_detect(self.frame_id, frame)
        
        if should_detect:
            self.metrics['yolo_inferences'] += 1
            self._last_yolo_frame = self.frame_id
            yolo_detections = self.detector.detect(frame)
            detections = [
                Detection(
                    track_id=None,
                    class_id=d.class_id,
                    class_name=d.class_name,
                    confidence=d.confidence,
                    bbox=d.bbox
                )
                for d in yolo_detections
            ]
            tracked = self.tracker.update(detections, now, frame)
        else:
            # Tracker-only frame (no YOLO)
            tracked = self.tracker.update([], now, frame)
            detections = []
        
        self.metrics['tracker_frames'] += 1
        
        # === PHASE A2/A4: Staged pose and behavior ===
        pose_results = []
        tracking_data = []
        suspicious_tracks = []
        
        for track in tracked:
            # Cheap movement/trajectory analysis
            is_suspicious = self._is_track_suspicious(track)
            if is_suspicious:
                suspicious_tracks.append(track.track_id)
            
            # Only run expensive pose estimation if suspicious OR tracking confidence degraded
            pose = None
            if (self.pose_estimator and self.config.pose_enabled and 
                (is_suspicious or track.tracker_confidence < self.config.tracker_confidence_threshold * 1.5)):
                pose_result = self.pose_estimator.estimate(
                    frame, track.bbox, track.track_id
                )
                if pose_result:
                    self.metrics['mediapipe_invocations'] += 1
                    pose = PoseData(
                        track_id=pose_result.track_id,
                        landmarks={
                            k: PoseLandmark(x=v[0], y=v[1], visibility=v[2])
                            for k, v in pose_result.landmarks.items()
                        },
                        keypoints=pose_result.keypoints,
                        head=pose_result.head,
                        hip=pose_result.hip,
                        shoulder=pose_result.shoulder,
                        visible=pose_result.visible,
                        confidence=pose_result.confidence
                    )
                    pose_results.append(pose)
            
            # Tracking data
            td = TrackingData(
                track_id=track.track_id,
                bbox=track.bbox,
                center=track.center,
                speed=track.speed,
                direction=track.direction,
                distance_travelled=track.distance_travelled,
                presence_duration=track.presence_duration,
                pose=pose
            )
            tracking_data.append(td)
        
        # === PHASE A6: Staged GRU ===
        # Only run GRU for candidate suspicious tracks
        activities = []
        for track in tracking_data:
            activity = None
            if self.activity_classifier and self.activity_classifier.gru_loaded:
                if track.track_id in suspicious_tracks or track.speed > 10:
                    self.metrics['gru_invocations'] += 1
                    activity = self.activity_classifier.classify(track, frame, self.last_frame, now)
            if activity is None:
                activity = ActivityData(label="normal", confidence=0.0)
            activities.append(activity)
        
        # Determine overall activity (highest confidence)
        overall_activity = max(activities, key=lambda a: a.confidence) if activities else ActivityData()
        
        # === Interaction detection ===
        interaction = self.interaction_detector.detect(tracking_data, now)
        
        # === Following detection ===
        following_events = []
        if self.following_detector:
            following_events = self.following_detector.update(tracked, now)
        
        # === Behavior engine ===
        behavior_results = []
        if self.behavior_engine:
            behavior_results = self.behavior_engine.update(tracked, now)
        
        # === Temporal status ===
        temporal_status = TemporalData()
        if tracking_data:
            tid = tracking_data[0].track_id
            temporal_status.ready = self.activity_classifier.temporal_buffer.is_ready(tid) if self.activity_classifier else False
            temporal_status.confidence = overall_activity.temporal_confidence
            temporal_status.sequence_length = self.config.temporal_sequence_length
            temporal_status.frames_buffered = self.activity_classifier.temporal_buffer.get_buffered_count(tid) if self.activity_classifier else 0
        
        # === Compute visual risk signal ===
        visual_risk = self._compute_visual_risk(overall_activity, interaction, len(tracking_data), following_events, behavior_results)
        
        # === Build evidence ===
        evidence = []
        evidence.append(f"Persons detected: {len(tracking_data)}")
        evidence.append(f"YOLO frame: {should_detect} (interval={self.config.yolo_detection_interval})")
        evidence.append(f"Suspicious tracks: {suspicious_tracks}")
        if interaction.detected:
            evidence.append(f"Interaction: {interaction.confidence:.2f} confidence")
        evidence.append(f"Activity: {overall_activity.label} ({overall_activity.confidence:.2f})")
        if following_events:
            for ev in following_events:
                evidence.append(f"FOLLOWING: target={ev['target_id']} follower={ev['follower_id']} score={ev['score']:.0f}")
        for br in behavior_results:
            if br.score >= 50:
                evidence.append(f"{br.behavior.upper()}: score={br.score:.0f} subjects={br.subjects}")
        if temporal_status.ready:
            evidence.append(f"Temporal model: READY")
        else:
            evidence.append(f"Temporal model: WARMING_UP ({temporal_status.frames_buffered} frames)")
        
        # === Performance metrics ===
        processing_time = (time.time() - start_time) * 1000
        self._update_fps(start_time)
        self._log_metrics_if_needed(now)
        
        self.last_frame = frame.copy()
        
        # Build result
        result = VisionOutput(
            frame_id=self.frame_id,
            source=self.config.video_source,
            persons_detected=len(tracking_data),
            detections=detections,
            tracking=tracking_data,
            pose=pose_results,
            interaction=interaction,
            activity=overall_activity,
            temporal=temporal_status,
            visual_risk_signal=visual_risk,
            evidence=evidence,
            processing_time_ms=processing_time,
            simulation=self.config.simulation_mode
        )
        
        # Attach behavior data
        result.following = following_events
        result.behaviors = [b.to_dict() for b in behavior_results] if behavior_results else []
        
        return result
    
    def _is_track_suspicious(self, track: TrackedPerson) -> bool:
        """
        Cheap movement/trajectory analysis to decide if expensive
        pose/GRU should be run on this track.
        """
        # High speed = suspicious
        if track.speed > self.config.attack_speed_threshold:
            return True
        
        # Rapid direction changes
        if len(track.velocity_history) >= 3:
            recent_vels = list(track.velocity_history)[-3:]
            angles = []
            for i in range(1, len(recent_vels)):
                v1 = recent_vels[i-1]
                v2 = recent_vels[i]
                dot = v1[0]*v2[0] + v1[1]*v2[1]
                n1 = math.hypot(*v1)
                n2 = math.hypot(*v2)
                if n1 > 1e-6 and n2 > 1e-6:
                    cos = max(-1, min(1, dot/(n1*n2)))
                    angles.append(abs(math.degrees(math.acos(cos))))
            if angles and max(angles) > 45:
                return True
        
        # Tracking confidence degraded
        if track.tracker_confidence < self.config.tracker_confidence_threshold:
            return True
        
        return False
    
    def _compute_visual_risk(self, activity: ActivityData, interaction: InteractionData, 
                             person_count: int, following_events: List[Dict], 
                             behavior_results: List) -> float:
        risk = 0.0
        
        # Activity-based risk
        activity_risks = {
            "fall": 0.8,
            "attack": 0.9,
            "fight": 0.85,
            "possible_confrontation": 0.7,
            "rapid_movement": 0.4,
            "abnormal_movement": 0.5,
            "warming_up": 0.0,
            "normal": 0.1,
            "unknown": 0.0,
        }
        risk += activity_risks.get(activity.label, 0.0) * activity.confidence
        
        # Interaction risk
        if interaction.detected:
            risk += 0.3 * interaction.confidence
        
        # Following risk (highest among following events)
        if following_events:
            max_follow = max(ev['score'] for ev in following_events)
            risk += (max_follow / 100.0) * 0.6
        
        # Behavior engine risk
        for br in behavior_results:
            if br.score >= 50:
                risk += (br.score / 100.0) * 0.4
        
        # Multiple people slightly increases base risk
        if person_count > 1:
            risk += 0.1 * min(person_count - 1, 3)
        
        return min(1.0, risk)
    
    def _update_fps(self, start_time: float):
        now = time.time()
        self._frame_times.append(now - start_time)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        if self._frame_times:
            avg_time = sum(self._frame_times) / len(self._frame_times)
            self.metrics['fps'] = 1000.0 / avg_time if avg_time > 0 else 0.0
    
    def _log_metrics_if_needed(self, now: float):
        if not self.config.metrics_enabled:
            return
        if now - self.metrics['last_metrics_log'] < self.config.metrics_log_interval / 30.0:
            return
        
        self.metrics['last_metrics_log'] = now
        # Update queue metrics
        if self.event_queue:
            qm = self.event_queue.get_metrics()
            self.metrics['backend_queue_size'] = qm['queue_size']
            self.metrics['dropped_low_priority'] = qm['dropped_low_priority']
        
        # Log concise summary (avoid spam)
        print(f"[VisionAgent Metrics] FPS={self.metrics['fps']:.1f} "
              f"YOLO={self.metrics['yolo_inferences']} "
              f"MP={self.metrics['mediapipe_invocations']} "
              f"GRU={self.metrics['gru_invocations']} "
              f"Queue={self.metrics['backend_queue_size']}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Concise performance summary for reporting"""
        return {
            'frames_processed': self.metrics['frames_processed'],
            'yolo_inferences': self.metrics['yolo_inferences'],
            'yolo_per_frame': round(self.metrics['yolo_inferences'] / max(1, self.metrics['frames_processed']), 3),
            'tracker_frames': self.metrics['tracker_frames'],
            'mediapipe_invocations': self.metrics['mediapipe_invocations'],
            'mediapipe_per_frame': round(self.metrics['mediapipe_invocations'] / max(1, self.metrics['frames_processed']), 4),
            'gru_invocations': self.metrics['gru_invocations'],
            'gru_per_frame': round(self.metrics['gru_invocations'] / max(1, self.metrics['frames_processed']), 4),
            'fps': round(self.metrics['fps'], 1),
            'backend_queue_size': self.metrics['backend_queue_size'],
            'dropped_low_priority': self.metrics['dropped_low_priority'],
        }
    
    def _get_current_state(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "running": self.running,
            "video_source": self.video_source.is_opened() if self.video_source else False,
            "components": self._health.component_status,
            "metrics": self.get_performance_summary(),
        }
    
    async def _start_continuous_processing(self) -> None:
        if self.running:
            return
        self.running = True
        self._process_task = asyncio.create_task(self._processing_loop())
    
    async def _stop_continuous_processing(self) -> None:
        self.running = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
    
    async def _processing_loop(self) -> None:
        frame_interval = 1.0 / self.config.max_fps
        while self.running:
            try:
                result = await self._process_single_frame()
                # Could publish to event bus here
                await asyncio.sleep(frame_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[VisionAgent] Processing error: {e}")
                await asyncio.sleep(1.0)
    
    async def _shutdown(self) -> None:
        await self._stop_continuous_processing()
        if self.event_queue:
            await self.event_queue.stop()
        if self.video_source:
            self.video_source.close()
        if self.detector:
            self.detector.close()
        if self.pose_estimator:
            self.pose_estimator.close()
        if self.activity_classifier:
            self.activity_classifier.close()


import math
