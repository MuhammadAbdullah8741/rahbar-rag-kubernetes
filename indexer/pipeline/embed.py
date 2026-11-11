"""Stage 4: Embed. One vector per chunk, from the pinned model only."""

from __future__ import annotations

import hashlib
import math
import re
import httpx

from .config import IndexerSettings


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    """Embed with settings.embed_model and nothing else.

    With Ollama: POST {ollama_url}/api/embed with {"model": ..., "input": [texts]}
    returns {"embeddings": [[...], ...]}. Batch the calls; one request per chunk is slow.
    """
    if settings.embed_model == "fixture-hash-v1":
        vectors = []
        for text in texts:
            vector = [0.0] * 768
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                slot = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 768
                vector[slot] += 1
            norm = math.sqrt(sum(v * v for v in vector)) or 1
            vectors.append([v / norm for v in vector])
        return vectors
    vectors = []
    with httpx.Client(timeout=180, trust_env=False) as client:
        for start in range(0, len(texts), 16):
            response = client.post(
                settings.ollama_url.rstrip("/") + "/api/embed",
                json={
                    "model": settings.embed_model,
                    "input": ["search_document: " + t for t in texts[start : start + 16]],
                    "truncate": False,
                    "keep_alive": "30m",
                },
            )
            response.raise_for_status()
            batch = response.json()["embeddings"]
            if len(batch) != len(texts[start : start + 16]):
                raise ValueError("Embedding count does not match input count")
            vectors.extend(batch)
    return vectors
