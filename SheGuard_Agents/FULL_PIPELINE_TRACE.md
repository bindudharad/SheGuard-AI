# Full Pipeline Trace - Test Incident SG-E2E-TRACE-001

## Trace Information
- Incident ID: SG-E2E-TRACE-001
- Trace ID: TRACE-E2E-TRACE-001
- Mode: Simulation

## Pipeline Execution Trace

### Vision Agent
- Event: PROCESS_FRAME -> FRAME_PROCESSED
- Input: incident_id=SG-E2E-TRACE-001, camera_id=CAM-01, simulation=true
- Output: persons_detected=0, interaction.detected=false, activity.label=unknown, visual_risk_signal=0.0
- Event Published: FRAME_PROCESSED to EventBus with incident_id and trace_id

### Orchestrator (_handle_vision)
- Received: FRAME_PROCESSED event
- Action: Extracted nested interaction.detected and activity.label
- Published: CONTEXT_REQUEST to EventBus with incident_id

### Context Agent
- Event: CONTEXT_REQUEST -> CONTEXT_UPDATED
- Output: context_score=0.1075, time_period=late_night, isolation_status=ELEVATED
- Event Published: CONTEXT_UPDATED to EventBus with incident_id

### Orchestrator (_handle_context)
- Received: CONTEXT_UPDATED event
- Action: Both vision_data and context_data present -> THREAT_ASSESS
- Published: THREAT_ASSESS with transformed VisionSignal/ContextSignal

### Threat Agent
- Event: THREAT_ASSESS -> THREAT_UPDATED
- Processing: Vision (0) + Context (10.75) weighted = 2.69 risk
- Output: risk_score=2.69, threat_level=SAFE, confidence=0.6
- Event Published: THREAT_UPDATED to EventBus with incident_id

### Orchestrator (_handle_threat)
- Received: THREAT_UPDATED event
- Action: Published DECISION_REQUEST to DecisionAgent

### Decision Agent
- Event: THREAT_UPDATED -> DECISION_MADE
- Processing: risk < 29 (safe_max) -> CONTINUE_MONITORING
- Output: decision=CONTINUE_MONITORING
- Event Published: DECISION_MADE to EventBus with incident_id

### Orchestrator (_handle_decision)
- Received: DECISION_MADE event
- Action: Decision is CONTINUE_MONITORING -> No further action

## Pipeline Summary
Vision -> Orchestrator -> Context -> Orchestrator -> Threat -> Orchestrator -> Decision -> Orchestrator
All incident_id and trace_id preserved throughout. No cross-contamination between incidents.

## Moderate Threat Trace (SG-MOD-001)
Vision: persons=2, interaction=true (0.78), activity=possible_confrontation (0.82)
Context: score=0.68, late_night, elevated isolation
Threat: risk=50.17, level=SAFE, conf=0.82
Decision: INCREASE_MONITORING

## Critical Threat Trace (SG-CRIT-001)
Vision: persons=2, interaction=true (0.95), activity=attack (0.95)
Audio: distress=HELP (0.95)
Context: score=0.95, late_night, elevated isolation
Threat: risk=75.24, level=WARNING, conf=0.9
Decision: CREATE_INCIDENT
Response: ACTIVE (GET_LOCATION, NOTIFY_GUARDIAN, UPDATE_DASHBOARD)

## x402 Intelligence Flow Trace (SG-X402-001)
Initial: Threat risk=50.17 -> Decision INCREASE_MONITORING
Intelligence: risk_score=94.0, confidence=0.94
Re-evaluation: Threat risk=47.0 (intelligence added but weight limited)
Final Decision: INCREASE_MONITORING
