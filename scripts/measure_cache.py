"""Calibrate semantic cache on declared same-intent and different-intent pairs."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app.config import get_settings
from app.services.embedding import embed_query
from app.services.cache import cosine, exact_terms

pairs = [
    ("How much is the admission fee?", "How much is the admission fee?", True),
    (
        "What is the security deposit?",
        "How much is the refundable security deposit?",
        True,
    ),
    (
        "What is the student activities fund charge?",
        "How much is the student activities fund?",
        True,
    ),
    (
        "What CGPA causes academic warning?",
        "When is a student put on academic warning?",
        True,
    ),
    ("What is the admission fee?", "Is the admission fee refundable?", False),
    ("Is the security deposit refundable?", "Is the tuition fee refundable?", False),
    ("What are the summer rules in 2023?", "What are the summer rules in 2026?", False),
    ("What grade points does B carry?", "What grade points does B- carry?", False),
    ("Can I repeat a failed course?", "Can I withdraw from a failed course?", False),
    (
        "How much is the student activities fund?",
        "How much is the security deposit?",
        False,
    ),
    ("What CGPA causes academic warning?", "What CGPA earns a gold medal?", False),
    (
        "What is the fee refund in the first 10 days?",
        "What is the fee refund after 30 days?",
        False,
    ),
]
settings = get_settings()
vectors = {}
for a, b, _ in pairs:
    for question in (a, b):
        if question not in vectors:
            vectors[question] = embed_query(question, settings)
rows = [
    dict(
        a=a,
        b=b,
        same_intent=same,
        similarity=cosine(vectors[a], vectors[b]),
        exact_terms_match=exact_terms(a) == exact_terms(b),
    )
    for a, b, same in pairs
]
results = []
for threshold in [0.90, 0.95, 0.98]:
    decisions = [
        (r["similarity"] >= threshold and r["exact_terms_match"], r["same_intent"])
        for r in rows
    ]
    results.append(
        dict(
            threshold=threshold,
            hits=sum(hit for hit, _ in decisions),
            false_hits=sum(hit and not same for hit, same in decisions),
            missed_equivalent=sum(not hit and same for hit, same in decisions),
        )
    )
result = dict(
    embed_model=settings.embed_model,
    selected_threshold=0.98,
    pairs=rows,
    results=results,
)
(ROOT / "eval/cache-experiments.json").write_text(json.dumps(result, indent=2))
print(json.dumps(results, indent=2))
