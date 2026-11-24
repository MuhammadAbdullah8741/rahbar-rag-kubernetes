import json
import math
import sys
from pathlib import Path

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings
from pipeline.embed import embed
from pipeline.extract import extract


def normalize(vector):
    norm = math.sqrt(sum(x * x for x in vector))
    if not norm:
        raise ValueError("Zero-length embedding")
    return [x / norm for x in vector]


def main():
    root = Path("/corpus")
    files = {
        "original": "raw/fee-structure-page.html",
        "exact_copy": "batch-b/copy-fee-structure-page.html",
        "near_copy": "batch-b/near-fee-structure-page.html",
        "grading": "raw/grading-page.html",
    }
    settings = get_settings()
    vectors, inputs = {}, {}
    for label, filename in files.items():
        print("Processing", filename, file=sys.stderr, flush=True)
        doc = clean(extract(str(root / filename), "test", False))
        pieces = chunk(doc, settings.chunk_size, settings.chunk_overlap)
        if not pieces:
            raise ValueError(f"No chunks extracted from {filename}")
        inputs[label] = [f"{c.section}\n{c.text}" for c in pieces]
        rows = [normalize(v) for v in embed(inputs[label], settings)]
        vectors[label] = normalize([sum(col) / len(rows) for col in zip(*rows)])
    scores = {
        key: round(sum(a*b for a, b in zip(vectors["original"], v)), 6)
        for key, v in vectors.items() if key != "original"
    }
    print(json.dumps({
        "model": settings.embed_model,
        "chunks_per_document": {k: len(v) for k, v in inputs.items()},
        "near_copy_changed_embedding_input": inputs["original"] != inputs["near_copy"],
        "cosine_similarity_to_original_fee_page": scores,
    }, indent=2))


if __name__ == "__main__":
    main()
