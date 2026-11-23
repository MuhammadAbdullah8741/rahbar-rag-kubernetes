import json
from pathlib import Path
import yaml

def main():
    env={'CHROMA_COLLECTION':'rahbar-a3-ab','CACHE_ENABLED':'false','TOP_K':'5'}
    pod={'restartPolicy':'Never','automountServiceAccountToken':False,
         'securityContext':{'runAsUser':10001,'runAsGroup':10001,'fsGroup':10001},
         'hostAliases':[{'ip':'192.168.65.254','hostnames':['host.docker.internal']}],
         'containers':[{'name':'eval','image':'rahbar-eval:a3-tools','imagePullPolicy':'Never',
         'command':['python','eval/suite.py','--api','http://api:8000','--label','baseline-ab','--out','/results/baseline-ab.json'],
         'envFrom':[{'configMapRef':{'name':'rahbar-config'}}],
         'env':[{'name':k,'value':v} for k,v in env.items()],
         'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1000m','memory':'768Mi'}},
         'volumeMounts':[{'name':'results','mountPath':'/results'},{'name':'gate','mountPath':'/gate','readOnly':True}]}],
         'volumes':[{'name':'results','persistentVolumeClaim':{'claimName':'a3-results'}},{'name':'gate','configMap':{'name':'a3-gate'}}]}
    job={'apiVersion':'batch/v1','kind':'Job','metadata':{'name':'eval-baseline','namespace':'rahbar'},
         'spec':{'backoffLimit':0,'activeDeadlineSeconds':14400,'template':{'metadata':{'labels':{'app':'eval'}},'spec':pod}}}
    Path('k8s/eval-baseline-job.yaml').write_text(yaml.safe_dump(job))
    gate={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'a3-gate','namespace':'rahbar'},'data':{'gate.json':Path('config/gate.json').read_text()}}
    Path('k8s/gate-configmap.yaml').write_text(yaml.safe_dump(gate))
    policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'a3-evaluation','namespace':'rahbar'},
            'spec':{'podSelector':{},'policyTypes':['Ingress','Egress'],
                    'ingress':[{'from':[{'podSelector':{'matchLabels':{'app':'eval'}}}], 'ports':[{'protocol':'TCP','port':8000}]}],
                    'egress':[{'to':[{'podSelector':{'matchLabels':{'app':'eval'}}}], 'ports':[{'protocol':'TCP','port':8000}]}]}}
    eval_policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'a3-eval-egress','namespace':'rahbar'},
                 'spec':{'podSelector':{'matchLabels':{'app':'eval'}},'policyTypes':['Egress'],
                 'egress':[{'to':[{'podSelector':{}}],'ports':[{'protocol':'TCP','port':8000}]},
                           {'to':[{'ipBlock':{'cidr':'192.168.65.254/32'}}],'ports':[{'protocol':'TCP','port':11434}]}]}}
    Path('k8s/eval-networkpolicy.yaml').write_text(yaml.safe_dump_all([policy,eval_policy]))
    job['metadata']['name']='eval-candidate'
    pod['containers'][0]['command']=['/bin/sh','-ec','python eval/suite.py --api http://api-candidate:8000 --label candidate --out /results/candidate.json; python eval/gate.py --baseline /results/baseline-ab.json --candidate /results/candidate.json --thresholds /gate/gate.json --out /results/candidate-gate.json']
    pod['containers'][0]['env'][0]['value']='rahbar-a3-candidate'
    pod['containers'][0]['env'][2]['value']='3'
    Path('k8s/eval-job.yaml').write_text(yaml.safe_dump(job))

if __name__=='__main__': main()
