import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("SHEGUARD_DB_PATH", ROOT_DIR / "sheguard.db"))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT_DIR / DB_PATH

DATABASE_URL = os.environ.get("SHEGUARD_DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    from app.models import entities  # noqa: F401

    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            rows = conn.execute(text("PRAGMA table_info(users)")).mappings().all()
            columns = {row["name"] for row in rows}
            if rows and "user_id" not in columns:
                legacy_exists = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='legacy_users'")
                ).first()
                if not legacy_exists:
                    conn.execute(text("ALTER TABLE users RENAME TO legacy_users"))
            camera_rows = conn.execute(text("PRAGMA table_info(cctv_cameras)")).mappings().all()
            camera_columns = {row["name"] for row in camera_rows}
            if camera_rows and "camera_name" not in camera_columns:
                conn.execute(text("ALTER TABLE cctv_cameras RENAME TO legacy_cctv_cameras"))

    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("sqlite"):
        _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    additions = {
        "incidents": {
            "threat_level": "VARCHAR(30)",
            "kidnap_suspicion_score": "INTEGER DEFAULT 0 NOT NULL",
            "ai_provider": "VARCHAR(80)",
            "explanation": "TEXT",
            "camera_id": "VARCHAR(120)",
            "image_path": "TEXT",
            "video_path": "TEXT",
            "status": "VARCHAR(30) DEFAULT 'new' NOT NULL",
            "linked_user_id": "INTEGER",
            "matching_distance_meters": "FLOAT",
            "emergency_session_id": "VARCHAR(80)",
        },
        "evidence": {
            "metadata_path": "TEXT",
            "pre_event_video_path": "TEXT",
            "confidence": "FLOAT",
            "threat_score": "INTEGER",
        },
        "live_locations": {
            "session_id": "VARCHAR(80)",
            "battery": "INTEGER",
            "accuracy": "FLOAT",
        },
    }
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_incidents_threat_level ON incidents(threat_level)",
        "CREATE INDEX IF NOT EXISTS ix_incidents_camera_id ON incidents(camera_id)",
        "CREATE INDEX IF NOT EXISTS ix_incidents_linked_user_id ON incidents(linked_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_incidents_emergency_session_id ON incidents(emergency_session_id)",
        "CREATE INDEX IF NOT EXISTS ix_incidents_status ON incidents(status)",
        "CREATE INDEX IF NOT EXISTS ix_incidents_type_created ON incidents(incident_type, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_evidence_incident_created ON evidence(incident_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_live_locations_session_timestamp ON live_locations(session_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS ix_tracking_sessions_status ON tracking_sessions(status)",
        "CREATE INDEX IF NOT EXISTS ix_incident_victim_links_incident_id ON incident_victim_links(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_victim_links_user_id ON incident_victim_links(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_emergency_sessions_status ON emergency_sessions(status)",
        "CREATE INDEX IF NOT EXISTS ix_emergency_sessions_user_id ON emergency_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_emergency_notifications_session_channel ON emergency_notifications(emergency_session_id, channel)",
        "CREATE INDEX IF NOT EXISTS ix_evidence_records_incident_id ON evidence_records(incident_id)",
    ]
    with engine.begin() as conn:
        for table, columns in additions.items():
            rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
            existing = {row["name"] for row in rows}
            for name, ddl in columns.items():
                if rows and name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        for statement in indexes:
            conn.execute(text(statement))
