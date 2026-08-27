from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.cloud_ai import EmbeddingClient, deterministic_embedding


MEMORY_PATH = Path(__file__).resolve().parents[1] / "database" / "incident_memory.jsonl"


@dataclass
class SimilarIncident:
    incident_id: int | None
    similarity: float
    summary: str
    metadata: dict[str, Any]


class IncidentMemory:
    def __init__(self, path: str | Path = MEMORY_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_client = EmbeddingClient()

    def remember(self, incident_id: int | None, summary: str, metadata: dict[str, Any] | None = None) -> list[float]:
        embedding = self.embedding_client.embed_text(summary)
        record = {
            "incident_id": incident_id,
            "summary": summary,
            "metadata": metadata or {},
            "embedding": embedding,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        return embedding

    def search(self, query: str, limit: int = 5) -> list[SimilarIncident]:
        query_embedding = self.embedding_client.embed_text(query)
        matches: list[SimilarIncident] = []
        if not self.path.exists():
            return matches
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            similarity = cosine_similarity(query_embedding, record.get("embedding") or deterministic_embedding(record.get("summary", "")))
            matches.append(
                SimilarIncident(
                    incident_id=record.get("incident_id"),
                    similarity=similarity,
                    summary=record.get("summary", ""),
                    metadata=record.get("metadata") or {},
                )
            )
        matches.sort(key=lambda item: item.similarity, reverse=True)
        return matches[:limit]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    size = min(len(a), len(b))
    if size == 0:
        return 0.0
    dot = sum(a[index] * b[index] for index in range(size))
    norm_a = math.sqrt(sum(value * value for value in a[:size]))
    norm_b = math.sqrt(sum(value * value for value in b[:size]))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
