"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

router = APIRouter()
RETRIEVAL = Histogram("rahbar_retrieval_seconds", "Embedding and retrieval latency")
GENERATION = Histogram(
    "rahbar_generation_seconds",
    "Generation and validation latency",
    buckets=(1, 5, 10, 30, 60, 120, 240, 480),
)
CACHE_HITS = Counter("rahbar_cache_hits_total", "Semantic cache hits")
CACHE_LOOKUPS = Counter("rahbar_cache_lookups_total", "Semantic cache lookups")
CACHE_HIT_RATIO = Gauge("rahbar_cache_hit_ratio", "Per-process cache hits / lookups")
ABSTENTIONS = Counter("rahbar_abstentions_total", "Questions declined without evidence")
FALLBACKS = Counter("rahbar_fallbacks_total", "Safe responses after errors or invalid generation")
TOKENS = Histogram(
    "rahbar_tokens_per_request",
    "Provider-reported tokens per request",
    ["direction"],
    buckets=(0, 50, 100, 500, 1000, 4000, 8000, 16000),
)

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
