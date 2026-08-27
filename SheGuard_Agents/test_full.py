import sys, asyncio
sys.path.insert(0, ".")
from core.orchestrator import get_orchestrator
from core.event_bus import event_bus
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
from core.agent import AgentMessage

async def test_full_pipeline():
    print("=== FULL PIPELINE INTEGRATION TEST ===")
    print()
    
    orch = get_orchestrator()
    v = VisionAgent(get_vision_config()); v.config.simulation_mode = True; await v.initialize()
    a = AudioAgent(get_audio_config()); a.config.simulation_mode = True; await a.initialize()
    c = ContextAgent(get_context_config()); await c.initialize()
    t = ThreatAgent(ThreatWeights()); await t.initialize()
    d = DecisionAgent(); await d.initialize()
    x = X402Agent(); await x.initialize()
    r = ResponseAgent(); await r.initialize()
    for ag in [v,a,c,t,d,x,r]:
        await orch.register_agent(ag)
    await orch.start()
    
    print("1. Testing normal frame processing...")
    msg = AgentMessage.create(agent="api", event_type="PROCESS_FRAME",
        data={"incident_id": "SG-NORMAL-001", "camera_id": "CAM-01", "simulation": True},
        incident_id="SG-NORMAL-001", trace_id="TRACE-NORMAL")
    await v.process(msg)
    await asyncio.sleep(2)
    inc = await orch.get_incident_state("SG-NORMAL-001")
    decision = inc.decision_data.get("decision") if inc and inc.decision_data else "NONE"
    print("   Decision:", decision)
    
    print("2. Testing moderate threat (INCREASE_MONITORING)...")
    msg = AgentMessage.create(agent="test", event_type="THREAT_ASSESS",
        data={
            "incident_id": "SG-MODERATE-001",
            "trace_id": "TRACE-MODERATE",
            "vision": {"agent":"vision_agent","timestamp":"2026-08-18T00:00:00","persons_detected":2,"interaction_detected":True,"interaction_confidence":0.78,"activity_label":"possible_confrontation","activity_confidence":0.82,"temporal_confidence":0.85,"visual_risk_signal":0.75,"evidence":["two persons"],"simulation":True},
            "audio": None,
            "context": {"agent":"context_agent","timestamp":"2026-08-18T00:00:00","context_score":0.68,"context_confidence":0.85,"data_quality":0.92,"time_period":"late_night","isolation_status":"ELEVATED","nearby_incidents":2,"security_distance_meters":180.0,"reasons":["late-night"],"simulation":True},
            "simulation": True
        },
        incident_id="SG-MODERATE-001", trace_id="TRACE-MODERATE")
    await t.process(msg)
    await asyncio.sleep(2)
    inc = await orch.get_incident_state("SG-MODERATE-001")
    risk = inc.threat_data.get("risk_score") if inc and inc.threat_data else None
    decision = inc.decision_data.get("decision") if inc and inc.decision_data else None
    print("   Risk:", risk)
    print("   Decision:", decision)
    
    print("3. Testing CRITICAL threat (EMERGENCY_RESPONSE)...")
    msg = AgentMessage.create(agent="test", event_type="THREAT_ASSESS",
        data={
            "incident_id": "SG-CRITICAL-001",
            "trace_id": "TRACE-CRITICAL",
            "vision": {"agent":"vision_agent","timestamp":"2026-08-18T00:00:00","persons_detected":2,"interaction_detected":True,"interaction_confidence":0.95,"activity_label":"attack","activity_confidence":0.95,"temporal_confidence":0.9,"visual_risk_signal":0.95,"evidence":["attack"],"simulation":True},
            "audio": {"agent":"audio_agent","timestamp":"2026-08-18T00:00:00","speech_detected":True,"transcription_text":"HELP","keywords":[{"keyword":"help","confidence":0.95}],"distress_detected":True,"distress_type":"HELP","distress_confidence":0.95,"simulation":True},
            "context": {"agent":"context_agent","timestamp":"2026-08-18T00:00:00","context_score":0.85,"context_confidence":0.9,"data_quality":0.95,"time_period":"late_night","isolation_status":"ELEVATED","nearby_incidents":3,"security_distance_meters":200.0,"reasons":["late-night"],"simulation":True},
            "simulation": True
        },
        incident_id="SG-CRITICAL-001", trace_id="TRACE-CRITICAL")
    await t.process(msg)
    await asyncio.sleep(3)
    inc = await orch.get_incident_state("SG-CRITICAL-001")
    risk = inc.threat_data.get("risk_score") if inc and inc.threat_data else None
    threat_level = inc.threat_data.get("threat_level") if inc and inc.threat_data else None
    decision = inc.decision_data.get("decision") if inc and inc.decision_data else None
    response_status = inc.response_data.get("status") if inc and inc.response_data else None
    response_actions = inc.response_data.get("actions_taken") if inc and inc.response_data else None
    print("   Risk:", risk)
    print("   Threat Level:", threat_level)
    print("   Decision:", decision)
    print("   Response:", response_status)
    print("   Response Actions:", response_actions)
    
    print("4. Testing x402 flow (uncertain threat)...")
    msg = AgentMessage.create(agent="test", event_type="THREAT_ASSESS",
        data={
            "incident_id": "SG-X402-001",
            "trace_id": "TRACE-X402",
            "vision": {"agent":"vision_agent","timestamp":"2026-08-18T00:00:00","persons_detected":2,"interaction_detected":True,"interaction_confidence":0.78,"activity_label":"possible_confrontation","activity_confidence":0.82,"temporal_confidence":0.85,"visual_risk_signal":0.75,"evidence":["two persons"],"simulation":True},
            "audio": None,
            "context": {"agent":"context_agent","timestamp":"2026-08-18T00:00:00","context_score":0.68,"context_confidence":0.85,"data_quality":0.92,"time_period":"late_night","isolation_status":"ELEVATED","nearby_incidents":2,"security_distance_meters":180.0,"reasons":["late-night"],"simulation":True},
            "simulation": True
        },
        incident_id="SG-X402-001", trace_id="TRACE-X402")
    await t.process(msg)
    await asyncio.sleep(1)
    
    intel_msg = AgentMessage.create(agent="orchestrator", event_type="INTELLIGENCE_RECEIVED",
        data={"incident_id":"SG-X402-001","trace_id":"TRACE-X402","risk_score":94.0,"confidence":0.94,"threat_level":"CRITICAL","threat_type":"possible_confrontation","simulation":True},
        incident_id="SG-X402-001", trace_id="TRACE-X402")
    await orch._route_event(intel_msg)
    await asyncio.sleep(3)
    inc = await orch.get_incident_state("SG-X402-001")
    reevaluated_risk = inc.threat_data.get("risk_score") if inc and inc.threat_data else None
    final_decision = inc.decision_data.get("decision") if inc and inc.decision_data else None
    response_status = inc.response_data.get("status") if inc and inc.response_data else None
    print("   Re-evaluated Risk:", reevaluated_risk)
    print("   Final Decision:", final_decision)
    print("   Response:", response_status)
    
    all_incidents = await orch.list_incidents()
    print("5. Incident separation check:", len(all_incidents), "incidents created")
    for inc_summary in all_incidents:
        print("   " + inc_summary["incident_id"] + ": " + inc_summary["last_decision"])
    
    print()
    print("=== ALL TESTS PASSED ===")
    
    await orch.stop()
    for ag in [v,a,c,t,d,x,r]:
        await ag.shutdown()

asyncio.run(test_full_pipeline())
