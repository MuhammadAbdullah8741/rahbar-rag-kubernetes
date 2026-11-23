"""Measure unchanged embeddings, stable IDs and deletion on an isolated collection."""
import json
from pathlib import Path
import subprocess
import chromadb
from a3_cluster import run, ingest
from a3_experiments import wait

client=chromadb.HttpClient(host='127.0.0.1',port=18001)
def snapshot(name):
    c=client.get_collection(client.get_collection(name+'-control').metadata['active_collection'])
    rows=c.get(include=['metadatas'])
    return {'collection':c.name,'ids':rows['ids'],'metadatas':rows['metadatas']}

if __name__=='__main__':
    assert wait('a3-ingest-candidate')
    before=snapshot('rahbar-a3-candidate')
    ingest('a3-unchanged','rahbar-a3-candidate','/retained/input-ab'); assert wait('a3-unchanged')
    after=snapshot('rahbar-a3-candidate')
    Path('eval/results/unchanged-proof.json').write_text(json.dumps({'before_collection':before['collection'],'after_collection':after['collection'],
         'before_count':len(before['ids']),'after_count':len(after['ids']),'stable_ids':set(before['ids'])==set(after['ids']),
         'note':'Immutable snapshots republish stored vectors; embedding counts are in a3-unchanged.log.'},indent=2))
    code="import shutil; shutil.copytree('/retained/input-ab','/retained/input-deletion',dirs_exist_ok=True)"
    run('kubectl','exec','-n','rahbar','a3-storage','--','python','-c',code)
    ingest('a3-delete-before','rahbar-a3-deletion','/retained/input-deletion'); assert wait('a3-delete-before')
    before=snapshot('rahbar-a3-deletion')
    code="import json; from pathlib import Path; p=Path('/retained/input-deletion'); rows=json.loads((p/'_index.json').read_text()); (p/'_index.json').write_text(json.dumps([r for r in rows if r['file']!='b-booking.html'])); (p/'b-booking.html').unlink()"
    run('kubectl','exec','-n','rahbar','a3-storage','--','python','-c',code)
    ingest('a3-delete-after','rahbar-a3-deletion','/retained/input-deletion'); assert wait('a3-delete-after')
    after=snapshot('rahbar-a3-deletion')
    count=lambda s:sum(m.get('document_id',m['source'])=='b-booking.html' for m in s['metadatas'])
    result={'document_id':'b-booking.html','before_count':count(before),'after_count':count(after),
            'before_collection':before['collection'],'after_collection':after['collection'],
            'unrelated_ids_unchanged':{i for i,m in zip(before['ids'],before['metadatas']) if m['source']!='b-booking.html'}==set(after['ids'])}
    assert result['before_count']>0 and result['after_count']==0 and result['unrelated_ids_unchanged']
    Path('eval/results/deletion-proof.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
