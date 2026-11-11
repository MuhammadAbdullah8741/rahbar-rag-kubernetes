# AI usage

This log records assistance received so far. Extend it as implementation proceeds. The team must review and understand the work before submission.

| Tool | What it wrote or shaped | What we changed afterwards, and why |
| --- | --- | --- |
| Codex, 6 November 2026 | Reviewed the assignment and starter; diagnosed Docker socket access in WSL; installed development/OCR tools and minikube; installed Python dependencies; ran starter tests, Ruff and mypy; initialized the starter repository with the supplied author identity; wrote the local setup guide and added configurable DEV_HOST for the development server. | No student revisions recorded yet. Team review and later changes must be added as they occur. |
| Codex, Kubernetes milestone | Drafted the three Dockerfiles, Kustomize manifests, readiness/model-pin checks and tests, architecture/Job decision record, and deployment instructions. | Student review pending. The team requested that subsequent commits and all GitHub changes be performed manually by the students. |

| Codex, implementation and evaluation, 7-8 November 2026 | Implemented extraction/OCR, cleaning/chunking, real embeddings, atomic Chroma publication, hybrid retrieval, Ollama/fixture providers, citation validation, retry/fallback, Redis cache/conversations, metrics, tests, container manifests, workflow drafts, corpus/golden evaluation, fault/cache experiments and documentation. Diagnosed PDF column/hidden-text issues, numeric citation aliases and grade-code cache collisions. | These are AI-assisted changes, not claimed independent student authorship. Student review, understanding, corrections and manual Git commits/GitHub actions remain required. No student revisions or external workflow successes are invented here. |

The students must append their actual review and changes. After the student subsequently authorized GitHub work, Codex configured main
protection, pushed dev, opened PR #1, requested Umar review, stored Docker Hub
Actions secrets, and committed the nginx admission-readiness CI repair. Umar review
and approval are not generated or impersonated. The initial manual-only restriction
applied until that later authorization.
Public source text was downloaded for retrieval; the model was instructed to treat
retrieved instructions as untrusted data. Test fixture generation does not substitute
for the recorded real Ollama evaluation.

On 11 November 2026, Codex resumed CI repair and prepared the Classroom handover.
Student understanding and any subsequent student revisions must be recorded by the
team; this log does not claim that an unobserved review has occurred.

Codex also ran a clearly labelled controlled fixture-label regression on GitHub,
recorded the measured 20-percentage-point recall drop, and restored the original
label. The real corpus baseline was not changed. GitHub check records and downloaded
artifacts are genuine; screenshots are still a separate outstanding requirement.
