from a3_release_demo import fresh_query
from a3_cluster import collect
import json
from pathlib import Path
fresh_query('a3-final-query')
collect()
response=json.loads(Path('eval/results/a3-final-query.log').read_text())
records=[json.loads(line) for file in Path('traces').glob('*.jsonl') for line in file.read_text().splitlines()]
trace=next(r for r in records if r['trace_id']==response['request_id'])
assert response['answered_from_context'] and 'D17' in response['answer']
assert len(trace['embedding_version'])==64 and trace['latency']['embedding']>0
assert all(p['document_id'] for p in trace['retrieval'][0]['passages'])
Path('eval/results/final-smoke-trace.json').write_text(json.dumps(trace,indent=2))
print('PASS: final deployed source, D17 answer, explicit model digest, embedding timing and document IDs')
