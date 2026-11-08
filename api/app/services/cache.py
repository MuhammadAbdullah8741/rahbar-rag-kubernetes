"""Redis semantic cache and expiring conversation turns, shared by API replicas."""

import hashlib
import json
import math
import re
from typing import Any
import redis
from ..config import Settings
from ..schemas import AskResponse


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return -1
    return sum(x * y for x, y in zip(a, b)) / (
        math.sqrt(sum(x * x for x in a) * sum(y * y for y in b)) or 1
    )


def exact_terms(text: str) -> set[str]:
    terms = set(re.findall(r"\b(?:\d[\d.,-]*|[a-z]{2,}\d+[a-z0-9]*)\b", text.lower()))
    if re.search(r"\b(?:grade|points|letter)\b", text, re.I):
        normalized = text.replace("\u2212", "-").replace("\u2013", "-")
        terms.update(t.upper() for t in re.findall(r"(?<!\w)[A-F][+-]?(?!\w)", normalized, re.I))
    return terms


class SemanticCache:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis: Any = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_timeout=2,
            socket_connect_timeout=2,
            decode_responses=True,
        )

    def key(self, generation: str) -> str:
        config = (
            "grounding-v2-grade-guard",
            self.settings.embed_model,
            self.settings.llm_model,
            self.settings.llm_provider,
            self.settings.top_k,
            self.settings.relevance_floor,
            self.settings.hybrid,
            self.settings.temperature,
        )
        digest = hashlib.sha256(repr(config).encode()).hexdigest()[:16]
        return f"rahbar:cache:{generation}:{digest}"

    def get(self, generation: str, question: str, vector: list[float]) -> AskResponse | None:
        for item in self.redis.lrange(self.key(generation), 0, 255):
            entry = json.loads(item)
            if exact_terms(question) != exact_terms(entry["question"]):
                continue
            if cosine(vector, entry["vector"]) >= self.settings.cache_threshold:
                return AskResponse.model_validate(entry["response"])
        return None

    def put(self, generation: str, question: str, vector: list[float], result: AskResponse) -> None:
        if result.fallback or not result.answered_from_context or result.confidence == "low":
            return
        key = self.key(generation)
        with self.redis.pipeline() as pipe:
            pipe.lpush(
                key,
                json.dumps(
                    {"question": question, "vector": vector, "response": result.model_dump()}
                ),
            )
            pipe.ltrim(key, 0, 255)
            pipe.expire(key, 86400)
            pipe.execute()

    def last_question(self, session_id: str) -> str | None:
        turns = self.redis.lrange("rahbar:session:" + session_id, 0, 0)
        return json.loads(turns[0])["question"] if turns else None

    def store_turn(self, session_id: str, question: str, result: AskResponse) -> None:
        key = "rahbar:session:" + session_id
        with self.redis.pipeline() as pipe:
            pipe.lpush(key, json.dumps({"question": question, "answer": result.answer}))
            pipe.ltrim(key, 0, 9)
            pipe.expire(key, 3600)
            pipe.execute()
