"""Collect comparisons, timestamped run aliases and resource summaries from real runs."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

root=Path('eval/results'); cluster=root/'cluster'
for source in cluster.glob('*.json'):
    if '.partial.' in source.name: continue
    data=json.loads(source.read_text())
    if 'timestamp' in data and 'module' in data:
        stamp=data['timestamp'].replace(':','').replace('+','_')
        shutil.copyfile(source,root/(data['label']+'-'+stamp+'.json'))
maxima={}
for line in (root/'resource-samples-a3.jsonl').read_text().splitlines():
    sample=json.loads(line)
    for row in sample['output'].splitlines():
        name,cpu,memory=row.split()
        role=next((r for r in ('api','chroma','eval','a3-ingest','a3-unchanged') if name.startswith(r)),None)
        if role is None: continue
        role='indexer' if role.startswith('a3-') else role
        c=float(cpu[:-1]) if cpu.endswith('m') else float(cpu)*1000
        m=float(memory[:-2])*(1024 if memory.endswith('Gi') else 1)
        old=maxima.setdefault(role,{'peak_observed_cpu_m':0,'peak_observed_memory_Mi':0})
        old['peak_observed_cpu_m']=max(old['peak_observed_cpu_m'],c); old['peak_observed_memory_Mi']=max(old['peak_observed_memory_Mi'],m)
maxima['note']='kubectl top samples, not guaranteed lifetime peaks; indexer cgroup memory.peak is also saved in Job logs'
(root/'resource-summary.json').write_text(json.dumps(maxima,indent=2))
for name,args in {
 'cluster-inventory.txt':['get','all,pvc,configmap,cronjob,job','-n','rahbar'],
 'cluster-resource-final.txt':['top','pods','-n','rahbar'],
 'rollout-history.txt':['rollout','history','deployment/api','-n','rahbar'],
}.items():
    r=subprocess.run(['kubectl']+args,text=True,capture_output=True)
    (root/name).write_text('$ kubectl '+' '.join(args)+'\n'+r.stdout+r.stderr)
for job in ('a3-final-verify','a3-sized-verify'):
    r=subprocess.run(['kubectl','logs','-n','rahbar','job/'+job],text=True,capture_output=True)
    (root/(job+'.log')).write_text(r.stdout+r.stderr)
print(json.dumps(maxima,indent=2))
