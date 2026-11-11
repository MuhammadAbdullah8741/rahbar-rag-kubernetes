"""Deterministic extractive provider for model-free CI, never the real deployment."""

import re
from ...schemas import Answer, Citation, Passage


class FixtureProvider:
    name = "fixture"

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        p = passages[0]
        sentences = re.split(r"(?<=[.!?])\s+", p.text)
        sentences = [s for s in sentences if not re.search(r"ignore.*instructions", s, re.I)]
        text = " ".join(sentences[:2])
        return Answer(
            reasoning="Extracted directly from fixture evidence.",
            answer=f"{text} [{p.source} / {p.section}]",
            citations=[Citation(source=p.source, section=p.section, page=p.page)],
            answered_from_context=True,
            confidence="high",
        )
