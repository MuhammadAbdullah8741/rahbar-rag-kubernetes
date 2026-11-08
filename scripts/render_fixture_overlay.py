"""Create a disposable fixture overlay; the real dev/prod overlays remain intact."""

import sys
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
out = root / "k8s/overlays/ci-generated"
out.mkdir(exist_ok=True)
prefix, tag = sys.argv[1:]
corpus = {
    p.name: p.read_text()
    for p in (root / "eval/fixtures").glob("*.md")
    if p.name != "README.md"
}
if not corpus:
    corpus = {
        p.name: p.read_text() for p in (root / "eval/fixtures/corpus").glob("*.md")
    }
(out / "corpus.yaml").write_text(
    yaml.safe_dump(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "fixture-corpus"},
            "data": corpus,
        },
        sort_keys=False,
    )
)
patches = []
values = {
    "EMBED_MODEL": "fixture-hash-v1",
    "LLM_PROVIDER": "fixture",
    "RELEVANCE_FLOOR": "0.2",
    "CACHE_ENABLED": "false",
}
patches.append(
    {
        "target": {"kind": "ConfigMap", "name": "rahbar-config"},
        "patch": yaml.safe_dump(
            [
                {"op": "replace", "path": "/data/" + k, "value": v}
                for k, v in values.items()
            ]
        ),
    }
)
for kind, name, path in [
    ("Job", "indexer", "/spec/template/spec/volumes"),
    ("CronJob", "reindex", "/spec/jobTemplate/spec/template/spec/volumes"),
]:
    patches.append(
        {
            "target": {"kind": kind, "name": name},
            "patch": yaml.safe_dump(
                [
                    {
                        "op": "replace",
                        "path": path,
                        "value": [
                            {"name": "tmp", "emptyDir": {}},
                            {"name": "corpus", "configMap": {"name": "fixture-corpus"}},
                        ],
                    }
                ]
            ),
        }
    )
patches.append(
    {
        "target": {"kind": "CronJob", "name": "reindex"},
        "patch": "- op: replace\n  path: /spec/suspend\n  value: true\n",
    }
)
manifest = {
    "apiVersion": "kustomize.config.k8s.io/v1beta1",
    "kind": "Kustomization",
    "namespace": "rahbar",
    "resources": ["../../base", "corpus.yaml"],
    "patches": patches,
    "images": [
        {"name": "rahbar-" + c, "newName": prefix + "-" + c, "newTag": tag}
        for c in ["api", "indexer", "ui"]
    ],
}
(out / "kustomization.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
