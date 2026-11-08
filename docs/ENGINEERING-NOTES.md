# Engineering notes

## 1. Indexing in API startup: what breaks with three replicas?

Every replica would extract/OCR/embed the same documents and race to modify one
collection. A restart or scale-out would become an expensive write event; readiness
would depend on ingestion rather than serving capability. Our API startup only
constructs clients and checks dependencies ([api/app/main.py:30](../api/app/main.py#L30)).
The Job owns all writes ([indexer/pipeline/store.py:23](../indexer/pipeline/store.py#L23)). It creates a
writer lock, fills a fresh collection, verifies its count and updates one control
pointer. A partially written replacement never becomes the active snapshot. The
CronJob forbids overlapping scheduled Jobs; the writer lock also covers manual Jobs.

## 2. Swapped readiness/liveness during 90 seconds of slow Chroma

Our liveness endpoint does not query dependencies; readiness does. See
[api/app/services/readiness.py:13](../api/app/services/readiness.py#L13) and
[k8s/base/api.yaml:66](../k8s/base/api.yaml#L66). If swapped, the dependency-aware liveness
check would fail repeatedly and restart otherwise healthy processes, while the
process-only readiness check would route traffic to API pods unable to retrieve.
With the actual liveness period 20 seconds and threshold three, a sustained outage
can trigger a restart after roughly three failed probes if incorrectly wired.
Correct wiring removes unready endpoints while allowing recovery without a restart.
The dependency checks use bounded two-second network timeouts. Startup and runtime
readiness both verify the collection pin and nonempty count.

## 3. What the CPU HPA measures

[k8s/base/hpa.yaml:10](../k8s/base/hpa.yaml#L10) sets 3-8 replicas and a 70% CPU target.
It measures API-container CPU relative to its CPU request, not Windows Ollama CPU,
model queue length, GPU utilization or end-to-end response latency. API requests
spend substantial time waiting for remote generation; low API CPU can coexist with
slow answers. More API replicas can overload the same host model. A production
system should bound model concurrency and scale on queue depth/in-flight requests
and latency, alongside scaling the actual inference workers. The assignment's CPU
HPA is present and observable, but is not claimed to solve inference capacity.

## 4. Indexer memory, margin and failure exit

The completed real Job indexed 340 chunks in 412.6 seconds. Its cgroup
`memory.peak` was 258,052,096 bytes (246.1 MiB) against a 1 GiB limit, leaving
777.9 MiB for that run. The final log is `docs/evidence/real-indexer-final.txt`.
This is a measured whole-container peak, including OCR subprocesses, rather than
a guarantee for larger corpora. The earlier interrupted run's `kubectl top` sample
was 522 MiB; those historical samples remain in `docs/evidence/resource-samples.json`.
We release PDF page caches after extraction and restrict Tesseract to
one OpenMP thread under the one-core quota. See
[indexer/pipeline/extract.py:86](../indexer/pipeline/extract.py#L86) and
[k8s/base/indexer-job.yaml:32](../k8s/base/indexer-job.yaml#L32).

Exceeding the cgroup memory limit can produce reason `OOMKilled` and exit code 137
(SIGKILL). Inspect `kubectl describe pod` and container lastState before diagnosing
an arbitrary 137 as OOM: an external kill can use the same exit code. Adjust requests
and limits from measurements or reduce peak processing memory; do not merely
increase Job retries. `kubectl top pods -n rahbar --containers` supplied the samples.

## 5. Recall by type: worst case and why

The prewritten golden set's measured retrieval recall@5 by type is:

| Type | recall@5 |
| --- | ---: |
| ordinary | 0.7500 |
| version | 1.0000 |
| exact | 1.0000 |
| injection | 1.0000 |

Ordinary questions are weakest. The incomplete-grade question retrieved alternate
policy sections containing related grading text but missed its labelled HTML
section; the scanned faculty start-up question missed the final-approval section.
OCR/heading quality and short fragments weaken retrieval. We retained the original
labels and misses rather than changing the benchmark after seeing results. Exact
terms benefit from lexical ranking alongside cosine similarity. See
[api/app/retrieval/chroma.py:109](../api/app/retrieval/chroma.py#L109) and every hit in
`eval/chunk-experiments.json`. Retrieval recall does not establish answer correctness;
the real generation results separately report citation validity and abstention.

## 6. API-only embedding model change

[api/app/retrieval/chroma.py:51](../api/app/retrieval/chroma.py#L51) refuses retrieval when
model name or dimension differs. Readiness returns 503; liveness remains 200.
`docs/evidence/real-embedding-pin-check.txt` records changing the shared ConfigMap,
restarting only the API, observing an unready new pod and restoring the correct pin. The
isolated fault script reproduced the exception. A matching dimension alone is not
sufficient: coordinate model changes with a new index publication. The shared
ConfigMap normally keeps API and Job pins equal. Installed model digests are also
recorded, because a mutable model tag could otherwise change without a name change.

## 7. The failure that consumed more than an hour

Citation-generation integration and PDF extraction debugging spanned multiple
sessions, exceeding an hour of elapsed debugging work; we did not measure a precise
uninterrupted stopwatch duration. Initial Llama answers had correct structured
sources but numeric aliases, omitted inline labels, or an extra uncited sentence.
Repeated full evaluation runs therefore returned safe fallbacks. More prompt text
alone was insufficient. A dynamic regex schema also exposed an unsupported escaped
space in Ollama's grammar conversion, and its more complex form was unreliable.

We kept the standard structured Answer schema and strict source/section/page
membership validation. Numbered aliases resolve only against retrieved evidence.
For a single sentence, its validated structured citations can be rendered inline;
multiple uncited claims and explicit invalid references still fail and retry once.
See [api/app/services/validation.py:5](../api/app/services/validation.py#L5) and regression
tests in `api/tests/test_grounding.py`. We preserved initial failures rather than
claiming they passed. The lesson was to isolate a failing response before spending
time rerunning all questions, and to separate citation presentation from provenance
validation without silently attributing multiple unsupported claims.
