# SheGuard AI

## What is SheGuard AI?

SheGuard AI is an integrated emergency response and incident management system that combines computer vision, threat detection, and automated alerting to provide real-time emergency response capabilities. The system monitors video feeds, analyzes incidents, and automatically notifies relevant stakeholders through multiple channels.

## Major Components

- **SheGuard_Agents**: Core agent module containing threat detection agents, vision pipelines, and emergency response logic. Includes audio, context, decision, response, threat, and vision agent subsystems.

- **SheGuard_AI**: Python-based AI/ML module with fall detection, action classification, and model training capabilities. Contains main pipeline, training scripts, and model artifacts.

- **SheGuard_App**: Flutter mobile application providing the user interface for incident monitoring, management, and alerts. Includes iOS and Android platform-specific code.

- **SheGuard_Backend**: Python backend service implementing API endpoints, database management, and service orchestration. Handles incident processing, user management, and integration with external services.

- **SheGuard_Dashboard**: Web-based dashboard for visualizing incidents, system status, and analytics. Built with Flutter and connects to the backend API.

## Project Structure

```
SheGuard_Agents/    - Agent modules, pipelines, and threat detection logic
SheGuard_AI/        - AI/ML pipeline, fall detection, action classification
SheGuard_App/       - Flutter mobile application (frontend)
SheGuard_Backend/   - Python backend API and service layer
SheGuard_Dashboard/ - Web dashboard frontend
.env                - Environment configuration (not committed, see .gitignore)
.gitignore         - Git ignore rules
```

## Technologies

- **Python**: Core backend, AI/ML models, agent logic
- **Flutter**: Mobile and web dashboard applications
- **TensorFlow/Lite**: Model integration (pose_landmarker_lite.task)
- **YOLOv8**: Object detection model
- **Groq/Llama**: AI inference API
- **PostgreSQL/SQLite**: Database storage
- **Redis**: Caching and real-time features
- **Docker**: Containerization
- **Git**: Version control

## Environment Variables

The project uses a `.env` file for configuration (excluded from version control via `.gitignore`). Key environment variables include:

- `SHEGUARD_DB_PATH`: Path to the database file
- `SHEGUARD_JWT_SECRET`: JWT secret key for authentication
- `SHEGUARD_TOKEN_TTL_SECONDS`: Token time-to-live in seconds
- `SHEGUARD_ADMIN_USERNAME`: Admin username
- `SHEGUARD_ADMIN_PASSWORD`: Admin password
- `GROQ_API_KEY`: Groq AI API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for alerts
- `TELEGRAM_CHAT_ID`: Chat ID for emergency alerts
- `SHEGUARD_SERVICE_TOKEN`: Service token for AI engine ingestion

Additional environment variables are defined in `SheGuard_Backend/.env.example` and `SheGuard_Dashboard/.env.example` as placeholders.

## Component Communication

- **SheGuard_Dashboard** connects to **SheGuard_Backend** via REST API
- **SheGuard_Backend** processes incidents and coordinates with **SheGuard_Agents** for threat analysis
- **SheGuard_Agents** analyzes video feeds and generates incident alerts
- Alerts are dispatched through **Telegram** bot and email notifications
- Real-time updates via WebSocket connections

## Development & Testing

- Run the full system: `cd SheGuard_AI && python run_all.bat` or `cd SheGuard_Backend && python main.py`
- Backend API documentation: Check `SheGuard_Backend/README.md` and `PROJECT_API_DOCUMENTATION.md`
- Agent testing: `cd SheGuard_Agents && python test_all_agents.py`
- Dashboard development: `cd SheGuard_Dashboard && flutter run`
- Database migrations: `cd SheGuard_Backend && python -m migration_sources`
- Environment setup: Copy `.env.example` to `.env` and fill in actual values

## Notes

- Never commit real API keys or credentials. The `.env` file is excluded via `.gitignore`.
- Example configuration files (`*.env.example`) contain placeholders and can be safely committed.
- Large model files and generated datasets are excluded from version control.
- See individual folder READMEs for more detailed setup instructions.