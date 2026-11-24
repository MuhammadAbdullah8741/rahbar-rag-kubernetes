"""Record cluster CPU and memory samples while ingestion and evaluation execute."""
import datetime
import json
from pathlib import Path
import subprocess
import time

out=Path('eval/results/resource-samples-a3.jsonl')
for _ in range(30):
    r=subprocess.run(['kubectl','top','pods','-n','rahbar','--no-headers'],text=True,capture_output=True)
    row={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'output':r.stdout,'error':r.stderr}
    with out.open('a') as stream: stream.write(json.dumps(row)+'\n')
    time.sleep(20)
