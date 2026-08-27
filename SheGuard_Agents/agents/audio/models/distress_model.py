from typing import Optional, Dict, Any
import numpy as np

from agents.audio.schemas import AudioConfig, Transcription, DistressSignal

class DistressDetector:
    def __init__(self, config: AudioConfig):
        self.config = config
        self.sensitivity = config.distress_sensitivity
        self._loaded = False
        
    def initialize(self) -> bool:
        # For now, we use a rule-based approach
        # In the future, this could be replaced with an actual audio classification model
        self._loaded = True
        print('[DistressDetector] Rule-based distress detector initialized')
        return True
    
    def detect(self, audio_data: np.ndarray, transcription: Optional[Transcription]) -> DistressSignal:
        if not self._loaded:
            return DistressSignal(detected=False, type='none', confidence=0.0)
        
        # Calculate audio features
        rms = float(np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))) / 32768.0
        zero_crossings = np.sum(np.diff(np.signbit(audio_data))) / len(audio_data)
        
        distress_detected = False
        distress_type = 'none'
        confidence = 0.0
        details = {
            'rms_energy': rms,
            'zero_crossing_rate': float(zero_crossings)
        }
        
        # Check for keyword-based distress
        if transcription and transcription.text:
            text = transcription.text.lower()
            emergency_keywords = ['help', 'bachao', 'madad', 'sos', 'emergency', 'danger']
            for kw in emergency_keywords:
                if kw in text:
                    distress_detected = True
                    distress_type = 'keyword'
                    confidence = max(confidence, transcription.confidence or 0.8)
                    details['keyword'] = kw
                    break
        
        # Check for audio-based distress (high energy, high zero crossing = potential scream)
        if rms > 0.3 and zero_crossings > 0.1:
            # Potential scream/distress sound
            audio_confidence = min(1.0, (rms - 0.2) * 2)
            if audio_confidence > self.sensitivity:
                distress_detected = True
                if distress_type == 'keyword':
                    distress_type = 'combined'
                    confidence = max(confidence, audio_confidence)
                else:
                    distress_type = 'sound'
                    confidence = max(confidence, audio_confidence)
                details['audio_distress'] = True
        
        return DistressSignal(
            detected=distress_detected,
            type=distress_type,
            confidence=confidence,
            details=details
        )
    
    def close(self):
        self._loaded = False
