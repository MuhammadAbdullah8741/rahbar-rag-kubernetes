import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('before'); p.add_argument('after'); p.add_argument('--out',required=True); a=p.parse_args()
    b=json.loads(Path(a.before).read_text()); c=json.loads(Path(a.after).read_text()); rows=[]
    for level in ('module','component','noise','noise_delta','end_to_end'):
        for key,v in b[level].items():
            w=c[level].get(key)
            if isinstance(v,(int,float)) and isinstance(w,(int,float)): rows.append({'level':level,'metric':key,'before':v,'after':w,'delta':w-v})
    result={'before':a.before,'after':a.after,'same_golden':b['golden_sha256']==c['golden_sha256'],'rows':rows}
    Path(a.out).write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
