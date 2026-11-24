from pathlib import Path
import yaml
from a3_cluster import apply
job=yaml.safe_load(Path('k8s/eval-baseline-job.yaml').read_text())
job['metadata']['name']='a3-coverage'
c=job['spec']['template']['spec']['containers'][0]; c['image']='rahbar-eval:a3-tools'
c['command']=['/bin/sh','-c',
    'python eval/coverage.py --out /results/coverage-before.json; before=$?; '
    'echo BEFORE_EXIT=$before; '
    'python eval/coverage.py --golden eval/golden-expanded.jsonl --out /results/coverage-after.json; after=$?; '
    'echo AFTER_EXIT=$after; exit $after']
Path('k8s/coverage-job.yaml').write_text(yaml.safe_dump(job)); apply(job)
