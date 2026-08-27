import base64
import os
from dataclasses import dataclass
from typing import Optional

from groq import Groq


DEFAULT_PROMPT = (
    "Analyze this image. Is there a person injured, fallen, unconscious, "
    "or in danger? Describe situation clearly."
)


@dataclass
class GroqAnalysis:
    description: str
    confirms_danger: bool
    severity: str
    model: str
    error: Optional[str] = None


class GroqVisionClient:
    def __init__(self, model: Optional[str] = None):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def analyze_image(self, image_path: str, event_type: str, local_confidence: float) -> GroqAnalysis:
        if self.client is None:
            return GroqAnalysis(
                description="Groq analysis skipped because GROQ_API_KEY is not set.",
                confirms_danger=False,
                severity="unknown",
                model=self.model,
                error="missing_api_key",
            )

        try:
            base64_image = self._encode_image(image_path)
            prompt = (
                f"{DEFAULT_PROMPT}\n\n"
                f"Local ML event type: {event_type}. Local confidence: {local_confidence:.2f}. "
                "Reply with a concise safety assessment and state whether danger is likely."
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                temperature=0.2,
                max_completion_tokens=300,
            )

            description = response.choices[0].message.content or ""
            confirms_danger = self._confirms_danger(description)
            severity = "high" if confirms_danger else "medium"
            return GroqAnalysis(
                description=description.strip(),
                confirms_danger=confirms_danger,
                severity=severity,
                model=self.model,
            )
        except Exception as exc:
            return GroqAnalysis(
                description=f"Groq analysis failed: {exc}",
                confirms_danger=False,
                severity="unknown",
                model=self.model,
                error=str(exc),
            )

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def _confirms_danger(text: str) -> bool:
        lowered = text.lower()
        danger_terms = [
            "danger",
            "injured",
            "fallen",
            "fall",
            "unconscious",
            "collapsed",
            "medical attention",
            "emergency",
            "attack",
            "assault",
            "distress",
            "help",
        ]
        denial_terms = [
            "no danger",
            "not in danger",
            "does not appear",
            "no visible injury",
            "not injured",
            "normal activity",
        ]

        has_danger = any(term in lowered for term in danger_terms)
        has_denial = any(term in lowered for term in denial_terms)
        return has_danger and not has_denial
