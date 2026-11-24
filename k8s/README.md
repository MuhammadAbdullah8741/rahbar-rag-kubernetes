# Assignment 3 Kubernetes reproduction

Run from the repository root inside WSL Ubuntu. Python below means
`$HOME/.venvs/rahbar/bin/python`; dependencies are installed by the root Makefile.
Docker Desktop, minikube, kubectl and host Ollama must be running. Models are
`nomic-embed-text:latest` and `llama3.2:3b`. The host address in the dev manifests
is `192.168.65.254`; update hostAliases and the Ollama egress policy together if
your Docker Desktop uses another address. No GitHub operation is required.

## Fresh cluster

```bash
export PATH="$HOME/.local/bin:$HOME/.venvs/rahbar/bin:$PATH"
make install VENV="$HOME/.venvs/rahbar"
python corpus/fetch.py
minikube start --driver=docker --memory=4096 --cpus=4
minikube addons enable metrics-server
minikube addons enable ingress
docker build -t rahbar-api:a3 api
docker build -t rahbar-indexer:a3 indexer
docker build -t rahbar-ui:dev ui
docker build -t rahbar-eval:a3-tools -f eval/Dockerfile .
minikube image load rahbar-api:a3 rahbar-indexer:a3 rahbar-ui:dev rahbar-eval:a3-tools
python scripts/a3_bootstrap.py
kubectl apply -f k8s/a3-retention-pvc.yaml -f k8s/a3-results-pvc.yaml
python scripts/load_corpus.py
python scripts/a3_cluster.py seed
python scripts/a3_cluster.py ingest --name a3-initial-a --collection rahbar --corpus /retained/input-a
kubectl wait -n rahbar --for=condition=complete job/a3-initial-a --timeout=7200s
python scripts/a3_cluster.py ingest --name a3-initial-ab --collection rahbar-a3-ab
kubectl wait -n rahbar --for=condition=complete job/a3-initial-ab --timeout=7200s
kubectl apply -f k8s/a3-api.yaml
kubectl apply -f k8s/gate-configmap.yaml -f k8s/eval-networkpolicy.yaml
kubectl rollout status -n rahbar deployment/api --timeout=180s
```

The bootstrap initially suspends the CronJob until input has been seeded.
After creating the candidate ingestion template, run `python scripts/a3_cron.py`
to enable the verified weekly Job. Each invocation
of the helper needs a new Job name. Job pod templates are immutable.

## Ingestion, evaluation and candidate

```bash
python scripts/a3_cluster.py ingest --name a3-ingest-candidate
kubectl wait -n rahbar --for=condition=complete job/a3-ingest-candidate --timeout=7200s
python scripts/a3_cluster.py candidate --top-k 3
kubectl rollout status -n rahbar deployment/api-candidate --timeout=180s
kubectl apply -f k8s/eval-baseline-job.yaml
kubectl logs -n rahbar -f job/eval-baseline
kubectl wait -n rahbar --for=condition=complete job/eval-baseline --timeout=14400s
kubectl apply -f k8s/eval-job.yaml
kubectl logs -n rahbar -f job/eval-candidate
```

`eval-job.yaml` runs all three evaluation levels, then the gate. A failed gate
returns nonzero and Kubernetes marks the Job failed. Results and traces are on
`a3-results`. Thresholds are mounted from `a3-gate`, never baked into an image.
The baseline Job must finish before the candidate Job. The candidate has its own
Service, Deployment selector and collection, so live requests cannot select it.

## Storage, traces and operation

```bash
python scripts/a3_cluster.py collect
python eval/trace_tool.py --directory traces
python eval/trace_tool.py --directory traces --id TRACE_ID
kubectl logs -n rahbar -l app=api --tail=100
kubectl port-forward -n rahbar svc/api 18002:8000
# another terminal
curl http://127.0.0.1:18002/metrics
kubectl get all,pvc,configmap,cronjob,job -n rahbar
kubectl top pods -n rahbar
```

Only ingestion Job code writes Chroma. NetworkPolicies limit its reachable
clients, but Chroma itself has no read-only credentials here: this is an
application-level writer contract, not database-enforced authorization.
The writer lock prevents overlapping publishes. CronJob concurrencyPolicy is
Forbid. Archives, quarantine, verified raw copies, embedding cache and reports
live on `rahbar-a3-retention`; traces and evaluations live on `a3-results`.

A collection publish uses an immutable snapshot and atomic pointer. Unchanged
chunks retain IDs and reuse vectors, but snapshot publication still writes
their stored vectors. The implementation does not claim zero physical writes.

## Final 33-question evaluation

After the setup and candidate-ingestion steps above, build the final tags and
run the final experiment orchestration (all evaluation requests run in Jobs):

```bash
docker tag rahbar-api:a3 rahbar-api:a3-final
docker build -t rahbar-eval:a3-submission -f eval/Dockerfile .
minikube image load rahbar-api:a3-final rahbar-eval:a3-submission
kubectl set image -n rahbar deployment/api api=rahbar-api:a3-final
kubectl set image -n rahbar deployment/api-candidate api=rahbar-api:a3-final
python scripts/a3_final_experiments.py
python scripts/a3_final_release.py
```

The first script runs baseline, repeat, top-k 3, top-k 0 and Batch A on the
same final golden set. The second runs coverage, candidate/bad/strict/restored
ConfigMap gates and promotes only a passing candidate, then demonstrates undo.
`eval/results/final/` contains the final evidence. Old `cluster/` results and
older screenshots retain their original 25-question provenance.
Named Jobs must be absent before repeating these scripts; save their results
and choose new names rather than deleting evidence before collecting it.
