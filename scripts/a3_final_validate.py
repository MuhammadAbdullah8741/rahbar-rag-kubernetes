"""Validate final evidence and prepare machine-readable delivery summaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval'))
from gate import gate
from suite import mean, percentile


def load(p):
    return json.loads(p.read_text())


if __name__=='__main__':
    final=ROOT/'eval/results/final'
    golden_hash=hashlib.sha256((ROOT/'eval/golden.jsonl').read_bytes()).hexdigest()
    runs={name:load(final/(name+'.json')) for name in ['baseline-ab','baseline-repeat','candidate','bad-candidate','batch-a']}
    for name,result in runs.items():
        assert result['golden_sha256']==golden_hash,(name,'outdated golden')
        assert len(result['rows'])==33
        assert result['end_to_end']['errors']==0,(name,'request errors')
    assert len({v['scorer_sha256'] for v in runs.values()})==1
    thresholds=load(ROOT/'config/gate.json')
    assert gate(runs['baseline-ab'],runs['bad-candidate'],thresholds)
    for before,after,name in [('baseline-ab','baseline-repeat','repeat-comparison'),('batch-a','baseline-ab','drift-comparison')]:
        subprocess.run([sys.executable,'eval/compare.py',str(final/(before+'.json')),str(final/(after+'.json')),'--out',str(final/(name+'.json'))],cwd=ROOT,check=True)
    raw=[]
    for p in (ROOT/'traces').glob('*.jsonl'):
        for line in p.read_text().splitlines():
            if line.strip(): raw.append(json.loads(line))
    by_id={r['trace_id']:r for r in raw}
    ids=[r['response']['request_id'] for r in runs['baseline-ab']['rows']]
    selected=[by_id[i] for i in ids]
    (final/'baseline-traces.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in selected))
    scores=[r['response']['retrieved'][0]['score'] for r in selected if r['response'].get('retrieved')]
    summary={'queries':len(selected),'top1_similarity':{'mean':mean(scores),'p50':percentile(scores,.5),'p95':percentile(scores,.95)},'abstention_rate':mean([not r['response']['answered_from_context'] for r in selected]),'cache_hit_rate':mean([r['cache_status']=='hit' for r in selected]),'flagged_injection_queries':sum(bool(r.get('guardrail_actions')) for r in selected)}
    (final/'trace-summary.json').write_text(json.dumps(summary,indent=2))
    release=load(final/'release-decision.json')
    if release.get('rollout_undo')=='completed':
        def trace(label):
            response=load(ROOT/'eval/results'/(label+'.log'))
            return by_id[response['request_id']]
        before=trace('final-release-query'); bad=trace('final-bad-release-query'); after=trace('final-undo-query')
        proof={'before_trace':before['trace_id'],'bad_trace':bad['trace_id'],'after_trace':after['trace_id'],
               'before_collection':before['collection'],'bad_collection':bad['collection'],'after_collection':after['collection'],
               'before_embedding_version':before['embedding_version'],'after_embedding_version':after['embedding_version'],
               'after_answer':after['response']['answer'],'after_answered':after['response']['answered_from_context']}
        assert proof['before_collection']==proof['after_collection']!=proof['bad_collection']
        assert proof['before_embedding_version']==proof['after_embedding_version']
        assert proof['after_answered'] and 'D17' in proof['after_answer']
        (final/'rollback-proof.json').write_text(json.dumps(proof,indent=2))
    status={'golden_sha256':golden_hash,'scorer_sha256':runs['candidate']['scorer_sha256'],'questions_per_run':33,'runs':list(runs),'candidate_decision':load(final/'candidate-gate.json')['decision'],'trace_count':len(selected),'coverage_before':load(final/'coverage-before.json')['coverage'],'coverage_after':load(final/'coverage-after.json')['coverage']}
    (final/'delivery-validation.json').write_text(json.dumps(status,indent=2)); print(json.dumps(status,indent=2))
