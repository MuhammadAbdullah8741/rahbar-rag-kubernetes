"""A3 three-level evaluation. Real embeddings, retrieval and HTTP answers; no fabricated results."""

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from fact_rubrics import RUBRICS, fact_checks
import httpx
from app.config import get_settings
from app.retrieval.chroma import ChromaRetriever
from app.services.embedding import embed_query


def read_jsonl(path):
    return [
        json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
    ]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def percentile(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True)) / (
        math.sqrt(sum(x * x for x in a) * sum(y * y for y in b)) or 1
    )


def matches(ref, hit):
    return all(ref.get(k) == hit.get(k) for k in ("source", "page")) and (
        not ref.get("section") or ref["section"] == hit.get("section")
    )


def retrieval_scores(refs, hits):
    if not refs:
        return {}
    ranks = [
        next((i + 1 for i, h in enumerate(hits) if matches(r, h)), None) for r in refs
    ]
    # Document/page relevance is binary; duplicate chunks of one reference earn no extra gain.
    seen = set()
    gains = []
    for h in hits[:5]:
        found = next(
            (i for i, r in enumerate(refs) if matches(r, h) and i not in seen), None
        )
        gains.append(int(found is not None))
        if found is not None:
            seen.add(found)
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(5, len(refs))))
    return {
        "recall_at_3": mean([r is not None and r <= 3 for r in ranks]),
        "recall_at_5": mean([r is not None and r <= 5 for r in ranks]),
        "mrr": 1 / min(r for r in ranks if r is not None) if any(ranks) else 0,
        "ndcg_at_5": dcg / ideal,
    }


def normalize(text):
    return re.sub(r"[^a-z0-9%+-]", "", str(text).lower())


def answer_scores(q, response, text_by_id):
    citations = response.get("citations", [])
    hits = response.get("retrieved", [])
    answered = response.get("answered_from_context", False)
    membership = (
        mean([any(matches(c, h) for h in hits) for c in citations])
        if citations
        else (0 if answered else None)
    )
    expected = q.get("expect", "")
    cited = [
        text_by_id.get(h["chunk_id"], "")
        for h in hits
        if any(matches(c, h) for c in citations)
    ]
    checks = None
    if q.get("id") in RUBRICS:
        checks = fact_checks(q["id"], response.get("answer", ""), "\n".join(cited))
        faithful = (
            all(checks["answer_facts"] + checks["evidence_facts"]) if answered else None
        )
    else:
        faithful = (
            (
                bool(expected)
                and normalize(expected) in normalize(response.get("answer", ""))
                and any(normalize(expected) in normalize(t) for t in cited)
            )
            if answered
            else None
        )
    correct_citation = (
        any(any(matches(r, c) for r in q["relevant"]) for c in citations)
        if q["relevant"]
        else None
    )
    return {
        "citation_validity": membership,
        "faithfulness": faithful,
        "citation_ground_truth": correct_citation,
        "answerable_success": bool(answered and faithful and correct_citation)
        if q["relevant"]
        else None,
        "abstention_correctness": not answered and not citations
        if q.get("must_abstain")
        else None,
    }


def embedding_metrics(settings, pairs):
    times = []

    def embed(text):
        start = time.perf_counter()
        v = embed_query(text, settings)
        times.append(time.perf_counter() - start)
        return v

    para = []
    unrelated = []
    for p in pairs:
        a = embed(p["text"])
        para.append(cosine(a, embed(p["paraphrase"])))
        unrelated.append(cosine(a, embed(p["unrelated"])))
    first = embed(pairs[0]["text"])
    second = embed(pairs[0]["text"])
    return {
        "paraphrase_mean": mean(para),
        "unrelated_mean": mean(unrelated),
        "gap": mean(para) - mean(unrelated),
        "seconds_per_chunk": mean(times),
        "max_repeat_difference": max(abs(a - b) for a, b in zip(first, second)),
        "paraphrase_pairs": len(para),
        "unrelated_pairs": len(unrelated),
        "samples_seconds": times,
    }


def typo(text):
    words = text.split()
    for i, w in enumerate(words):
        if len(w) > 4:
            words[i] = w[:2] + w[3] + w[2] + w[4:]
            break
    return " ".join(words)


def suite(args):
    random.seed(42)
    settings = get_settings()
    retriever = ChromaRetriever(settings)
    snapshot = retriever.snapshot()
    data = snapshot.get(include=["documents"])
    texts = dict(zip(data["ids"], data["documents"]))
    questions = read_jsonl(args.golden)
    pairs = json.loads(Path(args.pairs).read_text())
    out = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "label": args.label,
        "seed": 42,
        "scorer_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
            + Path(__file__).with_name("fact_rubrics.py").read_bytes()
        ).hexdigest(),
        "golden_sha256": hashlib.sha256(Path(args.golden).read_bytes()).hexdigest(),
        "config": {k: v for k, v in vars(settings).items() if k != "llm_api_key"},
        "collection": snapshot.name,
        "collection_metadata": snapshot.metadata,
        "scoring": {
            "faithfulness": "Fixed fact rubrics for H1-H8/q22, atomic match otherwise; all required answer and cited evidence facts; conditional on answered; not semantic entailment",
            "citation_ground_truth": "expected source/page/section in FINAL citations, not merely retrieval",
            "noise": "transpose one pair of letters in first word longer than four characters",
        },
        "module": embedding_metrics(settings, pairs),
        "rows": [],
    }
    dest = Path(
        args.out
        or f"eval/results/{args.label}-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=650, trust_env=False) as client:
        for q in questions:
            vector = embed_query(q["question"], settings)
            clean = [
                p.model_dump()
                for p in retriever.search(
                    q["question"], settings.top_k, snapshot, vector
                )
            ]
            noisy = typo(q["question"])
            noise = [
                p.model_dump()
                for p in retriever.search(
                    noisy, settings.top_k, snapshot, embed_query(noisy, settings)
                )
            ]
            start = time.perf_counter()
            try:
                r = client.post(
                    args.api.rstrip("/") + "/api/ask",
                    json={"question": q["question"], "follow_up": True},
                )
                r.raise_for_status()
                response = r.json()
                error = None
            except Exception as exc:
                response = {
                    "answer": "",
                    "answered_from_context": False,
                    "citations": [],
                    "retrieved": [],
                    "fallback": True,
                }
                error = str(exc)
            row = {
                "id": q["id"],
                "question": q["question"],
                "relevant": q["relevant"],
                "expect": q.get("expect"),
                "must_abstain": bool(q.get("must_abstain")),
                "retrieval": retrieval_scores(q["relevant"], clean),
                "noise": retrieval_scores(q["relevant"], noise),
                "noise_query": noisy,
                "retrieved": clean,
                "response": response,
                "seconds": time.perf_counter() - start,
                "error": error,
            }
            row["answers"] = answer_scores(q, response, texts)
            if error:
                row["answers"] = {
                    k: (0 if v is not None else None) for k, v in row["answers"].items()
                }
            out["rows"].append(row)
            dest.with_suffix(".partial.json").write_text(json.dumps(out, indent=2))
            print(
                f"{q['id']} {row['seconds']:.2f}s answered={response['answered_from_context']} error={error}",
                flush=True,
            )
    out["component"] = {
        k: mean([r["retrieval"].get(k) for r in out["rows"]])
        for k in ("recall_at_3", "recall_at_5", "mrr", "ndcg_at_5")
    }
    out["noise"] = {
        k: mean([r["noise"].get(k) for r in out["rows"]]) for k in out["component"]
    }
    out["noise_delta"] = {k: out["noise"][k] - v for k, v in out["component"].items()}
    out["end_to_end"] = {
        k: mean([r["answers"][k] for r in out["rows"]])
        for k in out["rows"][0]["answers"]
    }
    out["end_to_end"].update(
        latency_p50=percentile([r["seconds"] for r in out["rows"]], 0.5),
        latency_p95=percentile([r["seconds"] for r in out["rows"]], 0.95),
        answered_count=sum(r["response"]["answered_from_context"] for r in out["rows"]),
        cache_hit_rate=mean([r["response"].get("cached", False) for r in out["rows"]]),
        errors=sum(r["error"] is not None for r in out["rows"]),
    )
    dest.write_text(json.dumps(out, indent=2))
    table = "Level | Metric | Value\n--- | --- | ---\n"
    for level in ("module", "component", "noise_delta", "end_to_end"):
        for k, v in out[level].items():
            if not isinstance(v, list):
                table += f"{level} | {k} | {v}\n"
    dest.with_suffix(".md").write_text(table)
    stamped = dest.parent / (
        args.label + "-" + out["timestamp"].replace(":", "").replace("+", "_") + ".json"
    )
    stamped.write_text(json.dumps(out, indent=2))
    stamped.with_suffix(".md").write_text(table)
    print(table, flush=True)
    print("RESULT", dest, flush=True)
    return 1 if out["end_to_end"]["errors"] else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://api:8000")
    p.add_argument("--golden", default="eval/golden.jsonl")
    p.add_argument("--pairs", default="eval/embedding-pairs.json")
    p.add_argument("--label", default="baseline")
    p.add_argument("--out")
    sys.exit(suite(p.parse_args()))
