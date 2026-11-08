# AI usage

This log records assistance received so far. Extend it as implementation proceeds. The team must review and understand the work before submission.

| Tool | What it wrote or shaped | What we changed afterwards, and why |
| --- | --- | --- |
| Codex, 6 November 2026 | Reviewed the assignment and starter; diagnosed Docker socket access in WSL; installed development/OCR tools and minikube; installed Python dependencies; ran starter tests, Ruff and mypy; initialized the starter repository with the supplied author identity; wrote the local setup guide and added configurable DEV_HOST for the development server. | No student revisions recorded yet. Team review and later changes must be added as they occur. |
| Codex, Kubernetes milestone | Drafted the three Dockerfiles, Kustomize manifests, readiness/model-pin checks and tests, architecture/Job decision record, and deployment instructions. | Student review pending. The team requested that subsequent commits and all GitHub changes be performed manually by the students. |

| Codex, implementation and evaluation, 7-8 November 2026 | Implemented extraction/OCR, cleaning/chunking, real embeddings, atomic Chroma publication, hybrid retrieval, Ollama/fixture providers, citation validation, retry/fallback, Redis cache/conversations, metrics, tests, container manifests, workflow drafts, corpus/golden evaluation, fault/cache experiments and documentation. Diagnosed PDF column/hidden-text issues, numeric citation aliases and grade-code cache collisions. | These are AI-assisted changes, not claimed independent student authorship. Student review, understanding, corrections and manual Git commits/GitHub actions remain required. No student revisions or external workflow successes are invented here. |

The students must append their actual review and changes. No tools committed or pushed
implementation changes after the instruction to leave GitHub/Git commits manual.
Public source text was downloaded for retrieval; the model was instructed to treat
retrieved instructions as untrusted data. Test fixture generation does not substitute
for the recorded real Ollama evaluation.
