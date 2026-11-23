"""The indexer Job's entry point. It runs once and exits (section 4.2).

    python -m pipeline.run --dummy    # week 1: three fake chunks, no model needed
    python -m pipeline.run            # the real pipeline: extract, clean, chunk, embed, store

Exit code 0 means the index was written; anything else fails the Job, and
Kubernetes retries it up to the Job's backoffLimit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from .config import IndexerSettings, get_settings
from .models import Chunk
from .report import save as save_report

_verification_events = []


def log(msg: str, **fields: object) -> None:
    _verification_events.append({"msg": msg, **fields})
    print(
        json.dumps(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "logger": "rahbar.indexer",
                "msg": msg,
                **fields,
            }
        ),
        flush=True,
    )


def _front_matter(path: Path) -> dict[str, str]:
    """Read `key: value` lines between leading '---' markers (used by eval/fixtures)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def verify_manifest(path: Path, record: dict) -> dict[str, str]:
    """Check provenance and integrity against the download manifest."""
    missing = [key for key in ("name", "url") if not str(record.get(key) or "").strip()]
    if str(record.get("doc_version") or "").strip().lower() in {"", "unknown"} and not record.get("date"):
        missing.append("date or doc_version")
    checks = {"metadata": "missing " + ", ".join(missing) if missing else "pass"}
    try:
        with path.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        return {**checks, "bytes": str(exc), "sha256": "file unreadable"}
    checks["bytes"] = "pass" if size == record.get("bytes") else "size mismatch or missing"
    checks["sha256"] = "pass" if digest == record.get("sha256") else "hash mismatch or missing"
    return checks


def discover(corpus_dir: str) -> list[tuple[Path, str, bool]]:
    """List (path, doc_version, superseded) for every document to index.

    corpus/fetch.py writes _index.json next to the files it downloads; use it when
    present. Otherwise read Markdown front matter (the CI fixtures work this way).
    """
    root = Path(corpus_dir)
    index = root / "_index.json"
    if index.exists():
        entries = json.loads(index.read_text(encoding="utf-8"))
        return [
            (
                root / e["file"],
                str(e.get("doc_version", "unknown")),
                bool(e.get("superseded", False)),
            )
            for e in entries
        ]
    found = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".pdf", ".md", ".html", ".txt"}:
            continue
        if path.name.lower().startswith("readme"):
            continue
        meta = _front_matter(path) if path.suffix.lower() == ".md" else {}
        found.append(
            (
                path,
                meta.get("doc_version", "unknown"),
                meta.get("superseded", "false").lower() == "true",
            )
        )
    return found


def run_pipeline(settings: IndexerSettings) -> int:
    from .chunk import chunk
    from .clean import clean
    from .embed import embed
    from .extract import extract
    from .store import store

    documents = discover(settings.corpus_dir)
    if not documents:
        raise SystemExit(f"no documents found in {settings.corpus_dir}")
    all_chunks: list[Chunk] = []
    manifest = Path(settings.corpus_dir) / "_index.json"
    records = {entry["file"]: entry for entry in json.loads(manifest.read_text())} if manifest.exists() else {}
    from .similarity import document_vector, version_key

    from .retention import retain

    signatures: dict[str, list[float]] = {}
    versions: dict[str, str] = {}
    replacements = {}
    threshold = float(os.environ.get("NEAR_DUPLICATE_THRESHOLD", "0.99"))
    if not 0 < threshold <= 1:
        raise ValueError("NEAR_DUPLICATE_THRESHOLD must be between zero (exclusive) and one")
    accepted_hashes: dict[str, str] = {}
    def processing_order(item):
        path, version, old = item
        record = records.get(str(path.relative_to(settings.corpus_dir)), {})
        return bool(record.get("supersedes_file")), old, version_key(version) if record.get("supersedes_file") else ()

    for path, doc_version, superseded in sorted(documents, key=processing_order):
        if records:
            checks = verify_manifest(path, records[str(path.relative_to(settings.corpus_dir))])
            passed = all(reason == "pass" for reason in checks.values())
            log("manifest verification", source=path.name, passed=passed, checks=checks)
            if not passed:
                retain(path, "quarantine", doc_version, checks)
                continue
        from .quality import checked_extract

        doc, report = checked_extract(path, doc_version, superseded, clean, extract)
        log("extraction verification", source=path.name, **report)
        if doc is None:
            retain(path, "quarantine", doc_version, report)
            continue
        if records:
            digest = records[str(path.relative_to(settings.corpus_dir))]["sha256"]
        else:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
        original = accepted_hashes.get(digest)
        log("exact duplicate verification", source=path.name, passed=original is None,
            sha256=digest, duplicate_of=original,
            reason="exact duplicate" if original else "unique file content")
        if original is not None:
            retain(path, "quarantine", doc_version, {"exact_duplicate_of": original})
            continue
        pieces = chunk(doc, settings.chunk_size, settings.chunk_overlap)
        if not pieces:
            log("content verification", source=path.name, passed=False, reason="no indexable text")
            retain(path, "quarantine", doc_version, {"reason": "no indexable text"})
            continue
        record = records.get(str(path.relative_to(settings.corpus_dir)), {})
        previous = record.get("supersedes_file")
        if previous:
            previous_version = version_key(versions.get(previous, ""))
            if not previous_version or version_key(doc_version) <= previous_version or previous in replacements:
                log("recency verification", source=path.name, passed=False,
                    reason="missing, conflicting or non-newer revision", previous=previous)
                retain(path, "quarantine", doc_version, {"invalid_revision_of": previous})
                continue
        vector = document_vector(pieces, settings)
        scores = {name: sum(a*b for a, b in zip(vector, other, strict=True))
                  for name, other in signatures.items() if name != previous}
        closest = max(scores, key=lambda name: scores[name]) if scores else None
        score = scores[closest] if closest is not None else None
        unique = score is None or score < threshold
        log("near duplicate verification", source=path.name, passed=unique, closest=closest,
            cosine=score, threshold=threshold, excluded_predecessor=previous)
        if not unique:
            retain(path, "quarantine", doc_version, {"near_duplicate_of": closest, "cosine": score, "threshold": threshold})
            continue
        if previous:
            replacements[previous] = path.name
            log("revision accepted", source=path.name, previous=previous, version=doc_version)
        if superseded:
            retain(path, "archive", doc_version, {"reason": "manifest marks version superseded"})
        accepted_hashes[digest] = path.name
        signatures[path.name] = vector
        versions[path.name] = doc_version
        log("chunked", source=path.name, chunks=len(pieces))
        if superseded:
            log("superseded metadata", source=path.name,
                replaced_by="newer manifest version (superseded=true)", chunks=len(pieces))
        retain(path, "data-lake", doc_version, {"reason": "verified document"})
        all_chunks.extend(pieces)
    for piece in all_chunks:
        if piece.source in replacements:
            piece.superseded = True
    for source, successor in replacements.items():
        retain(Path(settings.corpus_dir) / source, "archive", versions[source], {"replaced_by": successor})
        log("superseded metadata", source=source, replaced_by=successor,
            chunks=sum(piece.source == source and piece.superseded for piece in all_chunks))
    save_report(_verification_events)
    vectors = embed([c.text for c in all_chunks], settings)
    return store(all_chunks, vectors, settings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the RAHBAR index, then exit.")
    parser.add_argument("--dummy", action="store_true", help="write three fake chunks")
    args = parser.parse_args()
    settings = get_settings()
    log(
        "indexer starting",
        dummy=args.dummy,
        embed_model=settings.embed_model,
        collection=settings.collection,
        chroma=f"{settings.chroma_host}:{settings.chroma_port}",
        pod=os.environ.get("HOSTNAME", "-"),
    )
    started = time.perf_counter()
    try:
        if args.dummy:
            from .dummy import write_dummy_index
            from .store import get_client

            count = write_dummy_index(settings, get_client(settings))
        else:
            count = run_pipeline(settings)
            from .embed import counts

            log("embedding summary", **counts)
    except NotImplementedError as exc:
        log("indexer stage not implemented yet", error=str(exc))
        return 2
    peak = Path("/sys/fs/cgroup/memory.peak")
    try:
        memory_peak_bytes = int(peak.read_text()) if peak.exists() else None
    except (OSError, ValueError):
        memory_peak_bytes = None
    log(
        "indexer finished",
        chunks=count,
        seconds=round(time.perf_counter() - started, 1),
        memory_peak_bytes=memory_peak_bytes,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
