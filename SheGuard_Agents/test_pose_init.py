import sys
sys.path.insert(0, '.')
from agents.vision.config import get_vision_config
from agents.vision.pipeline.pose_estimator import MediaPipePoseEstimator

cfg = get_vision_config()
print('Config loaded')

estimator = MediaPipePoseEstimator(cfg)
print('Estimator created')
result = estimator.initialize()
print('Initialize result:', result)
print('SUCCESS')
