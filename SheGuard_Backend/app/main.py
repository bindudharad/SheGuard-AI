from pathlib import Path

import os
import time
import logging
import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.logging_config import configure_logging
from app.database import init_database
from app.routes import agent_sync, cameras, contacts, emergency, incidents, locations, notifications, realtime, system, users
from app.services.gpu import get_gpu_status, log_gpu_status
from app.services.incident_session import start_incident_watchdog
from app.services.local_network import log_local_network_status
from app.services.realtime import realtime_hub

# Configure structured logging
logger = configure_logging()
app = FastAPI(title="SheGuard Backend", version="2.0.0")
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
INCIDENT_UPLOADS_DIR = UPLOADS_DIR / "incidents"
INCIDENT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def _cors_origins() -> list[str]:
    raw = os.environ.get("SHEGUARD_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

cors_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    logger.info(
        "request_start",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
        }
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(process_time * 1000, 2),
            }
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "request_error",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "duration_ms": round(process_time * 1000, 2),
            }
        )
        raise

@app.on_event("startup")
async def startup() -> None:
    logger.info("STARTUP EVENT CALLED")
    init_database()
    start_incident_watchdog()
    log_gpu_status(logger)
    log_local_network_status(logger, port=8000)
    # Capture the main event loop for realtime hub
    loop = asyncio.get_running_loop()
    logger.info(f"Got running loop: {loop}")
    realtime_hub.set_loop(loop)
    logger.info("startup_complete", extra={"version": "2.0.0"})

@app.get("/")
def health():
    return {"status": "ok", "service": "SheGuard Backend", "version": "2.0.0"}

@app.get("/health")
def health_check():
    """Detailed health check for monitoring."""
    import sqlite3
    db_path = os.environ.get("SHEGUARD_DB_PATH", "sheguard.db")
    db_healthy = False
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        db_healthy = True
    except Exception as e:
        logger.warning("health_check_db_failed", extra={"error": str(e)})
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "SheGuard Backend",
        "version": "2.0.0",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": time.time(),
    }

@app.get("/health/gpu")
def gpu_health():
    return get_gpu_status().__dict__

@app.get("/health/ready")
def readiness_check():
    """Readiness check for load balancers."""
    import sqlite3
    db_path = os.environ.get("SHEGUARD_DB_PATH", "sheguard.db")
    ready = True
    checks = {}
    
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not ready: {e}"
        ready = False
    
    # Check uploads directory
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = UPLOADS_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        checks["storage"] = "ready"
    except Exception as e:
        checks["storage"] = f"not ready: {e}"
        ready = False
    
    return {
        "ready": ready,
        "checks": checks,
        "timestamp": time.time(),
    }

app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(locations.router)
app.include_router(incidents.router)
app.include_router(emergency.router)
app.include_router(notifications.router)
app.include_router(cameras.router)
app.include_router(realtime.router)
app.include_router(system.router)
# Additive agent-orchestration sync endpoints (service-token protected).
app.include_router(agent_sync.router)