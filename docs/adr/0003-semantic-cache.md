# ADR 0003: Redis cache scoped to index generation

Status: implemented; threshold measurements are in `eval/cache-experiments.json`.

All API replicas share Redis. Cache entries contain the query embedding, original
question, and validated response. Numeric and course-code tokens must match
before cosine similarity can produce a hit. Redis stores at most 256 entries per
namespace for 24 hours. This bounded list is adequate for this assignment, but a
larger service should use a vector index rather than scanning entries.

The namespace includes the active index generation, embedding model, generator,
model name, temperature, relevance floor, top-k, hybrid setting and validation version. Publishing a
new Chroma control pointer therefore makes old cached answers unreachable without
giving the indexer network access to Redis. Old namespaces expire naturally.

Abstentions, low-confidence answers and fallbacks are never cached. A request with
conversation history or an explicit follow-up flag bypasses cache reads and
writes. Conversation turns are kept separately for one hour, at most ten turns;
the last question supplies bounded context for the next request.

Semantic similarity is not proof of identical intent. The selected threshold must
have zero false hits on the recorded positive/negative pair set; this is an
empirical result on that set, not a universal guarantee.
