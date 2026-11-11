#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

Scores retrieval, citation membership and abstention, saves measured responses,
and rejects regressions against an explicitly established baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05  # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95  # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0  # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of the relevant (source, section) pairs found in the top k retrieved.
    Return None when the question has no relevant passages (must-abstain questions)."""
    if not relevant:
        return None

    def matches(expected, actual):
        if expected.get("chunk_id"):
            return expected["chunk_id"] == actual.get("chunk_id")
        return (
            expected.get("source") == actual.get("source")
            and expected.get("section") == actual.get("section")
            and ("page" not in expected or expected["page"] == actual.get("page"))
        )

    return sum(any(matches(r, h) for h in retrieved[:k]) for r in relevant) / len(
        relevant
    )


def citation_validity(response: dict) -> float | None:
    """Fraction of the response's citations that match a passage in response['retrieved'].
    Return None when there are no citations."""
    citations = response.get("citations", [])
    if not citations:
        return 0.0 if response.get("answered_from_context") else None
    refs = {
        (p["source"], p["section"], p.get("page"))
        for p in response.get("retrieved", [])
    }
    return sum(
        (c["source"], c["section"], c.get("page")) in refs for c in citations
    ) / len(citations)


def summarise(rows: list[dict]) -> dict:
    """Overall recall@3, recall@5, citation validity and abstention correctness, plus
    recall@5 broken down by question type. This dict becomes results.json."""

    def mean(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    for row in rows:
        row["recall_at_3"] = recall_at_k(
            row["relevant"], row["response"]["retrieved"], 3
        )
        row["recall_at_5"] = recall_at_k(
            row["relevant"], row["response"]["retrieved"], 5
        )
        row["citation_validity"] = citation_validity(row["response"])
    abstains = [r for r in rows if r["must_abstain"]]
    return {
        "recall_at_3": mean([r["recall_at_3"] for r in rows]),
        "recall_at_5": mean([r["recall_at_5"] for r in rows]),
        "citation_validity": mean([r["citation_validity"] for r in rows]),
        "abstention_correctness": mean(
            [not r["response"]["answered_from_context"] for r in abstains]
        ),
        "fallback_count": sum(bool(r["response"].get("fallback")) for r in rows),
        "answerable_answer_rate": mean(
            [r["response"]["answered_from_context"] for r in rows if r["relevant"]]
        ),
        "by_type": {
            kind: {
                "recall_at_3": mean(
                    [r["recall_at_3"] for r in rows if r["type"] == kind]
                ),
                "recall_at_5": mean(
                    [r["recall_at_5"] for r in rows if r["type"] == kind]
                ),
            }
            for kind in sorted({r["type"] for r in rows})
        },
        "rows": rows,
    }


def gate(results: dict, baseline: dict | None) -> list[str]:
    """Return one message per failed gate (section 5.4); an empty list means pass."""
    failures = []
    if results.get("recall_at_5") is None:
        failures.append("No answerable retrieval questions were evaluated")
    elif (
        baseline
        and results["recall_at_5"] < baseline["recall_at_5"] - MAX_RECALL5_DROP - 1e-9
    ):
        failures.append("recall@5 dropped more than 5 percentage points")
    if results.get("abstention_correctness") != REQUIRED_ABSTENTION:
        failures.append("Must-abstain correctness must be 100%")
    if (
        results.get("citation_validity") is None
        or results["citation_validity"] < MIN_CITATION_VALIDITY
    ):
        failures.append("Citation validity is below 95% or there are no cited answers")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate RAHBAR against a golden set."
    )
    parser.add_argument(
        "--api", required=True, help="base URL, e.g. http://192.168.49.2"
    )
    parser.add_argument(
        "--host", help="Host header, when your Ingress rule names a host"
    )
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="write these results as the new baseline",
    )
    args = parser.parse_args()

    questions = load_golden(args.golden)
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=600.0, headers=headers, trust_env=False) as client:
        for q in questions:
            started = time.perf_counter()
            response = ask(client, args.api, q["question"])
            rows.append(
                {
                    "id": q["id"],
                    "type": q.get("type", "ordinary"),
                    "must_abstain": bool(q.get("must_abstain", False)),
                    "relevant": q.get("relevant") or [],
                    "expect": q.get("expect"),
                    "response": response,
                    "seconds": round(time.perf_counter() - started, 2),
                }
            )
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")
            args.out.with_suffix(".partial.json").write_text(
                json.dumps(rows, indent=2), encoding="utf-8"
            )

    try:
        results = summarise(rows)
        baseline = (
            json.loads(args.baseline.read_text()) if args.baseline.exists() else None
        )
        failures = gate(results, None if args.update_baseline else baseline)
        if baseline is None and not args.update_baseline:
            failures.append(
                "Baseline is missing; establish it deliberately with --update-baseline"
            )
    except NotImplementedError as exc:
        print(f"\nnot implemented yet: {exc}")
        return 2

    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline and not failures:
        args.baseline.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
