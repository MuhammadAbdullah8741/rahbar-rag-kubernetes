"""Keep job-scoped document copies and decision records on the mounted volume."""
import hashlib
import json
import os
import shutil
from pathlib import Path


def retain(source, category, version, reason):
    root = os.environ.get("RAHBAR_RETENTION_DIR")
    if not root:
        return
    target = Path(root) / os.environ["HOSTNAME"] / category / source.name
    target.mkdir(parents=True, exist_ok=True)
    record = {"source": source.name, "version": version, "reason": reason}
    if source.is_file():
        tmp = target / "payload.tmp"
        shutil.copyfile(source, tmp)
        with tmp.open("rb") as stream:
            record["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        tmp.replace(target / "payload")
    tmp = target / "decision.tmp"
    tmp.write_text(json.dumps(record, indent=2) + "\n")
    tmp.replace(target / "decision.json")
    print(json.dumps({"msg": "retained document", "category": category,
                      "directory": str(target), **record}), flush=True)
