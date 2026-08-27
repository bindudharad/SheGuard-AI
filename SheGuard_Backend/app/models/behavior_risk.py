from datetime import datetime
from typing import Optional


from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class BehaviorEvent(Base):
    """Behavior event: following, approaching, chasing, fleeing, confrontation, isolation"""
    __tablename__ = "behavior_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    behavior_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    follower_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tracks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    camera_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    incident_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


    incident = relationship("Incident", back_populates="behavior_events")


class RiskEvent(Base):
    """Unified risk/fusion event from Threat Fusion Engine"""
    __tablename__ = "risk_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    behaviors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    contributions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tracks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    temporal_trend: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    camera_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    incident_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)



    incident = relationship("Incident", back_populates="risk_events")

    incident = relationship("Incident", back_populates="risk_events")

class X402Payment(Base):
    """x402 payment metadata for advanced intelligence"""
    __tablename__ = "x402_payments"

    payment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True, index=True)
    service: Mapped[str] = mapped_column(String(80), nullable=False, default="safety-intelligence")
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(20), nullable=False, default="ALGO")
    network: Mapped[str] = mapped_column(String(20), nullable=False, default="testnet")
    transaction_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")
    intelligence_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    simulation: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


    incident = relationship("Incident", back_populates="x402_payments")
    incident = relationship("Incident", back_populates="x402_payments")
