"""Stage 1: Extract. PDF (or HTML, or Markdown) to text, page by page."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup, NavigableString, Tag
from pdf2image import convert_from_path
import pytesseract

from .models import Document, Page


def _region_text(page) -> str:
    tables = [
        t
        for t in page.find_tables()
        if len(t.extract()) >= 3 and any(len([v for v in row if v]) >= 2 for row in t.extract())
    ]
    bounds = [t.bbox for t in tables]
    outside = page.filter(
        lambda o: not any(
            b[0] <= o.get("x0", -1) <= b[2] and b[1] <= o.get("top", -1) <= b[3] for b in bounds
        )
    )
    events = [
        (line["top"], line["bottom"], line["text"])
        for line in outside.extract_text_lines(return_chars=False)
    ]
    for table in tables:
        text = "TABLE\n" + "\n".join(
            " | ".join(" ".join((v or "").split()) for v in row) for row in table.extract()
        )
        events.append((table.bbox[1], table.bbox[3], text))
    output = []
    bottom = 0.0
    for top, end, text in sorted(events):
        if top - bottom > 6:
            output.append("")
        output.append(text)
        bottom = end
    return "\n".join(output)


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    """Return the document's text page by page.

    Detect pages with no text layer and OCR them; mark those pages ocr=True.
    The OCR libraries need system packages in your Dockerfile (tesseract-ocr,
    poppler-utils), not only pip packages.
    """
    source = Path(path)
    doc = Document(source.name, str(doc_version), superseded)
    if source.suffix.lower() == ".pdf":
        with pdfplumber.open(path) as pdf:
            for number, raw_page in enumerate(pdf.pages, 1):
                # Some booklet pages retain hidden text outside the visible viewport.
                page = raw_page.crop((0, 0, raw_page.width, raw_page.height))
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                scanned = len(text.strip()) < 30
                if scanned:
                    images = convert_from_path(path, dpi=180, first_page=number, last_page=number)
                    text = pytesseract.image_to_string(images[0], config="--psm 3")
                    images[0].close()
                else:
                    if source.name.startswith("prospectus-"):
                        # Verified three-column prospectus layout; read each column downwards.
                        text = "\n\n".join(
                            _region_text(
                                page.crop(
                                    (
                                        left * page.width,
                                        0.10 * page.height,
                                        right * page.width,
                                        0.94 * page.height,
                                    )
                                )
                            )
                            for left, right in [(0.06, 0.355), (0.36, 0.645), (0.65, 0.94)]
                        )
                    else:
                        text = _region_text(page)
                doc.pages.append(Page(source.name, number, text, scanned))
                raw_page.close()
    else:
        text = source.read_text(encoding="utf-8")
        if source.suffix.lower() in {".html", ".htm"}:
            soup = BeautifulSoup(text, "html.parser")
            for node in soup(["script", "style", "nav", "header", "footer"]):
                node.decompose()
            main = soup.find("main") or soup.find(id="main") or soup.body or soup
            if not isinstance(main, Tag):
                main = soup
            for table in main.find_all("table"):
                if not isinstance(table, Tag):
                    continue
                rows = [
                    " | ".join(
                        c.get_text(" ", strip=True)
                        for c in row.find_all(["th", "td"])
                        if isinstance(c, Tag)
                    )
                    for row in table.find_all("tr")
                    if isinstance(row, Tag)
                ]
                table.replace_with(NavigableString("\nTABLE\n" + "\n".join(rows) + "\n"))
            for heading in main.find_all(re.compile(r"^h[1-6]$")):
                if isinstance(heading, Tag):
                    heading.replace_with(
                        NavigableString("\n## " + heading.get_text(" ", strip=True) + "\n")
                    )
            text = main.get_text("\n", strip=True)
        else:
            text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
        doc.pages.append(Page(source.name, 1, text))
    return doc
