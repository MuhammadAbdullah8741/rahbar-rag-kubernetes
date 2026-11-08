"""Query embeddings: the same pinned model and dimension as the indexer."""

import hashlib
import math
import re

import httpx

from ..config import Settings


def embed_query(text: str, settings: Settings) -> list[float]:
    if settings.embed_model == "fixture-hash-v1":
        vector = [0.0] * 768
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 768] += 1
        norm = math.sqrt(sum(v * v for v in vector)) or 1
        return [v / norm for v in vector]
    with httpx.Client(timeout=180, trust_env=False) as client:
        r = client.post(
            settings.ollama_url.rstrip("/") + "/api/embed",
            json={
                "model": settings.embed_model,
                "input": "search_query: " + text,
                "truncate": False,
                "keep_alive": "30m",
            },
        )
        r.raise_for_status()
        vector = r.json()["embeddings"][0]
    if len(vector) != settings.embed_dimension:
        raise ValueError("Query embedding dimension differs from configured pin")
    return vector
