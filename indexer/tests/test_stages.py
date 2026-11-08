import json
from unittest.mock import Mock

import pytest
from pipeline.models import Document, Page, Chunk
from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.extract import extract
from pipeline.embed import embed
from pipeline.store import store
from pipeline.config import get_settings
from pipeline.run import discover, run_pipeline


def test_html_tables_and_headings_survive_extraction(tmp_path):
    path = tmp_path / "fees.html"
    path.write_text(
        "<html><nav>irrelevant</nav><main><h2>Tuition</h2><table><tr><th>Degree</th><th>Fee</th></tr><tr><td>BS</td><td>12000</td></tr></table></main></html>"
    )
    doc = extract(str(path), "2026", False)
    assert "irrelevant" not in doc.pages[0].text
    assert "BS | 12000" in doc.pages[0].text
    assert "## Tuition" in doc.pages[0].text


def test_ocr_fallback_marks_page(monkeypatch, tmp_path):
    image = Mock()
    page = Mock()
    page.width = 100
    page.height = 100
    page.crop.return_value = page
    page.extract_text.return_value = ""
    pdf = Mock()
    pdf.pages = [page]
    pdf.__enter__ = Mock(return_value=pdf)
    pdf.__exit__ = Mock()
    monkeypatch.setattr("pipeline.extract.pdfplumber.open", lambda _: pdf)
    monkeypatch.setattr("pipeline.extract.convert_from_path", lambda *a, **k: [image])
    monkeypatch.setattr(
        "pipeline.extract.pytesseract.image_to_string", lambda *a, **k: "Scanned policy content"
    )
    doc = extract(str(tmp_path / "scan.pdf"), "2023", True)
    assert doc.pages[0].ocr and doc.pages[0].text == "Scanned policy content"
    image.close.assert_called_once()


def test_clean_preserves_paragraphs_and_repairs_hyphenation():
    doc = Document("x", "v", False, [Page("x", 1, "Head\n\nregis-\ntration\x00    rules")])
    text = clean(doc).pages[0].text
    assert "registration" in text and "\x00" not in text and "\n\n" in text


def test_chunks_bound_size_keep_metadata_and_stable_ids():
    doc = Document(
        "x", "2023", True, [Page("x", 2, "## Rules\n" + " ".join(f"word{i}" for i in range(130)))]
    )
    parts = chunk(doc, 50, 10)
    assert len(parts) > 2 and all(len(c.text.split()) <= 50 for c in parts)
    assert parts[0].text.split()[-10:] == parts[1].text.split()[:10]
    assert parts[0].metadata() == dict(
        source="x", section="Rules", page=2, doc_version="2023", superseded=True
    )
    assert [c.id for c in parts] == [c.id for c in chunk(doc, 50, 10)]
    with pytest.raises(ValueError):
        chunk(doc, 50, 50)


def test_fixture_embeddings_are_deterministic_normalized(monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "fixture-hash-v1")
    a, b = embed(["attendance rules", "attendance rules"], get_settings())
    assert a == b and len(a) == 768 and sum(x * x for x in a) == pytest.approx(1)


def test_atomic_store_publishes_only_complete_index(monkeypatch):
    client = Mock()
    lock = Mock(name="lock")
    lock.name = "lock"
    collection = Mock()
    collection.count.return_value = 1
    client.create_collection.side_effect = [lock, collection]
    control = client.get_or_create_collection.return_value
    monkeypatch.setattr("pipeline.store.get_client", lambda _: client)
    piece = Chunk("id", "text", "x", "Rules", 1, "2026", False)
    assert store([piece], [[1, 0]], get_settings()) == 1
    control.modify.assert_called_once()
    assert control.modify.call_args.kwargs["metadata"]["dimension"] == 2
    client.delete_collection.assert_called_once_with("lock")


def test_failed_store_never_changes_active_pointer(monkeypatch):
    client = Mock()
    lock = Mock()
    lock.name = "lock"
    collection = Mock()
    collection.add.side_effect = ConnectionError()
    client.create_collection.side_effect = [lock, collection]
    monkeypatch.setattr("pipeline.store.get_client", lambda _: client)
    with pytest.raises(ConnectionError):
        store([Chunk("id", "text", "x", "Rules", 1, "2026", False)], [[1, 0]], get_settings())
    client.get_or_create_collection.assert_not_called()
    client.delete_collection.assert_called_once()
    with pytest.raises(ValueError):
        store([], [], get_settings())


def test_discovery_and_full_fixture_pipeline(tmp_path, monkeypatch):
    path = tmp_path / "rules.md"
    path.write_text(
        "---\ndoc_version: 2026\nsuperseded: false\n---\n## Attendance\nMinimum attendance is 80 percent."
    )
    assert discover(str(tmp_path))[0][1:] == ("2026", False)
    monkeypatch.setenv("CORPUS_DIR", str(tmp_path))
    monkeypatch.setenv("EMBED_MODEL", "fixture-hash-v1")
    sink = Mock(return_value=1)
    monkeypatch.setattr("pipeline.store.store", sink)
    assert run_pipeline(get_settings()) == 1
    assert sink.call_args.args[0][0].section == "Attendance"
    (tmp_path / "_index.json").write_text(
        json.dumps([{"file": "rules.md", "doc_version": "2023", "superseded": True}])
    )
    assert discover(str(tmp_path))[0][1:] == ("2023", True)
