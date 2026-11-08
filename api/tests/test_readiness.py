from dataclasses import replace
from typing import Any

import httpx
import pytest
import redis
from fastapi.testclient import TestClient

from app.config import Settings
from app.services import readiness


@pytest.mark.parametrize(
    "model,dimension,count,cache_down,expected",
    [
        ("dummy-768", 768, 3, False, True),
        ("old-model", 768, 3, False, False),
        ("dummy-768", 384, 3, False, False),
        ("dummy-768", 768, 0, False, False),
        ("dummy-768", 768, 3, True, False),
    ],
)
def test_dependency_readiness(monkeypatch, model, dimension, count, cache_down, expected):
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.startswith("/api/v2/tenants/default_tenant/")
        if request.url.path.endswith("/count"):
            return httpx.Response(200, json=count)
        return httpx.Response(
            200,
            json={
                "id": "collection-id",
                "metadata": {"embed_model": model, "dimension": dimension},
            },
        )

    client_type = httpx.Client
    monkeypatch.setattr(
        readiness.httpx,
        "Client",
        lambda **kw: client_type(transport=httpx.MockTransport(respond), **kw),
    )

    class Cache:
        def __init__(self, **kw: Any):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ping(self):
            if cache_down:
                raise redis.ConnectionError("offline")
            return True

    monkeypatch.setattr(readiness.redis, "Redis", Cache)
    settings = replace(Settings(), check_dependencies=True, embed_model="dummy-768")
    checks = readiness.check_dependencies(settings)
    assert readiness.is_ready(checks) is expected
    if model != "dummy-768":
        assert "expected dummy-768/768, found old-model/768" in checks["embedding"]


def test_missing_chroma_collection_is_not_ready(monkeypatch):
    client_type = httpx.Client
    monkeypatch.setattr(
        readiness.httpx,
        "Client",
        lambda **kw: client_type(
            transport=httpx.MockTransport(lambda req: httpx.Response(404)), **kw
        ),
    )
    monkeypatch.setattr(
        readiness.redis,
        "Redis",
        lambda **kw: (_ for _ in ()).throw(redis.ConnectionError("offline")),
    )
    checks = readiness.check_dependencies(replace(Settings(), check_dependencies=True))
    assert not readiness.is_ready(checks)
    assert "HTTPStatusError" in checks["chroma"]
    assert "ConnectionError" in checks["redis"]


def test_failed_readiness_does_not_fail_liveness(monkeypatch):
    from app.main import app
    from app.routes import health

    monkeypatch.setenv("CHECK_DEPENDENCIES", "false")
    monkeypatch.setenv("RETRIEVER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setattr(health, "check_dependencies", lambda settings: {"chroma": "empty"})
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json()["checks"]["chroma"] == "empty"
