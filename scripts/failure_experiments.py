"""Controlled faults in an isolated process; never alters the active collection."""

import dataclasses
import json
import sys
from pathlib import Path
from unittest.mock import Mock
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "api"), str(ROOT / "eval")]
from app.config import Settings
from app.retrieval.chroma import ChromaRetriever
from app.schemas import Passage
from app.services.answer import answer_question
from run_eval import recall_at_k

rows = []
scan = ROOT / "corpus/raw/faculty-entrepreneurship-and-technical-start-ups-policy.pdf"
with pdfplumber.open(scan) as pdf:
    text_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
extracted = json.loads((ROOT / "corpus/raw/extraction.json").read_text())
doc = next(d for d in extracted if d["source"] == scan.name)
rows.append(
    dict(
        stage="extraction",
        fault="Disable OCR and read PDF text layer only",
        text_layer_characters=text_chars,
        restored_ocr_characters=sum(len(p["text"]) for p in doc["pages"]),
        ocr_pages=sum(p["ocr"] for p in doc["pages"]),
    )
)
experiment = json.loads((ROOT / "eval/chunk-experiments.json").read_text())[1]
import yaml

gold = {
    q["id"]: q
    for q in yaml.safe_load((ROOT / "eval/golden.yaml").read_text())["questions"]
}
bad = []
good = []
for row in experiment["rows"]:
    relevant = gold[row["id"]]["relevant"]
    if relevant:
        good.append(recall_at_k(relevant, row["hits"], 5))
        bad.append(
            recall_at_k(
                relevant, [{**hit, "section": "Document"} for hit in row["hits"]], 5
            )
        )
rows.append(
    dict(
        stage="chunking",
        fault="Discard section metadata as a naive fixed-window splitter would",
        broken_recall5=sum(bad) / len(bad),
        restored_recall5=sum(good) / len(good),
    )
)
s = Settings(
    chroma_host="127.0.0.1",
    chroma_port=18001,
    collection="rahbar-tune-400",
    embed_model="wrong-model",
)
try:
    ChromaRetriever(s).snapshot()
    raise AssertionError("Mismatched model was accepted")
except ValueError as error:
    rows.append(
        dict(
            stage="retrieval",
            fault="Change API embedding model only",
            observed=str(error),
        )
    )
p = Passage(
    chunk_id="fault-evidence",
    source="fixture.md",
    section="Rules",
    page=1,
    text="Minimum attendance is 80%.",
    score=0.9,
)
retriever = Mock()
retriever.name = "fault-fixture"
retriever.retrieve.return_value = [p]
provider = Mock()
provider.name = "fault-provider"
provider.generate.side_effect = ValueError("invalid JSON schema")
result = answer_question("What is minimum attendance?", retriever, provider, Settings())
assert (
    provider.generate.call_count == 2
    and result.fallback
    and not result.answered_from_context
)
rows.append(
    dict(
        stage="generation",
        fault="Provider returns a schema validation error on every attempt",
        attempts=provider.generate.call_count,
        response=result.model_dump(),
    )
)
(ROOT / "docs/evidence/failure-experiments.json").write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
