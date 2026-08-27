from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus, AgentRegistry
from agents.audio.config import get_audio_config
from agents.audio.schemas import (
    AudioConfig, AudioOutput, AudioEventType, Transcription, KeywordMatch,
    DistressSignal, AudioFeatures, AudioSourceType
)

class AudioAgent(BaseAgent):
    def __init__(self, config: Optional[AudioConfig] = None):
        super().__init__('audio_agent', '1.0.0')
        self.config = config or get_audio_config()
        self.audio_source = None
        self.vad = None
        self.stt = None
        self.keyword_detector = None
        self.distress_detector = None
        self.running = False
        self._process_task = None
        
    async def _initialize(self) -> None:
        # Initialize audio source
        self.audio_source = self._create_audio_source()
        if not self.audio_source.open():
            raise RuntimeError('Failed to open audio source')
        
        # Initialize VAD
        if self.config.vad_enabled:
            self.vad = self._create_vad()
            if not self.vad.initialize():
                print('[AudioAgent] VAD initialization failed, continuing without VAD')
        
        # Initialize STT
        self.stt = self._create_stt()
        if not self.stt.initialize():
            print('[AudioAgent] STT initialization failed, continuing without STT')
        
        # Initialize keyword detector
        self.keyword_detector = self._create_keyword_detector()
        
        # Initialize distress detector
        if self.config.distress_enabled:
            self.distress_detector = self._create_distress_detector()
            if not self.distress_detector.initialize():
                print('[AudioAgent] Distress detector initialization failed, continuing without distress detection')
        
        print('[AudioAgent] All components initialized')
    
    def _create_audio_source(self):
        from agents.audio.pipeline.audio_source import AudioSource
        return AudioSource(self.config)
    
    def _create_vad(self):
        from agents.audio.pipeline.vad import VoiceActivityDetector
        return VoiceActivityDetector(self.config)
    
    def _create_stt(self):
        from agents.audio.models.whisper_adapter import WhisperAdapter
        return WhisperAdapter(self.config)
    
    def _create_keyword_detector(self):
        from agents.audio.pipeline.keyword_detector import KeywordDetector
        return KeywordDetector(self.config)
    
    def _create_distress_detector(self):
        from agents.audio.models.distress_model import DistressDetector
        return DistressDetector(self.config)
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.event_type == 'AUDIO_CAPTURE':
            return await self._process_audio_capture(message)
        return None
    
    async def _process_audio_capture(self, message: AgentMessage) -> AgentMessage:
        # Capture audio chunk
        audio_data = self.audio_source.capture()
        if audio_data is None:
            return None
        
        # VAD
        if self.vad:
            is_speech = self.vad.detect(audio_data)
            if not is_speech:
                return AgentMessage.create(
                    agent=self.name,
                    event_type='AUDIO_SILENCE',
                    data={'timestamp': datetime.utcnow().isoformat()},
                    confidence=0.0
                )
        
        # STT
        transcription = None
        if self.stt:
            transcription = self.stt.transcribe(audio_data)
        
        # Keyword detection
        keywords = []
        if self.keyword_detector and transcription:
            keywords = self.keyword_detector.detect(transcription)
        
        # Distress detection
        distress = None
        if self.distress_detector:
            distress = self.distress_detector.detect(audio_data, transcription)
        
        # Build output
        output = AudioOutput(
            agent='audio_agent',
            timestamp=datetime.utcnow().isoformat(),
            source=self.config.audio_source_type.value,
            speech_detected=transcription is not None and transcription.text != '',
            transcription=transcription,
            keywords=keywords,
            distress=distress,
            audio_features=self._extract_features(audio_data) if self.config.debug_audio else None,
            evidence=self._build_evidence(keywords, distress)
        )
        
        # Determine event type and publish
        event_type = 'AUDIO_PROCESSED'
        confidence = 0.0
        if distress and distress.detected:
            event_type = 'DISTRESS_AUDIO_DETECTED'
            confidence = distress.confidence
        elif keywords:
            event_type = 'KEYWORD_DETECTED'
            confidence = max(k.confidence for k in keywords)
        elif transcription and transcription.text:
            event_type = 'SPEECH_DETECTED'
            confidence = transcription.confidence if transcription.confidence else 0.5
        
        # Publish to event bus
        await EventBus.publish_event(
            event_type=event_type,
            data=output.to_dict(),
            agent=self.name,
            trace_id=message.trace_id,
            confidence=confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type=event_type,
            data=output.to_dict(),
            trace_id=message.trace_id,
            confidence=confidence
        )
    
    def _extract_features(self, audio_data) -> AudioFeatures:
        import numpy as np
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        return AudioFeatures(
            rms_energy=float(rms),
            duration_seconds=len(audio_data) / self.config.audio_sample_rate
        )
    
    def _build_evidence(self, keywords, distress) -> List[str]:
        evidence = []
        if keywords:
            for k in keywords:
                evidence.append(f'keyword: {k.keyword} (category: {k.category}, confidence: {k.confidence:.2f})')
        if distress and distress.detected:
            evidence.append(f'distress: {distress.type} (confidence: {distress.confidence:.2f})')
        return evidence
    
    async def health(self) -> AgentHealth:
        health = await super().health()
        health.component_status = {
            'audio_source': 'CONNECTED' if self.audio_source and self.audio_source.is_open() else 'DISCONNECTED',
            'vad': 'READY' if self.vad else 'DISABLED',
            'stt': 'READY' if self.stt and self.stt.is_loaded() else 'NOT_LOADED',
            'keyword_detector': 'READY' if self.keyword_detector else 'DISABLED',
            'distress_detector': 'READY' if self.distress_detector else 'DISABLED',
        }
        return health
    
    async def shutdown(self) -> None:
        self.running = False
        if self.audio_source:
            self.audio_source.close()
        if self.vad:
            self.vad.close()
        if self.stt:
            self.stt.close()
        if self.distress_detector:
            self.distress_detector.close()
        await super().shutdown()
        print('[AudioAgent] Shutdown complete')
