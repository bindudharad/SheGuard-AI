# Run Full SheGuard AI+ System

## Prerequisites
- Python 3.10+
- Windows/Linux/macOS
- 4GB+ RAM
- Webcam (optional - simulation mode works without)

## 1. Environment Setup
`ash
cd C:\Programs\codex\SheGuard\SheGuard_Agents
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn pydantic pydantic-settings torch ultralytics mediapipe faster-whisper numpy scikit-learn joblib python-dotenv requests
`

## 2. Environment Variables (.env)
Create a .env file in SheGuard_Agents:
`nv
# Vision
VISION_VIDEO_SOURCE_TYPE=webcam
VISION_VIDEO_SOURCE=0
VISION_YOLO_MODEL_PATH=yolov8n.pt
VISION_GRU_MODEL_PATH=models/v2/sheguard_sequence_model.pt
VISION_SIMULATION_MODE=true

# Audio
AUDIO_SAMPLE_RATE=16000
AUDIO_WHISPER_MODEL=tiny.en
AUDIO_SIMULATION_MODE=true

# Context
CONTEXT_TIMEZONE=Asia/Kolkata

# x402
X402_SIMULATION_MODE=true

# General
LOG_LEVEL=INFO
`

## 3. Start Backend API Server
`ash
cd C:\Programs\codex\SheGuard\SheGuard_Agents
python -m api.main
# OR
uvicorn api.main:app --host 127.0.0.1 --port 8000
`

Server starts on http://127.0.0.1:8000

## 4. Verify Health
`ash
# Health check
curl http://127.0.0.1:8000/health
# Expected: {'status': 'ok', 'service': 'SheGuard Agents API', 'version': '1.0.0'}

# Orchestrator health
curl http://127.0.0.1:8000/orchestrator/health
# Expected: {'orchestrator': 'READY', 'active_incidents': 0, 'registered_agents': 7}
`

## 5. Run Tests

### Full E2E Pipeline Test
`ash
python test_e2e_pipeline.py
`
Expected output: === FULL PIPELINE TEST COMPLETE ===

### All Agents Initialization Test
`ash
python test_all_agents_v2.py
`
Expected output: ALL AGENTS INITIALIZED SUCCESSFULLY

### Vision Unit Tests
`ash
python -m pytest agents/vision/tests/ -v
`

## 6. Test API Endpoints

### Vision - Process Frame (Simulation)
`ash
curl -X POST http://127.0.0.1:8000/vision/process-frame \
  -H "Content-Type: application/json" \
  -d "{\"simulation\": true}"
`

### List Incidents
`ash
curl http://127.0.0.1:8000/incidents
`

### Get Incident Details
`ash
curl http://127.0.0.1:8000/incidents/{incident_id}
`

### Agent Health
`ash
curl http://127.0.0.1:8000/agents/vision_agent/health
curl http://127.0.0.1:8000/agents/threat_agent/health
`

## 7. Mobile App Configuration

Update SheGuard_App/lib/config/api_config.dart:
`dart
// For Android Emulator
static const String baseUrl = 'http://10.0.2.2:8000';

// For Physical Device (replace with your machine's IP)
// static const String baseUrl = 'http://192.168.1.XXX:8000';
`

Then rebuild:
`ash
cd C:\Programs\codex\SheGuard\SheGuard_App
flutter pub get
flutter build apk
`

## 8. Dashboard (Optional)
`ash
cd C:\Programs\codex\SheGuard\SheGuard_Dashboard
npm install
npm run dev
`
Dashboard runs on http://localhost:5173 (configure Vite proxy to backend)

## 9. Test Scenarios

### Safe Test
`ash
# Normal frame with no threats
curl -X POST http://127.0.0.1:8000/vision/process-frame \
  -H "Content-Type: application/json" \
  -d "{\"simulation\": true, \"incident_id\": \"SG-SAFE-TEST\"}"
# Expected: Decision = CONTINUE_MONITORING
`

### Critical Test (Direct Threat Assessment)
`ash
# Use the comprehensive test script
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from core.orchestrator import get_orchestrator
from agents.threat.agent import ThreatAgent
from agents.threat.schemas import ThreatWeights
from core.agent import AgentMessage

async def test():
    orch = get_orchestrator()
    t = ThreatAgent(ThreatWeights()); await t.initialize()
    await orch.register_agent(t)
    await orch.start()
    
    msg = AgentMessage.create(agent='test', event_type='THREAT_ASSESS',
        data={'incident_id':'SG-TEST','trace_id':'TRACE-TEST',
            'vision':{'agent':'vision_agent','timestamp':'2026-08-18T00:00:00','persons_detected':2,'interaction_detected':True,'interaction_confidence':0.95,'activity_label':'attack','activity_confidence':0.95,'temporal_confidence':0.9,'visual_risk_signal':0.95,'evidence':[],'simulation':True},
            'audio':{'agent':'audio_agent','timestamp':'2026-08-18T00:00:00','speech_detected':True,'transcription_text':'HELP','keywords':[{'keyword':'help','confidence':0.95}],'distress_detected':True,'distress_type':'HELP','distress_confidence':0.95,'simulation':True},
            'context':{'agent':'context_agent','timestamp':'2026-08-18T00:00:00','context_score':0.95,'context_confidence':0.95,'data_quality':0.95,'time_period':'late_night','isolation_status':'ELEVATED','nearby_incidents':5,'security_distance_meters':100.0,'reasons':[],'simulation':True},
            'simulation':True},
        incident_id='SG-TEST', trace_id='TRACE-TEST')
    await t.process(msg)
    await asyncio.sleep(3)
    inc = await orch.get_incident_state('SG-TEST')
    print('Risk:', inc.threat_data.get('risk_score'))
    print('Decision:', inc.decision_data.get('decision'))
    print('Response:', inc.response_data.get('status'))
    await orch.stop()
    await t.shutdown()

asyncio.run(test())
"
`

## 10. Shutdown
Press Ctrl+C in the terminal running the API server.

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Run pip install -r requirements.txt (create if missing) |
| WinError 127 (VAD) | Expected on Windows - runs in degraded mode |
| sklearn version warning | Re-save models with current sklearn version |
| Camera not found | Set VISION_SIMULATION_MODE=true |
| Port 8000 in use | Change port in pi.main or kill existing process |
| Mobile can't connect | Use 10.0.2.2 for emulator, machine IP for device |

## 12. Production Deployment Checklist
- [ ] Add persistent database (PostgreSQL)
- [ ] Implement JWT/API key authentication
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up real Algorand testnet wallet for x402
- [ ] Configure Telegram bot token and chat ID
- [ ] Update mobile app API base URL
- [ ] Configure CORS for production domains
- [ ] Add rate limiting middleware
- [ ] Set up audit logging
- [ ] Configure backup/restore for database
