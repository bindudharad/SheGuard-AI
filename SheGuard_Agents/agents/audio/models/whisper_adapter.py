from typing import Optional
import numpy as np
import torch

from agents.audio.schemas import AudioConfig, Transcription

class WhisperAdapter:
    def __init__(self, config: AudioConfig):
        self.config = config
        self.model = None
        self._loaded = False
        
    def initialize(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.config.stt_model_size,
                device=self.config.stt_device,
                compute_type=self.config.stt_compute_type
            )
            self._loaded = True
            print(f'[STT] faster-whisper model {self.config.stt_model_size} loaded on {self.config.stt_device}')
            return True
        except Exception as e:
            print(f'[STT] Failed to load faster-whisper: {e}')
            return False
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[Transcription]:
        if not self._loaded or self.model is None:
            return None
        
        try:
            # Convert to float32
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # faster-whisper expects mono audio
            if len(audio_float.shape) > 1:
                audio_float = np.mean(audio_float, axis=1)
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_float,
                language=self.config.stt_language if self.config.stt_language != 'auto' else None,
                beam_size=1,
                best_of=1,
                temperature=0.0
            )
            
            full_text = ' '.join([seg.text for seg in segments]).strip()
            if not full_text:
                return None
            
            # Calculate average confidence from segment probabilities
            confidences = []
            seg_list = []
            for seg in segments:
                seg_list.append({
                    'text': seg.text,
                    'start': seg.start,
                    'end': seg.end,
                    'avg_logprob': seg.avg_logprob
                })
                # Convert logprob to probability
                conf = np.exp(seg.avg_logprob) if seg.avg_logprob < 0 else 1.0
                confidences.append(conf)
            
            avg_confidence = float(np.mean(confidences)) if confidences else 0.0
            
            return Transcription(
                text=full_text,
                language=info.language,
                confidence=avg_confidence,
                start_time=seg_list[0]['start'] if seg_list else None,
                end_time=seg_list[-1]['end'] if seg_list else None,
                segments=seg_list
            )
        except Exception as e:
            print(f'[STT] Transcription error: {e}')
            return None
    
    def is_loaded(self) -> bool:
        return self._loaded
    
    def close(self):
        self.model = None
        self._loaded = False
