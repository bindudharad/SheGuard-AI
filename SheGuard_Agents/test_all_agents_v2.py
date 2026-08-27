import sys
import asyncio
sys.path.insert(0, '.')

from agents.vision.agent import VisionAgent
from agents.vision.config import get_vision_config
from agents.audio.agent import AudioAgent
from agents.audio.config import get_audio_config
from agents.context.agent import ContextAgent
from agents.context.config import get_context_config
from agents.threat.agent import ThreatAgent
from agents.threat.schemas import ThreatWeights
from agents.decision.agent import DecisionAgent
from agents.x402.agent import X402Agent
from agents.response.agent import ResponseAgent

async def test_all_agents():
    print('=== Testing all agents ===')
    
    # Vision
    print('Initializing Vision Agent...')
    cfg = get_vision_config()
    cfg.simulation_mode = True
    vision = VisionAgent(cfg)
    await vision.initialize()
    health = await vision.health()
    status = health.to_dict()['status']
    print('Vision:', status)
    
    # Audio
    print('Initializing Audio Agent...')
    cfg = get_audio_config()
    cfg.simulation_mode = True
    audio = AudioAgent(cfg)
    await audio.initialize()
    health = await audio.health()
    status = health.to_dict()['status']
    print('Audio:', status)
    
    # Context
    print('Initializing Context Agent...')
    cfg = get_context_config()
    context = ContextAgent(cfg)
    await context.initialize()
    health = await context.health()
    status = health.to_dict()['status']
    print('Context:', status)
    
    # Threat
    print('Initializing Threat Agent...')
    threat = ThreatAgent(ThreatWeights())
    await threat.initialize()
    health = await threat.health()
    status = health.to_dict()['status']
    print('Threat:', status)
    
    # Decision
    print('Initializing Decision Agent...')
    decision = DecisionAgent()
    await decision.initialize()
    health = await decision.health()
    status = health.to_dict()['status']
    print('Decision:', status)
    
    # x402
    print('Initializing X402 Agent...')
    x402 = X402Agent()
    await x402.initialize()
    health = await x402.health()
    status = health.to_dict()['status']
    print('X402:', status)
    
    # Response
    print('Initializing Response Agent...')
    response = ResponseAgent()
    await response.initialize()
    health = await response.health()
    status = health.to_dict()['status']
    print('Response:', status)
    
    print()
    print('ALL AGENTS INITIALIZED SUCCESSFULLY')
    
    # Shutdown all
    for agent in [vision, audio, context, threat, decision, x402, response]:
        await agent.shutdown()

asyncio.run(test_all_agents())
