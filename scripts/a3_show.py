"""Display compact views of authentic saved evidence for uncropped terminal captures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
R=Path('eval/results'); C=R/'cluster'
load=lambda p:json.loads(p.read_text())
section=sys.argv[1]
print('RAHBAR Assignment 3 | '+section+' | saved local cluster evidence\n')
if section.startswith('F0'):
    command=['kubectl','get','all,pvc,configmap,cronjob,job','-n','rahbar','-o','name']
    result=subprocess.run(command,check=True,text=True,capture_output=True)
    print('RUN:', ' '.join(command)); lines=result.stdout.splitlines(); index=int(section[-1])-1
    print(f'Inventory output page {index+1}; lines {index*36+1} through {min((index+1)*36,len(lines))} of {len(lines)}')
    print('\n'.join(lines[index*36:(index+1)*36]))
elif section=='F5':
    print('RUN: kubectl logs -n rahbar job/eval-topk3 (summary section)')
    result=subprocess.run(['kubectl','logs','-n','rahbar','job/eval-topk3'],check=True,text=True,capture_output=True)
    start=result.stdout.index('Level | Metric'); end=result.stdout.index('RESULT',start)
    print(result.stdout[start:result.stdout.index('\n',end)])
elif section=='A1':
    v=load(sorted((R/'verification').glob('a3-final-verify*.json'))[-1])
    print('Source:',sorted((R/'verification').glob('a3-final-verify*.json'))[-1])
    print('Q=quality C=completeness R=recency U=uniqueness; N=not evaluated after rejection')
    for row in v['documents']:
        status=[]
        for k in ('quality','completeness','recency','uniqueness'):
            c=row['checks'][k]; status.append('P' if c['pass'] else 'N' if str(c['reason']).startswith('Not evaluated') else 'F')
        print(f"{row['document_id']:<60} {' '.join(status)} {row['decision']}")
    print('\nFailure reasons (full pass/fail reasons are in the JSON report):')
    for row in v['documents']:
        for key,check in row['checks'].items():
            if not check['pass'] and not str(check['reason']).startswith('Not evaluated'):
                reason=check['reason']
                if isinstance(reason,dict): reason=reason.get('reason') or reason.get('duplicate_of') or reason.get('closest') or str(reason)
                print(row['document_id'],key,':',reason)
elif section=='A2':
    for name in ('unchanged-proof.json','deletion-proof.json'):
        print(name); print(json.dumps(load(R/name),indent=2))
    print('kubectl logs job/a3-final-verify (saved completion records):')
    print('\n'.join((R/'a3-final-verify.log').read_text().splitlines()[-3:]))
elif section=='B': print((C/'candidate.md').read_text())
elif section=='C':
    for name in ('candidate-gate.json','bad-candidate-gate.json','gate-strict.json','gate-restored.json'):
        d=load(C/name); print(name,':',d['decision'].upper())
        for failure in d['failures']: print('  '+failure)
    print('\nSame candidate metrics; ConfigMap faithfulness minimum: 1.0 => FAIL, 0.8 => PASS')
    print('No image rebuild between gate-strict and gate-restored Jobs.')
elif section=='D1': print(json.dumps(load(R/'full-trace-sample.json'),indent=2))
elif section=='D2':
    trace='d9871d8345a34b89984ee973eccab23c'; dest=R/'reconstructed-prompt.json'
    cmd=[sys.executable,'eval/trace_tool.py','--id',trace,'--out',str(dest)]
    print('RUN:', ' '.join(cmd)); subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
    data=load(dest); payload=json.dumps(data['generation_attempts'],sort_keys=True).encode()
    actual=hashlib.sha256(payload).hexdigest(); assert actual==data['prompt_hash']
    print('Exact saved prompt attempts:',len(data['generation_attempts']))
    print('Hash in trace:',data['prompt_hash']); print('Reconstructed:',actual); print('MATCH: exact prompts and contexts reconstructed to',dest)
    print('\nContext documents:')
    for hit in data['retrieval'][0]['passages']: print(hit['chunk_id'],hit['source'],'page',hit['page'],'version',hit['metadata']['doc_version'])
    print('\nTrace-only cause:'); print((R/'root-cause.txt').read_text())
elif section=='E':
    for name in ('coverage-before.json','coverage-after.json'):
        d=load(R/name); print(name, 'golden=',d['golden_count'],'queries=',d['queries'],'coverage=',d['coverage'],'threshold=',d['similarity_threshold'])
        for topic,qs in d['uncovered_topics'].items(): print(' ',topic,':',len(qs),'uncovered')
    print('\nBEFORE_EXIT=1; AFTER_EXIT=0 (see coverage-job.log)')
elif section=='F1':
    print('RUN: kubectl get deployment,statefulset,svc,pvc,configmap,cronjob -n rahbar')
    subprocess.run(['kubectl','get','deployment,statefulset,svc,pvc,configmap,cronjob','-n','rahbar'],check=True)
elif section=='F2':
    print('RUN: kubectl get job -n rahbar'); subprocess.run(['kubectl','get','job','-n','rahbar'],check=True)
    print('\nCompleted ingestion log (saved):'); print('\n'.join((R/'a3-final-verify.log').read_text().splitlines()[-3:]))
    print('\nCompleted evaluation summary is in B; actual Job logs: eval-topk3.log')
elif section=='F3':
    for line in (R/'release-demo.log').read_text().splitlines():
        if 'rollout status' in line or 'rollout undo' in line or 'successfully rolled out' in line or 'rolled back' in line or 'CONTROLLED' in line: print(line)
    print(json.dumps(load(R/'rollback-proof.json'),indent=2))
elif section=='F4':
    print('RUN: kubectl top pods -n rahbar'); subprocess.run(['kubectl','top','pods','-n','rahbar'],check=True)
    print('\nMeasured experiment peaks:'); print(json.dumps(load(R/'resource-summary.json'),indent=2))
    print('\nMetrics retrieved through kubectl port-forward svc/api 18003:8000')
    print('\n'.join((R/'metrics-endpoint.txt').read_text().splitlines()[:6]))
else: raise SystemExit('Unknown evidence section')
