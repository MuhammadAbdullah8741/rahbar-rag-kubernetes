# ADR 0004: Host Ollama and public-document data boundary

Status: accepted.

The implemented real provider is host Ollama: `llama3.2:3b` generates and
`nomic-embed-text:latest` embeds 768-dimensional vectors. `docs/evidence/model-pins.json`
records installed model digests. The API and indexer use the same model name;
collection metadata records its name and dimension and readiness rejects a mismatch.
Model tags can move: reproducing the experiment requires checking the recorded
digest, not silently pulling a replacement under the same tag.

On this Windows/WSL Docker Desktop installation, the Kubernetes containers reach
Ollama through `host.docker.internal` at 192.168.65.254. The dev overlay provides
that host alias and allows only TCP 11434 to that address. Different Docker hosts
must adjust both the alias and policy. Ollama must listen on an interface reachable
from Docker; it is not deployed inside the cluster or exposed through Ingress.

The corpus contains only intentionally selected public institutional documents.
Do not upload student records, passwords, private assessment answers or personal
documents. Logs include request IDs, retrieved chunk IDs/scores and usage, not
raw questions, model reasoning or API keys. Redis conversation storage is ephemeral
with a TTL. The model's evidence summary is not returned to the user.

A generic hosted-provider interface exists, but hosted evaluation was not performed.
It would transmit questions and retrieved text to the configured provider and
requires an explicit data-handling decision plus a Kubernetes Secret. The local
configuration needs no paid API key. CI uses a clearly labelled deterministic
fixture provider and fixture embeddings; it does not claim to measure Llama quality.
