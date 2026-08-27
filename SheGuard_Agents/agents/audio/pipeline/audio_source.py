from typing import Optional, List
import numpy as np
import sounddevice as sd

from agents.audio.schemas import AudioConfig, AudioSourceType

class AudioSource:
    def __init__(self, config: AudioConfig):
        self.config = config
        self.stream = None
        self.sample_rate = config.audio_sample_rate
        self.channels = config.audio_channels
        self.chunk_size = int(config.audio_sample_rate * config.audio_chunk_seconds)
        self._buffer = []
        
    def open(self) -> bool:
        try:
            if self.config.audio_source_type == AudioSourceType.MICROPHONE:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.chunk_size,
                    dtype='int16'
                )
                self.stream.start()
                return True
            elif self.config.audio_source_type == AudioSourceType.VIDEO_FILE:
                print('[AudioSource] Video file audio extraction not yet implemented')
                return False
            else:
                print(f'[AudioSource] Unsupported source type: {self.config.audio_source_type}')
                return False
        except Exception as e:
            print(f'[AudioSource] Failed to open: {e}')
            return False
    
    def capture(self) -> Optional[np.ndarray]:
        if not self.stream:
            return None
        try:
            data, overflowed = self.stream.read(self.chunk_size)
            if overflowed:
                print('[AudioSource] Buffer overflow')
            # Convert to mono if stereo
            if self.channels > 1:
                data = np.mean(data, axis=1).astype(np.int16)
            else:
                data = data.flatten().astype(np.int16)
            return data
        except Exception as e:
            print(f'[AudioSource] Capture error: {e}')
            return None
    
    def is_open(self) -> bool:
        return self.stream is not None and self.stream.active
    
    def close(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None

def list_audio_devices():
    import sounddevice as sd
    devices = sd.query_devices()
    input_devices = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            input_devices.append({'index': i, 'name': d['name'], 'channels': d['max_input_channels']})
    return input_devices
