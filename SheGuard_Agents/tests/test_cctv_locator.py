"""CCTV association tests (Phase 9)."""
from __future__ import annotations

from emergency.cctv_locator import associate_cameras, best_camera, haversine_meters


def test_haversine_known_distance():
    # ~111m per 0.001 deg latitude
    d = haversine_meters(12.97, 77.59, 12.971, 77.59)
    assert 100 < d < 125


def test_closest_online_camera_selected_first():
    cams = [
        {"camera_id": 1, "camera_name": "Cam-01", "latitude": 12.972, "longitude": 77.59, "online_status": "online"},
        {"camera_id": 2, "camera_name": "Cam-02", "latitude": 12.9705, "longitude": 77.59, "online_status": "online"},
        {"camera_id": 3, "camera_name": "Cam-03", "latitude": 13.10, "longitude": 77.60, "online_status": "offline"},
    ]
    selected = associate_cameras(cams, 12.97, 77.59, max_distance_meters=500, max_cameras=3)
    assert [c.camera_id for c in selected][:2] == [2, 1]
    assert all(c.camera_id != 3 for c in selected)


def test_distance_limit_filters_far_cameras():
    cams = [{"camera_id": 1, "camera_name": "Far", "latitude": 13.10, "longitude": 77.70, "online_status": "online"}]
    selected = associate_cameras(cams, 12.97, 77.59, max_distance_meters=500)
    assert selected == []


def test_offline_registry_still_returns_unknown_distance_online():
    cams = [
        {"camera_id": 7, "camera_name": "DroidCam-live", "latitude": None, "longitude": None, "online_status": "online"},
    ]
    selected = associate_cameras(cams, None, None)
    assert len(selected) == 1 and selected[0].distance_meters is None


def test_best_camera_prefers_online_closest():
    from emergency.models import CameraAssociation

    cams = [
        CameraAssociation(2, "C2", distance_meters=300.0, online_status="online"),
        CameraAssociation(1, "C1", distance_meters=50.0, online_status="offline"),
        CameraAssociation(3, "C3", distance_meters=None, online_status="online"),
    ]
    assert best_camera(cams).camera_id == 2
    offline_only = [cams[1]]
    assert best_camera(offline_only) is None


def test_no_metadata_never_claims_coverage():
    cams = [{"camera_id": 9, "camera_name": "Unknown-loc", "online_status": "unknown"}]
    selected = associate_cameras(cams, 12.97, 77.59)
    assert selected == [] or selected[0].distance_meters is None
