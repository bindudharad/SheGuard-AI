# Full Bug Report - SheGuard AI+

## Summary
Total Bugs Found: 15
- Critical: 5
- High: 5  
- Medium: 3
- Low: 2

## Critical Bugs (5) - ALL FIXED

### BUG-001: VisionAgent Not Publishing to EventBus
- Severity: CRITICAL
- Component: agents/vision/agent.py
- Root Cause: VisionAgent._process() returned AgentMessage but never called EventBus.publish_event()
- Fix: Added EventBus.publish_event() call in PROCESS_FRAME handler
- Status: FIXED

### BUG-002: Orchestrator Not Extracting Nested Vision Data
- Severity: CRITICAL
- Component: core/orchestrator.py:_handle_vision()
- Root Cause: VisionOutput uses nested structures but orchestrator accessed flat keys
- Fix: Added nested extraction: interaction.get("detected"), activity.get("label")
- Status: FIXED

### BUG-003: Multiple Agents Missing incident_id in EventBus.publish_event()
- Severity: CRITICAL
- Components: agents/context/agent.py, agents/threat/agent.py, agents/decision/agent.py, agents/response/agent.py
- Root Cause: EventBus.publish_event() called without incident_id parameter
- Fix: Added incident_id to all EventBus.publish_event() calls
- Status: FIXED

### BUG-004: Orchestrator Timestamp Format Mismatch
- Severity: CRITICAL
- Component: core/orchestrator.py:_maybe_request_threat_assessment()
- Root Cause: ContextResult.timestamp is datetime but ThreatRequest expects string
- Fix: Added datetime -> isoformat() conversion
- Status: FIXED

### BUG-005: Orchestrator Data Format Transformation Missing
- Severity: CRITICAL
- Component: core/orchestrator.py:_maybe_request_threat_assessment() and _handle_intelligence_response()
- Root Cause: Stored VisionOutput/ContextResult formats differ from ThreatRequest formats
- Fix: Added complete transformation functions
- Status: FIXED

## High Bugs (5) - ALL FIXED

### BUG-006: ThreatRequest Schema Missing Intelligence Field
- Severity: HIGH
- Component: agents/threat/schemas.py
- Fix: Added intelligence field to ThreatRequest
- Status: FIXED

### BUG-007: Intelligence Score Scale Mismatch
- Severity: HIGH
- Component: agents/threat/agent.py:_assess_threat()
- Root Cause: Intelligence risk_score (0-100) normalized to 0-1 but other scores 0-100
- Fix: Removed /100 normalization
- Status: FIXED

### BUG-008: Intelligence Contribution After Total Score
- Severity: HIGH
- Component: agents/threat/agent.py:_assess_threat()
- Root Cause: Intelligence calculated after total_score
- Fix: Moved intelligence before total_score calculation
- Status: FIXED

### BUG-009: Intelligence Weight Too Low
- Severity: HIGH
- Component: agents/threat/agent.py
- Root Cause: Intelligence used same context_weight (0.25)
- Fix: Increased intelligence weight to 0.5
- Status: FIXED

### BUG-010: Audio VAD Unavailable on Windows
- Severity: HIGH
- Component: agents/audio/agent.py
- Root Cause: Silero VAD fails with WinError 127 on Windows
- Fix: Graceful degradation - continues without VAD
- Status: PARTIALLY FIXED (OS limitation)

## Medium Bugs (3) - NOT FIXED (Production Blockers)

### BUG-011: No Persistent Database
- Severity: MEDIUM
- Component: core/orchestrator.py
- Status: NOT FIXED

### BUG-012: No API Authentication
- Severity: MEDIUM
- Component: api/main.py
- Status: NOT FIXED

### BUG-013: x402 Real Payments Untested
- Severity: MEDIUM
- Component: agents/x402/agent.py
- Status: NOT FIXED

## Low Bugs (2)

### BUG-014: GRU Temporal Model Warmup
- Severity: LOW
- Component: agents/vision/pipeline/activity_classifier.py
- Status: DOCUMENTED (Expected behavior)

### BUG-015: sklearn Version Mismatch Warning
- Severity: LOW
- Component: agents/vision/models/gru
- Status: PARTIAL (Warning only, works)

## Regression Tests After Fixes - ALL PASS
1. test_e2e_pipeline.py - PASSES
2. API integration test - PASSES
3. Direct agent process() calls - PASS
4. Full pipeline trace verification - PASS
5. Multiple concurrent incidents - PASS (no cross-contamination)
6. Incident/Trace ID integrity - PASS

## Remaining Production Blockers
1. Add persistent database
2. Add API authentication
3. Add HTTPS/TLS
4. Real x402/Algorand integration
5. Real Telegram bot
6. Intelligence weight tuning
7. WebSocket support
8. Rate limiting, audit logging
