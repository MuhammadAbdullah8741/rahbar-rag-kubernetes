import json
from pathlib import Path
rows=[]
for file in Path('traces').glob('*.jsonl'):
    rows.extend(json.loads(line) for line in file.read_text().splitlines())
def trace(label):
    response=json.loads(Path('eval/results',label+'.log').read_text())
    return next(r for r in rows if r['trace_id']==response['request_id'])
before=trace('a3-release-query'); bad=trace('a3-bad-release-query'); after=trace('a3-undo-query')
version=lambda r:r['retrieval'][0]['collection_metadata'].get('embedding_version',r['embedding_version'])
proof={'before_trace':before['trace_id'],'bad_trace':bad['trace_id'],'after_trace':after['trace_id'],
       'before_collection':before['collection'],'bad_collection':bad['collection'],'after_collection':after['collection'],
       'before_embedding_version':version(before),'after_embedding_version':version(after),
       'after_answer':after['response']['answer'],'after_answered':after['response']['answered_from_context']}
assert proof['before_collection']==proof['after_collection']!=proof['bad_collection']
assert proof['before_embedding_version']==proof['after_embedding_version']
assert proof['after_answered'] and 'D17' in proof['after_answer']
Path('eval/results/rollback-proof.json').write_text(json.dumps(proof,indent=2)); print(json.dumps(proof,indent=2))
Path('eval/results/full-trace-sample.json').write_text(json.dumps(bad,indent=2))
