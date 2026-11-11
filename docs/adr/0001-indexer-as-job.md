# ADR 0001 Index documents in a separate Job

## Status

Accepted for the initial Kubernetes deployment, 6 November 2026.

## Context

The API has three replicas. Indexing in each API's startup would make all three write the same Chroma collection, repeat expensive extraction after restarts, and couple readiness to the indexing duration. A new API image should not require re-reading the documents.

## Decision

`k8s/base/indexer-job.yaml` runs the indexing image once, with restartPolicy OnFailure and a bounded retry/deadline. `k8s/base/reindex-cronjob.yaml` uses the same image, arguments and configuration. API replicas only read the collection. `/readyz` checks the collection, model and dimension plus Redis; `/healthz` does not call dependencies.

Chroma runs as a one-replica StatefulSet with a volumeClaimTemplate. Redis has a separate persistent volume. All application objects use namespace rahbar.

## Options considered

API startup indexing was rejected because every replica and restart would become a writer. An init container per API pod has the same problem. Running indexing manually on a developer laptop would lose the reproducible cluster Job and its recorded status/logs.

## Consequences

API pods can be alive but not ready before the first Job completes. The real Job reads
public files from a shared corpus PVC and performs all five stages. A weekly CronJob
runs Sunday at 02:00 Asia/Karachi with concurrencyPolicy Forbid. An atomic Chroma
collection-creation lock also prevents independently submitted writers from
publishing concurrently. The writer fills a fresh versioned collection, verifies
its count, then changes one control-pointer metadata record. Readers retain their
snapshot and subsequent requests see the new generation. Cache namespaces change
with that generation. Old collections are retained for rollback and must eventually
be pruned manually after confirming that no request or active pointer uses them.

A forcibly killed writer may leave its lock collection behind. Inspect all indexer
Jobs before removing a stale `<collection>-writer-lock`; never remove a lock merely
because a new Job is waiting. A failed staging collection is harmless to readers.
