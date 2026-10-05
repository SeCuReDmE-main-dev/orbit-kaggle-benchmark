"""Rebuild the source-only replay notebook; never execute the replay locally."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATHS = [
    "harness/replay_synthetic.py",
    "harness/synthetic/manifest.json",
    "harness/synthetic/reference-cases.json",
    "harness/source/package.json",
    "harness/source/tools/engine-jsonl.ts",
    "harness/source/packages/evidence-review/src/index.ts",
    "harness/source/packages/evidence-review/src/classification.ts",
    "harness/source/packages/evidence-review/src/relations.ts",
]
files = {}
for path in PATHS:
    content = (ROOT / path).read_bytes()
    files[path] = {"sha256": hashlib.sha256(content).hexdigest(),
                   "base64": base64.b64encode(content).decode("ascii")}
script_path = HERE / "run_replay.py"
script = script_path.read_text(encoding="utf-8")
script = re.sub(r"(?ms)^FILES = .*?\nNODE_URL = ",
                lambda _: "FILES = " + repr(files) + "\nNODE_URL = ", script, count=1)
ast.parse(script)
script_path.write_text(script, encoding="utf-8", newline="\n")
script_bytes = script_path.read_bytes()
script_hash = hashlib.sha256(script_bytes).hexdigest()
code = ("import base64, hashlib\n"
        + "source = base64.b64decode(" + repr(base64.b64encode(script_bytes).decode("ascii")) + ")\n"
        + "assert hashlib.sha256(source).hexdigest() == " + repr(script_hash) + "\n"
        + "exec(compile(source, 'orbit_kaggle_synthetic_replay.py', 'exec'), {'__name__': '__main__'})\n")
notebook = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "cells": [
        {"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# Orbit: deterministic synthetic replay\n",
            "Source-only package: 36 authored cases, three unchanged engines, 108 decisions, ",
            "324 metamorphic checks, and 54 relation checks. No model calls.\n\n",
            "Enable internet for pinned esbuild and, only if necessary, the SHA-256-verified ",
            "official Node 22.20.0 fallback. Runtime writes remain under `/kaggle/working/`, ",
            "including the npm cache. No private datasets are required.\n\n",
            "This development corpus uses specification-derived expectations. Passing does ",
            "not establish general factual accuracy, semantic entailment, or a winning engine. ",
            "Failed checks preserve detailed synthetic rows and fail the cell.\n"]},
        {"cell_type": "code", "id": "replay", "metadata": {},
         "execution_count": None, "outputs": [], "source": code.splitlines(keepends=True)}
    ]
}
notebook_path = HERE / "orbit-synthetic-replay.ipynb"
notebook_path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8", newline="\n")
provenance = {
    "format": "orbit-kaggle-replay-provenance-v1", "status": "prepared-not-executed",
    "scope": "authored-development-synthetic-only", "modelCalls": 0,
    "sourceBytesPreserved": True,
    "inputs": [{"path": path, "sha256": item["sha256"]} for path, item in files.items()],
    "scriptSha256": script_hash,
    "notebookSha256": hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
    "expected": {"decisions": 108, "metamorphicChecks": 324, "relationChecks": 54},
    "runtime": {"nodeMinimum": 20, "nodeFallback": "22.20.0", "esbuild": "0.25.12"},
    "results": "/kaggle/working/orbit-synthetic-replay/results",
    "limitations": ["Prepared notebook is not execution evidence.",
                    "Specification-derived expectations are not independent human accuracy judgments.",
                    "Not the frozen final 60-question model campaign."]
}
(HERE / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"notebook": str(notebook_path), "scriptSha256": script_hash,
                  "inputs": len(files), "execution": "not-performed"}))
