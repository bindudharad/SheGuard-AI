from fastapi import APIRouter

from backend.services.local_network import local_network_info


router = APIRouter(tags=["system"])


@router.get("/system/local-network")
def system_local_network():
    info = local_network_info(port=8000)
    return {
        "local_ip": info.local_ip,
        "port": info.port,
        "base_url": info.base_url,
        "tracking_base_url": f"{info.base_url}/track",
        "wifi_accessible": info.wifi_accessible,
        "warnings": info.warnings,
        "required_run_command": "uvicorn backend.app:app --host 0.0.0.0 --port 8000",
    }
