from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from groq_client import GroqAnalysis, GroqVisionClient


@dataclass
class CloudAIResult:
    provider: str
    summary: str
    confirms_danger: bool = False
    severity: str = "unknown"
    error: str | None = None
    metadata: dict[str, Any] | None = None


class CloudAIOrchestrator:
    def __init__(self, enabled: bool = True, min_confidence: float = 0.78, min_threat_score: int = 5) -> None:
        self.enabled = enabled
        self.min_confidence = min_confidence
        self.min_threat_score = min_threat_score
        self.groq = GroqVisionClient()
        self.timeout = float(os.environ.get("CLOUD_AI_TIMEOUT_SECONDS", "15"))

    def should_analyze(self, event_type: str, confidence: float, threat_score: int) -> bool:
        dangerous = event_type.lower() in {"fall", "fight", "attack", "unconscious", "dragging", "forced_movement", "weapon"}
        return bool(self.enabled and dangerous and (confidence >= self.min_confidence or threat_score >= self.min_threat_score))

    def analyze_incident(self, image_path: str | None, event_type: str, confidence: float, threat_score: int) -> CloudAIResult:
        if not self.should_analyze(event_type, confidence, threat_score):
            return CloudAIResult("local", "Cloud AI skipped by safety gate.", False, "skipped")

        if image_path:
            groq_result: GroqAnalysis = self.groq.analyze_image(image_path, event_type, confidence)
            if not groq_result.error:
                return CloudAIResult("groq", groq_result.description, groq_result.confirms_danger, groq_result.severity)

            gemini = self._try_gemini(image_path, event_type, confidence, threat_score)
            if gemini.error is None:
                return gemini

        openrouter = self._try_openrouter(event_type, confidence, threat_score)
        if openrouter.error is None:
            return openrouter

        return CloudAIResult(
            "local",
            f"Local AI detected {event_type} with confidence {confidence:.2f}; cloud reasoning unavailable.",
            threat_score >= self.min_threat_score,
            "high" if threat_score >= 7 else "medium",
            error="all_cloud_providers_unavailable",
        )

    def _try_gemini(self, image_path: str, event_type: str, confidence: float, threat_score: int) -> CloudAIResult:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return CloudAIResult("gemini", "Gemini skipped: missing GEMINI_API_KEY.", error="missing_api_key")
        try:
            image_bytes = Path(image_path).read_bytes()
            body = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    "Give a concise safety interpretation. "
                                    f"Local event={event_type}, confidence={confidence:.2f}, threat={threat_score}/10."
                                )
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                                }
                            },
                        ]
                    }
                ]
            }
            model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            response = requests.post(url, json=body, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return CloudAIResult("gemini", text.strip(), threat_score >= 5, "high" if threat_score >= 7 else "medium", metadata=data)
        except Exception as exc:
            return CloudAIResult("gemini", f"Gemini failed: {exc}", error=str(exc))

    def _try_openrouter(self, event_type: str, confidence: float, threat_score: int) -> CloudAIResult:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return CloudAIResult("openrouter", "OpenRouter skipped: missing OPENROUTER_API_KEY.", error="missing_api_key")
        try:
            model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Create one concise emergency summary for a safety alert. "
                                f"Event={event_type}, confidence={confidence:.2f}, threat={threat_score}/10."
                            ),
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 120,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            return CloudAIResult("openrouter", text.strip(), threat_score >= 5, "high" if threat_score >= 7 else "medium")
        except Exception as exc:
            return CloudAIResult("openrouter", f"OpenRouter failed: {exc}", error=str(exc))


class EmbeddingClient:
    def embed_text(self, text: str) -> list[float]:
        api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("HF_TOKEN")
        if not api_key:
            return deterministic_embedding(text)
        provider = "nvidia" if os.environ.get("NVIDIA_API_KEY") else "huggingface"
        try:
            if provider == "nvidia":
                response = requests.post(
                    os.environ.get("NVIDIA_EMBEDDING_URL", "https://integrate.api.nvidia.com/v1/embeddings"),
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"input": [text], "model": os.environ.get("NVIDIA_EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")},
                    timeout=15,
                )
                response.raise_for_status()
                return [float(x) for x in response.json()["data"][0]["embedding"]]
        except Exception:
            return deterministic_embedding(text)
        return deterministic_embedding(text)


def deterministic_embedding(text: str, dimensions: int = 64) -> list[float]:
    import hashlib
    import math

    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % dimensions
        vector[index] += 1.0 if digest[1] % 2 == 0 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]

