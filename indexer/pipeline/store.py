"""Stage 5: Store. The only code in the whole system that writes to Chroma."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .config import IndexerSettings
from .models import Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb  # the thin client, from chromadb-client in requirements.txt
    from chromadb.config import Settings as ChromaSettings

    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    """Write every chunk with its vector and metadata, and record the embedding model
    and vector dimension in the collection metadata (section 4.4). Return the count."""
    if not chunks or len(chunks) != len(vectors):
        raise ValueError("Non-empty chunks and matching embeddings are required")
    dimension = len(vectors[0])
    if not dimension or any(len(v) != dimension for v in vectors):
        raise ValueError("Embedding dimensions must agree")
    client = get_client(settings)
    lock_name = settings.collection + "-writer-lock"
    # Atomic collection creation admits only one writer. A killed writer leaves a
    # conservative lock: an operator must check Jobs before removing a stale lock.
    lock = client.create_collection(lock_name, metadata={"owner": str(uuid4())})
    name = settings.collection + "-" + uuid4().hex[:12]
    try:
        collection = client.create_collection(
            name,
            metadata={
                "hnsw:space": "cosine",
                "embed_model": settings.embed_model,
                "dimension": dimension,
                "generation": name,
            },
        )
        for start in range(0, len(chunks), 128):
            batch = chunks[start : start + 128]
            collection.add(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                embeddings=vectors[start : start + 128],
                metadatas=[c.metadata() for c in batch],
            )
        count = collection.count()
        if count != len(chunks):
            raise ValueError("Stored index count differs from planned chunk count")
        control = client.get_or_create_collection(settings.collection + "-control")
        # One metadata update publishes the whole index; old readers keep their snapshot.
        # Generation also invalidates every semantic-cache namespace immediately.
        control.modify(
            metadata={
                "active_collection": name,
                "generation": name,
                "embed_model": settings.embed_model,
                "dimension": dimension,
            }
        )
        return int(count)
    finally:
        client.delete_collection(lock.name)
