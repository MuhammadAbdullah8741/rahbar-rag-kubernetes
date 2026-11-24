"""Summarize one completed A+B run. Run in the repository root."""
import json
import sys
from pathlib import Path

def load(path):
    events = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("logger") == "rahbar.indexer":
            events.append(row)
    return events

def main():
    results = Path("eval/results")
    paths = [Path(sys.argv[1])] if len(sys.argv) > 1 else sorted(results.glob("verify-ab-*.log"), reverse=True)
    for path in paths:
        events = load(path)
        if events and events[-1]["msg"] == "indexer finished" and any(e["msg"] == "near duplicate verification" for e in events):
            break
    else:
        raise SystemExit("No completed Step 22 log found. Pass its saved log path as an argument.")
    rows = {}
    for event in events:
        source = event.get("source")
        if source is None:
            continue
        row = rows.setdefault(source, {"source": source, "decision": "unrecorded", "checks": {}})
        msg = event["msg"]
        if msg.endswith("verification"):
            row["checks"][msg] = {k:v for k,v in event.items() if k not in ("source","ts","logger","msg")}
            if event.get("passed") is False:
                row["decision"] = "rejected"
        elif msg == "chunked":
            row.update(decision="indexed", chunks=event["chunks"])
        elif msg == "revision accepted":
            row["supersedes"] = event["previous"]
        elif msg == "superseded metadata":
            row["superseded_by"] = event["replaced_by"]
    rejected = [r["source"] for r in rows.values() if r["decision"] == "rejected"]
    indexed = [r for r in rows.values() if r["decision"] == "indexed"]
    chunks = sum(r["chunks"] for r in indexed)
    if len(indexed) + len(rejected) != len(rows) or chunks != events[-1]["chunks"]:
        raise SystemExit("Log is incomplete or contains multiple attempts. Inspect the original log.")
    out = path.with_suffix(".verification.json")
    report = dict(run=path.stem, documents=len(rows), indexed=len(indexed), rejected=len(rejected),
                  chunks=chunks, records=list(rows.values()))
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Documents: {len(rows)} | Indexed: {len(indexed)} | Rejected: {len(rejected)} | Chunks: {chunks}")
    for name in rejected:
        print("Rejected:", name)
    print("Report:", out)

if __name__ == "__main__":
    main()
