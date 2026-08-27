import asyncio
import uuid
import sys
sys.path.insert(0, '.')
from agents.context.agent import ContextAgent
from agents.context.config import get_context_config
from agents.threat.agent import ThreatAgent
from agents.threat.schemas import ThreatWeights, ThreatLevel
from agents.decision.agent import DecisionAgent
from agents.x402.agent import X402Agent
from agents.response.agent import ResponseAgent
from core.agent import AgentMessage
from datetime import datetime

async def test_pipeline():
    print('=== PHASE I: END-TO-END PIPELINE TEST ===')
    print()
    
    print('1. Agent initialization...')
    context = ContextAgent(get_context_config())
    await context.initialize()
    threat = ThreatAgent(ThreatWeights())
    await threat.initialize()
    decision = DecisionAgent()
    await decision.initialize()
    x402 = X402Agent()
    await x402.initialize()
    response = ResponseAgent()
    await response.initialize()
    print('   PASS: All agents initialized')
    print()
    
    trace_id = str(uuid.uuid4())
    incident_id = 'SG-TEST-001'
    
    print('2. Context agent...')
    context_msg = AgentMessage.create(
        agent='context_agent', event_type='CONTEXT_REQUEST',
        data={'incident_id': incident_id, 'trace_id': trace_id, 'camera_id': 'CAM-04',
              'latitude': 13.3392, 'longitude': 77.1015, 'person_count': 2,
              'interaction_participants': 2, 'timestamp': datetime.utcnow(), 'simulation': True},
        trace_id=trace_id, incident_id=incident_id, confidence=0.0)
    ctx_result = await context.process(context_msg)
    assert ctx_result is not None
    assert ctx_result.event_type == 'CONTEXT_UPDATED'
    ctx_score = ctx_result.data.get('context_score', 0)
    print('   PASS: Context score =', round(ctx_score, 4))
    print()
    
    print('3. Threat agent...')
    threat_msg = AgentMessage.create(
        agent='threat_agent', event_type='THREAT_ASSESS',
        data={'incident_id': incident_id, 'trace_id': trace_id,
              'intelligence': {
                  'following_events': [{'target_id': 'P1', 'follower_id': 'P2', 'score': 75, 'confidence': 0.85}],
                  'behavioral_events': [{'behavior': 'following', 'score': 75, 'subjects': ['P1', 'P2']]}},
              'simulation': True},
        trace_id=trace_id, incident_id=incident_id, confidence=0.8)
    threat_result = await threat.process(threat_msg)
    assert threat_result is not None
    risk_level = threat_result.data.get('risk_level', 'unknown')
    risk_score = threat_result.data.get('risk_score', 0)
    print('   PASS: Risk level =', risk_level, ', score =', risk_score)
    print()
    
    print('4. Decision agent...')
    dec_msg = AgentMessage.create(
        agent='threat_agent', event_type='THREAT_ESCALATED',
        data={'incident_id': incident_id, 'trace_id': trace_id, 'risk_score': risk_score,
              'risk_level': risk_level, 'behaviors': ['following'], 'confidence': 0.85},
        trace_id=trace_id, incident_id=incident_id, confidence=0.85)
    dec_result = await decision.process(dec_msg)
    if dec_result:
        print('   PASS: Decision =', dec_result.data.get('decision', 'none'))
    else:
        print('   NOTE: Decision agent returned None')
    print()
    
    print('5. X402 agent (simulation)...')
    x402_msg = AgentMessage.create(
        agent='x402_agent', event_type='X402_PAYMENT_REQUEST',
        data={'incident_id': incident_id, 'trace_id': trace_id, 'amount': 100, 'simulation': True},
        trace_id=trace_id, incident_id=incident_id, confidence=0.0)
    x402_result = await x402.process(x402_msg)
    if x402_result:
        print('   PASS: X402 result =', x402_result.event_type)
    else:
        print('   NOTE: X402 agent returned None')
    print()
    
    print('6. Response agent...')
    resp_msg = AgentMessage.create(
        agent='decision_agent', event_type='EMERGENCY_DECLARED',
        data={'incident_id': incident_id, 'trace_id': trace_id, 'decision': 'EMERGENCY_RESPONSE',
              'required_action': 'EMERGENCY_RESPONSE', 'confidence': 0.85},
        trace_id=trace_id, incident_id=incident_id, confidence=0.85)
    resp_result = await response.process(resp_msg)
    if resp_result:
        print('   PASS: Response =', resp_result.event_type)
    else:
        print('   NOTE: Response agent returned None (backend not running)')
    print()
    
    print('7. ThreatLevel enum...')
    levels = [e.value for e in ThreatLevel]
    assert 'EMERGENCY' in levels
    print('   PASS: Valid levels =', levels)
    print()
    
    print('=== PHASE I TESTS COMPLETED ===')

asyncio.run(test_pipeline())
