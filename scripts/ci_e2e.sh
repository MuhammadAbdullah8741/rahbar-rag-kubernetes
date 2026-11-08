#!/usr/bin/env bash
set -euo pipefail
# Isolated disposable fixture deployment. Never targets the developer's minikube.
CLUSTER=${CLUSTER:-rahbar-ci}
TAG=${TAG:-ci}
PREFIX=${PREFIX:-rahbar}
if kind get clusters | grep -Fxq "$CLUSTER"; then
  echo "Refusing to reuse existing cluster $CLUSTER" >&2
  exit 1
fi
export KUBECONFIG
KUBECONFIG=$(mktemp)
cleanup() {
  kubectl --context "kind-$CLUSTER" -n rahbar get pods,jobs -o wide || true
  kubectl --context "kind-$CLUSTER" -n rahbar logs job/indexer || true
  if [[ -n "${FORWARD_PID:-}" ]]; then kill "$FORWARD_PID" 2>/dev/null || true; fi
  kind delete cluster --name "$CLUSTER"
  rm -f "$KUBECONFIG"
}
trap cleanup EXIT
kind create cluster --name "$CLUSTER" --image kindest/node:v1.35.0 --wait 180s
kind get kubeconfig --name "$CLUSTER" > "$KUBECONFIG"
if [[ "${LOCAL_IMAGE_CACHE:-0}" == 1 ]]; then
  # Local reruns can reuse a complete Docker image without another registry pull.
  # Normal GitHub runs use the registry references in the manifests.
  for dependency in chromadb/chroma:1.0.12 redis:7.4.2-alpine; do
    if docker image inspect "$dependency" >/dev/null 2>&1; then
      # Docker Desktop retains a multi-platform index after pulling one platform.
      # Import only that platform; kind load's --all-platforms expects absent blobs.
      docker save "$dependency" | docker exec -i "$CLUSTER-control-plane" \
        ctr -n k8s.io images import --platform linux/amd64 -
    fi
  done
fi
if [[ "$PREFIX" == rahbar ]]; then
  for component in api indexer ui; do
    docker build -t "rahbar-$component:$TAG" "$component"
    kind load docker-image "rahbar-$component:$TAG" --name "$CLUSTER"
  done
fi
# The same ingress controller as the tested local assignment environment.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.15.1/deploy/static/provider/kind/deploy.yaml
kubectl label node "$CLUSTER-control-plane" ingress-ready=true --overwrite
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=600s
python scripts/render_fixture_overlay.py "$PREFIX" "$TAG"
# Start storage before the writer, so cold registry pulls do not exhaust Job retries.
kubectl kustomize k8s/overlays/ci-generated | python -c 'import sys,yaml; print(yaml.safe_dump_all(d for d in yaml.safe_load_all(sys.stdin) if d.get("kind") != "Job"))' | kubectl apply -f -
kubectl -n rahbar rollout status statefulset/chroma --timeout=600s
kubectl -n rahbar rollout status deployment/redis --timeout=180s
kubectl apply -k k8s/overlays/ci-generated
kubectl -n rahbar wait --for=condition=complete job/indexer --timeout=600s
kubectl -n rahbar rollout status deployment/api --timeout=180s
kubectl -n rahbar rollout status deployment/ui --timeout=180s
kubectl -n ingress-nginx port-forward service/ingress-nginx-controller 18080:80 > /tmp/rahbar-ci-forward.log 2>&1 &
FORWARD_PID=$!
for attempt in {1..30}; do
  if curl -fsS -H 'Host: rahbar.local' http://127.0.0.1:18080/ >/dev/null; then break; fi
  sleep 1
done
python eval/run_eval.py --api http://127.0.0.1:18080 --host rahbar.local \
  --golden eval/fixtures/golden.fixture.yaml --baseline eval/fixtures/baseline.json \
  --out eval/fixtures/ci-results.json
