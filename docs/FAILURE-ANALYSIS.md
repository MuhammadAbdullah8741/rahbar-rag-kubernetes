# Failure analysis

Reproducible controlled experiments: `scripts/failure_experiments.py`; observed
outputs: `docs/evidence/failure-experiments.json`. Experiments run in an isolated
process and do not modify the active index. They are not claimed as production outages.

## Extraction: OCR disabled

Reading only the entrepreneurship PDF text layer returned **0 characters** across
all eight pages. Restoring OCR produced **11,757 characters**. The symptom is a
missing source despite a successful PDF-open operation. Diagnose by comparing
per-page extracted text lengths and OCR flags, rather than checking file existence.
The remedy is low-text detection, Poppler rasterization and Tesseract extraction.

## Chunking: section metadata discarded

Replacing every retrieved section label with `Document` reduced source-and-section
recall@5 from **0.8462 to 0.0** on the fixed golden questions. This deliberately tests
metadata loss, not a fresh semantic-index benchmark. Diagnose by inspecting the
retrieved section field beside the original heading. The remedy is carrying section,
page, source, version and superseded metadata through every chunk and into Chroma.

## Retrieval: API-only embedding pin change

An API setting of `wrong-model` against the existing index raised **Embedding pin
mismatch; refusing retrieval** before a query vector could be compared. The live
canary evidence also records liveness 200 and readiness 503 for a mismatch. Diagnose
using `/readyz`, startup logs and collection metadata. Restore the shared pin or
rebuild the index with a deliberate coordinated model change; never compare vectors
from unrelated models merely because dimensions happen to match.

## Generation: invalid structured output

A fault provider raised a schema error on each attempt. The service made **exactly
two calls** (initial plus one retry), returned a safe uncited fallback and did not
claim the answer came from context. Diagnose the `generation validation failed`
log entries and fallback counter. Fix the provider output contract/prompt; do not
weaken validation or cache fallback text. This test uses a deterministic failing
provider rather than relying on random model misbehavior.

## Additional problems actually encountered

Llama used numeric inline citation aliases despite returning correct full citations
in its JSON array. The original strict validator rejected these answers. The prompt
now requests structured references; numbered aliases are resolved only when the
retrieved passage, section and validated citation array agree. A regression test
rejects nonexistent aliases. Every claim sentence still requires a valid citation.

The first cache experiment produced one false hit even at 0.98: B and B- grade
questions embedded almost identically. Exact grade-code matching fixes that case.
Both before/after result files are retained. This is why similarity alone was not
accepted as sufficient evidence of equal intent.

The final provider constrains each citation to a complete retrieved reference using
an enum of source/section/page objects. A one-sentence answer may render its already
validated structured references inline when the label is omitted. This does not
repair multiple uncited claims or an explicit invalid reference. The dynamic regex
answer constraint was removed after unreliable grammar behavior was observed.

A live request returned HTTP 502 when the HPA reduced six API replicas to three.
The event log identified a terminating pod: the 30-second termination grace period
was shorter than CPU-only model generation. The API now allows 650 seconds for
two bounded 300-second provider attempts plus draining; its five-second preStop
removes it from routing before shutdown. The interrupted run is preserved in
`docs/evidence/interrupted-evaluation.txt`, and the subsequent full run is in
`docs/evidence/live-evaluation.txt`. This fixes the shutdown budget; it does not
make CPU HPA an inference-capacity signal or guarantee all network requests succeed.

One model response said `answered_from_context=false` but returned the factual
text `No Refund`. Abstentions are now normalized to a fixed refusal with low
confidence, so the UI cannot display an unsupported claim as a refusal. A regression
test covers that contradictory output without changing the evaluation labels.

The first fresh kind run exhausted its wait while downloading Chroma; the indexer
was also retrying before storage existed. CI now starts storage, waits for readiness,
then creates the Job. A local Docker Desktop cache import exposed a separate
multi-platform manifest issue: `kind load` requested blobs for platforms that had
not been downloaded. The optional local cache path imports only linux/amd64.
Normal GitHub runs pull the manifest references directly. The final clean run is
recorded separately from the interrupted attempts.
