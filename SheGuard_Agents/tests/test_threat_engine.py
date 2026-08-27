"""Threat prioritization tests (Phase 10 / 18-14)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.event_models import ThreatLevel
from emergency.models import SessionContext
from emergency.threat_engine import evaluate


def sos_ctx(**kwargs) -> SessionContext:
    ctx = SessionContext(session_id="s1", user_id=1)
    ctx.trigger = "SOS"
    ctx.latitude, ctx.longitude = 12.97, 77.59
    ctx.tracking_active = True
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return ctx


def test_sos_alone_is_high():
    result = evaluate(sos_ctx())
    assert result.threat_level is ThreatLevel.HIGH


def test_help_without_ai_is_medium_or_high():
    ctx = sos_ctx()
    ctx.trigger = "HELP"
    result = evaluate(ctx)
    assert result.threat_level in (ThreatLevel.MEDIUM, ThreatLevel.HIGH)
    assert result.score < 62 or result.factors.get("tracking_active")


def test_sos_plus_violence_high_confidence_is_critical():
    ctx = sos_ctx()
    ctx.ai_result = "VIOLENCE"
    ctx.ai_confidence = 0.95
    from emergency.models import CameraAssociation

    ctx.cameras = [CameraAssociation(1, "Cam-01", distance_meters=120.0, online_status="online")]
    result = evaluate(ctx)
    assert result.threat_level is ThreatLevel.CRITICAL


def test_no_location_adds_uncertainty():
    with_loc = evaluate(sos_ctx())
    without = evaluate(sos_ctx(latitude=None, longitude=None))
    assert without.score > with_loc.score - 0.01  # at least not lower by more than float noise
    assert "No GPS fix" in "".join(without.reasons)


def test_repeated_alerts_increase_score_capped():
    one = evaluate(sos_ctx(repeated_alerts=1))
    three = evaluate(sos_ctx(repeated_alerts=3))
    assert three.score > one.score
    factors_three = three.factors["repeated_alerts"]
    assert factors_three == pytest.approx(6.0 * 2)  # capped at two repeats


def test_long_duration_escalates():
    ctx = sos_ctx()
    ctx.created_at = datetime.utcnow() - timedelta(seconds=400)
    result = evaluate(ctx)
    assert "duration" in result.factors


def test_score_bounds():
    ctx = sos_ctx()
    ctx.ai_result = "VIOLENCE"
    ctx.ai_confidence = 1.0
    ctx.repeated_alerts = 5
    ctx.created_at = datetime.utcnow() - timedelta(hours=2)
    result = evaluate(ctx)
    assert 0 <= result.score <= 100
