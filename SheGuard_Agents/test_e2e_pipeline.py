import sys
import asyncio
import uuid
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
from core.agent import AgentMessage, AgentHealth
from core.event_bus import EventBus
from datetime import datetime

async def test_full_pipeline():
    print('=== FULL END-TO-END PIPELINE TEST ===')
    print()
    
    # Initialize all agents
    print('1. Initializing all agents...')
    
    vision_cfg = get_vision_config()
    vision_cfg.simulation_mode = True
    vision = VisionAgent(vision_cfg)
    await vision.initialize()
    
    audio_cfg = get_audio_config()
    audio_cfg.simulation_mode = True
    audio = AudioAgent(audio_cfg)
    await audio.initialize()
    
    context_cfg = get_context_config()
    context = ContextAgent(context_cfg)
    await context.initialize()
    
    threat = ThreatAgent(ThreatWeights())
    await threat.initialize()
    
    decision = DecisionAgent()
    await decision.initialize()
    
    x402 = X402Agent()
    await x402.initialize()
    
    response = ResponseAgent()
    await response.initialize()
    
    print('   All agents initialized successfully')
    print()
    
    trace_id = str(uuid.uuid4())
    incident_id = 'SG-TEST-001'
    
    print('2. Simulating vision frame processing...')
    print('   Vision: 2 persons, interaction detected, activity: possible_confrontation')
    print()
    
    print('3. Requesting context...')
    context_message = AgentMessage.create(
        agent='context_agent',
        event_type='CONTEXT_REQUEST',
        data={
            'incident_id': incident_id,
            'trace_id': trace_id,
            'camera_id': 'CAM-04',
            'latitude': 13.3392,
            'longitude': 77.1015,
            'person_count': 2,
            'interaction_participants': 2,
            'timestamp': datetime.utcnow(),
            'simulation': True
        },
        trace_id=trace_id,
        incident_id=incident_id,
        confidence=0.0
    )
    
    context_result = await context.process(context_message)
    c_event = context_result.event_type if context_result else 'None'
    print('   Context result:', c_event)
    if context_result:
        ctx_data = context_result.data
        cs = ctx_data.get('context_score', 0)
        cc = ctx_data.get('context_confidence', 0)
        print('   Context score:', cs)
        print('   Context confidence:', cc)
    print()
    
    print('4. Assessing threat...')
    threat_message = AgentMessage.create(
        agent='threat_agent',
        event_type='THREAT_ASSESS',
        data={
            'incident_id': incident_id,
            'trace_id': trace_id,
            'vision': {
                'agent': 'vision_agent',
                'timestamp': datetime.utcnow().isoformat(),
                'persons_detected': 2,
                'interaction_detected': True,
                'interaction_confidence': 0.78,
                'activity_label': 'possible_confrontation',
                'activity_confidence': 0.82,
                'temporal_confidence': 0.85,
                'visual_risk_signal': 0.75,
                'evidence': ['two persons detected', 'persistent interaction', 'abnormal movement pattern'],
                'simulation': True
            },
            'audio': None,
            'context': {
                'agent': 'context_agent',
                'timestamp': datetime.utcnow().isoformat(),
                'context_score': 0.68,
                'context_confidence': 0.85,
                'data_quality': 0.92,
                'time_period': 'late_night',
                'isolation_status': 'ELEVATED',
                'nearby_incidents': 2,
                'security_distance_meters': 180.0,
                'reasons': ['late-night period', 'elevated historical activity', 'nearby incidents', 'limited security proximity'],
                'simulation': True
            },
            'simulation': True
        },
        trace_id=trace_id,
        incident_id=incident_id,
        confidence=0.0
    )
    
    threat_result = await threat.process(threat_message)
    t_event = threat_result.event_type if threat_result else 'None'
    print('   Threat result:', t_event)
    if threat_result:
        th_data = threat_result.data
        rs = th_data.get('risk_score', 0)
        tl = th_data.get('threat_level', 'UNKNOWN')
        tt = th_data.get('threat_type', 'UNKNOWN')
        conf = th_data.get('confidence', 0)
        reasons = th_data.get('reasons', [])
        print('   Risk score:', rs)
        print('   Threat level:', tl)
        print('   Threat type:', tt)
        print('   Confidence:', conf)
        print('   Reasons:', reasons)
    print()
    
    print('5. Making decision...')
    if threat_result:
        th_data = threat_result.data
        decision_message = AgentMessage.create(
            agent='decision_agent',
            event_type='THREAT_UPDATED',
            data={
                'incident_id': incident_id,
                'trace_id': trace_id,
                'risk_score': th_data.get('risk_score', 0),
                'threat_level': th_data.get('threat_level', 'SAFE'),
                'threat_type': th_data.get('threat_type', 'none'),
                'confidence': th_data.get('confidence', 0),
                'vision_available': True,
                'audio_available': False,
                'context_available': True,
                'uncertainty': 1.0 - th_data.get('confidence', 0),
                'previous_decisions': 0,
                'timestamp': datetime.utcnow(),
                'simulation': True
            },
            trace_id=trace_id,
            incident_id=incident_id,
            confidence=th_data.get('confidence', 0)
        )
        
        decision_result = await decision.process(decision_message)
        d_event = decision_result.event_type if decision_result else 'None'
        print('   Decision result:', d_event)
        if decision_result:
            dec_data = decision_result.data
            dec = dec_data.get('decision', 'UNKNOWN')
            reasoning = dec_data.get('reasoning', '')
            next_agent = dec_data.get('next_agent', 'NONE')
            print('   Decision:', dec)
            print('   Reasoning:', reasoning)
            print('   Next agent:', next_agent)
    print()
    
    if decision_result and decision_result.data.get('decision') == 'REQUEST_ADDITIONAL_INTELLIGENCE':
        print('6. Requesting additional intelligence (x402)...')
        x402_message = AgentMessage.create(
            agent='x402_agent',
            event_type='ADDITIONAL_INTELLIGENCE_REQUIRED',
            data={
                'incident_id': incident_id,
                'trace_id': trace_id,
                'risk_score': th_data.get('risk_score', 0),
                'threat_level': th_data.get('threat_level', 'SAFE'),
                'vision': None,
                'audio': None,
                'context': None,
                'evidence': None,
                'simulation': True
            },
            trace_id=trace_id,
            incident_id=incident_id,
            confidence=0.0
        )
        
        x402_result = await x402.process(x402_message)
        x_event = x402_result.event_type if x402_result else 'None'
        print('   X402 result:', x_event)
        if x402_result:
            x402_data = x402_result.data
            pid = x402_data.get('payment_id', '')
            state = x402_data.get('state', '')
            ir = x402_data.get('risk_score', 0)
            ic = x402_data.get('confidence', 0)
            print('   Payment ID:', pid)
            print('   State:', state)
            print('   Intelligence risk:', ir)
            print('   Intelligence confidence:', ic)
    else:
        print('6. Skipping x402 (decision was confident)')
    print()
    
    print('7. Executing response...')
    if threat_result:
        th_data = threat_result.data
        response_message = AgentMessage.create(
            agent='response_agent',
            event_type='EMERGENCY_DECLARED',
            data={
                'incident_id': incident_id,
                'trace_id': trace_id,
                'decision': 'EMERGENCY_RESPONSE',
                'risk_score': th_data.get('risk_score', 0),
                'threat_level': th_data.get('threat_level', 'CRITICAL'),
                'threat_type': th_data.get('threat_type', 'possible_confrontation'),
                'confidence': th_data.get('confidence', 0),
                'vision_data': {},
                'audio_data': {},
                'context_data': {},
                'intelligence_data': {},
                'simulation': True
            },
            trace_id=trace_id,
            incident_id=incident_id,
            confidence=th_data.get('confidence', 0)
        )
        
        response_result = await response.process(response_message)
        r_event = response_result.event_type if response_result else 'None'
        print('   Response result:', r_event)
        if response_result:
            resp_data = response_result.data
            iid = resp_data.get('incident_id', '')
            status = resp_data.get('status', '')
            actions = resp_data.get('actions_taken', [])
            evidence_count = len(resp_data.get('evidence', []))
            notif_count = len(resp_data.get('notifications', []))
            print('   Incident ID:', iid)
            print('   Status:', status)
            print('   Actions:', actions)
            print('   Evidence count:', evidence_count)
            print('   Notifications:', notif_count)
    print()
    
    print('8. Shutting down all agents...')
    for agent in [vision, audio, context, threat, decision, x402, response]:
        await agent.shutdown()
    
    print()
    print('=== FULL PIPELINE TEST COMPLETE ===')

asyncio.run(test_full_pipeline())
