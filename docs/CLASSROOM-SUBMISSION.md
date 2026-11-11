# Google Classroom submission handover

Team: M Abdullah (24i-3050) and Umar Siddique.
Assignment 02: RAHBAR - Grounded RAG on Kubernetes.

**Not ready to submit as complete until the CD and image links below are verified.**
Submit one entry per team. Section 8 of the manual requests these four items:

1. Repository: https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes
2. Successful `cd.yml` run: pending approved merge and successful publication/deployment.
3. Docker Hub images with the full deployed commit SHA:
   - API: pending publication at https://hub.docker.com/r/abdullah0990/rahbar-api/tags
   - Indexer: pending publication at https://hub.docker.com/r/abdullah0990/rahbar-indexer/tags
   - UI: pending publication at https://hub.docker.com/r/abdullah0990/rahbar-ui/tags
4. Evaluation files, already committed on dev:
   - https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/blob/dev/eval/results.json
   - https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/blob/dev/eval/baseline.json

After merging, use the same file links with `main` instead of `dev`. If Classroom
provides file attachments, you may also attach these two JSON files directly; the
manual specifically requires that they remain committed in the repository.

## Final steps

- Umar opens PR #1, reviews Files changed, then Review changes > Approve > Submit review
  from his own account, after the final changes. Corrections should be genuine.
- All six required checks must pass. Merge the approved PR into main.
- Open Actions > CD and wait for test, all three build-push jobs, and deploy to succeed.
- Copy that exact successful run URL and the full commit SHA into item 2/3 above.
- Confirm all three Docker Hub tag pages show that same SHA publicly.
- Preserve real screenshots of the deliberately failing evaluation/disabled merge
  button and repaired green checks under docs/evidence. API records alone do not
  satisfy the manual's explicit screenshot instruction.
- Run `python scripts/check_submission.py`; inspect warnings, not only its exit code.
- In Classroom open Assignment 02, select Add or create > Link for the repository,
  successful CD and Docker Hub links; include the evaluation links/files. Submit
  one team entry using Turn in only after verifying the attachments.

The handout deadline is 8 November 2026, 23:59 PKT. This handover is being completed
on 11 November; the team must confirm acceptance with the instructor.
