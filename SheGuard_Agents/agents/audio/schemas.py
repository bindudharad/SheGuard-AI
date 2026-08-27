from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class AudioSourceType(str, Enum):
    MICROPHONE = 'microphone'
    VIDEO_FILE = 'video_file'
    NETWORK_STREAM = 'network_stream'

class AudioMode(str, Enum):
    REAL = 'real'
    SIMULATION = 'simulation'

class AudioEventType(str, Enum):
    SPEECH_DETECTED = 'SPEECH_DETECTED'
    KEYWORD_DETECTED = 'KEYWORD_DETECTED'
    DISTRESS_AUDIO_DETECTED = 'DISTRESS_AUDIO_DETECTED'
    AUDIO_SILENCE = 'AUDIO_SILENCE'
    AUDIO_ERROR = 'AUDIO_ERROR'
    AUDIO_SOURCE_CONNECTED = 'AUDIO_SOURCE_CONNECTED'
    AUDIO_SOURCE_DISCONNECTED = 'AUDIO_SOURCE_DISCONNECTED'
    AUDIO_AGENT_READY = 'AUDIO_AGENT_READY'
    AUDIO_AGENT_DEGRADED = 'AUDIO_AGENT_DEGRADED'

@dataclass
class Transcription:
    text: str
    language: str = 'auto'
    confidence: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    segments: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class KeywordMatch:
    keyword: str
    category: str
    confidence: float
    matched_text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class DistressSignal:
    detected: bool
    type: str  # 'keyword', 'sound', 'combined'
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AudioFeatures:
    rms_energy: float
    duration_seconds: float
    zero_crossing_rate: Optional[float] = None
    spectral_centroid: Optional[float] = None

@dataclass
class AudioOutput:
    agent: str
    timestamp: str
    source: str
    speech_detected: bool
    transcription: Optional[Transcription] = None
    keywords: List[KeywordMatch] = field(default_factory=list)
    distress: Optional[DistressSignal] = None
    audio_features: Optional[AudioFeatures] = None
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent': self.agent,
            'timestamp': self.timestamp,
            'source': self.source,
            'speech_detected': self.speech_detected,
            'transcription': self.transcription.__dict__ if self.transcription else None,
            'keywords': [k.__dict__ for k in self.keywords],
            'distress': self.distress.__dict__ if self.distress else None,
            'audio_features': self.audio_features.__dict__ if self.audio_features else None,
            'evidence': self.evidence
        }

@dataclass
class AudioConfig:
    audio_enabled: bool = True
    audio_source_type: AudioSourceType = AudioSourceType.MICROPHONE
    audio_device_index: int = 0
    audio_video_path: str = ''
    audio_network_url: str = ''
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_seconds: float = 2.0
    audio_overlap_seconds: float = 0.5
    vad_enabled: bool = True
    vad_aggressiveness: int = 2
    vad_min_speech_duration_ms: int = 250
    vad_max_silence_duration_ms: int = 1000
    stt_model: str = 'faster-whisper'
    stt_model_size: str = 'tiny.en'
    stt_language: str = 'auto'
    stt_device: str = 'cpu'
    stt_compute_type: str = 'int8'
    keyword_enabled: bool = True
    keyword_fuzzy_matching: bool = True
    keyword_similarity_threshold: float = 0.82
    keyword_categories: List[str] = field(default_factory=lambda: ['emergency', 'distress', 'help', 'stop'])
    distress_enabled: bool = True
    distress_sensitivity: float = 0.5
    processing_buffer_size: int = 10
    max_latency_ms: int = 1000
    debug_audio: bool = False
    save_debug_audio: bool = False
    debug_audio_dir: str = 'debug_audio'
    simulation_mode: bool = False
    store_raw_audio: bool = False
    raw_audio_retention_days: int = 7
    raw_audio_dir: str = 'raw_audio'
    models_dir: str = 'models/audio'
