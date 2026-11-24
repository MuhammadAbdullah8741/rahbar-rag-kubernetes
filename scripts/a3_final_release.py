"""Finalize coverage, mounted-config gates and an approved-only release drill."""
import copy
import json
from pathlib import Path
import sys
import yaml
from a3_cluster import run, apply
from a3_experiments import wait
from a3_release_demo import fresh_query
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'eval'))
from gate import gate


def job(name, command):
    j=yaml.safe_load(Path('k8s/eval-baseline-job.yaml').read_text())
    j['metadata']['name']=name
    c=j['spec']['template']['spec']['containers'][0]
    c['image']='rahbar-eval:a3-submission'; c['command']=['sh','-c',command]
    Path('k8s',name+'.yaml').write_text(yaml.safe_dump(j)); apply(j)
    return wait(name)


def collect():
    Path('eval/results/final').mkdir(exist_ok=True)
    run('kubectl','cp','rahbar/a3-storage:/results/final/.','eval/results/final')
    run('kubectl','cp','rahbar/a3-storage:/results/traces/.','traces')


def gate_job(name,candidate='candidate'):
    return job(name,'python eval/gate.py --baseline /results/final/baseline-ab.json --candidate /results/final/'+candidate+'.json --thresholds /gate/gate.json --out /results/final/'+name+'.json')


if __name__=='__main__':
    job('final-coverage','python eval/coverage.py --out /results/final/coverage-before.json; before=$?; echo BEFORE_EXIT=$before; python eval/coverage.py --golden eval/golden-expanded.jsonl --out /results/final/coverage-after.json; after=$?; echo AFTER_EXIT=$after; exit $after')
    original=yaml.safe_load(Path('k8s/gate-configmap.yaml').read_text())
    apply(original)
    passed=gate_job('final-gate-candidate')
    assert not gate_job('final-gate-bad','bad-candidate')
    strict=copy.deepcopy(original); t=json.loads(strict['data']['gate.json']); t['end_to_end.faithfulness']['min']=1.01
    strict['data']['gate.json']=json.dumps(t); apply(strict)
    assert not gate_job('final-gate-strict')
    apply(original); restored=gate_job('final-gate-restored'); assert passed==restored
    collect()
    root=Path('eval/results/final')
    for old,new in [('final-gate-candidate','candidate-gate'),('final-gate-bad','bad-candidate-gate'),('final-gate-strict','gate-strict'),('final-gate-restored','gate-restored')]:
        (root/(new+'.json')).write_bytes((root/(old+'.json')).read_bytes())
    decision={'candidate':'approved' if passed else 'blocked','bad_candidate':'blocked','strict_config_rejected':True,'restored_config_passed':restored,'strict_minimum':1.01}
    if passed:
        run('kubectl','set','env','deployment/api','-n','rahbar','CHROMA_COLLECTION=rahbar-a3-candidate','TOP_K=3')
        run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
        fresh_query('final-release-query')
        run('kubectl','set','env','deployment/api','-n','rahbar','CHROMA_COLLECTION=rahbar','TOP_K=0')
        run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
        fresh_query('final-bad-release-query')
        run('kubectl','rollout','undo','deployment/api','-n','rahbar')
        run('kubectl','rollout','status','deployment/api','-n','rahbar','--timeout=180s')
        fresh_query('final-undo-query')
        decision['rollout_undo']='completed'
    else:
        decision['rollout_undo']='Final candidate blocked; prior successful 25-question release/undo retained as historical evidence.'
    (root/'release-decision.json').write_text(json.dumps(decision,indent=2))
    collect()
    print(json.dumps(decision),flush=True)
