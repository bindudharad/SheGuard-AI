from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_database
from logging_config import configure_logging
from backend.routes import cameras, contacts, incidents, locations, realtime, system, users
from backend.services.gpu import get_gpu_status, log_gpu_status
from backend.services.local_network import log_local_network_status


logger = configure_logging()
app = FastAPI(title="SheGuard AI Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_database()
    log_gpu_status(logger)
    log_local_network_status(logger, port=8000)


@app.get("/")
def health():
    return {"status": "ok", "service": "SheGuard AI Backend", "version": "2.0.0"}


@app.get("/health/gpu")
def gpu_health():
    return get_gpu_status().__dict__


app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(locations.router)
app.include_router(incidents.router)
app.include_router(cameras.router)
app.include_router(realtime.router)
app.include_router(system.router)
