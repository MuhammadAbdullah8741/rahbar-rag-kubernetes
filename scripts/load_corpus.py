"""Copy only manifest-listed public source files to the Kubernetes corpus PVC."""

import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(["kubectl", "-n", "rahbar", *args], check=True, **kwargs)


def main():
    raw = ROOT / "corpus/raw"
    manifest = json.loads((raw / "_index.json").read_text())
    # The manifest produced by fetch.py is a list of source records.
    files = ["_index.json"] + [record["file"] for record in manifest]
    for name in files:
        if Path(name).name != name or not (raw / name).is_file():
            raise ValueError(f"Invalid source file: {name}")
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "corpus-loader", "labels": {"app": "corpus-loader"}},
        "spec": {
            "serviceAccountName": "indexer",
            "automountServiceAccountToken": False,
            "restartPolicy": "Never",
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 10001,
                "runAsGroup": 10001,
                "fsGroup": 10001,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "containers": [
                {
                    "name": "loader",
                    "image": "rahbar-indexer:dev",
                    "imagePullPolicy": "IfNotPresent",
                    "command": ["sleep", "600"],
                    "securityContext": {
                        "readOnlyRootFilesystem": True,
                        "allowPrivilegeEscalation": False,
                        "capabilities": {"drop": ["ALL"]},
                    },
                    "resources": {
                        "requests": {"cpu": "10m", "memory": "32Mi"},
                        "limits": {"cpu": "100m", "memory": "128Mi"},
                    },
                    "volumeMounts": [{"name": "corpus", "mountPath": "/corpus"}],
                }
            ],
            "volumes": [
                {"name": "corpus", "persistentVolumeClaim": {"claimName": "corpus"}}
            ],
        },
    }
    run("apply", "-f", "-", input=json.dumps(pod).encode())
    try:
        run("wait", "--for=condition=Ready", "pod/corpus-loader", "--timeout=180s")
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for name in files:
                archive.add(raw / name, arcname=name)
        run(
            "exec",
            "-i",
            "corpus-loader",
            "--",
            "tar",
            "xf",
            "-",
            "-C",
            "/corpus",
            input=stream.getvalue(),
        )
        print(f"Copied {len(files) - 1} public documents and index manifest")
    finally:
        run("delete", "pod", "corpus-loader", "--wait=false")


if __name__ == "__main__":
    main()
