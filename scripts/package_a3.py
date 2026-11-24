"""Create a local handover without .git, credentials, caches or generated QA images."""
import hashlib
import json
from pathlib import Path
import zipfile
from pypdf import PdfReader

root=Path(__file__).resolve().parents[1]; out=root.parent/'Classroom-submission'
report=out/'Assignment_03_Report.pdf'
pdf=PdfReader(report)
assert len(pdf.pages)>=8
assert 'Screenshot appendix' in pdf.pages[8].extract_text()
assert all(float(p.mediabox.height)>float(p.mediabox.width) for p in pdf.pages[:8])
assert all(float(p.mediabox.width)>float(p.mediabox.height) for p in pdf.pages[8:])
raw_names={r['file'] for r in json.loads((root/'corpus/raw/_index.json').read_text())}|{'_index.json'}
allowed_roots={'.github','api','indexer','eval','traces','config','k8s','scripts','corpus','docs','ui'}
allowed_top={'README.md','Makefile','ARCHITECTURE.md','LICENSE','run_batch_ab.py','rollback_grading.py','complete_batch_b.py','summarize_verification.py','near_duplicate_check.py','calibrate_duplicates.py','.gitignore'}
files=[]
for path in root.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(root); parts=rel.parts
    if parts[0] not in allowed_roots and str(rel) not in allowed_top: continue
    if any(p in {'.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.venv','venv'} for p in parts): continue
    if '.coverage' in path.name or path.suffix in {'.pyc','.ready','.pid'} or '.partial.' in path.name: continue
    if parts[:2]==('docs','evidence'): continue
    if parts[:2]==('corpus','raw') and path.name not in raw_names: continue
    if 'secret' in path.name.lower() and path.name!='secret.placeholder.yaml': continue
    if path.name.startswith('.env'): continue
    files.append(path)
archive=out/'Assignment_03_Local_Submission.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in files: z.write(path,'rahbar-starter/'+path.relative_to(root).as_posix())
    z.write(report,report.name)
    z.write(out/'SUBMIT-ASSIGNMENT-03.txt','SUBMIT-ASSIGNMENT-03.txt')
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
summary={'report_pages':len(pdf.pages),'body_pages':8,'appendix_pages':len(pdf.pages)-8,
         'archive_files':len(files)+2,'archive_bytes':archive.stat().st_size,
         'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
         'outstanding':[], 'golden_questions':33, 'human_questions':8, 'synthetic_human_reviews':8}
(out/'Assignment_03_Delivery_Check.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
