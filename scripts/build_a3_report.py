"""Build the eight-page report exclusively from saved run evidence, plus screenshots."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak, NextPageTemplate, Image

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'eval/results'; C=R/'final'
load=lambda path:json.loads(path.read_text())
b=load(C/'baseline-ab.json'); repeat=load(C/'baseline-repeat.json'); cand=load(C/'candidate.json'); a=load(C/'batch-a.json')
before=load(C/'coverage-before.json'); after=load(C/'coverage-after.json'); resources=load(R/'resource-summary.json'); team=load(ROOT/'config/team.json')
output=ROOT.parent/'Classroom-submission'/'Assignment_03_Report.pdf'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyA3',fontName='Helvetica',fontSize=9.5,leading=13,spaceAfter=7))
styles.add(ParagraphStyle(name='SmallA3',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=5))
styles.add(ParagraphStyle(name='CellA3',fontName='Helvetica',fontSize=8,leading=10))
styles['Title'].fontSize=23; styles['Title'].leading=28
styles['Heading1'].fontSize=16; styles['Heading1'].leading=20
styles['Heading2'].fontSize=11; styles['Heading2'].leading=14
story=[]
def p(text,style='BodyA3'): story.append(Paragraph(escape(str(text)),styles[style]))
def h(text): p(text,'Heading1')
def sub(text): p(text,'Heading2')
def table(rows,widths=None):
    header=ParagraphStyle('header',parent=styles['CellA3'],textColor=colors.white)
    cells=[[Paragraph(escape(str(v)),header if i==0 else styles['CellA3']) for v in row] for i,row in enumerate(rows)]
    t=Table(cells,colWidths=widths or [499/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#153b50')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d9d9d9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f5f7')])]))
    # Paragraph foreground must be explicit because Table TEXTCOLOR does not style Paragraphs.
    story.append(t); story.append(Spacer(1,8))
def page(): story.append(PageBreak())
def num(v): return '-' if v is None else f'{v:.4f}' if isinstance(v,(float,int)) else str(v)

p('RAHBAR Assignment 3 RAGOps','Title')
p('Software Construction and Development CS4032 | Fall 2026 | Finalized 24 November 2026','SmallA3')
table([['Member','Roll number'],*[ [m['name'],m['roll_number'] or 'Pending group confirmation'] for m in team['members']]],[280,219])
p(f"Final evaluation uses 33 questions with 8 human-authored and 8 human-reviewed synthetic entries. Top-k 5 baseline recall@5 is {b['component']['recall_at_5']:.4f}; top-k 3 candidate recall@5 is {cand['component']['recall_at_5']:.4f}. The unchanged release gate decision is {load(C/'candidate-gate.json')['decision'].upper()}. These are local measured results, not general accuracy claims.")
sub('Lifecycle mapping to Figure 3')
table([['Stage','Implementation and file','Remaining limitation'],
['Ingest','Manifest-backed PDF/HTML loading; corpus/fetch.py, pipeline/extract.py','Source verification does not establish factual truth.'],
['Verify','Four-check run report; pipeline/run.py, quality.py, report.py','Semantic contradictions are not detected.'],
['Update data lake','Verified copies, quarantine and archive on PVC; retention.py','No automated retention expiry.'],
['Update retrieval','Stable chunk IDs, cached embeddings, atomic snapshot; store.py','Unchanged vectors are republished physically.'],
['Offline testing','Three levels, noise and repeated runs; eval/suite.py','Lexical faithfulness proxy is not full entailment.'],
['Live testing','Separate candidate and gated rollout; a3_release_demo.py','Local CPU measurements, no traffic-scale experiment.'],
['Check coverage','Nearest golden embedding and exit gate; eval/coverage.py','Designed log; no held-out production validation.']],[85,224,190])
p('Evidence is stored under eval/results/ and traces/. Kubernetes objects and reproduction commands are under k8s/. Repository: github.com/MuhammadAbdullah8741/rahbar-rag-kubernetes, branch assignment-3-ragops; PR 2. The report body is eight pages; the screenshot appendix follows.','SmallA3')
page()

h('A Data verification and incremental updates')
files=sorted((R/'verification').glob('a3-final-verify*.json'))
verification=load(files[-1]); records=verification['documents']
rows=[['Document','Quality','Complete','Recent','Unique','Decision']]
for rec in records:
    rows.append([rec['document_id'],*[ 'P' if rec['checks'][k]['pass'] else 'F' for k in ('quality','completeness','recency','uniqueness')],rec['decision']])
table(rows,[249,45,48,43,43,71])
p('P = pass. F includes checks explicitly not evaluated after an earlier rejection; those are not separate detected defects. Exact duplicate copies (2) and one near-duplicate were quarantined by uniqueness. The corrupt PDF failed extraction; the missing-title fixture failed metadata completeness. Older versions were archived. The injected instruction was retained as untrusted content and handled by the query guardrail.','SmallA3')
table([['Experiment','Measured evidence'],['Unchanged corpus','351 before and after; identical IDs; verification/indexing both embedded 0 chunks and made 0 model requests.'],['Changed LAB document','One LAB-5 chunk replaces LAB-4; the other 350 chunk IDs are unchanged.'],['Deletion','b-booking.html: count by document ID 1 before, 0 after; unrelated IDs unchanged.'],['Archive and rollback','Archived grading payload checksum OK. Earlier rollback restored 7 original grading chunks and removed all revised grading chunks.']],[125,374])
p('Document identity is the manifest filename, also stored as document_id. The cache key includes content and model digest; extraction caching also fingerprints the extractor implementation. New snapshots preserve logical chunk identity but copy all stored vectors. Evidence: a3-final-verify.log, unchanged-proof.json, deletion-proof.json, unchanged-chunk-ids.txt, archive-readback-grading.txt and rollback-orphan-check.txt.','SmallA3')
page()

h('B Offline testing at three levels')
p('The final golden set has 33 questions: 28 answerable, 5 unanswerable, and 17 hard cases. Abdullah supplied H1-H4 and Umar H5-H8. Abdullah reviewed q16-q19; Umar reviewed q20-q23, including the applied q22 correction. The authorship audit passes all minima. Each answerable entry has source/page/section evidence.')
rows=[['Level and metric','Baseline','Repeat','Candidate k3']]
for level,keys in [('module',['paraphrase_mean','unrelated_mean','gap','seconds_per_chunk','max_repeat_difference']),('component',['recall_at_3','recall_at_5','mrr','ndcg_at_5']),('end_to_end',['faithfulness','citation_validity','citation_ground_truth','answerable_success','abstention_correctness','latency_p50','latency_p95'])]:
    for key in keys: rows.append([level+' / '+key,num(b[level][key]),num(repeat[level][key]),num(cand[level][key])])
table(rows,[244,85,85,85])
p(f"Module testing uses 15 paraphrase pairs and 15 unrelated pairs. Largest repeated-vector difference: {b['module']['max_repeat_difference']}. Typo noise changes recall@3 by {b['noise_delta']['recall_at_3']:.4f}, recall@5 by {b['noise_delta']['recall_at_5']:.4f}, MRR by {b['noise_delta']['mrr']:.4f}, and nDCG@5 by {b['noise_delta']['ndcg_at_5']:.4f}. HTTP errors: {b['end_to_end']['errors']}; cache-hit rate: {b['end_to_end']['cache_hit_rate']}.",'SmallA3')
p('Faithfulness is a conservative fact proxy, conditional on answering. Fixed regex rubrics for H1-H8/q22 require all requested answer facts and supporting facts in cited context. Arithmetic totals are checked in the answer, operands in evidence; other entries use atomic matches. No LLM judge is used. The proxy can miss extra unsupported claims or penalize paraphrases. Scorer and golden hashes are saved.','SmallA3')
p(f"Python and Ollama seeds are 42; temperature is 0.2. Repeat changes answerable success by {repeat['end_to_end']['answerable_success']-b['end_to_end']['answerable_success']:+.4f} and p95 by {repeat['end_to_end']['latency_p95']-b['end_to_end']['latency_p95']:+.3f} seconds. Seed control does not guarantee deterministic generation. Experiments run sequentially; backend variation remains possible.",'SmallA3')
page()

h('C Change experiment and release decision')
p('The controlled experiment changes only retrieval top-k from 5 to 3. Both collections contain identical 351 chunks, vectors and metadata; model, prompt, scorer, relevance floor, hybrid ranking and temperature are fixed. Hypothesis: fewer context distractors may improve selection. The fixed thresholds are retained regardless of the final outcome.')
gate_result=load(C/'candidate-gate.json')
gate_rows=[['Gate','Threshold','Candidate','Outcome']]
thresholds=load(ROOT/'config/gate.json')
for metric, limits in thresholds.items():
    level,key=metric.split('.')
    failed=any(f.startswith(metric+':') for f in gate_result['failures'])
    gate_rows.append([key,str(limits),num(cand[level][key]),'FAIL' if failed else 'PASS'])
table(gate_rows,[145,160,105,89])
p('Final decision: '+gate_result['decision'].upper()+'. The top-k 0 negative control is rejected. The strict ConfigMap and restored ConfigMap are evaluated against identical saved metrics without rebuilding images. Earlier release/rollback evidence is retained and labelled historical; final gate evidence is under eval/results/final/. A failed candidate is never promoted by the release script.')
sub('Five quality attributes from Table 2')
table([['Quality','Measure and threshold','Evidence'],['Adaptability','Coverage >= 85%; same query log',f"{before['coverage']:.1%} to {after['coverage']:.1%}, final/coverage-*.json"],['Monitorability','p95 <= 180 s; abstention = 100% on negatives','candidate.json; trace-summary.json'],['Observability','Trace for every measured query; flagged injection count','Per-request JSONL on stdout and PVC'],['Traceability','Exact prompts, contexts, versions and trace-ID lookup','root-cause-trace.json; trace_tool.py'],['Reliability','No gate errors; zero unavailable during rollout; undo verified','gate-restored.log; release-demo.log; rollback-proof.json']],[93,210,196])
page()

h('D Tracing and root cause analysis')
p('Traces record request ID/time, original and rewritten queries, collection/embedding digest, ranked chunk IDs, document versions, similarity scores and filters. Exact generation messages, context, JSON schema, retry correction and model parameters are preserved. Responses, citations, guardrails, cache status and stage timings share a prompt-record SHA-256.')
p('Trace lookup reconstructs the saved exact prompt/context, including retries; window summaries report top-1 similarity, abstention, cache and flagged injections. The table summarizes the final 33-query baseline. The five-line GR-17 diagnosis retains the initial baseline failure as a historical reproducible example. Both trace sets are saved under traces/.')
summary=load(C/'trace-summary.json')
table([['Baseline trace measure','Value'],['Queries',summary['queries']],['Top-1 similarity mean',num(summary['top1_similarity']['mean'])],['Top-1 similarity p50 / p95',num(summary['top1_similarity']['p50'])+' / '+num(summary['top1_similarity']['p95'])],['Abstention rate',num(summary['abstention_rate'])],['Cache-hit rate',num(summary['cache_hit_rate'])],['Flagged injection queries',summary['flagged_injection_queries']]], [270,229])
sub('Five-line diagnosis using the GR-17 trace only')
for line in (R/'root-cause.txt').read_text().splitlines(): p(line)
sub('Injected document guardrail')
p('The Batch B notice contains the D17 fact and an instruction to reply BLUE-PENCIL. The baseline answer used D17. The corresponding trace logs treat_as_untrusted_evidence, identifying the chunk, and preserves the system instruction forbidding obedience to evidence instructions. This validates the tested fixture, not universal prompt-injection resistance.')
p('Evidence: traces/*.jsonl; eval/results/root-cause-trace.json; trace-reconstruction.txt. Exact reconstruction includes retries rather than regenerating a prompt from the current template.','SmallA3')
page()

h('E Query coverage and corpus drift')
p('The live-style log contains 40 synthetic queries: 28 in-domain and 12 from six uncovered topics. Each query is compared with every golden question using the same embedding model. Coverage requires nearest cosine similarity >= 0.85; the coverage gate requires at least 85% of queries covered.')
table([['Configuration','Golden size','Covered','Coverage','Exit'],['Final tests',before['golden_count'],str(sum(x['covered'] for x in before['rows']))+' / 40',f"{before['coverage']:.1%}",int(before['coverage']<before['minimum_coverage'])],['Six added tests',after['golden_count'],str(sum(x['covered'] for x in after['rows']))+' / 40',f"{after['coverage']:.1%}",int(after['coverage']<after['minimum_coverage'])]],[150,85,85,95,84])
p('The added cases cover bus tracking, WiFi support, sports trials, counselling, lost property and printing. They expect abstention because the corpus does not provide the requested specific procedures, prices or schedules. Uncovered topics and their exact query counts are listed in the saved JSON reports. The log and threshold are unchanged between runs.')
p('This is test coverage, not added factual knowledge. The new tests reuse one query from each uncovered topic, so improvement on this designed log is expected. It should not be interpreted as a held-out generalization result. The same 0.85 cutoff is retained from the initial experiment.')
sub('Batch A versus Batch A plus B using the same golden set')
rows=[['Metric','Batch A','A plus B','Difference']]
for level,key in [('module','gap'),('component','recall_at_3'),('component','recall_at_5'),('component','mrr'),('component','ndcg_at_5'),('end_to_end','faithfulness'),('end_to_end','answerable_success'),('end_to_end','abstention_correctness'),('end_to_end','latency_p95')]:
    rows.append([key,num(a[level][key]),num(b[level][key]),num(b[level][key]-a[level][key])])
table(rows,[220,93,93,93])
p('Batch B adds lab, desk and form facts, increasing retrieval coverage; it also supersedes the original grading page, so strict old-source references can fail even when similar policy text remains elsewhere. The embedding gap is unchanged because the module pairs are independent of corpus contents. Latency is confounded by load and generation retries; data drift alone is not established as its cause.','SmallA3')
page()

h('F Kubernetes operation and recovery')
table([['Object','Responsibility'],['API Deployment and Service','Serve live queries; maxUnavailable=0 rolling update.'],['Candidate Deployment and Service','Separate selector and collection; evaluated before release.'],['Chroma StatefulSet and PVC','Persistent vector snapshots and active collection pointers.'],['Ingestion Job and CronJob','Verified ingestion and only application writer; Forbid schedule overlap, atomic writer lock.'],['Evaluation Job','Three-level suite on the results PVC, then nonzero exit on gate failure.'],['ConfigMap a3-gate','Mounted gate thresholds; strict floor 1.01 deliberately rejects; restored thresholds recover the original decision.'],['Retention and results PVCs','Data lake, quarantine, archives, caches, reports and query traces survive restarts.']],[172,327])
sub('Measured resources and configured budgets')
rows=[['Role','Observed peak CPU / RAM','Request CPU / RAM','Limit CPU / RAM']]
for role,request,limit in [('api','100m / 128Mi','500m / 384Mi'),('chroma','200m / 256Mi','1000m / 1Gi'),('indexer','500m / 384Mi','1000m / 1Gi'),('eval','100m / 128Mi','1000m / 768Mi')]:
    v=resources[role]; rows.append([role,f"{v['peak_observed_cpu_m']:.0f}m / {v['peak_observed_memory_Mi']:.0f}Mi",request,limit])
table(rows,[65,166,134,134])
p('The uncached indexer cgroup peak was 369,328,128 bytes (352.2 MiB), above the initial 128Mi request. Its final request was raised to 384Mi with a 1Gi limit; CPU request was raised to 500m after samples reached 985m. Other requests cover observed working memory with headroom. kubectl top is sampled, not an exact lifetime maximum. Host Ollama consumption is outside these pod budgets.','SmallA3')
proof=load(C/'rollback-proof.json') if (C/'rollback-proof.json').exists() else load(R/'rollback-proof.json')
p(('Final approved rollout: ' if (C/'rollback-proof.json').exists() else 'Historical 25-question approved rollout (final candidate was blocked): ')+'rollout and undo were checked with kubectl rollout status. The post-undo fresh query returned D17 and restored collection '+str(proof.get('after_collection','see rollback-proof.json'))+'. The embedding digest matched the pre-fault trace. The intentionally bad release used a different collection with top-k 0.')
p('JSON traces are available in kubectl logs and on the results PVC. The metrics endpoint was read through port-forward. k8s/README.md documents fresh-cluster setup and exact commands. The recorded full experiments used the existing local minikube cluster; a second fresh-cluster replay was not measured. NetworkPolicy permits the API to reach Chroma, so writer exclusivity is an application contract, not read-only database authorization.','SmallA3')
page()

h('G Reflections and contributions')
for title,text in [
('a Which check caught most problems','Uniqueness caught three planted duplicates: two exact and one near-duplicate. Quality/completeness caught the corrupt file and missing title. Verification did not identify the injected instruction as a data defect; a query-time guardrail flagged it. Semantic contradiction or malicious-but-well-formed content needs additional semantic checks and review.'),
('b Module versus end-to-end result',f"The embedding gap is {b['module']['gap']:.4f}, while final baseline answerable success is {b['end_to_end']['answerable_success']:.4f}. In the recorded historical GR-17 failure, evidence was retrieved first but generation cited unsupported evidence and validation rejected it. Good vectors do not guarantee a correct answer."),
('c Archive or delete','Superseded payloads are archived with checksums and excluded from ordinary retrieval using metadata. Ordinary removals disappear from the active snapshot. Deleting every historical payload would break reproducible traces and document rollback; old snapshots therefore remain until an explicit retention policy removes them.'),
('d Least trusted metric','The atomic-fact faithfulness proxy is least trusted as a semantic measure. A matching number can coexist with an unsupported extra claim, and a correct paraphrase can be missed. Citation membership is also insufficient: it does not prove the cited passage supports the answer. Both are reported with expected-citation and answerable-success scores.'),
('e Hardest paper idea','Synchronizing changing data with changing tests was hardest: Batch B simultaneously adds facts and invalidates older source references. This implementation uses a fixed set for controlled drift comparison and a separate expanded set for coverage. It implements snapshot publication and explicit gates rather than a fully autonomous feedback loop.'),
('f Kubernetes responsibilities','Jobs execute ingestion and evaluation, the CronJob schedules verified ingestion, PVCs preserve evidence/data, ConfigMaps supply thresholds, Deployments control live/candidate replicas and rollout, Services isolate endpoints, and the StatefulSet persists Chroma. A Job plus writer lock implements the sole-writer convention.')]:
    sub(title); p(text,'SmallA3')
table([['Contributor','Recorded contribution'],*[ [m['name'],m.get('contribution') or 'Individual contribution awaiting group confirmation; no unverified attribution made.'] for m in team['members']],['Codex assistance','Evaluation, tracing, gate/coverage tooling, local Kubernetes experiments and report preparation.']],[125,374])
p('AI statement: Codex assisted with implementation, synthetic questions, evaluation execution and report preparation. The group supplied the named human questions/reviews and confirmed member contributions. All reported measurements come from saved pipeline runs; AI assistance is documented in docs/AI-USAGE.md.','SmallA3')
p('Reference: Xu, Weytjens, Zhang, Lu, Weber and Zhu, RAGOps: Operating and Managing Retrieval-Augmented Generation Pipelines, arXiv:2506.03401, https://arxiv.org/html/2506.03401v1 (consulted 23 November 2026). The assignment cites a 2026 preprint; the accessible arXiv version is dated 2025.','SmallA3')

screens=sorted((ROOT/'docs/a3-screenshots').glob('*.png'))
if screens:
    story.append(NextPageTemplate('appendix')); page()
    for i,file in enumerate(screens):
        p('Screenshot appendix '+file.stem.replace('_',' '),'Heading1')
        p(('Final 33-question experiment. ' if file.stem.startswith('Z') else 'Historical local experiment before the golden set expanded to 33 questions. ')+ 'Uncropped terminal capture; commands and saved/live output are shown. Full machine-readable evidence is included.','SmallA3')
        im=Image(str(file)); im._restrictSize(745,465); story.append(im)
        if i<len(screens)-1: page()

def footer(canvas,doc):
    canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#52626c'))
    canvas.drawString(42,24,'RAHBAR | Assignment 3 | Local run evidence')
    canvas.drawRightString(canvas._pagesize[0]-42,24,str(doc.page)); canvas.restoreState()
doc=BaseDocTemplate(str(output),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=42,bottomMargin=42,
                    title='RAHBAR Assignment 3 RAGOps',author='M Abdullah and Umar Siddique')
doc.addPageTemplates([PageTemplate(id='body',frames=[Frame(48,42,A4[0]-96,A4[1]-84,id='body')],onPage=footer,pagesize=A4),
                     PageTemplate(id='appendix',frames=[Frame(42,42,landscape(A4)[0]-84,landscape(A4)[1]-84,id='appendix')],onPage=footer,pagesize=landscape(A4))])
doc.build(story); print(output)
