"""Ollama provider: ollama-host or ollama-incluster (section 3.5). Yours to build."""

from __future__ import annotations

import httpx
from .prompt import messages
from ...services.usage import record_usage
from ...config import Settings
from ...schemas import Answer, Passage
from ...services.tracing import event


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings  # ollama_url, llm_model, temperature

    def generate(
        self, question: str, passages: list[Passage], correction: str | None = None
    ) -> Answer:
        prompt = messages(question, passages)
        schema = Answer.model_json_schema()
        # The model selects complete references from retrieved evidence; it cannot
        # invent a page number or combine unrelated source/section fields.
        schema["properties"]["citations"]["items"] = {
            "enum": [{"source": p.source, "section": p.section, "page": p.page} for p in passages]
        }
        refusal = "The available documents do not contain enough evidence to answer this question."
        prompt[0]["content"] += "\nFor an abstention use exactly: " + refusal
        if correction:
            prompt[0]["content"] += (
                "\nRETRY: Your previous output failed validation. Return exactly one sentence "
                "and put its references only in the citations array. All JSON citations must "
                "copy source, section and page exactly. Do not add uncited background. "
                "If the evidence does not answer the question, abstain with no citations."
            )
        if correction == "abstention_with_citations":
            prompt[0]["content"] += (
                "\nYour previous response set answered_from_context to false but supplied citations. "
                "Read the passages again. If a passage directly answers the question, give the "
                "supported answer, set answered_from_context to true, and cite that passage. "
                "If evidence is insufficient, set answered_from_context to false and citations to []."
            )
        event("generation_attempts", prompt=prompt, schema=schema, correction=correction,
              model=self.settings.llm_model, parameters={"temperature": self.settings.temperature,
              "seed": 42, "num_ctx": 4096, "num_predict": 400})
        with httpx.Client(timeout=self.settings.llm_timeout, trust_env=False) as client:
            r = client.post(
                self.settings.ollama_url.rstrip("/") + "/api/chat",
                json={
                    "model": self.settings.llm_model,
                    "messages": prompt,
                    "format": schema,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {
                        "seed": 42,
                        "temperature": self.settings.temperature,
                        "num_ctx": 4096,
                        "num_predict": 400,
                    },
                },
            )
            r.raise_for_status()
            data = r.json()
        record_usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0))
        return Answer.model_validate_json(data["message"]["content"])
