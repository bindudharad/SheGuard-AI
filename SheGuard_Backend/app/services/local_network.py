from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass


@dataclass
class LocalNetworkInfo:
    local_ip: str
    port: int
    base_url: str
    wifi_accessible: bool
    warnings: list[str]


def detect_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if _is_lan_ip(ip):
                return ip
    except OSError:
        pass

    hostname = socket.gethostname()
    for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
        ip = item[4][0]
        if _is_lan_ip(ip):
            return ip
    return "0.0.0.0"


def local_network_info(port: int = 8000) -> LocalNetworkInfo:
    ip = detect_local_ip()
    warnings = []
    if ip == "0.0.0.0":
        warnings.append("Could not detect a specific LAN IP. Check WiFi connection.")
    if not _firewall_rule_hint_present(port):
        warnings.append(
            f"Windows Firewall may block TCP port {port}. Allow inbound connections for Python/uvicorn or port {port}."
        )
    return LocalNetworkInfo(
        local_ip=ip,
        port=port,
        base_url=f"http://{ip}:{port}",
        wifi_accessible=_is_lan_ip(ip),
        warnings=warnings,
    )


def log_local_network_status(logger, port: int = 8000) -> LocalNetworkInfo:
    info = local_network_info(port)
    logger.info("[SYSTEM] Local IP detected: %s", info.local_ip)
    logger.info("[SYSTEM] Server accessible on local WiFi: %s", info.base_url)
    logger.info("[SYSTEM] Tracking page example: %s/track/sos-example", info.base_url)
    for warning in info.warnings:
        logger.warning("[NETWORK] %s", warning)
    return info


def _is_lan_ip(ip: str) -> bool:
    return ip.startswith("192.168.") or ip.startswith("10.") or _is_172_lan(ip)


def _is_172_lan(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4 or parts[0] != "172":
        return False
    try:
        second = int(parts[1])
    except ValueError:
        return False
    return 16 <= second <= 31


def _firewall_rule_hint_present(port: int) -> bool:
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"],
            capture_output=True,
            text=True,
            timeout=4,
        )
    except Exception:
        return False
    output = result.stdout.lower()
    return str(port) in output and ("allow" in output or "python" in output or "uvicorn" in output)
