# GitHub delivery evidence

Checked 11 November 2026. This records observed state, not a completion claim.

- Repository: https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes
- Implementation PR: https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/pull/1
- Initial failing e2e (nginx admission startup, not evaluation regression):
  https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42499860522
- Admission readiness repair: commit `dd0a3bd`.
- Initial repair run exposed TTL deletion of admission Jobs:
  https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42957078530
- Final repair commit: `9f9937e`. All six PR checks passed:
  https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42957528780
- Matching push run passed:
  https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42957519351
- Machine-readable successful check records: [github-ci-success.json](github-ci-success.json).
- Actual main protection API response: [branch-protection.json](branch-protection.json).
  One approval, administrator enforcement, conversation resolution and strict required
  checks: test, manifests, images (api), images (indexer), images (ui), e2e.
- Required Docker Hub secrets are configured; their values are never included here.
- Umar has been requested as reviewer. No review approval existed at the initial check.

## Controlled gate demonstration

Only fixture f01's expected section was changed to `CONTROLLED-GATE-FAILURE` in
commit `9fd363c`; the baseline and application code were unchanged.
The push run failed at the evaluation gate (not deployment):
https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42957730259

Measured recall@5 was 0.80 versus baseline 1.00; citation validity and abstention
correctness stayed 1.00. `github-gate-failed-results.json` is the downloaded Actions
artifact, and `github-gate-failure.txt` is the actual job log. The matching PR run is:
https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/actions/runs/42957735931

The original fixture label was restored by reverting `9fd363c`.
Final checks: https://github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes/pull/1/checks

The blocked-state API snapshot was taken while the push evaluation had failed
and the matching PR evaluation was still running. It is not a screenshot.

Still to verify: restored-fixture CI,
actual blocked/green screenshots, partner approval, merge, successful CD, and public
Docker Hub SHA tags. Screenshot automation is unavailable (native pipe missing and
no browser surfaces connected), so authenticated screenshots require the student's UI.

No second PR is fabricated as Umar's work. A second partner PR should contain his
actual follow-up improvements if the team still wants the two-PR workflow.
