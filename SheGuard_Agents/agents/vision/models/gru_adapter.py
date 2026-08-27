from typing import Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import joblib

try:
    import torch
    from torch import nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None

from agents.vision.schemas import VisionConfig, ActivityData


@dataclass
class GRUPrediction:
    label: str
    confidence: float
    probabilities: Dict[str, float]
    sequence_length: int
    model_status: str


class SequenceGRU(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_classes: int):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_classes = num_classes
        self.gru = nn.GRU(
            input_size, 
            hidden_size, 
            num_layers=2, 
            batch_first=True, 
            dropout=0.0,
            bidirectional=False
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(0.0),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.0),
            nn.Linear(hidden_size // 2, num_classes),
        )
    
    def forward(self, x):
        output, _ = self.gru(x)
        return self.head(output[:, -1, :])


class GRUAdapter:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.device = None
        self.sequence_length = config.temporal_sequence_length
        self.input_size = 116  # From metrics_v2.json
        self.hidden_size = 128
        self.num_classes = 4
        self.classes = ['attack', 'fall', 'fight', 'normal']
        self._loaded = False
        
    def load(self) -> bool:
        if self._loaded:
            return True
            
        try:
            # Load scaler and label encoder
            self.scaler = joblib.load(self.config.gru_scaler_path)
            self.label_encoder = joblib.load(self.config.gru_label_encoder_path)
            self.classes = list(self.label_encoder.classes_)
            
            # Load PyTorch model
            if not TORCH_AVAILABLE:
                print('[GRU] PyTorch not available')
                return False
                
            checkpoint = torch.load(
                self.config.gru_model_path,
                map_location='cpu',
                weights_only=False
            )
            
            self.sequence_length = checkpoint.get('sequence_length', self.sequence_length)
            self.input_size = checkpoint.get('input_size', self.input_size)
            self.hidden_size = checkpoint.get('hidden_size', self.hidden_size)
            self.num_classes = checkpoint.get('num_classes', self.num_classes)
            self.classes = checkpoint.get('classes', self.classes)
            
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            self.model = SequenceGRU(self.input_size, self.hidden_size, self.num_classes)
            self.model.load_state_dict(checkpoint['model_state'], strict=False)
            self.model.to(self.device)
            self.model.eval()
            
            self._loaded = True
            print(f'[GRU] Model loaded: seq_len={self.sequence_length}, input={self.input_size}, classes={self.classes}')
            return True
            
        except Exception as e:
            print(f'[GRU] Failed to load model: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def predict(self, sequence: np.ndarray) -> Optional[GRUPrediction]:
        if not self._loaded or self.model is None:
            return GRUPrediction(
                label='unknown',
                confidence=0.0,
                probabilities={},
                sequence_length=0,
                model_status='NOT_LOADED'
            )
        
        try:
            # sequence shape: (seq_len, features) -> (1, seq_len, features)
            if sequence.ndim == 2:
                sequence = sequence.reshape(1, sequence.shape[0], sequence.shape[1])
            
            # Scale features
            seq_len, feat_dim = sequence.shape[1], sequence.shape[2]
            flat = sequence.reshape(-1, feat_dim)
            scaled = self.scaler.transform(flat).reshape(1, seq_len, feat_dim).astype(np.float32)
            
            # Predict
            with torch.no_grad():
                tensor = torch.tensor(scaled, dtype=torch.float32, device=self.device)
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
            
            pred_idx = int(np.argmax(probs))
            label = self.classes[pred_idx] if pred_idx < len(self.classes) else 'unknown'
            confidence = float(probs[pred_idx])
            probabilities = {self.classes[i]: float(probs[i]) for i in range(min(len(self.classes), len(probs)))}
            
            return GRUPrediction(
                label=label,
                confidence=confidence,
                probabilities=probabilities,
                sequence_length=self.sequence_length,
                model_status='READY'
            )
        except Exception as e:
            print(f'[GRU] Prediction error: {e}')
            import traceback
            traceback.print_exc()
            return GRUPrediction(
                label='error',
                confidence=0.0,
                probabilities={},
                sequence_length=0,
                model_status='ERROR'
            )
    
    def close(self):
        self.model = None
        self._loaded = False
