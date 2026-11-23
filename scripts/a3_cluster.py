"""Repeatable local Kubernetes helpers. All vector writes remain inside ingestion Jobs."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import yaml
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_batch_ab import stage

def run(*args,**kwargs):
    print('+ '+' '.join(args),flush=True)
    return subprocess.run(args,check=True,text=True,**kwargs)

def apply(obj):
    return run('kubectl','apply','-f','-',input=yaml.safe_dump(obj))

def seed():
    helper={'apiVersion':'v1','kind':'Pod','metadata':{'name':'a3-storage','namespace':'rahbar','labels':{'app':'indexer'}},
      'spec':{'restartPolicy':'Never','securityContext':{'runAsUser':10001,'runAsGroup':10001,'fsGroup':10001},
      'containers':[{'name':'storage','image':'rahbar-indexer:a3','imagePullPolicy':'Never','command':['sleep','86400'],
      'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'200m','memory':'256Mi'}},
      'volumeMounts':[{'name':'retained','mountPath':'/retained'},{'name':'results','mountPath':'/results'}]}],
      'volumes':[{'name':'retained','persistentVolumeClaim':{'claimName':'rahbar-a3-retention'}},
                 {'name':'results','persistentVolumeClaim':{'claimName':'a3-results'}}]}}
    Path('k8s/a3-storage.yaml').write_text(yaml.safe_dump(helper)); apply(helper)
    run('kubectl','wait','-n','rahbar','--for=condition=Ready','pod/a3-storage','--timeout=120s')
    with tempfile.TemporaryDirectory() as tmp:
        stage(Path(tmp))
        run('kubectl','cp',tmp+'/input','rahbar/a3-storage:/retained/input-ab')
    # A-only contains exactly its manifest files, not extraction side products.
    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        records=json.loads(Path('corpus/raw/_index.json').read_text())
        for r in records: shutil.copyfile(Path('corpus/raw')/r['file'],Path(tmp)/r['file'])
        Path(tmp,'_index.json').write_text(json.dumps(records))
        run('kubectl','cp',tmp+'/.','rahbar/a3-storage:/retained/input-a')

def ingest(name,collection,corpus):
    job=yaml.safe_load(Path('k8s/base/indexer-job.yaml').read_text())
    job['metadata']={'name':name,'namespace':'rahbar'}; job['spec']['backoffLimit']=0
    pod=job['spec']['template']['spec']; pod['restartPolicy']='Never'
    pod['hostAliases']=[{'ip':'192.168.65.254','hostnames':['host.docker.internal']}]
    pod['volumes'].append({'name':'retained','persistentVolumeClaim':{'claimName':'rahbar-a3-retention'}})
    c=pod['containers'][0]; c['image']='rahbar-indexer:a3'; c['imagePullPolicy']='Never'
    c['volumeMounts'].append({'name':'retained','mountPath':'/retained'})
    c['env']=[{'name':k,'value':v} for k,v in {'RAHBAR_RETENTION_DIR':'/retained','CORPUS_DIR':corpus,'CHROMA_COLLECTION':collection}.items()]
    Path('k8s',name+'.yaml').write_text(yaml.safe_dump(job)); apply(job)
    return job

def candidate(collection,k):
    d=yaml.safe_load(Path('k8s/a3-api.yaml').read_text())
    d['metadata']['name']='api-candidate'; d['spec']['replicas']=1
    d['spec']['selector']['matchLabels']={'app':'api','track':'candidate'}
    d['spec']['template']['metadata']['labels']={'app':'api','track':'candidate'}
    c=d['spec']['template']['spec']['containers'][0]
    c['env']=[{'name':a,'value':v} for a,v in {'CHROMA_COLLECTION':collection,'CACHE_ENABLED':'false','TRACE_DIR':'/results/traces','TOP_K':str(k)}.items()]
    # Existing live Deployment selects app=api. Avoid overlapping ownership by
    # giving candidate a distinct app, then add matching dependency policies.
    d['spec']['selector']['matchLabels']={'app':'api-candidate'}
    d['spec']['template']['metadata']['labels']={'app':'api-candidate'}
    service={'apiVersion':'v1','kind':'Service','metadata':{'name':'api-candidate','namespace':'rahbar'},'spec':{'selector':{'app':'api-candidate'},'ports':[{'port':8000,'targetPort':8000}]}}
    policies=[]
    for file in ('k8s/base/networkpolicy.yaml','k8s/overlays/dev/ollama-egress.yaml'):
        for policy in yaml.safe_load_all(Path(file).read_text()):
            if not policy: continue
            raw=json.dumps(policy)
            if '"api"' not in raw: continue
            clone=json.loads(raw.replace('"api"','"api-candidate"'))
            clone['metadata']['name']='candidate-'+clone['metadata']['name']; clone['metadata']['namespace']='rahbar'
            policies.append(clone)
    Path('k8s/candidate.yaml').write_text(yaml.safe_dump_all([d,service]+policies))
    for obj in [d,service]+policies: apply(obj)

def collect():
    Path('traces').mkdir(exist_ok=True)
    run('kubectl','cp','rahbar/a3-storage:/results/.','eval/results/cluster')
    run('kubectl','cp','rahbar/a3-storage:/results/traces/.','traces')
    run('kubectl','cp','rahbar/a3-storage:/retained/reports/.','eval/results/verification')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['seed','ingest','candidate','collect']); p.add_argument('--name',default='a3-ingest'); p.add_argument('--collection',default='rahbar-a3-candidate'); p.add_argument('--corpus',default='/retained/input-ab'); p.add_argument('--top-k',type=int,default=3)
    a=p.parse_args()
    if a.action=='seed': seed()
    elif a.action=='ingest': ingest(a.name,a.collection,a.corpus)
    elif a.action=='candidate': candidate(a.collection,a.top_k)
    else: collect()
