"""Reconstruct exact prompts or aggregate traces over an inclusive UTC time window."""
import argparse
import datetime as dt
import json
from pathlib import Path
from suite import mean, percentile

def main():
    p=argparse.ArgumentParser(); p.add_argument('--directory',default='traces'); p.add_argument('--id'); p.add_argument('--since'); p.add_argument('--until'); p.add_argument('--out')
    a=p.parse_args(); rows=[]
    for file in Path(a.directory).glob('*.jsonl'):
        for line in file.read_text().splitlines():
            r=json.loads(line); r=r.get('trace',r)
            if 'trace_id' not in r: continue
            stamp=dt.datetime.fromisoformat(r['timestamp'])
            if a.since and stamp<dt.datetime.fromisoformat(a.since): continue
            if a.until and stamp>dt.datetime.fromisoformat(a.until): continue
            rows.append(r)
    rows=list({r['trace_id']:r for r in rows}.values())
    if a.id:
        row=next((r for r in rows if r['trace_id']==a.id),None)
        if row is None: raise SystemExit('Trace not found')
        if row.get('cache_origin_trace_id'):
            origin=next((r for r in rows if r['trace_id']==row['cache_origin_trace_id']),None)
            row={**row,'cache_origin':origin}
        result=row
    else:
        scores=[r['response']['retrieved'][0]['score'] for r in rows if r['response'].get('retrieved')]
        result={'queries':len(rows),'top1_similarity':{'min':min(scores) if scores else None,'mean':mean(scores),'p50':percentile(scores,.5),'p95':percentile(scores,.95),'max':max(scores) if scores else None},
                'abstention_rate':mean([not r['response']['answered_from_context'] for r in rows]),
                'cache_hit_rate':mean([r['cache_status']=='hit' for r in rows]),
                'stage_p95':{k:percentile([r['latency'][k] for r in rows if k in r['latency']],.95) for k in sorted({k for r in rows for k in r['latency']})},
                'flagged_injection_queries':sum(bool(r.get('guardrail_actions')) for r in rows)}
    output=json.dumps(result,indent=2); print(output)
    if a.out: Path(a.out).write_text(output)

if __name__=='__main__': main()
