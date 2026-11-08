import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
from app.config import Settings
from app.schemas import Answer, Citation, Passage
from app.providers.llm.ollama import OllamaProvider
from app.services.embedding import embed_query
from app.services.usage import tokens


def test_ollama_sends_constrained_schema_and_records_usage(monkeypatch):
    p = Passage(
        chunk_id="x", source="rules.pdf", section="Fees", page=1, text="Fee is 30.", score=0.9
    )
    answer = Answer(
        reasoning="Table",
        answer="Fee is 30 [rules.pdf / Fees].",
        citations=[Citation(source=p.source, section=p.section, page=1)],
        answered_from_context=True,
        confidence="high",
    )
    response = Mock()
    response.json.return_value = {
        "message": {"content": answer.model_dump_json()},
        "prompt_eval_count": 10,
        "eval_count": 20,
    }
    client = Mock()
    client.post.return_value = response
    manager = Mock()
    manager.__enter__ = Mock(return_value=client)
    manager.__exit__ = Mock()
    monkeypatch.setattr("app.providers.llm.ollama.httpx.Client", lambda **kw: manager)
    tokens.set((0, 0))
    actual = OllamaProvider(Settings()).generate("fee?", [p], correction="validation")
    payload = client.post.call_args.kwargs["json"]
    assert actual == answer and tokens.get() == (10, 20)
    assert payload["format"]["properties"]["answer"]["type"] == "string"
    assert payload["format"]["properties"]["citations"]["items"]["enum"] == [
        {"source": "rules.pdf", "section": "Fees", "page": 1}
    ]
    assert "RETRY" in payload["messages"][0]["content"]
    assert payload["stream"] is False


def test_embedding_dimension_mismatch_rejected(monkeypatch):
    response = Mock()
    response.json.return_value = {"embeddings": [[1, 2]]}
    client = Mock()
    client.post.return_value = response
    manager = Mock()
    manager.__enter__ = Mock(return_value=client)
    manager.__exit__ = Mock()
    monkeypatch.setattr("app.services.embedding.httpx.Client", lambda **kw: manager)
    with pytest.raises(ValueError):
        embed_query("fee?", Settings())


def test_eval_rejects_regression_and_missing_citations():
    path = Path(__file__).resolve().parents[2] / "eval/run_eval.py"
    spec = importlib.util.spec_from_file_location("evaluation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    good = {
        "recall_at_5": 0.9,
        "citation_validity": 1.0,
        "abstention_correctness": 1.0,
        "fallback_count": 0,
    }
    assert module.gate(good, {"recall_at_5": 0.95}) == []
    assert module.gate(good, {"recall_at_5": 0.96})
    assert module.gate({**good, "citation_validity": 0.94}, None)
    assert module.gate({**good, "abstention_correctness": 0.5}, None)
    # The assignment gates recall, citation validity and must-abstain correctness.
    # Fallbacks remain visible in the report rather than changing those criteria.
    assert module.gate({**good, "fallback_count": 1}, None) == []
    response = {
        "answered_from_context": True,
        "citations": [{"source": "invented", "section": "X", "page": 1}],
        "retrieved": [],
    }
    assert module.citation_validity(response) == 0
