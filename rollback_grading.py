"""Run from the RAHBAR repo: python3 rollback_grading.py RETENTION_POD"""
import json
import subprocess
import sys
import time
from pathlib import Path

def kubectl(*args, **kwargs):
    return subprocess.run(["kubectl", "-n", "rahbar", *args], check=True, text=True, **kwargs)

restore = """
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
import chromadb
src = Path('/test-input')
dst = Path('/tmp/rollback-input')
dst.mkdir(exist_ok=True)
folder = Path('/retained') / os.environ['ARCHIVE_POD'] / 'archive/grading-page.html'
info = json.loads((folder/'decision.json').read_text())
records = json.loads((src/'_index.json').read_text())
original = next(r for r in records if r['file'] == info['source'])
revision = info['reason']['replaced_by']
assert any(r['file'] == revision and r.get('supersedes_file') == original['file'] for r in records)
assert hashlib.sha256((folder/'payload').read_bytes()).hexdigest() == original['sha256'] == info['sha256']
assert info['version'] == original['doc_version']
records = [r for r in records if r['file'] != revision]
for r in records:
    name = r['file']
    assert Path(name).name == name
    if name == info['source']:
        shutil.copyfile(folder/'payload', dst/name)
        r['superseded'] = False
    else:
        shutil.copyfile(src/name, dst/name)
(dst/'_index.json').write_text(json.dumps(records))
client = chromadb.HttpClient(host=os.environ.get('CHROMA_HOST','chroma'), port=int(os.environ.get('CHROMA_PORT','8000')))
control = os.environ['CHROMA_COLLECTION'] + '-control'
def active():
    return client.get_collection(client.get_collection(control).metadata['active_collection'])
def current_count(c, name):
    return len(c.get(where={'$and':[{'source':name},{'superseded':False}]}, include=[])['ids'])
before = active()
print('BEFORE', before.name, current_count(before, original['file']), current_count(before, revision), flush=True)
subprocess.run([sys.executable,'-m','pipeline.run'],check=True,env={**os.environ,'CORPUS_DIR':str(dst)})
after = active()
old = current_count(after, original['file'])
new = current_count(after, revision)
assert old > 0 and new == 0
sample = after.get(where={'source':original['file']},limit=1,include=['embeddings'])
hits = after.query(query_embeddings=[list(sample['embeddings'][0])],where={'superseded':False},n_results=5,include=['metadatas'])
assert any(m['source']==original['file'] and m['doc_version']==info['version'] for m in hits['metadatas'][0])
print('ROLLBACK VERIFIED', after.name, 'restored_current=', old, 'revision_current=', new, 'retrieved_version=', info['version'], flush=True)
"""
pod = sys.argv[1]
prior = json.loads(kubectl("get","pod",pod,"-o","json",capture_output=True).stdout)
spec = prior["spec"]
container = next(c for c in spec["containers"] if c["name"]=="indexer")
assert any(e.get("name")=="CHROMA_COLLECTION" and e.get("value")=="rahbar-a3-ab" for e in container["env"])
name = "rollback-ab-" + str(int(time.time()))
job = json.loads(kubectl("create","job", name,"--from=cronjob/reindex","--dry-run=client","-o","json",capture_output=True).stdout)
template = job["spec"]["template"]["spec"]
c = template["containers"][0]
c.update(image=container["image"],imagePullPolicy="Never",command=["python","-u","-c",restore],
         env=[e for e in container["env"] if e["name"]!="RAHBAR_RETENTION_DIR"] + [{"name":"ARCHIVE_POD","value":pod}])
template["volumes"].append({"name":"archive","persistentVolumeClaim":{"claimName":"rahbar-a3-retention","readOnly":True}})
c["volumeMounts"].append({"name":"archive","mountPath":"/retained","readOnly":True})
job["spec"]["backoffLimit"]=0
template["restartPolicy"]="Never"
kubectl("create","-f","-",input=json.dumps(job))
print(f"kubectl -n rahbar logs -f job/{name} --pod-running-timeout=2m | tee eval/results/{name}.log")
