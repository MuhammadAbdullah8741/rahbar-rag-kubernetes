# Indexing and retrieval pipeline

## Extraction and cleaning

The seven-document corpus has 161 PDF pages. OCR was needed on 24/26 old-rule pages,
5/58 current-rule pages, 4/64 student-handbook pages and all eight start-up policy
pages. Low-text pages are rasterized at 180 dpi and OCRed with Tesseract. PDF text is
cropped to visible bounds; the prospectus uses three verified column regions.
HTML navigation/scripts are removed and headings retained. For example, a fee-table
row becomes `BBA / BS | 12,000` rather than unrelated column fragments. The PDF
grade table retains paired grade/point cells such as `A+ | 4.00 | C+ | 2.33`.

Cleaning applies Unicode normalization, removes NULs, repairs line-break hyphenation,
normalizes horizontal whitespace and removes repeated page-edge boilerplate. It
preserves paragraph breaks, punctuation, numbers and table delimiters. OCR clause
numbers remain imperfect; the original document is the authoritative reference.

## Chunk comparison

The implementation measures **whitespace words**, not tokenizer tokens. Every chunk
keeps source, section, physical page, document version and superseded status. IDs are
stable content/metadata hashes. Paragraphs and sentences are preferred boundaries;
long units use overlapping windows, and pages are never joined.

| Target words | Overlap words | recall@3 | recall@5 | Chunks | Stored/body input ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | 25 | 0.8462 | 0.8462 | 381 | 0.9943 |
| 400 | 50 | 0.8462 | 0.8462 | 340 | 0.9613 |
| 600 | 75 | 0.8462 | 0.8462 | 340 | 0.9613 |

Selected: **400/50**. The ratio counts stored body words divided by cleaned page
words, including headings in the denominator. It can therefore be below one:
headings are stored as metadata and repeated footer lines are removed at chunking.
It is a text storage ratio, not on-disk Chroma/vector bytes or model-token count.
400 and 600 yield the same segmentation because section/page boundaries dominate.
Full results and retrieved passages are in `eval/chunk-experiments.json`.

## Embedding and publication

`nomic-embed-text:latest`, dimension **768**, uses `search_document:` and
`search_query:` prefixes. The shared ConfigMap sets the pin. The indexer embeds in
batches of 16 and stores in batches of 128. A new collection records the model,
dimension and generation. A count check precedes one control-pointer metadata
update; the API checks metadata before retrieval and in readiness. Installed model
digests are saved separately because model tags can change.

Default retrieval excludes superseded documents; an explicitly requested matching
year selects that version. Cosine and lexical candidate ranks are fused. The 0.65
cosine floor applies even to lexical candidates. A score above the floor is only
candidate evidence: the model must still decline if the answer is absent.

## Semantic cache

Twelve declared query pairs include four equivalent intents and eight different
intents. Initial thresholds 0.90, 0.95 and 0.98 all produced one false hit (B/B-).
After exact grade matching, all three had zero false hits. At 0.98 only the exact
repeat hit; three paraphrases missed. We select **0.98** conservatively and accept
that lower reuse rate. See both `eval/cache-before-grade-guard.json` and
`eval/cache-experiments.json`. This small set is not proof of universal correctness.
Follow-ups, abstentions, low confidence and fallbacks are never semantically cached.
An index-generation namespace makes stale answers unreachable after publication.

## Evaluation method

`eval/golden.yaml` was authored before tuning: eight ordinary, two version, two
exact, two must-abstain and one injection question. Recall matches source and
section, plus page when specified; it accepts exact chunk IDs when supplied.
Citation validity requires a cited source/section/page among retrieved references.
The provider schema restricts citations to complete retrieved references. Runtime
validation requires a valid inline citation for each sentence; for a single
sentence it can render the validated structured citations when the label was omitted.
The gate requires at least 95% citation validity, 100% must-abstain correctness,
and no recall@5 regression greater than five percentage points against
the saved baseline. A refusal on an answerable question is also visible through
answerable_answer_rate. The deterministic fixture gate is separate from real-model
quality and has its own baseline. Expected answer snippets support manual audit;
they are not treated as an automatic semantic correctness score.

Fallback count and answerable answer rate are reported separately, rather than added
to the assignment's three required pass/fail thresholds. A passing gate therefore
does not mean every answerable question received an answer. The final verification
report lists any real-model fallbacks explicitly. The final prompt asks for one
sentence and structured citations; the server renders validated references inline.
Contradictory model abstentions are replaced with a fixed low-confidence refusal.
For explicit uppercase grade codes, generation validation also rejects a different
letter/sign in the answer. This catches B- becoming B+ but is not a general semantic
correctness checker. A validation-version key invalidates responses cached before
that guard was introduced.
