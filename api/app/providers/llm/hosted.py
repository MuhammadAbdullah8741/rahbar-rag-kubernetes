"""Hosted free-tier provider (Groq, Google AI Studio, OpenRouter). Yours to build.

The key arrives as LLM_API_KEY from a Kubernetes Secret created on the command
line. It never appears in a file you commit, and never in a log line.
"""

from __future__ import annotations

import httpx
from .prompt import messages
from ...services.usage import record_usage
from ...config import Settings
from ...schemas import Answer, Passage


class HostedProvider:
    name = "hosted"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings  # hosted_base_url, llm_model, llm_api_key, temperature

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        if not self.settings.llm_api_key or not self.settings.hosted_base_url:
            raise ValueError("Hosted provider requires a URL and Secret-supplied key")
        with httpx.Client(timeout=self.settings.llm_timeout) as client:
            r = client.post(
                self.settings.hosted_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + self.settings.llm_api_key},
                json={
                    "model": self.settings.llm_model,
                    "messages": messages(question, passages),
                    "temperature": self.settings.temperature,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "Answer",
                            "schema": Answer.model_json_schema(),
                            "strict": True,
                        },
                    },
                },
            )
            r.raise_for_status()
            data = r.json()
        usage = data.get("usage", {})
        record_usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return Answer.model_validate_json(data["choices"][0]["message"]["content"])
