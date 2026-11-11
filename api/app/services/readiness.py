"""Bounded, read-only dependency checks. Never run from the liveness endpoint."""

from __future__ import annotations

from urllib.parse import quote

import httpx
import redis

from ..config import Settings


def check_dependencies(settings: Settings) -> dict[str, str]:
    if not settings.check_dependencies and settings.retriever == "stub":
        return {"mode": "local-stub"}
    checks: dict[str, str] = {}
    base = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2"
    collections = "/tenants/default_tenant/databases/default_database/collections"
    try:
        with httpx.Client(base_url=base, timeout=2.0, trust_env=False) as client:
            name = settings.collection
            control = client.get(f"{collections}/{quote(name + '-control', safe='')}")
            if control.status_code != 404:
                control.raise_for_status()
                name = (control.json().get("metadata") or {}).get("active_collection", name)
            response = client.get(f"{collections}/{quote(name, safe='')}")
            response.raise_for_status()
            collection = response.json()
            metadata = collection.get("metadata") or {}
            model = metadata.get("embed_model")
            dimension = metadata.get("dimension")
            if model != settings.embed_model or dimension != settings.embed_dimension:
                checks["embedding"] = (
                    f"mismatch: expected {settings.embed_model}/{settings.embed_dimension}, "
                    f"found {model}/{dimension}"
                )
            else:
                checks["embedding"] = "ok"
            count = client.get(f"{collections}/{collection['id']}/count")
            count.raise_for_status()
            checks["chroma"] = "ok" if int(count.json()) > 0 else "collection is empty"
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        checks["chroma"] = f"unavailable or invalid collection: {type(exc).__name__}"
    try:
        with redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=2,
            socket_timeout=2,
        ) as cache:
            checks["redis"] = "ok" if cache.ping() else "ping failed"
    except redis.RedisError as exc:
        checks["redis"] = f"unavailable: {type(exc).__name__}"
    return checks


def is_ready(checks: dict[str, str]) -> bool:
    return all(value in {"ok", "local-stub"} for value in checks.values())
