import sys
import asyncio
sys.path.insert(0, '.')

from agents.vision.agent import VisionAgent
from agents.vision.config import get_vision_config
from agents.audio.agent import AudioAgent
from agents.audio.config import get_audio_config
from agents.context.agent import ContextAgent
from agents.context.config import get_context_config

async def test_all():
    print('=== Testing Vision Agent ===')
    cfg = get_vision_config()
    cfg.simulation_mode = True
    agent = VisionAgent(cfg)
    await agent.initialize()
    health = await agent.health()
    print('Vision:', health.to_dict()['status'])
    await agent.shutdown()
    
    print()
    print('=== Testing Audio Agent ===')
    cfg = get_audio_config()
    cfg.simulation_mode = True
    agent = AudioAgent(cfg)
    await agent.initialize()
    health = await agent.health()
    print('Audio:', health.to_dict()['status'])
    await agent.shutdown()
    
    print()
    print('=== Testing Context Agent ===')
    cfg = get_context_config()
    agent = ContextAgent(cfg)
    await agent.initialize()
    health = await agent.health()
    print('Context:', health.to_dict()['status'])
    await agent.shutdown()

asyncio.run(test_all())
print('ALL AGENTS INITIALIZED SUCCESSFULLY')
