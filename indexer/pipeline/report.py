"""Normalize verification events into the four required per-document checks."""

import datetime
import json
import os
from pathlib import Path


def build(events):
    rows = {}
    for e in events:
        if not e.get("source"):
            continue
        row = rows.setdefault(
            e["source"], {"document_id": e["source"], "checks": {}, "decision": "quarantine"}
        )
        checks = row["checks"]
        msg = e["msg"]

        def put(key, passed, reason):
            checks[key] = {"pass": bool(passed), "reason": reason}

        if msg == "manifest verification":
            put("completeness", e["passed"], e["checks"])
        elif msg == "extraction verification":
            put("quality", e["passed"], e.get("reason", "extraction failed"))
            if "completeness" not in checks or checks["completeness"]["pass"]:
                put(
                    "completeness",
                    e["passed"],
                    {k: v for k, v in e.items() if k not in ("msg", "source")},
                )
        elif msg in ("exact duplicate verification", "near duplicate verification"):
            put(
                "uniqueness",
                e["passed"],
                {k: v for k, v in e.items() if k not in ("msg", "source")},
            )
        elif msg == "recency verification":
            put("recency", e["passed"], e["reason"])
        elif msg == "revision accepted":
            put("recency", True, "Newer version replaces " + e["previous"])
        elif msg == "chunked":
            row.update(decision="indexed", chunks=e["chunks"])
        elif msg == "superseded metadata":
            put("recency", False, "Superseded by " + e["replaced_by"])
            row["decision"] = "archive"
    for row in rows.values():
        for key in ("quality", "completeness", "recency", "uniqueness"):
            if key not in row["checks"]:
                passed = key == "recency" and row["decision"] == "indexed"
                row["checks"][key] = {
                    "pass": passed,
                    "reason": "No newer version detected"
                    if passed
                    else "Not evaluated after an earlier rejection; not admitted",
                }
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "documents": list(rows.values()),
    }


def save(events):
    root = Path(os.environ.get("RAHBAR_RETENTION_DIR", "/tmp")) / "reports"
    root.mkdir(parents=True, exist_ok=True)
    path = root / (
        os.environ.get("HOSTNAME", "local")
        + "-"
        + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        + ".json"
    )
    path.write_text(json.dumps(build(events), indent=2))
    print(json.dumps({"msg": "verification report", "path": str(path)}), flush=True)
