"""Create synthetic live-style input and six honest abstention coverage extensions."""
import json
from pathlib import Path
base=[json.loads(l) for l in Path('eval/golden.jsonl').read_text().splitlines()]
live=[]
for i,q in enumerate([q for q in base if q['relevant']][:20]):
    live.append({'id':f'l{len(live)+1:02}','question':q['question'].replace('What is','Can you tell me').replace('How much','Please tell me how much'),'topic':'university policy','in_domain':True})
for q in base[:8]:
    live.append({'id':f'l{len(live)+1:02}','question':'Please help: '+q['question'],'topic':'university policy','in_domain':True})
topics=[('bus tracking','Where is my campus shuttle right now?','Can I track the university bus live?'),
        ('WiFi support','How do I reset my campus WiFi password?','Where can I change the password for campus wireless internet?'),
        ('sports trials','When are the university cricket team trials?','What is the date for cricket team selection?'),
        ('counselling','How can I book a student counselling appointment?','Where do I schedule a meeting with the campus counsellor?'),
        ('lost property','Where do I report a lost student ID card?','Who handles a missing campus identity card?'),
        ('printing','What does colour printing cost at the campus print shop?','How much do I pay per colour page at the university printing shop?')]
extra=[]
for topic,q1,q2 in topics:
    for question in (q1,q2): live.append({'id':f'l{len(live)+1:02}','question':question,'topic':topic,'in_domain':False})
    extra.append({'id':f'q{26+len(extra)}','question':q1,'relevant':[],'expect':'','must_abstain':True,'hard':False,'type':'coverage','author':'synthetic','human_reviewed':False,'topic':topic})
for path,rows in [('eval/live-queries.jsonl',live),('eval/golden-expanded.jsonl',base+extra)]:
    Path(path).write_text(''.join(json.dumps(r)+'\n' for r in rows))
print('Live:',len(live),'in-domain:',sum(r['in_domain'] for r in live),'expanded:',len(base+extra))
