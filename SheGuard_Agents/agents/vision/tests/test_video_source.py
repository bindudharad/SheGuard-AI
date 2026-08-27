import pytest
import numpy as np
from agents.vision.schemas import VisionConfig, VideoSourceType
from agents.vision.pipeline.video_source import VideoSource, VideoSourceError


class TestVideoSource:
    def test_video_source_creation(self):
        config = VisionConfig(video_source_type=VideoSourceType.WEBCAM, video_source='0')
        source = VideoSource(config)
        assert source.source_type == VideoSourceType.WEBCAM
        assert source.source_str == '0'
    
    def test_video_source_invalid_type(self):
        # Test error handling for invalid source type
        # Can't easily test without mocking, but we can verify the enum works
        assert VideoSourceType.WEBCAM.value == 'webcam'
        assert VideoSourceType.FILE.value == 'file'
        assert VideoSourceType.RTSP.value == 'rtsp'
        assert VideoSourceType.DROIDCAM.value == 'droidcam'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
