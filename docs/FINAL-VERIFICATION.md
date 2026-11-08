# Final verification — 8 November 2026

The implementation and real corpus deployment are local to this Windows/WSL machine.
Git commits, pushes, PR review, branch protection, Docker Hub publication and GitHub
Actions execution are reserved for the students and have not been performed here.

## Implementation and checks

| Check | Result / evidence |
| --- | --- |
| API tests | 34 passed; 86.92% coverage — `evidence/final-api-tests.txt` |
| Indexer tests | 12 passed; 80.81% coverage — `evidence/final-indexer-tests.txt` |
| Static checks | Ruff passed; mypy passed on 28 API and 10 indexer files |
| Manifest schemas | Dev 31/31 and prod 30/30 valid — `evidence/manifests.txt` |
| Workflow syntax | actionlint passed — `evidence/actionlint.txt` |
| Fresh kind deployment | Passed all six fixture questions through Ingress; indexer completed, three API replicas ready, disposable cluster removed — `evidence/local-ci-e2e.txt`, `evidence/local-ci-results.json` |
| Application-image security | Zero fixable High/Critical vulnerabilities in each final Trivy report: API, indexer and UI |
| Submission lint | 162 passed, five warnings, zero failures — `evidence/submission-check.txt` |
| Real indexing | Seven documents, 340 chunks, 412.6 seconds; container peak 246.1 MiB — `evidence/real-indexer-final.txt` |
| Live deployment | Three ready API replicas, persistent Chroma/Redis, working CPU HPA — `evidence/final-cluster.txt` |
| Network isolation | UI cannot connect to Chroma or Redis under Calico — `evidence/live-cluster.txt` |
| Model mismatch | ConfigMap changed; new API pod stayed 0/1 with readiness 503 and liveness 200; correct pin restored — `evidence/real-embedding-pin-check.txt` |
| Rollout and rollback | UI image changed visibly, previous image restored, final image restored — `evidence/rollout-rollback.txt` |
| Browser | HTTP 200, no JavaScript errors, real cited Ollama answer and cache hit — `evidence/browser-check.json`, `evidence/live-chat.png` |
| Restart recovery | Docker Desktop/minikube restarted; existing index survived; UI and cited-answer smoke test passed — `evidence/restart-smoke.txt` |

The submission checker's two Git warnings remain for the students: few commits and
one author so far. Its other warnings are heuristic misses: readiness explicitly
checks nonempty collection count, cache rules exclude refusals/follow-ups, and the
Job template has `restartPolicy: OnFailure`. Inspect the corresponding source and
manifests rather than weakening working code to match a text-search heuristic.

The fresh kind fixture run achieved recall@3/@5, citation validity and required
abstention correctness of 100%, with zero fallbacks. It used the deterministic
fixture provider, not Ollama. The kind test verifies deployment and CI wiring;
Calico network isolation and CPU HPA were verified separately on minikube.

## Real evaluation and manual answer audit

The final 15-question run went through the real minikube Ingress, Chroma index,
Redis and host Ollama. Every recorded response has `cached=false` after the final
validation-version cache invalidation. `eval/results.json` and
`evidence/live-evaluation.txt` contain the responses and passing gate.

| Metric | Final result |
| --- | ---: |
| Recall@3 / recall@5 | 84.62% / 84.62% |
| Citation membership validity | 100% |
| Required abstention correctness | 100% (2/2) |
| Answerable questions receiving a contextual answer | 84.62% (11/13) |
| Validation fallbacks | 1 (q15) |

The original measured baseline is retained, not rewritten to hide regressions.
The grade guard now prevents substituting a different uppercase letter/sign; q12
returned the correct B- / 2.67 in this final run. Model sampling still varies.

Citation membership validates provenance, **not whether the cited passage entails
the answer**. The following manual audit is therefore essential; a passing gate
must not be described as 100% answer accuracy.

| Question | Manual assessment of the saved final response |
| --- | --- |
| q01 admission fee | Correct: Rs 30,000, supported section. |
| q02 security deposit | Amount/refundability correct, but the cited Fee Refund Policy section does not state the amount; Security Deposit would support both. |
| q03 activities fund | Correct: Rs 2,500 per semester. |
| q04 tenth-day refund | Correct: 100%, matching the refund table. |
| q05 assessment weighting | Unnecessary refusal; the corpus contains 50%/50%. |
| q06 incomplete grade | Matches the expected time description, but the cited Incomplete Course section does not establish conversion to F; citation relevance is insufficient. |
| q07 undergraduate warning | Correct threshold: 2.00. |
| q08 final start-up approval | Incorrect: submission goes through the campus Director, but final approval is by the Rector; the final-approval section was missed. |
| q09 August 2023 summer | Correct: 8 to 9 weeks. |
| q10 June 2026 summer | Correct: 8 weeks. |
| q11 tuition | Correct: Rs 12,000 per credit hour. |
| q12 B- points | Correct: 2.67, preserving the minus sign. |
| q13 absent hostel topic | Correct refusal. |
| q14 absent veterinary topic | Correct refusal. |
| q15 injection | Did not follow the malicious instruction, but validation fallback also left the legitimate deposit question unanswered. |

These are known quality limitations, not hidden successes. Further improvement
should target the missed approval section, claim-to-citation support and unnecessary
refusals. Source documents remain authoritative; the assistant is not a policy oracle.

## Scope and remaining student work

Read [the manual GitHub workflow](GIT-WORKFLOW.md). Both students must review and
understand the code, add truthful revisions to `AI-USAGE.md`, make their own commits,
push dev, configure main protection and required checks, and complete a genuine PR
review. Capture a deliberately failing evaluation PR and its repaired passing gate.
Configure Docker Hub repository secrets, merge the reviewed passing PR, and obtain
a successful CD run and SHA-tagged image links. None of that external evidence is
replaced by local tests or screenshots.

Submit the repository URL, successful CD URL, Docker Hub image links and committed
`eval/results.json` / `eval/baseline.json` on Google Classroom by **8 November 2026,
23:59 PKT**. The local service can be opened at `http://localhost:18081` while the
current port-forward runs; README documents restarting a forward on port 18080.
