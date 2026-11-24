from pipeline.models import Document, Page
from pipeline.quality import checked_extract


def test_extraction_cache_reuses_content_but_refreshes_version(tmp_path, monkeypatch):
    monkeypatch.setenv("RAHBAR_RETENTION_DIR", str(tmp_path / "retained"))
    source = tmp_path / "policy.txt"
    source.write_text("old policy")
    calls = []

    def extract(path, version, superseded):
        calls.append(path)
        return Document(
            source.name, version, superseded, [Page(source.name, 1, source.read_text())]
        )

    first, _ = checked_extract(source, "v1", False, lambda d: d, extract)
    second, _ = checked_extract(source, "v2", True, lambda d: d, extract)
    assert len(calls) == 1 and second.doc_version == "v2" and second.superseded
    assert second.pages == first.pages
    source.write_text("changed policy")
    third, report = checked_extract(source, "v3", False, lambda d: d, extract)
    assert len(calls) == 2 and third.pages[0].text == "changed policy" and report["passed"]
