import sys, asyncio
sys.path.insert(0, '.')
from agents.vision.agent import VisionAgent
from agents.vision.config import get_vision_config

async def test():
    cfg = get_vision_config()
    cfg.simulation_mode = True  # Use simulation for testing
    agent = VisionAgent(cfg)
    print('Agent created')
    await agent.initialize()
    print('Agent initialized, status:', agent.status)
    health = await agent.health()
    print('Health:', health.to_dict())
    await agent.shutdown()
    print('Shutdown OK')

asyncio.run(test())
