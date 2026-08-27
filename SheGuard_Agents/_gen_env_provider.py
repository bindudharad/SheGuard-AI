import base64, os

content = r'''"""Provider for environmental data (weather, lighting, etc.).

Currently a stub. Replace with actual weather API integration when available.
"""

from __future__ import annotations

from typing import Optional


class EnvironmentProvider:
    """Provides environmental context.

    When no weather API is configured, returns UNAVAILABLE rather than fabricating
    data. The Context Agent must never assume safe conditions when data is missing.
    """

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key
        self.api_url = api_url

    def get(self, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
        """Returns environment data dict. Always returns a dict with status."""
        return {
            "status": "UNAVAILABLE",
            "data": None,
            "note": "weather provider not configured",
        }
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\providers\environment_provider.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")