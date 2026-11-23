"""Stage 4: Embed. One vector per chunk, from the pinned model only."""

from __future__ import annotations

import hashlib
import math
import re
import httpx
import json
import os
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from .config import IndexerSettings


counts = {stage: {"inputs": 0, "embedded": 0, "model_requests": 0}
          for stage in ("verification", "indexing")}


@lru_cache(maxsize=8)
def model_digest(url, model):
    if model == "fixture-hash-v1":
        return model
    with httpx.Client(timeout=15, trust_env=False) as client:
        response = client.get(url.rstrip("/") + "/api/tags")
        response.raise_for_status()
        for item in response.json()["models"]:
            if item["name"] == model and item.get("digest"):
                return item["digest"]
    raise ValueError(f"No digest found for configured model {model}")


def embed(texts, settings, stage="indexing"):
    stats = counts[stage]
    stats["inputs"] += len(texts)
    root = os.environ.get("RAHBAR_RETENTION_DIR")
    if not root:
        stats["embedded"] += len(texts)
        return compute(texts, settings, stage)
    digest = model_digest(settings.ollama_url, settings.embed_model)
    keys = [hashlib.sha256(("search_document: " + t).encode()).hexdigest() for t in texts]
    values = {}
    with closing(sqlite3.connect(Path(root) / "embedding-cache.sqlite", timeout=60)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS vectors (model TEXT, key TEXT, vector TEXT, PRIMARY KEY(model,key))")
        missing = {}
        for key, text in zip(keys, texts):
            if key in values or key in missing:
                continue
            row = db.execute("SELECT vector FROM vectors WHERE model=? AND key=?", (digest, key)).fetchone()
            if row:
                values[key] = json.loads(row[0])
            else:
                missing[key] = text
        if missing:
            fresh = compute(list(missing.values()), settings, stage)
            stats["embedded"] += len(fresh)
            with db:
                for key, vector in zip(missing, fresh, strict=True):
                    values[key] = vector
                    db.execute("INSERT OR IGNORE INTO vectors VALUES (?,?,?)", (digest, key, json.dumps(vector)))
    return [values[k] for k in keys]


def compute(texts: list[str], settings: IndexerSettings, stage: str) -> list[list[float]]:
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
            counts[stage]["model_requests"] += 1
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
