# ADR 0002: Page and section bounded chunks with hybrid retrieval

Status: accepted for the measured corpus.

The corpus mixes scanned rules, a three-column prospectus, HTML tables, and long
policy paragraphs. Blind character windows lose headings and can join unrelated
columns. Extraction keeps page numbers and table rows; cleaning repairs line
breaks; chunking retains the current heading and never crosses a page boundary.
Size and overlap are measured in whitespace words, not model tokenizer tokens.

We compared 200/25, 400/50 and 600/75 against the 15 questions written in
`eval/golden.yaml` before tuning. All achieved recall@5 0.8462. The settings made
381, 340 and 340 chunks respectively. We selected 400/50: larger windows produced
no additional benefit because page/section boundaries already limited length.
`eval/chunk-experiments.json` contains every retrieved passage and score.

Cosine retrieval is combined with a small lexical ranking using reciprocal-rank
fusion. Numbers, grade codes and clause identifiers benefit from lexical matches.
Returned relevance scores remain genuine cosine similarities, including lexical
candidates. The 0.65 floor suppresses weak evidence; the generator must still
decline when a related passage does not actually answer the question.

The two retrieval misses are retained in the report rather than changing the
golden labels after observing results. OCR errors and ambiguous headings remain
limitations. An alternative is token-aware paragraph splitting plus reranking,
but it adds dependencies and needs another independent validation set.
