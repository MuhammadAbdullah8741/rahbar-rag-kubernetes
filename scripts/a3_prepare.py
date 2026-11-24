"""Prepare reproducible A3 manifests and inspect source evidence. Run from repo root."""
import json
import copy
import subprocess
from pathlib import Path
import yaml
import chromadb

def main():
    root = Path('.')
    client = chromadb.HttpClient(host='127.0.0.1', port=18001)
    catalog = {}
    for name in ('rahbar', 'rahbar-a3-ab'):
        ctrl = client.get_collection(name+'-control')
        c = client.get_collection(ctrl.metadata['active_collection'])
        catalog[name] = {'name':c.name, 'metadata': c.metadata, 'rows': c.get(include=['documents','metadatas'])}
    Path('eval/results/source-catalog.json').write_text(json.dumps(catalog, indent=2))
    rows = catalog['rahbar']['rows']
    qs = yaml.safe_load(Path('eval/golden.yaml').read_text())['questions']
    for q in qs:
        q.update(author='synthetic', human_reviewed=False, provenance='Existing A2 set; human authorship not yet confirmed')
        for ref in q['relevant']:
            matches = [m for m in rows['metadatas'] if m['source']==ref['source'] and m['section']==ref['section']]
            ref['page'] = matches[0]['page'] if matches else None
        q['hard'] = q['type'] in ('version','injection','exact')
    extra = [
        ('Which desk handles practice room reservations?', 'b-booking.html', 'R12', True),
        ('What form is used for simulation lab access requests?', 'b-lab.html', 'LAB-5', True),
        ('Which ticket does the demo desk use?', 'b-injected-notice.html', 'D17', True),
        ('Where should borrowed headsets be returned?', 'b-returns.html', 'H6', True),
        ('Which form is required for grade review in the synthetic revised notice?', 'b-grading-revision.html', 'GR-17', True),
        ('How much money is paid once as the admission charge?', 'fee-structure-page.html', '30,000', True),
        ('How much of my deposit can I get back?', 'fee-structure-page.html', '20,000', True),
        ('What is the campus cafeteria breakfast menu tomorrow?', None, '', False),
        ('How do I claim university dental insurance?', None, '', False),
        ('What is the university parking permit price?', None, '', False),
    ]
    ab = catalog['rahbar-a3-ab']['rows']
    for question, source, answer, hard in extra:
        refs=[]
        if source:
            matches=[m for text,m in zip(ab['documents'], ab['metadatas']) if m['source']==source and answer.lower() in text.lower()]
            if not matches:
                raise ValueError(('Expected source fact absent; ingest the complete A+B batch first',source,answer))
            m=matches[-1]
            refs=[{k:m[k] for k in ('source','section','page')}]
        qs.append(dict(id=f'q{len(qs)+1:02}', question=question, relevant=refs, expect=answer,
                       must_abstain=source is None, hard=hard, type='hard' if hard else 'abstain',
                       author='synthetic',human_reviewed=False))
    Path('eval/golden.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in qs))
    print('Golden questions:',len(qs),'answerable:',sum(bool(q['relevant']) for q in qs))
    dep=json.loads(Path('/tmp/a3-api.json').read_text())
    dep.pop('status',None)
    dep['metadata']={'name':'api','namespace':'rahbar'}
    pod=dep['spec']['template']['spec']
    container=pod['containers'][0]
    container['image']='rahbar-api:a3'
    container['env']=[{'name':k,'value':v} for k,v in {'CHROMA_COLLECTION':'rahbar-a3-ab','CACHE_ENABLED':'false','TRACE_DIR':'/results/traces'}.items()]
    container['volumeMounts'].append({'name':'results','mountPath':'/results'})
    pod['volumes'].append({'name':'results','persistentVolumeClaim':{'claimName':'a3-results'}})
    Path('k8s/a3-api.yaml').write_text(yaml.safe_dump(dep))
    pvc={'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':{'name':'a3-results','namespace':'rahbar'},'spec':{'accessModes':['ReadWriteOnce'],'resources':{'requests':{'storage':'2Gi'}}}}
    Path('k8s/a3-results-pvc.yaml').write_text(yaml.safe_dump(pvc))

if __name__=='__main__': main()
