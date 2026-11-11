import re
from ..schemas import Answer, Passage


def validate_grounding(
    answer: Answer, passages: list[Passage], inline: bool = True, question: str = ""
) -> Answer:
    if not answer.answered_from_context:
        if answer.citations:
            raise ValueError("An abstention must not cite supporting evidence")
        # Do not expose a contradictory factual claim (for example "No Refund")
        # when the model itself says it did not answer from evidence.
        return answer.model_copy(
            update={
                "answer": "The available documents do not contain enough evidence to answer this question.",
                "confidence": "low",
            }
        )
    if re.search(r"\b(?:grade|points|letter)\b", question, re.I):

        def normalize(s: str) -> str:
            return s.replace("\u2212", "-").replace("\u2013", "-")

        # Uppercase standalone codes avoid confusing the article "a" with grade A.
        requested = set(re.findall(r"(?<!\w)[A-F][+-]?(?!\w)", normalize(question)))
        stated = set(re.findall(r"(?<!\w)[A-F][+-]?(?!\w)", normalize(answer.answer)))
        if requested and stated and not stated.issubset(requested):
            raise ValueError("Answer changed the requested grade code")
    refs = {(p.source, p.section, p.page) for p in passages}
    if not answer.citations or any(
        (c.source, c.section, c.page) not in refs for c in answer.citations
    ):
        raise ValueError("Citation was not retrieved for this request")
    if inline:
        allowed = {f"[{c.source} / {c.section}]" for c in answer.citations}
        # Resolve numbered aliases only against this request's retrieved evidence
        # and only when the same source is present in the validated citation array.
        for number, passage in enumerate(passages, 1):
            label = f"[{passage.source} / {passage.section}]"
            if label in allowed:
                answer.answer = answer.answer.replace(f"[{number} / {passage.section}]", label)
        protected = answer.answer
        for label in allowed:
            protected = protected.replace(label, " CITATIONTOKEN ")
        protected = re.sub(r"\b(Rs|Mr|Mrs|Dr|Prof|vs)\.", r"\1ABBREVIATION", protected)
        # Treat a citation immediately after punctuation as belonging to that sentence.
        protected = re.sub(r"([.!?])\s+(CITATIONTOKEN)", r" \2\1", protected)
        sentences = [
            s.strip() for s in re.split(r"[!?]+\s*|\.(?:\s+|$)|\n+", protected) if s.strip()
        ]
        # A one-sentence answer has an unambiguous link to its validated structured
        # citations. Render those references inline if the model omitted the label.
        # Never repair multiple uncited claims or an explicitly invalid reference.
        if len(sentences) == 1 and not re.search(r"\[[^\]]*\]", answer.answer):
            answer.answer = answer.answer.rstrip() + " " + " ".join(sorted(allowed))
            sentences[0] += " CITATIONTOKEN"
        if any("CITATIONTOKEN" not in sentence for sentence in sentences):
            raise ValueError("Missing inline source citation")
        for label in re.findall(r"\[[^\]]+ / [^\]]+\]", answer.answer):
            if label not in allowed:
                raise ValueError("Unretrieved inline citation")
    return answer
