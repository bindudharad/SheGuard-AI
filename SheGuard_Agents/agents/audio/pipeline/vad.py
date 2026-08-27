from typing import Optional
import numpy as np
import torch

from agents.audio.schemas import AudioConfig

class VoiceActivityDetector:
    def __init__(self, config: AudioConfig):
        self.config = config
        self.model = None
        self._loaded = False
        
    def initialize(self) -> bool:
        try:
            # Use Silero VAD
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self.model.eval()
            self._loaded = True
            print('[VAD] Silero VAD loaded successfully')
            return True
        except Exception as e:
            print(f'[VAD] Failed to load Silero VAD: {e}')
            return False
    
    def detect(self, audio_data: np.ndarray) -> bool:
        if not self._loaded or self.model is None:
            return True  # Default to speech if VAD unavailable
        
        try:
            # Silero expects 16kHz mono float32 in range [-1, 1]
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Ensure correct length for 16kHz (512 samples = 32ms)
            if len(audio_float) < 512:
                audio_float = np.pad(audio_float, (0, 512 - len(audio_float)))
            elif len(audio_float) > 512:
                audio_float = audio_float[:512]
            
            tensor = torch.from_numpy(audio_float).unsqueeze(0)
            speech_prob = self.model(tensor, 16000).item()
            
            return speech_prob > 0.5
        except Exception as e:
            print(f'[VAD] Detection error: {e}')
            return True  # Default to speech on error
    
    def close(self):
        self.model = None
        self._loaded = False
