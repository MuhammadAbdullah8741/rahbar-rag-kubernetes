import itertools
import json
import math
import sys
from pathlib import Path

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings
from pipeline.embed import embed
from pipeline.extract import extract


def unit(values):
    norm = math.sqrt(sum(v * v for v in values))
    if not norm:
        raise ValueError("Empty or zero-length document vector")
    return [v / norm for v in values]


def main():
    root = Path("/corpus/raw")
    records = json.loads((root / "_index.json").read_text())
    settings = get_settings()
    vectors = {}
    for i, record in enumerate(records, 1):
        name = record["file"]
        print(f"[{i}/{len(records)}] {name}", file=sys.stderr, flush=True)
        doc = clean(extract(str(root / name), record["doc_version"], record["superseded"]))
        pieces = chunk(doc, settings.chunk_size, settings.chunk_overlap)
        texts = [f"{c.section}\n{c.text}" for c in pieces]
        rows = [unit(v) for v in embed(texts, settings)]
        vectors[name] = unit([sum(col) / len(rows) for col in zip(*rows)])
    threshold = 0.99
    pairs = []
    for a, b in itertools.combinations(vectors, 2):
        score = sum(x*y for x, y in zip(vectors[a], vectors[b], strict=True))
        pairs.append(dict(a=a, b=b, cosine=round(score, 8), flagged=score >= threshold))
    pairs.sort(key=lambda p: p["cosine"], reverse=True)
    policy_names = {"undergraduate-academic-rules-aug-2023.pdf", "academic-rules-handbook-jun-2026.pdf"}
    policy = next(p for p in pairs if {p["a"], p["b"]} == policy_names)
    print(json.dumps(dict(model=settings.embed_model, threshold=threshold, pairs_checked=len(pairs),
                          flagged_pairs=sum(p["flagged"] for p in pairs), highest_pair=pairs[0],
                          policy_version_pair=policy, pairs=pairs), indent=2))


if __name__ == "__main__":
    main()
