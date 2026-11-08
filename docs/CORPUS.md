# Corpus audit

Seven public FAST-NUCES sources; 161 PDF pages plus two HTML pages. Fetch URLs,
SHA-256 hashes, versions and dates are recorded in `corpus/MANIFEST.md` and
`corpus/sources.yaml`. Downloaded files stay ignored in `corpus/raw/`.

| Source | Pages | Pages requiring OCR | Role |
| --- | ---: | ---: | --- |
| Undergraduate academic rules, August 2023 | 26 | 24 | Genuine older policy; superseded=true |
| Academic rules handbook, June 2026 | 58 | 5 | Current policy and long generative-AI guidance |
| Prospectus academic rules, 2026 | 5 | 0 | Three-column rules and grade table |
| Student handbook, June 2026 | 64 | 4 | Conduct, examinations, AI guidance |
| Fee structure HTML | 1 logical | 0 | Tuition/refund tables and exact amounts |
| Grading HTML | 1 logical | 0 | Letter-code/grade-point table and probation |
| Faculty entrepreneurship/start-ups policy | 8 | 8 | Fully image-only PDF; OCR required |

The old summer policy is 8-9 weeks (PDF page 20); the 2026 policy is 8 weeks
(PDF page 28) with four eligibility categories. Both sources remain indexed; the
retriever excludes superseded documents unless a matching older year is explicit.

The fee table supplies Fall 2026 tuition of Rs 12,000 per credit hour. The grading
table distinguishes B from B- (3.00 versus 2.67), an exact-token cache edge case.
The multi-paragraph generative-AI policy is a long definition/guidance example.
Hostel-room application procedures and pet veterinary reimbursement are deliberately
outside the selected corpus and are represented by must-abstain questions.

Extraction audit found hidden text outside the handbook's visible page bounds and
mixed reading order in the prospectus. We cropped to the visible page viewport and
used three verified column regions for this prospectus. Those document-specific
rules should be re-audited if the publisher replaces the layout. OCR is imperfect:
clause numbers and decorative text may remain noisy, and all quoted rules should
be checked against the original source for consequential use.

Only public source downloads are redistributed by reference. The repository license
does not grant rights to the university documents. No personal student records were
used. Run `make fetch` to reproduce the source download and its manifest.
