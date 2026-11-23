"""Schedule exactly the verified Job template after the persistent input is seeded."""
from pathlib import Path
import yaml
from a3_cluster import apply
job=yaml.safe_load(Path('k8s/a3-ingest-candidate.yaml').read_text())
pod=job['spec']['template']['spec']
pod['containers'][0]['resources']=yaml.safe_load(Path('k8s/base/indexer-job.yaml').read_text())['spec']['template']['spec']['containers'][0]['resources']
for item in pod['containers'][0]['env']:
    if item['name']=='CHROMA_COLLECTION': item['value']='rahbar-a3-ab'
cron={'apiVersion':'batch/v1','kind':'CronJob','metadata':{'name':'reindex','namespace':'rahbar'},
      'spec':{'schedule':'0 2 * * 0','timeZone':'Asia/Karachi','concurrencyPolicy':'Forbid','suspend':False,
              'successfulJobsHistoryLimit':2,'failedJobsHistoryLimit':2,'jobTemplate':{'spec':job['spec']}}}
Path('k8s/a3-cronjob.yaml').write_text(yaml.safe_dump(cron)); apply(cron)
