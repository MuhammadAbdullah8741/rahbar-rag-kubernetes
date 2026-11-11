"""The real retriever. Yours to build (sections 3.2 and 4.4).

Connection details are already here; the query is not.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import cached_property
from typing import Any

from ..config import Settings
from ..schemas import Passage
from ..services.embedding import embed_query


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def client(self) -> Any:
        import chromadb  # the thin client, from chromadb-client in requirements.txt
        from chromadb.config import Settings as ChromaSettings

        return chromadb.HttpClient(
            host=self.settings.chroma_host,
            port=self.settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def snapshot(self) -> Any:
        from chromadb.errors import NotFoundError

        name = self.settings.collection
        try:
            control = self.client.get_collection(name + "-control")
            name = control.metadata["active_collection"]
        except NotFoundError:
            pass
        collection = self.client.get_collection(name)
        meta = collection.metadata or {}
        if (
            meta.get("embed_model") != self.settings.embed_model
            or meta.get("dimension") != self.settings.embed_dimension
        ):
            raise ValueError("Embedding pin mismatch; refusing retrieval")
        return collection

    def prepare(self, question: str) -> tuple[Any, list[float]]:
        return self.snapshot(), embed_query(question, self.settings)

    def retrieve(self, question: str, k: int) -> list[Passage]:
        collection, vector = self.prepare(question)
        return self.search(question, k, collection, vector)

    def search(self, question: str, k: int, collection: Any, vector: list[float]) -> list[Passage]:
        all_rows = collection.get(include=["documents", "metadatas"])
        year = re.search(r"\b20\d{2}\b", question)
        versions = sorted(
            {
                m["doc_version"]
                for m in all_rows["metadatas"]
                if year and str(m["doc_version"]).startswith(year.group())
            }
        )
        where: dict[str, Any] = (
            {"doc_version": {"$in": versions}} if versions else {"superseded": False}
        )
        eligible = (
            [
                (i, t, m)
                for i, t, m in zip(all_rows["ids"], all_rows["documents"], all_rows["metadatas"])
                if m["doc_version"] in versions
            ]
            if versions
            else [
                (i, t, m)
                for i, t, m in zip(all_rows["ids"], all_rows["documents"], all_rows["metadatas"])
                if not m["superseded"]
            ]
        )
        if not eligible:
            return []
        hits = collection.query(
            query_embeddings=[vector],
            where=where,
            n_results=min(max(k * 3, 15), len(eligible)),
            include=["documents", "metadatas", "distances"],
        )
        passages = {}
        ranks: dict[str, float] = {}
        for rank, (cid, text, meta, distance) in enumerate(
            zip(hits["ids"][0], hits["documents"][0], hits["metadatas"][0], hits["distances"][0])
        ):
            passages[cid] = Passage(
                chunk_id=cid,
                text=text,
                source=meta["source"],
                section=meta["section"],
                page=meta["page"],
                score=1 - distance,
            )
            ranks[cid] = 1 / (60 + rank + 1)
        if self.settings.hybrid:
            terms = set(re.findall(r"[a-z0-9]+", question.lower())) - STOPWORDS
            tokenized = [
                (
                    cid,
                    text,
                    meta,
                    Counter(re.findall(r"[a-z0-9]+", (meta["section"] + " " + text).lower())),
                )
                for cid, text, meta in eligible
            ]
            idf = {
                t: math.log(1 + len(tokenized) / (1 + sum(t in row[3] for row in tokenized)))
                for t in terms
            }
            scores = [
                (sum(idf[t] * counts[t] / (counts[t] + 1.2) for t in terms), cid, text, meta)
                for cid, text, meta, counts in tokenized
            ]
            for rank, (score, cid, text, meta) in enumerate(
                sorted(scores, reverse=True)[: max(k * 3, 15)]
            ):
                if score <= 0:
                    continue
                ranks[cid] = ranks.get(cid, 0) + 1 / (60 + rank + 1)
                if cid not in passages:
                    # Keep a genuine cosine score for the relevance floor, not a lexical score.
                    stored = collection.get(ids=[cid], include=["embeddings"])["embeddings"][0]
                    cosine = sum(a * b for a, b in zip(vector, stored)) / (
                        math.sqrt(sum(a * a for a in vector) * sum(b * b for b in stored)) or 1
                    )
                    passages[cid] = Passage(
                        chunk_id=cid,
                        text=text,
                        source=meta["source"],
                        section=meta["section"],
                        page=meta["page"],
                        score=cosine,
                    )
        return [passages[cid] for cid in sorted(ranks, key=lambda i: ranks[i], reverse=True)[:k]]


STOPWORDS = set(
    "a an the is are was were to of in for on and or how what when which i my do does "
    "can may must be have has it this that with from at as me you".split()
)
