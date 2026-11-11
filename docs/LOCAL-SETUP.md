# Local setup and restart guide

The real RAG implementation, Docker images, minikube deployment and local CI checks
are complete. This file describes restarting the existing installation. For a clean
clone, follow [README](../README.md); for measured results and limitations, read
[FINAL-VERIFICATION.md](FINAL-VERIFICATION.md).

## Start the existing app after restarting Windows

1. Open Docker Desktop on Windows and wait until its engine is running. Keep its
   Ubuntu WSL integration enabled. Do not enable a second Kubernetes cluster in Docker Desktop.
2. Keep Ollama running on Windows. It must listen on `0.0.0.0:11434`; the installed
   models are `llama3.2:3b` and `nomic-embed-text:latest`. You do not need to download
   them again. `ollama list` confirms their presence.
3. Open Ubuntu/WSL and run:

```bash
export PATH="$HOME/.local/bin:$PATH"
cd '/mnt/x/semester 5/SCD/A2/rahbar-starter'
docker info
minikube start --driver=docker --cni=calico --memory=6144 --cpus=4 --kubernetes-version=v1.36.1
kubectl get pods,hpa -n rahbar
kubectl rollout status deployment/api -n rahbar --timeout=240s
kubectl rollout status deployment/ui -n rahbar --timeout=180s
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx --timeout=180s
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 18081:80 --address 0.0.0.0
```

Leave the last command running and open **http://localhost:18081** in Windows.
If that port is already forwarded, use the existing forward. If Windows localhost
forwarding is unavailable, run `hostname -I` in WSL and use that address with port 18081.
The dev Ingress accepts these hostnames without editing the Windows hosts file.

The existing Chroma index and Redis data are on persistent volumes. A normal
restart does not require rebuilding images, fetching the corpus, or reindexing.
Do not delete minikube, the namespace or PVCs merely to restart the app.

## If something is not ready

```bash
kubectl get pods -n rahbar
kubectl get events -n rahbar --sort-by=.lastTimestamp
kubectl logs -n rahbar deployment/api --tail=40
```

Readiness needs a nonempty Chroma collection with the matching embedding pin and
reachable Redis. Model generation separately needs Windows Ollama to be reachable.
The dev overlay uses `host.docker.internal` at `192.168.65.254`; update both hostAliases
and its narrow egress policy if Docker Desktop's host address changes.

If an old Ubuntu terminal reports Docker socket permission denied, reopen the
terminal or run `newgrp docker`; the account already belongs to the docker group.
Do not make the Docker socket world-writable. If WSL says Docker is unavailable,
first check that Docker Desktop is running and Ubuntu integration is enabled.

## Tests and tools already installed

The Python environment is `/home/nemesis/.venvs/rahbar`. kubectl, minikube, kind,
Trivy, kubeconform and actionlint are under `~/.local/bin`. Tesseract and Poppler
support OCR. Ubuntu is running inside WSL; no separate Ubuntu installation is needed.

```bash
make test lint VENV="$HOME/.venvs/rahbar"
python3 scripts/check_submission.py
```

`make dev` is an optional stub-only development server; use the Kubernetes URL
above for the real indexed documents and Ollama answers.

## Submission work reserved for the students

Follow [GIT-WORKFLOW.md](GIT-WORKFLOW.md) for manual commits, pushes, PR review,
branch protection, Docker Hub secrets, the failing/passing gate evidence, and the
successful CD run. No implementation commits or remote writes were made after the
instruction to leave these actions to the students. Review the known model errors
in the final verification report and complete the truthful AI-usage disclosure.

Submit by **8 November 2026, 23:59 PKT**.
