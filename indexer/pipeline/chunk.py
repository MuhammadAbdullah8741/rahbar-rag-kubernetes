"""Stage 3: Chunk. Structure-aware, with overlap."""

from __future__ import annotations

import hashlib
import re

from .models import Chunk, Document


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    """Split on sections, then paragraphs, then sentences, keeping each chunk under
    `size` whitespace words, with `overlap` words shared between neighbours. Every chunk keeps
    the section heading it sits under, its page, doc_version and superseded."""
    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < chunk size")
    result: list[Chunk] = []
    section = "Document"
    for page in doc.pages:
        blocks: list[tuple[str, str]] = []
        buffer: list[str] = []
        for line in page.text.splitlines():
            stripped = line.strip()
            if re.fullmatch(
                r"(?:\d+\s+)?(?:FAST-NUCES|Student Handbook 2026)(?:\s+\d+)?", stripped
            ):
                continue
            markdown = re.match(r"^#{1,6}\s+(.+)", stripped)
            numbered = re.match(r"^\d+(?:\.\d+)*[.)]?\s+[A-Z]", stripped)
            words = stripped.split()
            titlecase = (
                1 < len(words) <= 8
                and re.fullmatch(r"[A-Za-z' /&()-]+", stripped)
                and all(
                    w[:1].isupper() or w in {"of", "for", "and", "the", "a", "or", "to", "in"}
                    for w in words
                )
            )
            # Numbered prose clauses belong to their surrounding named section.
            numbered_heading = numbered and not re.match(r"^\d+\.\d+|^\d+\)", stripped)
            sentence_heading = stripped in {
                "Evaluation criteria for a technical start-up",
                "Procedure for submitting the application",
                "Procedure for evaluating the application",
                "Mandatory periodic (six monthly) deliverables of the start-up",
                "Other terms and conditions",
            }
            heading = (
                markdown
                or titlecase
                or sentence_heading
                or (numbered_heading and len(words) <= 8 and not stripped.endswith((".", ";", ":")))
            )
            if heading:
                if buffer:
                    blocks.append((section, "\n".join(buffer)))
                    buffer = []
                section = markdown.group(1) if markdown else stripped
            elif stripped:
                buffer.append(stripped)
            elif buffer and buffer[-1] != "":
                buffer.append("")
        if buffer:
            blocks.append((section, "\n".join(buffer)))
        for title, text in blocks:
            units = re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])", text)
            windows: list[str] = []
            current: list[str] = []
            for unit in units:
                words = unit.split()
                # An oversized sentence/definition is the final fallback split.
                for start in range(0, len(words), size - overlap):
                    part = words[start : start + size]
                    if len(current) + len(part) > size and current:
                        windows.append(" ".join(current))
                        current = current[-overlap:] if overlap else []
                    if len(current) + len(part) > size:
                        current = []
                    current.extend(part)
                    if start + size >= len(words):
                        break
            if current:
                windows.append(" ".join(current))
            for body in windows:
                key = f"{doc.source}|{doc.doc_version}|{page.page}|{title}|{body}"
                cid = hashlib.sha256(key.encode()).hexdigest()[:24]
                if any(c.id == cid for c in result):
                    continue
                result.append(
                    Chunk(cid, body, doc.source, title, page.page, doc.doc_version, doc.superseded)
                )
    return result
