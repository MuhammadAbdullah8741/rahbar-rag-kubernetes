"""Measure three word-window settings against the prewritten golden set.

Run after extraction, with Chroma and Ollama reachable through environment settings.
Embedding cache is disposable and stays under ignored corpus/raw.
"""

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "indexer"), str(ROOT / "api")]
from pipeline.models import Document, Page
from pipeline.chunk import chunk
from pipeline.embed import embed
from pipeline.store import store
from pipeline.config import get_settings as index_settings
from app.config import get_settings
from app.retrieval.chroma import ChromaRetriever
from app.services.embedding import embed_query


def main():
    settings = index_settings()
    api = get_settings()
    docs = [
        Document(**{**d, "pages": [Page(**p) for p in d["pages"]]})
        for d in json.loads((ROOT / "corpus/raw/extraction.json").read_text())
    ]
    questions = yaml.safe_load((ROOT / "eval/golden.yaml").read_text())["questions"]
    vectors = {q["id"]: embed_query(q["question"], api) for q in questions}
    cache_path = ROOT / "corpus/raw/embedding-cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    results = []
    for size, overlap in [(200, 25), (400, 50), (600, 75)]:
        chunks = [c for d in docs for c in chunk(d, size, overlap)]
        keys = [
            hashlib.sha256((settings.embed_model + c.text).encode()).hexdigest()
            for c in chunks
        ]
        missing = {key: c.text for key, c in zip(keys, chunks) if key not in cache}
        items = list(missing.items())
        for start in range(0, len(items), 16):
            batch = items[start : start + 16]
            values = embed([text for _, text in batch], settings)
            cache.update(zip([key for key, _ in batch], values))
            cache_path.write_text(json.dumps(cache))
            print(
                f"{size}/{overlap}: embedded {min(start + 16, len(items))}/{len(items)}",
                flush=True,
            )
        name = f"rahbar-tune-{size}"
        store(
            chunks,
            [cache[key] for key in keys],
            dataclasses.replace(settings, collection=name),
        )
        retriever = ChromaRetriever(dataclasses.replace(api, collection=name))
        snapshot = retriever.snapshot()
        rows = []
        for q in questions:
            hits = retriever.search(q["question"], 5, snapshot, vectors[q["id"]])
            relevant = q["relevant"]

            def recall(k):
                return (
                    sum(
                        any(
                            p.source == r["source"] and p.section == r["section"]
                            for p in hits[:k]
                        )
                        for r in relevant
                    )
                    / len(relevant)
                    if relevant
                    else None
                )

            rows.append(
                {
                    "id": q["id"],
                    "type": q["type"],
                    "recall@3": recall(3),
                    "recall@5": recall(5),
                    "hits": [p.model_dump() for p in hits],
                }
            )
        valid = [r for r in rows if r["recall@5"] is not None]
        result = {
            "size_words": size,
            "overlap_words": overlap,
            "chunks": len(chunks),
            "amplification": sum(len(c.text.split()) for c in chunks)
            / sum(len(p.text.split()) for d in docs for p in d.pages),
            "recall@3": sum(r["recall@3"] for r in valid) / len(valid),
            "recall@5": sum(r["recall@5"] for r in valid) / len(valid),
            "rows": rows,
        }
        results.append(result)
        (ROOT / "eval/chunk-experiments.json").write_text(json.dumps(results, indent=2))
        print({k: v for k, v in result.items() if k != "rows"}, flush=True)


if __name__ == "__main__":
    main()
