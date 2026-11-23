import hashlib
import json
from pathlib import Path
import chromadb
client=chromadb.HttpClient(host='127.0.0.1',port=18001)
result={}
for name in ('rahbar-a3-ab','rahbar-a3-candidate'):
    c=client.get_collection(client.get_collection(name+'-control').metadata['active_collection'])
    d=c.get(include=['documents','metadatas','embeddings'])
    rows=[]
    for cid,text,m,v in zip(d['ids'],d['documents'],d['metadatas'],d['embeddings']):
        rows.append([cid,text,{k:m[k] for k in ('source','section','page','doc_version','superseded')},[float(x) for x in v]])
    fingerprint=hashlib.sha256(json.dumps(sorted(rows),sort_keys=True).encode()).hexdigest()
    result[name]={'collection':c.name,'chunks':c.count(),'content_metadata_vector_sha256':fingerprint}
result['identical']=result['rahbar-a3-ab']['content_metadata_vector_sha256']==result['rahbar-a3-candidate']['content_metadata_vector_sha256']
assert result['identical']
Path('eval/results/candidate-corpus-equality.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
