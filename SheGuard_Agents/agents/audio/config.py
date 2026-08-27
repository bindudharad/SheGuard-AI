from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from enum import Enum

class AudioSourceType(str, Enum):
  MICROPHONE = "microphone"
  VIDEO_FILE = "video_file"
  NETWORK_STREAM = "network_stream"

class AudioMode(str, Enum):
  REAL = "real"
  SIMULATION = "simulation"

class AudioSettings(BaseSettings):
  audio_enabled: bool = True
  audio_source_type: AudioSourceType = AudioSourceType.MICROPHONE
  audio_device_index: int = 0
  audio_video_path: str = ""
  audio_network_url: str = ""
  audio_sample_rate: int = 16000
  audio_channels: int = 1
  audio_chunk_seconds: float = 2.0
  audio_overlap_seconds: float = 0.5
  vad_enabled: bool = True
  vad_aggressiveness: int = 2
  vad_min_speech_duration_ms: int = 250
  vad_max_silence_duration_ms: int = 1000
  stt_model: str = "faster-whisper"
  stt_model_size: str = "tiny.en"
  stt_language: str = "auto"
  stt_device: str = "cpu"
  stt_compute_type: str = "int8"
  keyword_enabled: bool = True
  keyword_fuzzy_matching: bool = True
  keyword_similarity_threshold: float = 0.82
  keyword_categories: List[str] = ["emergency", "distress", "help", "stop"]
  distress_enabled: bool = True
  distress_sensitivity: float = 0.5
  processing_buffer_size: int = 10
  max_latency_ms: int = 1000
  debug_audio: bool = False
  save_debug_audio: bool = False
  debug_audio_dir: str = "debug_audio"
  simulation_mode: bool = False
  store_raw_audio: bool = False
  raw_audio_retention_days: int = 7
  raw_audio_dir: str = "raw_audio"
  models_dir: str = "models/audio"
  class Config:
    env_prefix = "AUDIO_"
    env_file = ".env"
    extra = "ignore"

def get_audio_config() -> AudioSettings:
  return AudioSettings()