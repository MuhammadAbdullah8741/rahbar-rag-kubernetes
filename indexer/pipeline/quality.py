"""Verify extracted content before chunking."""
import logging
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from .models import Document, Page

import pdfplumber


def checked_extract(path, version, superseded, clean, extract):
    expected = 1
    cache_path = None
    try:
        if path.suffix.lower() == ".pdf":
            with pdfplumber.open(path) as pdf:
                expected = len(pdf.pages)
        root = os.environ.get("RAHBAR_RETENTION_DIR")
        if root:
            implementation = b"".join((Path(__file__).parent / name).read_bytes() for name in ("extract.py", "clean.py", "quality.py"))
            key = hashlib.sha256(path.read_bytes() + implementation + path.name.encode()).hexdigest()
            cache_path = Path(root) / "extraction-cache" / (key + ".json")
        if cache_path and cache_path.exists():
            cached = json.loads(cache_path.read_text())
            doc = Document(path.name, str(version), superseded, [Page(**p) for p in cached["pages"]])
        else:
            doc = clean(extract(str(path), version, superseded))
    except Exception as exc:
        logging.exception("Could not extract %s", path.name)
        return None, {"passed": False, "reason": f"{type(exc).__name__}: {exc}"}

    pages = [p.page for p in doc.pages]
    text = "".join(p.text for p in doc.pages)
    issues = []
    if not expected or pages != list(range(1, expected + 1)):
        issues.append("missing or out-of-order pages")
    if not any(char.isalnum() for char in text):
        issues.append("no usable extracted text")
    if text.count("\ufffd") / max(1, len(text)) > 0.05:
        issues.append("replacement-character fraction above 5%")
    report = {
        "passed": not issues,
        "reason": ", ".join(issues) or "page sequence complete and text checks passed",
        "expected_pages": expected,
        "extracted_pages": len(pages),
        "blank_after_cleaning": [p.page for p in doc.pages if not p.text.strip()],
    }
    if not issues and cache_path and not cache_path.exists():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix("." + str(os.getpid()) + ".tmp")
        temporary.write_text(json.dumps(asdict(doc)))
        temporary.replace(cache_path)
    return (None if issues else doc), report
