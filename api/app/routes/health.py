"""Liveness and readiness (section 4.3). They answer different questions."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..services.readiness import check_dependencies, is_ready

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Is the process alive? Must never touch Chroma, Redis or the LLM."""
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    checks = check_dependencies(request.app.state.settings)
    ready = is_ready(checks)
    response.status_code = 200 if ready else 503
    return {"status": "ready" if ready else "not-ready", "checks": checks}
