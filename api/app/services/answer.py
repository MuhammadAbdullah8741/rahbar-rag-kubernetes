"""Retrieve, cache, generate, validate, and decline safely when evidence is missing."""

from __future__ import annotations
import logging
import time
import redis
from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..providers.llm.ollama import OllamaProvider
from ..retrieval.base import Retriever
from ..retrieval.chroma import ChromaRetriever
from ..routes import metrics
from ..schemas import Answer, AskResponse, RetrievedRef
from .cache import SemanticCache
from .usage import tokens
from .validation import validate_grounding

log = logging.getLogger("rahbar.answer")


def decline(fallback: bool = False) -> Answer:
    return Answer(
        reasoning="No validated supporting answer is available.",
        answer=(
            "I could not validate an answer safely. Please try again."
            if fallback
            else "The available documents do not contain enough evidence to answer this question."
        ),
        citations=[],
        answered_from_context=False,
        confidence="low",
    )


def answer_question(
    question: str,
    retriever: Retriever,
    provider: LLMProvider,
    settings: Settings,
    session_id: str | None = None,
    follow_up: bool = False,
) -> AskResponse:
    tokens.set((0, 0))
    passages = []
    cache = None
    vector: list[float] = []
    generation = ""
    cached = False
    fallback = False
    result = None
    query = question
    started = time.perf_counter()
    try:
        if isinstance(retriever, ChromaRetriever):
            cache = SemanticCache(settings)
            if session_id:
                try:
                    previous = cache.last_question(session_id)
                    if previous:
                        follow_up = True
                        query = previous[-500:] + "\nFollow-up: " + question
                except redis.RedisError:
                    log.warning("conversation store unavailable")
            collection, vector = retriever.prepare(query)
            generation = collection.name
            if settings.cache_enabled and not follow_up:
                metrics.CACHE_LOOKUPS.inc()
                try:
                    result = cache.get(generation, question, vector)
                except (redis.RedisError, ValueError, KeyError):
                    log.warning("cache lookup failed; continuing without cache")
                if result:
                    cached = True
                    metrics.CACHE_HITS.inc()
                    result = result.model_copy(
                        update={"request_id": request_id_var.get(), "cached": True}
                    )
            if not result:
                passages = retriever.search(query, settings.top_k, collection, vector)
        else:
            passages = retriever.retrieve(query, k=settings.top_k)
    except Exception as exc:
        log.warning("retrieval failed", extra={"error_type": type(exc).__name__})
        fallback = True
    metrics.RETRIEVAL.observe(time.perf_counter() - started)
    if not result:
        grounded = [p for p in passages if p.score >= settings.relevance_floor]
        answer = decline(fallback)
        if grounded and not fallback:
            started = time.perf_counter()
            for retry in range(2):
                try:
                    generated = (
                        provider.generate(query, grounded, correction="validation")
                        if retry and isinstance(provider, OllamaProvider)
                        else provider.generate(query, grounded)
                    )
                    answer = validate_grounding(
                        generated,
                        grounded,
                        inline=provider.name not in {"stub", "fixture"},
                        question=query,
                    )
                    break
                except Exception as exc:
                    log.warning(
                        "generation validation failed",
                        extra={"attempt": retry + 1, "error_type": type(exc).__name__},
                    )
            else:
                fallback = True
                answer = decline(True)
            metrics.GENERATION.observe(time.perf_counter() - started)
        result = AskResponse(
            request_id=request_id_var.get(),
            answer=answer.answer,
            citations=answer.citations,
            answered_from_context=answer.answered_from_context,
            confidence=answer.confidence,
            provider=provider.name,
            fallback=fallback,
            retrieved=[
                RetrievedRef(
                    chunk_id=p.chunk_id,
                    source=p.source,
                    section=p.section,
                    page=p.page,
                    score=p.score,
                )
                for p in passages
            ],
        )
        if cache and settings.cache_enabled and not follow_up and not fallback:
            try:
                cache.put(generation, question, vector, result)
            except redis.RedisError:
                log.warning("cache write failed")
    if cache and session_id:
        try:
            cache.store_turn(session_id, question, result)
        except redis.RedisError:
            log.warning("conversation write failed")
    if not result.answered_from_context:
        metrics.ABSTENTIONS.inc()
    if result.fallback:
        metrics.FALLBACKS.inc()
    input_tokens, output_tokens = tokens.get()
    metrics.TOKENS.labels("input").observe(input_tokens)
    metrics.TOKENS.labels("output").observe(output_tokens)
    lookups = metrics.CACHE_LOOKUPS._value.get()
    metrics.CACHE_HIT_RATIO.set(metrics.CACHE_HITS._value.get() / lookups if lookups else 0)
    log.info(
        "answered",
        extra={
            "retriever": retriever.name,
            "provider": provider.name,
            "top_k": settings.top_k,
            "chunk_ids": [p.chunk_id for p in result.retrieved],
            "scores": [round(p.score, 4) for p in result.retrieved],
            "answered_from_context": result.answered_from_context,
            "cached": cached,
            "fallback": result.fallback,
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
        },
    )
    return result
