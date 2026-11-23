"""Fixed, source-derived fact rubrics, declared before the final evaluation.

A conservative proxy, not a semantic judge. Arithmetic answers require the
computed result in the answer and its operands in cited evidence. No LLM judge.
"""

import re

RUBRICS = {
    "H1": ([r"\b12000\b", r"credit\s*hour"], [r"\b12000\b", r"credit\s*hour"]),
    "H2": ([r"before", r"semester"], [r"before", r"semester"]),
    "H3": ([r"\b500\b"], [r"\b500\b", r"recheck"]),
    "H4": (
        [r"\b0\b|exempt|not.{0,30}(pay|charg)|no.{0,30}(fee|pay)|waiv"],
        [r"graduate", r"higher degree", r"not payable again"],
    ),
    "H5": (
        [r"\b80\s*%", r"holiday", r"count|includ"],
        [r"\b80\s*%", r"15th", r"holiday"],
    ),
    "H6": ([r"result", r"announc|declar"], [r"result", r"announcement"]),
    "H7": (
        [
            r"\b50000\b",
            r"\b20000\b",
            r"\b30000\b",
            r"non.?refundable|not refundable",
            r"complet",
            r"clos",
        ],
        [r"\b30000\b", r"\b20000\b", r"non.?refundable", r"complet", r"clos"],
    ),
    "H8": (
        [r"\b182500\b", r"\b180000\b", r"\b2500\b"],
        [r"\b12000\b", r"credit\s*hour", r"\b2500\b", r"per semester"],
    ),
    "q22": ([r"\b20000\b", r"complet", r"clos"], [r"\b20000\b", r"complet", r"clos"]),
}


def fact_checks(question_id, answer, cited_text):
    def clean(text):
        return re.sub(r"(?<=\d),(?=\d)", "", text.lower())

    answer_rules, evidence_rules = RUBRICS[question_id]
    return {
        "answer_facts": [bool(re.search(p, clean(answer))) for p in answer_rules],
        "evidence_facts": [
            bool(re.search(p, clean(cited_text))) for p in evidence_rules
        ],
    }
