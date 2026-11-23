"""Gate measured candidate, roll out, demonstrate rollback, and save fresh traces."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'eval'))
from gate import gate
from a3_cluster import run, apply
from a3_experiments import wait

def gate_job(name):
    job=yaml.safe_load(Path('k8s/eval-job.yaml').read_text()); job['metadata']['name']=name
    c=job['spec']['template']['spec']['containers'][0]
    c['command']=['python','eval/gate.py','--baseline','/results/baseline-ab.json','--candidate','/results/candidate.json','--thresholds','/gate/gate.json','--out','/results/'+name+'.json']
    Path('k8s',name+'.yaml').write_text(yaml.safe_dump(job)); apply(job); return wait(name)

def fresh_query(label):
    code="import httpx,json; r=httpx.post('http://api:8000/api/ask',json={'question':'Which ticket does the demo desk use?','follow_up':True},timeout=650); r.raise_for_status(); print(json.dumps(r.json(),indent=2))"
    # Helper has indexer networking; evaluation-labelled temporary Job provides
    # the same explicitly allowed HTTP path as the measured suite.
    job=yaml.safe_load(Path('k8s/eval-baseline-job.yaml').read_text()); job['metadata']['name']=label
    c=job['spec']['template']['spec']['containers'][0]; c['image']='rahbar-eval:a3-tools'; c['command']=['python','-c',code]
    apply(job); assert wait(label)

if __name__=='__main__':
    load=lambda name:json.loads(Path('eval/results/cluster',name+'.json').read_text())
    thresholds=json.loads(Path('config/gate.json').read_text())
    assert gate(load('baseline-ab'),load('bad-candidate'),thresholds),'Bad candidate must be blocked'
    assert not gate(load('baseline-ab'),load('candidate'),thresholds),'Do not release failing candidate'
    decision={'bad_candidate':'blocked before rollout','candidate':'approved','top_k':3,'collection':'rahbar-a3-candidate'}
    Path('eval/results/release-decision.json').write_text(json.dumps(decision,indent=2)); print(json.dumps(decision),flush=True)
    original=yaml.safe_load(Path('k8s/gate-configmap.yaml').read_text())
    strict=copy.deepcopy(original); limits=json.loads(strict['data']['gate.json']); limits['end_to_end.faithfulness']['min']=1.0
    strict['data']['gate.json']=json.dumps(limits); apply(strict)
    assert not gate_job('gate-strict'),'Strict threshold should reject same measured candidate'
    apply(original); assert gate_job('gate-restored')
    candidate=json.loads(run('kubectl','get','deployment','api-candidate','-n','rahbar','-o','json',capture_output=True).stdout)
    c=candidate['spec']['template']['spec']['containers'][0]
    env={e['name']:e['value'] for e in c['env']}
    assert env['TOP_K']=='3' and env['CHROMA_COLLECTION']=='rahbar-a3-candidate'
    patch={'spec':{'template':{'spec':{'containers':[{'name':'api','image':c['image'],'env':c['env']}]}}}}
    run('kubectl','patch','deployment','api','-n','rahbar','--type=strategic','-p',json.dumps(patch))
    run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
    fresh_query('a3-release-query')
    run('kubectl','set','env','deployment/api','-n','rahbar','CHROMA_COLLECTION=rahbar','TOP_K=0')
    run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
    fresh_query('a3-bad-release-query')
    run('kubectl','rollout','undo','deployment/api','-n','rahbar')
    run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
    fresh_query('a3-undo-query')
    print('CONTROLLED RELEASE AND UNDO COMPLETE',flush=True)
