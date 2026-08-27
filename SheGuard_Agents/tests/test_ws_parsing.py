"""Backend WS frame parsing tests (Phase 3/12 contract)."""
from __future__ import annotations

import json

from emergency.ws_client import parse_raw_message
from core.event_models import EventType


def test_sos_frame_parsed():
    frame = json.dumps(
        {
            "event": "incident.created",
            "payload": {
                "success": True,
                "incident_id": 7,
                "timestamp": "2026-08-23T10:00:00",
                "incident": {
                    "incident_id": 7,
                    "user_id": 9,
                    "incident_type": "manual_sos",
                    "confidence": 1.0,
                    "latitude": 12.97,
                    "longitude": 77.59,
                },
            },
        }
    )
    evt = parse_raw_message(frame)
    assert evt is not None
    assert evt.event_type is EventType.SOS_TRIGGERED
    assert evt.user_id == 9 and evt.incident_id == 7
    assert evt.latitude == 12.97 and evt.longitude == 77.59


def test_silent_sos_flagged():
    frame = json.dumps(
        {
            "event": "incident.created",
            "payload": {"incident": {"incident_id": 8, "user_id": 9, "incident_type": "silent_sos"}},
        }
    )
    evt = parse_raw_message(frame)
    assert evt.silent is True


def test_ai_incident_becomes_ai_alert():
    for incident_type, expected in (("fall", "FALL"), ("attack", "VIOLENCE"), ("fight", "VIOLENCE")):
        frame = json.dumps(
            {
                "event": "incident.created",
                "payload": {
                    "incident": {
                        "incident_id": 10,
                        "incident_type": incident_type,
                        "confidence": 0.88,
                        "camera_id": "default-camera",
                    }
                },
            }
        )
        evt = parse_raw_message(frame)
        assert evt.event_type is EventType.AI_ALERT
        assert evt.ai_result == expected


def test_tracking_update_parsed_with_session():
    frame = json.dumps(
        {
            "event": "tracking_update",
            "payload": {
                "session_id": "sos-abc",
                "session": {"session_id": "sos-abc", "user_id": 4},
                "location": {
                    "location_id": 99,
                    "latitude": 12.5,
                    "longitude": 77.6,
                    "speed": 1.5,
                    "battery": 80,
                    "accuracy": 4.0,
                },
            },
        }
    )
    evt = parse_raw_message(frame)
    assert evt.event_type is EventType.LOCATION_UPDATED
    assert evt.session_id == "sos-abc" and evt.user_id == 4
    assert evt.battery == 80 and evt.speed == 1.5
    assert evt.event_id == "loc:99"  # idempotency key from backend row id


def test_emergency_lifecycle_events():
    started = parse_raw_message(
        json.dumps({"event": "emergency.started", "payload": {"session_id": "s", "user_id": 1}})
    )
    acked = parse_raw_message(
        json.dumps({"event": "emergency.acknowledged", "payload": {"session_id": "s", "user_id": 1}})
    )
    resolved = parse_raw_message(
        json.dumps({"event": "emergency.resolved", "payload": {"session_id": "s", "user_id": 1}})
    )
    assert started.event_type is EventType.EMERGENCY_CREATED
    assert acked.event_type is EventType.INCIDENT_ACKNOWLEDGED
    assert resolved.event_type is EventType.INCIDENT_RESOLVED


def test_unknown_and_malformed_frames_dropped():
    assert parse_raw_message(json.dumps({"event": "notification.sent", "payload": {}})) is None
    assert parse_raw_message("garbage") is None
    assert parse_raw_message(b"\x00\x01") is None
