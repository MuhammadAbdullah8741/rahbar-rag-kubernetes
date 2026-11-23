"""Semantic test coverage with fixed queries and thresholds; exits nonzero below target."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from app.config import get_settings
from app.services.embedding import embed_query
from suite import cosine, read_jsonl

def main():
    p=argparse.ArgumentParser(); p.add_argument('--golden',default='eval/golden.jsonl'); p.add_argument('--queries',default='eval/live-queries.jsonl')
    p.add_argument('--similarity',type=float,default=.85); p.add_argument('--minimum',type=float,default=.85); p.add_argument('--out',required=True)
    a=p.parse_args(); settings=get_settings(); golden=read_jsonl(a.golden); queries=read_jsonl(a.queries)
    vectors=[embed_query(q['question'],settings) for q in golden]; rows=[]
    for q in queries:
        v=embed_query(q['question'],settings); scores=[cosine(v,g) for g in vectors]; i=max(range(len(scores)),key=scores.__getitem__)
        rows.append({**q,'closest_id':golden[i]['id'],'closest_question':golden[i]['question'],'similarity':scores[i],'covered':scores[i]>=a.similarity})
    coverage=sum(r['covered'] for r in rows)/len(rows)
    topics={t:[r['question'] for r in rows if not r['covered'] and r['topic']==t] for t in sorted({r['topic'] for r in rows if not r['covered']})}
    result={'coverage':coverage,'similarity_threshold':a.similarity,'minimum_coverage':a.minimum,
            'embedding_model':settings.embed_model,'golden_count':len(golden),'queries':len(rows),'uncovered_topics':topics,'rows':rows}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    return int(coverage<a.minimum)

if __name__=='__main__': sys.exit(main())
