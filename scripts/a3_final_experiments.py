"""Run final 33-question experiments, preserving earlier 25-question evidence."""
import json
from pathlib import Path
import subprocess
import sys
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parent))
from a3_experiments import wait
from a3_cluster import run, apply


def configure(deployment, collection, k):
    run('kubectl','set','env','-n','rahbar','deployment/'+deployment,'CHROMA_COLLECTION='+collection,'TOP_K='+str(k),'CACHE_ENABLED=false')
    run('kubectl','rollout','status','-n','rahbar','deployment/'+deployment,'--timeout=180s')


def evaluate(name, collection, k, api='api-candidate'):
    job=yaml.safe_load(Path('k8s/eval-baseline-job.yaml').read_text())
    job['metadata']['name']='final-'+name
    c=job['spec']['template']['spec']['containers'][0]
    c['image']='rahbar-eval:a3-submission'
    c['command']=['python','eval/suite.py','--api','http://'+api+':8000','--label','final-'+name,'--out','/results/final/'+name+'.json']
    c['env']=[{'name':a,'value':str(b)} for a,b in {'CHROMA_COLLECTION':collection,'TOP_K':k,'CACHE_ENABLED':'false'}.items()]
    Path('k8s/final-'+name+'.yaml').write_text(yaml.safe_dump(job))
    apply(job)
    if not wait('final-'+name): raise RuntimeError(name+' failed')


if __name__=='__main__':
    configure('api','rahbar-a3-ab',5)
    evaluate('baseline-ab','rahbar-a3-ab',5,'api')
    evaluate('baseline-repeat','rahbar-a3-ab',5,'api')
    configure('api-candidate','rahbar-a3-candidate',3)
    evaluate('candidate','rahbar-a3-candidate',3)
    configure('api-candidate','rahbar-a3-candidate',0)
    evaluate('bad-candidate','rahbar-a3-candidate',0)
    configure('api-candidate','rahbar',5)
    evaluate('batch-a','rahbar',5)
    configure('api-candidate','rahbar-a3-candidate',3)
    print('FINAL EXPERIMENTS COMPLETE',flush=True)
