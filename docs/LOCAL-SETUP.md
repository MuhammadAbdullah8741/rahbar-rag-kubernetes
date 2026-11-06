# RAHBAR setup and first steps

Use Ubuntu inside WSL 2 for the commands below. Keep Docker Desktop running on Windows.

## Docker access

The `nemesis` account already belongs to the `docker` group. A fresh WSL session successfully ran `docker run --rm hello-world` on 6 November 2026. An older terminal can retain its previous group membership.

In that terminal, run:

```bash
newgrp docker
docker run --rm hello-world
```

Alternatively, close the Ubuntu terminal and open it again. Docker Desktop's WSL integration must remain enabled for Ubuntu. Do not change the socket permissions to make it world-writable.

## Development environment

Python 3.12, Git, Make and kubectl are available inside Ubuntu. Python virtual-environment support, Tesseract OCR and Poppler were installed during setup. Minikube v1.39.0 is installed under `~/.local/bin`; its download passed SHA-256 verification.

For an existing terminal, add that directory to the current session:

```bash
export PATH="$HOME/.local/bin:$PATH"
minikube version
kubectl version --client
```

Source files remain in the existing assignment folder. The virtual environment lives on the Linux filesystem. Pass its path to Make because the starter's default virtual-environment path does not handle spaces in the Windows project path safely.

```bash
cd '/mnt/x/semester 5/SCD/A2/rahbar-starter'
make install VENV="$HOME/.venvs/rahbar"
make test VENV="$HOME/.venvs/rahbar"
make lint VENV="$HOME/.venvs/rahbar"
make dev VENV="$HOME/.venvs/rahbar" DEV_HOST=0.0.0.0
```

Open http://localhost:8000 in the Windows browser. If Windows localhost forwarding does not work, run `hostname -I` in Ubuntu and open `http://<WSL-IP>:8000` instead. On 6 November the verified address was http://172.19.205.98:8000; that address can change after a WSL restart. `DEV_HOST=0.0.0.0` allows Windows to connect to the WSL address. The starter returns fixed example passages and answers. This confirms the API/UI connection; it does not yet answer from real documents. Press Ctrl+C in the terminal to stop the development server.

## Kubernetes cluster

Once minikube is installed, run these commands as your normal Ubuntu user:

```bash
minikube start --driver=docker --cni=calico --memory=6144 --cpus=4 --kubernetes-version=v1.36.1
minikube addons enable metrics-server
minikube addons enable ingress
kubectl get nodes
kubectl get pods -A
```

This downloads the Kubernetes images. Calico is required to enforce NetworkPolicy; metrics-server supplies the measurements used by autoscaling. Application deployment comes after writing the Dockerfiles and Kubernetes manifests. Docker Desktop's separate built-in Kubernetes cluster is unnecessary for this workflow.

## Model downloads

Install Ollama for Windows from https://ollama.com/download/windows . Then open a new PowerShell terminal:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama list
```

The first model generates answers. The second embeds passages and questions. These are larger downloads and are not needed for the initial stub-based deployment. Before real RAG integration, configure Ollama to accept connections from WSL/minikube and verify the reachable host address. Keep this service restricted to the development machine/network.

## Repository and implementation order

1. The local repository now has the unchanged starter as its first commit and a `dev` branch for subsequent work. This checkout uses M Abdullah's supplied Git identity. Umar should configure his own identity in his own checkout. Create a GitHub repository, protect `main`, and submit changes through pull requests.
2. Write Dockerfiles for API, UI and indexer, then deploy the stubs on minikube with Chroma, Redis, storage, probes, Ingress and network policies.
3. Verify a real corpus with six documents and forty pages, including the required version pair and scan. Write the golden evaluation questions before tuning.
4. Implement extraction/OCR, cleaning, chunking, embeddings, retrieval, grounded generation, validation, abstention and caching.
5. Measure three chunk configurations; build the evaluation gate, CI/CD, recovery demonstrations and submission evidence.

GitHub and Docker Hub accounts are needed for CI/CD. Store access tokens in GitHub Secrets; do not paste them into source files. Install CI utilities such as Trivy, kubeconform and kind in the workflows when those workflows are implemented.

Submission deadline from the brief: Sunday 8 November 2026, 23:59 Pakistan time.
