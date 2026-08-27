# 7-Agent Bug Report

## Summary
Total Bugs Found: 8
- Critical: 2 (FIXED)
- High: 3 (FIXED)
- Medium: 2 (PRODUCTION BLOCKERS - Not Fixed)
- Low: 1 (DOCUMENTED)

---

## Critical Bugs (FIXED)

### BUG-001: Vision Agent PoseLandmark Schema Mismatch
- Severity: CRITICAL
- Component: agents/vision/agent.py, agents/vision/schemas.py
- Root Cause: Vision agent created pose landmarks as dynamic type('obj', ...) objects instead of PoseLandmark dataclass, causing AttributeError in to_dict() when serializing landmarks.
- Fix: Added PoseLandmark to imports and changed landmark creation to use PoseLandmark(x=v[0], y=v[1], visibility=v[2])
- Test: test_e2e_pipeline.py - Vision frame processing now works end-to-end
- Status: FIXED

### BUG-002: Event Bus Missing Correlation IDs
- Severity: CRITICAL
- Component: Multiple agents publishing events
- Root Cause: Some agents called EventBus.publish_event() without incident_id and trace_id, breaking traceability.
- Fix: Ensured all event publications include proper incident_id and trace_id parameters.
- Test: Comprehensive pipeline test - all 4 incidents maintain correct IDs through full pipeline.
- Status: FIXED

---

## High Bugs (FIXED)

### BUG-003: Audio VAD Windows Incompatibility
- Severity: HIGH
- Component: agents/audio/agent.py, agents/audio/models/vad.py
- Root Cause: Silero VAD fails with WinError 127 on Windows due to missing shared library.
- Fix: Added graceful degradation - logs warning and continues without VAD when initialization fails.
- Test: Audio agent initializes successfully in simulation mode.
- Status: FIXED (Graceful Degradation)

### BUG-004: Orchestrator Data Format Transformation Missing
- Severity: HIGH
- Component: core/orchestrator.py _maybe_request_threat_assessment()
- Root Cause: Vision output uses nested structures (interaction.detected, activity.label) but ThreatAgent expects flat VisionSignal schema.
- Fix: Added transformation logic to convert nested VisionOutput to flat VisionSignal format.
- Test: Moderate and Critical threat scenarios work correctly.
- Status: FIXED

### BUG-005: x402 Intelligence Re-evaluation Loop Incomplete
- Severity: HIGH
- Component: agents/decision/agent.py, agents/x402/agent.py, core/orchestrator.py
- Root Cause: Decision agent's _process_intelligence() didn't properly trigger threat re-analysis through orchestrator.
- Fix: Verified complete flow: Decision REQUEST_INTELLIGENCE -> x402 -> INTELLIGENCE_RECEIVED -> Orchestrator routes to ThreatAgent for re-analysis -> DecisionAgent re-evaluates.
- Test: x402 intelligence flow test passes (Test 4 in comprehensive test).
- Status: FIXED

---

## Medium Bugs (PRODUCTION BLOCKERS - Not Fixed)

### BUG-006: No Persistent Database
- Severity: MEDIUM
- Component: core/orchestrator.py
- Root Cause: IncidentContext stored in memory dictionary self.incidents: Dict[str, IncidentContext] = {}
- Impact: All incident data lost on restart, no audit trail, no horizontal scaling.
- Fix Required: Add PostgreSQL/SQLite with SQLAlchemy migrations, persist incident state.
- Status: NOT FIXED - Production Blocker

### BUG-007: No API Authentication
- Severity: MEDIUM
- Component: api/main.py
- Root Cause: No authentication/authorization middleware, all endpoints publicly accessible.
- Impact: Unauthorized access to incident data, ability to trigger false emergencies.
- Fix Required: Implement JWT/API key authentication, role-based access control.
- Status: NOT FIXED - Production Blocker

---

## Low Bugs (DOCUMENTED)

### BUG-008: sklearn Version Mismatch Warning
- Severity: LOW
- Component: agents/vision/models/gru (sequence_model.pt, scalers, encoders)
- Root Cause: Model artifacts saved with sklearn 1.7.2, runtime using 1.6.0.
- Impact: Warning messages only, functionality works correctly.
- Fix: Re-save model artifacts with current sklearn version.
- Status: DOCUMENTED - No functional impact

---

## Regression Tests After Fixes
All tests pass:
1. test_e2e_pipeline.py - FULL PIPELINE TEST COMPLETE
2. test_all_agents_v2.py - ALL AGENTS INITIALIZED SUCCESSFULLY
3. Comprehensive pipeline test (SAFE, MODERATE, CRITICAL, x402, separation) - ALL TESTS PASSED
4. API integration test - Health, Orchestrator, Vision, Incidents endpoints
5. Incident/trace ID integrity verified across all tests

---

## Verification Commands
cd C:\Programs\codex\SheGuard\SheGuard_Agents
python test_e2e_pipeline.py
python test_all_agents_v2.py
python -m api.main  # then test endpoints
