"""Request-local, reproducible generation evidence, persisted per worker."""
from typing import Any
import contextvars
import hashlib
import json
import logging
import os
from pathlib import Path

current: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("trace", default=None)


def event(kind, **values):
    trace = current.get()
    if trace is not None:
        trace.setdefault(kind, []).append(values)


def persist(trace):
    for timing in trace.get("stage_timings", []):
        key = timing["stage"]
        trace.setdefault("latency", {})[key] = trace.get("latency", {}).get(key, 0) + timing["seconds"]
    if trace.get("embedding"):
        trace["embedding_version"] = trace["embedding"][-1]["version"]
    for retrieval in trace.get("retrieval", []):
        for passage in retrieval.get("passages", []):
            passage["document_id"] = passage["metadata"].get("document_id", passage["source"])
    trace["prompt_hash"] = hashlib.sha256(json.dumps(trace.get("generation_attempts", []), sort_keys=True).encode()).hexdigest()
    logging.getLogger("rahbar.trace").info("query_trace", extra={"trace": trace})
    folder = Path(os.environ.get("TRACE_DIR", "/tmp/traces"))
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (os.environ.get("HOSTNAME", "local") + "-" + str(os.getpid()) + ".jsonl")).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
