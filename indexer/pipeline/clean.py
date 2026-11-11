"""Stage 2: Clean. Remove artefacts without destroying structure."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import replace

from .models import Document


def clean(doc: Document) -> Document:
    """Strip headers and footers that repeat on every page; keep headings and
    section boundaries, because chunking and citations depend on them."""
    edges: Counter[str] = Counter()
    for page in doc.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        edges.update(set(lines[:2] + lines[-2:]))
    repeated = {
        line
        for line, count in edges.items()
        if len(doc.pages) >= 4
        and count >= max(3, len(doc.pages) * 0.6)
        and not re.match(r"^(?:#+|\d+\.)", line)
    }
    pages = []
    for page in doc.pages:
        text = unicodedata.normalize("NFKC", page.text).replace("\x00", "")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        lines = [
            line
            for line in lines
            if line not in repeated
            and not re.fullmatch(r"(?:Page\s+)?\d+(?:\s+of\s+\d+)?", line, re.I)
        ]
        text = re.sub(r"(?<=\w)-\n(?=[a-z])", "", "\n".join(lines))
        pages.append(replace(page, text=re.sub(r"\n{3,}", "\n\n", text).strip()))
    return replace(doc, pages=pages)
