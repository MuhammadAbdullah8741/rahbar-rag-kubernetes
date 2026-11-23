"""Fail closed on incomplete results, quality floors, regression or latency budget."""

import argparse
import json
import math
from pathlib import Path
import sys


def gate(baseline, candidate, thresholds):
    failures = []
    if baseline.get("golden_sha256") != candidate.get("golden_sha256"):
        failures.append("different golden sets")

    def value(data, path):
        try:
            for key in path.split("."):
                data = data[key]
            return (
                float(data) if data is not None and math.isfinite(float(data)) else None
            )
        except (KeyError, TypeError, ValueError):
            return None

    for path, spec in thresholds.items():
        got = value(candidate, path)
        before = value(baseline, path)
        if got is None:
            failures.append(path + ": missing/nonfinite")
            continue
        if "min" in spec and got < spec["min"] - 1e-9:
            failures.append(f"{path}: {got} < {spec['min']}")
        if "max" in spec and got > spec["max"] + 1e-9:
            failures.append(f"{path}: {got} > {spec['max']}")
        if "max_drop" in spec and (
            before is None or got < before - spec["max_drop"] - 1e-9
        ):
            failures.append(path + ": regression")
    return failures


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--thresholds", default="config/gate.json")
    p.add_argument("--out")
    a = p.parse_args()

    def load(f):
        return json.loads(Path(f).read_text())

    failures = gate(load(a.baseline), load(a.candidate), load(a.thresholds))
    result = {
        "decision": "reject" if failures else "release",
        "failures": failures,
        "baseline": a.baseline,
        "candidate": a.candidate,
        "thresholds": load(a.thresholds),
    }
    output = json.dumps(result, indent=2)
    print(output)
    if a.out:
        Path(a.out).write_text(output)
    sys.exit(bool(failures))
