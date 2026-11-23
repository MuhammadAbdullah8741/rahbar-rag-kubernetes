"""Prepare A3 infrastructure without prematurely starting an empty-corpus Job."""
import subprocess
from pathlib import Path
import yaml
from a3_cluster import apply
raw=subprocess.run(['kubectl','kustomize','k8s/overlays/dev'],check=True,text=True,capture_output=True).stdout
objects=[]
for obj in yaml.safe_load_all(raw):
    if obj['kind']=='Job': continue
    if obj['kind']=='Deployment' and obj['metadata']['name']=='api':
        obj['spec']['template']['spec']['containers'][0]['image']='rahbar-api:a3'
    if obj['kind']=='CronJob': obj['spec']['suspend']=True
    objects.append(obj)
Path('k8s/a3-bootstrap.yaml').write_text(yaml.safe_dump_all(objects))
for obj in objects: apply(obj)
