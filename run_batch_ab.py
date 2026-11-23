"""Launch an isolated A+B indexing Job from the repository root."""
import datetime
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)

def stage(folder):
    data = folder / "input"
    data.mkdir()
    records = {}
    for batch in ("raw", "batch-b"):
        src = Path("corpus") / batch
        for row in json.loads((src / "_index.json").read_text()):
            name = row["file"]
            if Path(name).name != name or name in records:
                raise ValueError(f"Invalid or repeated filename: {name}")
            shutil.copyfile(src / name, data / name)
            records[name] = row
    (data / "_index.json").write_text(json.dumps(list(records.values())))
    return len(records)

def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    job = "verify-ab-" + stamp
    image = "rahbar-indexer:" + job
    template = run("kubectl", "-n", "rahbar", "create", "job", job, "--from=cronjob/reindex",
                   "--dry-run=client", "-o", "json", capture_output=True)
    obj = json.loads(template.stdout)
    container = next(c for c in obj["spec"]["template"]["spec"]["containers"] if c["name"] == "indexer")
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        count = stage(folder)
        print(f"Combined manifest: {count} documents", flush=True)
        run("docker", "build", "-t", "rahbar-indexer:a3-exact", "indexer")
        (folder / "Dockerfile").write_text("FROM rahbar-indexer:a3-exact\nCOPY input/ /test-input/\n")
        run("docker", "build", "-t", image, temp)
        run("minikube", "image", "load", image)
    run("kubectl", "-n", "rahbar", "apply", "-f", "k8s/a3-retention-pvc.yaml")
    pod = obj["spec"]["template"]["spec"]
    pod["volumes"].append({"name": "retention", "persistentVolumeClaim": {"claimName": "rahbar-a3-retention"}})
    container["volumeMounts"].append({"name": "retention", "mountPath": "/retained"})
    container["image"] = image
    container["imagePullPolicy"] = "Never"
    overrides = {"RAHBAR_RETENTION_DIR": "/retained", "CORPUS_DIR": "/test-input", "CHROMA_COLLECTION": "rahbar-a3-ab"}
    container["env"] = [e for e in container.get("env", []) if e["name"] not in overrides]
    container["env"].extend({"name": k, "value": v} for k, v in overrides.items())
    run("kubectl", "-n", "rahbar", "create", "-f", "-", input=json.dumps(obj))
    Path("eval/results").mkdir(parents=True, exist_ok=True)
    print("Job:", job)
    print(f'kubectl -n rahbar logs -f job/{job} --pod-running-timeout=2m | tee eval/results/{job}.log')

if __name__ == "__main__":
    main()
