# Manual GitHub workflow

Only the students perform commits, pushes, PRs, reviews, branch protection and
GitHub settings changes. No new commit or remote write was made during implementation.
Three earlier local setup commits already exist; inspect them with `git log --oneline`.

## Review and commit locally

Run from Ubuntu/WSL. The working branch is dev. Review file groups and use genuine
small commits for reviewed changes; do not backdate commits or change authors to
simulate contributions. Umar should review and commit his own actual changes in
his own clone, configured with his name/email.

```bash
cd '/mnt/x/semester 5/SCD/A2/rahbar-starter'
git status
git diff
# Review, then commit each meaningful group yourself:
git add api indexer ui k8s ARCHITECTURE.md
git diff --cached --stat
git commit -m "feat: implement grounded RAG and Kubernetes deployment"
git add corpus eval scripts .github Makefile .gitignore
git diff --cached --stat
git commit -m "test: add measured evaluation and gated CI CD workflows"
git add README.md LICENSE docs
git diff --cached --stat
git commit -m "docs: document experiments architecture and reproduction"
```

`corpus/raw`, virtual environments, secrets and generated local overlays are ignored.
Check staged contents before every commit. Test files travel with the corresponding
implementation in the first group. Commit messages are suggestions, not commands
Codex has executed.

## Upload and review

```bash
# Add only if origin is absent; inspect git remote -v first.
git remote add origin https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes.git
git push -u origin main
git push -u origin dev
```

The first main push uploads the existing starter commit. Open a PR from dev to main.
Suggested title: **Implement grounded RAHBAR with evaluated Kubernetes deployment**.

Suggested description:

> Implement OCR-aware public-policy indexing, version-filtered retrieval, validated
> Ollama answers, citation/abstention safeguards and a shared semantic cache. Deploy
> three API replicas with persistent Chroma/Redis, a separate atomic indexer Job,
> weekly reindexing, restricted networking and health/model-pin checks. Add a fixed
> 15-question real corpus evaluation and deterministic fixture CI/CD deployment tests.
> See docs/PIPELINE.md and docs/evidence for measured results and known limitations.

Umar must review actual changes and request corrections where needed. Configure
main protection to require a PR, one approving review, and the successful CI jobs
(test, manifests, images for each component, e2e). Select the exact job names shown
by GitHub after the first workflow run. Do not assume protection works until a
failing check visibly blocks a merge.

## Docker Hub and CD

Create three Docker Hub repositories named `rahbar-api`, `rahbar-indexer`, and
`rahbar-ui`. This workflow expects them to be public so the ephemeral deployment
can pull without an imagePullSecret. Create an appropriately scoped Docker Hub
access token. In GitHub Settings > Secrets and variables > Actions, add repository
secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. Do not paste the token into chat,
source code, terminal history, screenshots or committed files.

After the reviewed PR passes and merges to main, CD runs CI first, publishes each
image with the commit SHA, then verifies a fixture deployment through Ingress on
kind. Save the successful Actions run URL and image tags. This is not a persistent
hosted service; the disposable cluster is removed after smoke testing.

## Evidence only you can produce

Save real screenshots under `docs/evidence/` of main branch protection, a blocked
merge caused by a failing evaluation check, and the repaired passing check/review.
For a deliberate gate-failure PR, temporarily replace one **fixture** golden section label with an incorrect
label, verify the resulting recall regression failure, then restore the correct
label before merging. State clearly that this is a controlled gate test.
Never modify the real measured baseline to hide a regression.

Record the successful CD URL in `docs/evidence/github-runs.md`, with PR/review and
commit links. No placeholder screenshot, invented run URL or fabricated partner
contribution is acceptable. These external evidence items remain outstanding until
the students perform them. The assignment deadline is 8 November 2026 at 23:59 PKT.

## Classroom submission

Submit one entry for the team containing all four items from the handout:

1. The repository URL; make it public or give both instructors access.
2. The URL of a successful **CD** run that tested, published and deployed.
3. Docker Hub links for all three images, showing their commit-SHA tags.
4. `eval/results.json` and `eval/baseline.json`, committed in the repository.

Before submission, run `python3 scripts/check_submission.py` and inspect
`docs/FINAL-VERIFICATION.md`. Its local checks do not replace the GitHub/CD evidence.
Complete Umar's actual review/contributions and both students' understanding of
the engineering notes; do not invent authorship or approval evidence.
