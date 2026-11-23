"""Validate content and human requirements without inventing review provenance."""

import json
from pathlib import Path
import sys

rows = [
    json.loads(line)
    for line in Path(sys.argv[1] if len(sys.argv) > 1 else "eval/golden.jsonl")
    .read_text()
    .splitlines()
]
counts = {
    "total": len(rows),
    "answerable": sum(bool(r["relevant"]) for r in rows),
    "unanswerable": sum(bool(r.get("must_abstain")) for r in rows),
    "hard": sum(bool(r.get("hard")) for r in rows),
    "human_written": sum(r.get("author") == "human" for r in rows),
    "synthetic_reviewed_by_human": sum(
        r.get("author") == "synthetic"
        and bool(r.get("human_reviewed"))
        and bool(r.get("reviewer"))
        for r in rows
    ),
}
minimums = {
    "total": 25,
    "answerable": 15,
    "unanswerable": 5,
    "hard": 5,
    "human_written": 8,
    "synthetic_reviewed_by_human": 8,
}
failures = [f"{k}: {counts[k]} < {v}" for k, v in minimums.items() if counts[k] < v]
for r in rows:
    if bool(r["relevant"]) == bool(r.get("must_abstain")):
        failures.append(r["id"] + ": contradictory answerability")
    for ref in r["relevant"]:
        if not ref.get("source") or not isinstance(ref.get("page"), int):
            failures.append(r["id"] + ": missing source/page")
print(json.dumps({"counts": counts, "failures": failures}, indent=2))
sys.exit(bool(failures))
