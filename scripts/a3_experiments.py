"""Run measured experiments sequentially to avoid competing for the host LLM."""
import copy
import json
from pathlib import Path
import subprocess
import time
import yaml
from a3_cluster import apply, candidate, ingest, run

def wait(name):
    while True:
        r=run('kubectl','get','job',name,'-n','rahbar','-o','json',capture_output=True)
        status=json.loads(r.stdout).get('status',{})
        if status.get('succeeded'):
            logs=run('kubectl','logs','-n','rahbar','job/'+name,capture_output=True).stdout
            Path('eval/results',name+'.log').write_text(logs); return True
        if status.get('failed'):
            logs=run('kubectl','logs','-n','rahbar','job/'+name,capture_output=True).stdout
            Path('eval/results',name+'.log').write_text(logs); print(logs[-3000:]); return False
        time.sleep(15)

def evaluate(name,api,collection,k,out,gate=False):
    job=yaml.safe_load(Path('k8s/eval-baseline-job.yaml').read_text()); job['metadata']['name']=name
    c=job['spec']['template']['spec']['containers'][0]
    c['image']='rahbar-eval:a3-tools'
    command=f'python eval/suite.py --api http://{api}:8000 --label {name} --out /results/{out}.json'
    if gate: command+=f'; python eval/gate.py --baseline /results/baseline-ab.json --candidate /results/{out}.json --thresholds /gate/gate.json --out /results/{out}-gate.json'
    c['command']=['/bin/sh','-ec',command]
    c['env']=[{'name':a,'value':v} for a,v in {'CHROMA_COLLECTION':collection,'TOP_K':str(k),'CACHE_ENABLED':'false'}.items()]
    Path('k8s',name+'.yaml').write_text(yaml.safe_dump(job)); apply(job); return wait(name)

if __name__=='__main__':
    if not wait('eval-baseline'): raise SystemExit('Baseline failed')
    evaluate('eval-repeat','api','rahbar-a3-ab',5,'baseline-repeat')
    if not wait('a3-ingest-candidate'): raise SystemExit('Candidate ingestion failed')
    run('kubectl','rollout','status','-n','rahbar','deployment/api-candidate','--timeout=180s')
    evaluate('eval-topk3','api-candidate','rahbar-a3-candidate',3,'candidate',True)
    candidate('rahbar-a3-candidate',0)
    run('kubectl','rollout','status','-n','rahbar','deployment/api-candidate','--timeout=180s')
    evaluate('eval-bad','api-candidate','rahbar-a3-candidate',0,'bad-candidate',True)
    candidate('rahbar',5)
    run('kubectl','rollout','status','-n','rahbar','deployment/api-candidate','--timeout=180s')
    evaluate('eval-batch-a','api-candidate','rahbar',5,'batch-a')
    candidate('rahbar-a3-candidate',3)
    print('EXPERIMENTS FINISHED',flush=True)
