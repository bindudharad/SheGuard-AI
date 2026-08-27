# Audio Agent - Existing System Audit Report

**Date**: 2026-08-17  
**Component**: SheGuard (Full Project)  
**Purpose**: Document existing audio capabilities for Audio Agent implementation

---

## 1. Existing Audio Functionality

### SheGuard_AI
- **No audio processing found** in main.py, detection.py, feature_extractor.py, tracking.py, video_clipper.py
- Groq client has audio/speech modules but only for API calls (cloud-based)
- No local speech recognition, microphone capture, or audio analysis

### SheGuard_Backend
- **No audio processing** in any service or route
- Telegram service supports photo/video but not audio messages
- Evidence storage handles images/videos only

### SheGuard_agents (Current)
- **No audio agent exists** - only vision and context agents
- Core framework (BaseAgent, EventBus, AgentRegistry) is audio-agnostic

### SheGuard_App (Flutter)
- No audio recording/speech features found in pubspec.yaml or lib/

### SheGuard_Dashboard (React)
- No audio visualization or playback components

---

## 2. Existing Speech-Recognition Libraries

**NOT FOUND** - No local speech recognition library is currently used in the project.

Available in environment (venv):
- groq.audio.speech - Cloud API only (Whisper via Groq)
- mediapipe.tasks.audio - Audio classifier/embedder (not speech-to-text)

---

## 3. Existing Audio Models

**NOT FOUND** - No local audio models (Whisper, Vosk, etc.) present in:
- SheGuard_AI/models/
- SheGuard_agents/models/
- SheGuard_Backend/models/

---

## 4. Existing Whisper/Vosk/etc. Implementation

**NOT FOUND** - No Whisper, faster-whisper, Vosk, or other STT implementation exists.

---

## 5. Existing Microphone Code

**NOT FOUND** - No microphone capture code in the project.

---

## 6. Existing Video-Audio Extraction

**NOT FOUND** - Video processing exists (OpenCV) but audio extraction from video files is not implemented.

---

## 7. Existing FFmpeg Setup

**NOT FOUND** - FFmpeg is not referenced in any Python code. Not in requirements.txt.

---

## 8. Existing Python Audio Dependencies

**Current requirements.txt (SheGuard_agents)**:
`
opencv-python
mediapipe==0.10.14
ultralytics
numpy
torch
scikit-learn
joblib
pydantic
pydantic-settings
pyyaml
fastapi
uvicorn
requests
httpx
pytest
pytest-asyncio
`

**Missing audio dependencies**:
- sounddevice / pyaudio (microphone capture)
- librosa / torchaudio (audio processing)
- faster-whisper / whisper / vosk (speech recognition)
- webrtcvad / silero-vad (VAD)
- ffmpeg-python (video audio extraction)

---

## 9. Existing Agent Architecture

**Reusable - SheGuard_agents/core/**:
- gent.py - BaseAgent class with health monitoring, async processing
- vent_bus.py - EventBus with pub/sub, AgentRegistry for agent management
- Message format: AgentMessage with event_id, timestamp, agent, event_type, confidence, data, trace_id, incident_id

**Vision Agent Pattern** (agents/vision/):
- Config via Pydantic Settings (env_file=.env, env_prefix=VISION_)
- Pipeline modules: video_source, detector, tracker, pose_estimator, temporal_buffer, activity_classifier, interaction_detector
- Schemas via Pydantic models
- Tests in agents/vision/tests/

---

## 10. Existing Event System

**EventBus** (core/event_bus.py):
- Async pub/sub with asyncio.Queue per event_type
- AgentRegistry for agent discovery and health
- AgentMessage.create() factory for structured events
- Supports trace_id for request tracing

---

## 11. Existing Errors

**NOT FOUND** - No audio-related errors since no audio code exists.

---

## 12. Reusable Components

| Component | Location | Reusable For Audio Agent |
|-----------|----------|-------------------------|
| BaseAgent | core/agent.py | YES - inherit for AudioAgent |
| EventBus | core/event_bus.py | YES - publish audio events |
| AgentRegistry | core/event_bus.py | YES - register audio agent |
| Pydantic Config | agents/vision/config.py | YES - pattern for AudioConfig |
| Pipeline Pattern | agents/vision/pipeline/ | YES - structure for audio pipeline |
| Schemas | agents/vision/schemas.py | YES - pattern for AudioOutput schema |
| VideoSource | agents/vision/pipeline/video_source.py | YES - pattern for AudioSource |
| Tests Pattern | agents/vision/tests/ | YES - pattern for audio tests |

---

## 13. Duplicate Components

**NOT FOUND** - No audio code exists to duplicate.

---

## 14. Missing Functionality (Complete Implementation Required)

1. **Audio Capture**: Microphone, video file audio extraction, network streams
2. **Audio Preprocessing**: Resampling, mono conversion, normalization
3. **Voice Activity Detection (VAD)**: Separate speech from silence/noise
4. **Speech-to-Text**: Local STT (faster-whisper recommended for CPU)
5. **Keyword Detection**: Emergency keywords (EN/HI/KN) with fuzzy matching
6. **Distress Sound Detection**: Scream/cry/distress vocalization detection
7. **Structured Audio Output**: Standardized event schema
8. **Event Bus Integration**: Publish DISTRESS_AUDIO_DETECTED events
9. **Health Monitoring**: Component-level status (VAD, STT, keyword, distress)
10. **Configuration**: Environment-based config for all audio parameters
11. **Simulation Mode**: For testing without hardware
12. **Privacy Controls**: No permanent raw audio storage by default

---

## 15. Recommended Implementation

### Speech Recognition: faster-whisper
- **Reason**: CPU-optimized (CTranslate2), supports 99+ languages, no GPU required
- **Model**: tiny.en (39MB) or base (74MB) for English; small (244MB) for multilingual
- **Fits**: Torch 2.5.1+cpu environment, Python 3.10

### VAD: webrtcvad or silero-vad
- **webrtcvad**: Lightweight, proven, no ML dependencies
- **silero-vad**: Better accuracy, ONNX runtime, slightly heavier

### Audio Capture: sounddevice
- **Reason**: Cross-platform, low latency, supports Windows WASAPI
- **Alternative**: pyaudio (more complex setup on Windows)

### Keyword Detection: Custom implementation
- Normalized text matching with rapidfuzz for fuzzy matching
- Configurable keyword dictionaries per language
- Transliteration support for Hindi/Kannada

### Distress Detection: 
- **Phase 1**: Acoustic features (RMS, ZCR, spectral centroid) + rule-based
- **Phase 2**: silero-vad or custom classifier for scream/cry detection

### Architecture:
`
AudioAgent (BaseAgent)
├── AudioSource (microphone/video/file)
├── Preprocessing (resample, normalize, mono)
├── VAD (webrtcvad)
├── SpeechRecognizer (faster-whisper adapter)
├── KeywordDetector (exact + fuzzy)
├── DistressDetector (acoustic + optional ML)
└── Analyzer (combine signals -> structured output)
`

### Event Types to Publish:
- SPEECH_DETECTED
- KEYWORD_DETECTED  
- DISTRESS_KEYWORD_DETECTED
- DISTRESS_SOUND_DETECTED
- AUDIO_ERROR
- AUDIO_SOURCE_CONNECTED/DISCONNECTED
- AUDIO_AGENT_READY/DEGRADED

---

## 16. Environment Check

| Check | Status |
|-------|--------|
| Python 3.10+ | 3.10.11 |
| Torch CPU | 2.5.1+cpu |
| NumPy | (in requirements) |
| FFmpeg | ? (system check needed) |
| Microphone | ? (hardware check needed) |
| sounddevice | Not installed |
| faster-whisper | Not installed |
| webrtcvad | Not installed |
| rapidfuzz | Not installed |

---

## 17. Next Steps

1. Create Audio Agent directory structure
2. Add audio dependencies to requirements.txt
3. Implement AudioConfig (Pydantic Settings)
4. Implement AudioSource (microphone, video file)
5. Implement Preprocessing + VAD
6. Implement SpeechRecognizer adapter (faster-whisper)
7. Implement KeywordDetector (multilingual + fuzzy)
8. Implement DistressDetector (acoustic features)
9. Implement AudioAgent (BaseAgent integration)
10. Create schemas, tests, documentation
11. Integrate with EventBus
12. Test with real microphone and video files
