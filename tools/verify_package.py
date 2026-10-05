"""Static public-package checks. Never import benchmark modules or call models."""
from __future__ import annotations

import argparse
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "metadata/artifacts.json"
RECEIPT = "metadata/package-validation.json"
EXCLUDED_PARTS = {"private", ".git", "outputs", "node_modules", "__pycache__", "secrets"}
EXCLUDED_SUFFIXES = {".zip", ".bin", ".pyc", ".pyo"}
EXCLUDED_FILES = {"harness/source/engine-jsonl.mjs"}
LABELS = ["llm-evaluation", "evidence-provenance", "synthetic-data", "uncertainty",
          "model-evaluation", "reproducibility", "scoped-claims", "protocol-compliance"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def excluded(path):
    parts = Path(path).parts
    return (bool(set(parts) & EXCLUDED_PARTS) or Path(path).suffix in EXCLUDED_SUFFIXES
            or Path(path).as_posix() in EXCLUDED_FILES
            or any(part == ".env" or part.startswith(".env.") for part in parts))


def public_files():
    return sorted(path for path in ROOT.rglob("*") if path.is_file()
                  and not excluded(path.relative_to(ROOT))
                  and path.relative_to(ROOT).as_posix() not in (CATALOG, RECEIPT))


def describe(relative):
    tags = ["reproducibility", "scoped-claims"]
    scope = {"dataset": "package-metadata", "executionEvidence": False}
    status = "public-source-or-documentation"
    if relative.startswith("pilot/native-pass-fail"):
        tags += ["synthetic-data", "llm-evaluation", "model-evaluation", "uncertainty"]
        scope = {"dataset": "prospective-six-question-native-pass-fail-task", "questions": 6,
                 "executionEvidence": "receipt" in Path(relative).name,
                 "distinctFrom": ["historical-six-question-diagnostic-dict-pilot", "36-case-development-replay",
                                  "60-question-C-campaign"]}
        status = ("separately-identified-native-run-receipt" if scope["executionEvidence"]
                  else "prospective-native-task-preparation-not-an-execution")
    elif relative.startswith("harness/kaggle-replay"):
        tags += ["synthetic-data", "evidence-provenance", "uncertainty"]
        scope = {"dataset": "36-case-authored-synthetic-Kaggle-replay", "questions": 36,
                 "packets": 6, "executionEvidence": "receipt" in Path(relative).name,
                 "distinctFrom": ["six-question-native-pilot", "60-question-B-receipt", "C-model-answer-analysis"]}
        status = "separate-replay-execution-receipt" if scope["executionEvidence"] else "prepared-Kaggle-replay-not-execution-evidence"
    elif relative.startswith("pilot/"):
        tags += ["synthetic-data", "llm-evaluation", "model-evaluation", "uncertainty"]
        scope = {"dataset": "six-question-synthetic-development-pilot", "questions": 6,
                 "documents": 12, "executionEvidence": relative.endswith("historical-run-metadata.json"),
                 "distinctFrom": ["36-case-development-replay", "60-question-C-campaign"]}
        status = "historical-observation-metadata" if scope["executionEvidence"] else "prepared-source-live-binary-parity-unverified"
    elif relative.startswith("harness/synthetic/") or relative == "harness/replay_synthetic.py":
        tags += ["synthetic-data", "uncertainty", "evidence-provenance"]
        scope = {"dataset": "36-case-authored-synthetic-development-replay", "questions": 36,
                 "packets": 6, "executionEvidence": False,
                 "distinctFrom": ["six-question-native-pilot", "60-question-B-receipt"]}
        status = "development-fixtures" if "/synthetic/" in relative else "prepared-replay-adapter-not-executed-in-this-package"
    elif relative.startswith("harness/source/"):
        tags += ["evidence-provenance", "uncertainty"]
        scope = {"dataset": "frozen-historical-C-engine-source", "executionEvidence": False}
        status = "frozen-byte-export"
    elif relative.startswith("harness/scoring/") or relative.startswith("analysis-preparation/"):
        tags += ["evidence-provenance", "model-evaluation", "uncertainty"]
        scope = {"dataset": "C-and-C4-private-input-aggregate-preparation", "executionEvidence": False,
                 "syntheticScorableQuestions": 36, "realQuestionsUnscored": 24,
                 "identitiesPooled": False}
        status = "prepared-analysis-not-executed"
    elif relative.startswith("evidence/analysis-20261005/"):
        tags += ["evidence-provenance", "model-evaluation", "uncertainty", "llm-evaluation"]
        scope = {"dataset": "Kaggle-reanalysis-of-C-and-C4-distinct-identities",
                 "executionEvidence": True, "newModelCalls": 0, "identitiesPooled": False,
                 "syntheticScorableQuestions": 36, "realQuestionsUnscored": 24,
                 "latestRecoveredAccuracy": True}
        if relative.endswith("c-resumption-analysis.json"):
            scope.update({"dataset": "C-236-production-Kaggle-reanalysis", "productions": 236,
                          "extractions": 60, "completedPackets": 59, "completeCampaign": False})
        elif relative.endswith("c4-complement-analysis.json"):
            scope.update({"dataset": "separate-C4-four-production-Kaggle-reanalysis", "productions": 4,
                          "newExtractions": 0, "packets": 1, "syntheticDecisionsPerCondition": 6})
        status = "Kaggle-executed-zero-model-call-reanalysis"
    elif relative.startswith("evidence/replay-20261005/"):
        tags += ["synthetic-data", "evidence-provenance", "uncertainty"]
        scope = {"dataset": "separate-36-case-synthetic-Kaggle-replay", "questions": 36,
                 "executionEvidence": True, "newModelCalls": 0, "engines": 3,
                 "distinctFrom": ["historical-60-question-B", "six-question-native-pilot", "C-C4-model-reanalysis"]}
        status = "Kaggle-executed-deterministic-replay-receipt"
    elif relative.startswith("evidence/native-20261005/"):
        tags += ["synthetic-data", "llm-evaluation", "model-evaluation", "evidence-provenance", "uncertainty"]
        scope = {"dataset": "separately-identified-six-question-native-pass-fail-task",
                 "questions": 6, "executionEvidence": True,
                 "distinctFrom": ["historical-six-question-diagnostic-dict-pilot", "36-case-replay", "C-C4-reanalysis"]}
        status = "native-pass-fail-execution-receipt"
    elif relative.startswith("evidence/"):
        tags += ["evidence-provenance", "model-evaluation", "uncertainty"]
        scope = {"dataset": "sanitized-historical-receipt", "executionEvidence": True}
        status = "historical-receipt-not-new-execution"
        if "native-pass-fail" in relative:
            tags += ["llm-evaluation", "synthetic-data"]
            scope.update({"dataset": "separately-identified-native-pass-fail-task-run", "questions": 6})
            status = "native-task-run-receipt"
        elif "replay" in relative:
            tags += ["synthetic-data"]
            scope.update({"dataset": "separate-36-case-synthetic-Kaggle-replay", "questions": 36,
                          "distinctFrom": ["historical-60-question-B", "six-question-native-pilot"]})
            status = "synthetic-replay-run-receipt"
        elif "historical-221" in relative:
            scope.update({"dataset": "historical-C-221-production-aggregate", "productions": 221,
                          "latestRecoveredAccuracy": False})
        elif "c-resumption" in relative:
            scope.update({"dataset": "C-236-production-coverage-plus-B-60-question-receipt",
                          "productions": 236, "extractions": 60, "packets": 59,
                          "BQuestions": 60, "BScoredSyntheticEvaluations": 108,
                          "BUnscoredRealEvaluations": 72, "latestRecoveredAccuracy": False})
        elif "c4-complement" in relative:
            scope.update({"dataset": "separate-C4-four-production-complement", "productions": 4,
                          "newExtractions": 0, "packets": 1, "identitiesPooled": False,
                          "coverageAcrossIdentities": 240, "latestRecoveredAccuracy": False})
        elif "d-provider" in relative:
            tags += ["protocol-compliance", "llm-evaluation"]
            scope.update({"dataset": "D-provider-12-output-lot-protocol-observations",
                          "semanticAccuracyEstablished": False})
        elif "e-qualification" in relative:
            tags += ["protocol-compliance"]
            scope.update({"dataset": "E-native-worker-qualification", "modelTrajectories": 0,
                          "modelPerformanceScore": False})
        elif "export-manifest" in relative:
            scope = {"dataset": "public-byte-export-provenance", "executionEvidence": False}
            status = "export-provenance"
    elif relative.startswith("docs/") or relative == "README.md":
        tags += ["evidence-provenance", "llm-evaluation", "uncertainty", "protocol-compliance"]
        scope = {"dataset": "editorial-and-methodology-cross-scope-index", "executionEvidence": False}
        status = "article-draft-for-author-review" if relative.endswith("article.en.md") else "public-documentation"
    kind = {".py": "python-source", ".ipynb": "notebook-source", ".json": "json-metadata",
            ".md": "documentation", ".ts": "typescript-source"}.get(Path(relative).suffix, "configuration")
    return {"type": kind, "status": status, "scope": scope, "tags": sorted(set(tags))}


def refresh_catalog(files):
    entries = [{"path": path.relative_to(ROOT).as_posix(), **describe(path.relative_to(ROOT).as_posix()),
                "sha256": sha(path)} for path in files]
    catalog = {"format": "orbit-public-artifact-catalog-v1", "labels": LABELS,
               "exclusions": sorted(EXCLUDED_PARTS | EXCLUDED_FILES) + [CATALOG, RECEIPT, ".env*", "*.zip", "*.bin", "*.py[cod]"],
               "selfHashPolicy": "Catalog and regenerable validation receipt are excluded to prevent hash cycles.",
               "artifacts": entries}
    (ROOT / CATALOG).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / CATALOG).write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def validate(files):
    errors, warnings = [], []
    counts = {"publicArtifacts": len(files), "jsonParsed": 0, "pythonAstParsed": 0,
              "notebooksChecked": 0, "notebookCodeCellsParsed": 0, "exportHashesVerified": 0,
              "pilotHashesVerified": 0, "catalogHashesVerified": 0, "embeddedSourceHashesVerified": 0,
              "ipythonLinesReplacedForStaticParsing": 0, "relativeMarkdownLinksChecked": 0,
              "newPreparationHashesVerified": 0, "embeddedReplayBytesVerified": 0,
              "nativeContractFunctionsVerified": 0, "executedAnalysisScopeChecks": 0}

    def check(condition, message):
        if not condition:
            errors.append(message)

    def assignment(tree, name):
        return next(node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))

    def notebook_python(source, location):
        lines = []
        for line in source.splitlines(keepends=True):
            stripped = line.lstrip()
            if stripped.startswith("%") or stripped.startswith("!"):
                recognized = re.match(r"%(?:choose|pip|load_ext)(?:\s|$)", stripped)
                if not recognized:
                    raise ValueError("Unrecognized IPython syntax: " + location)
                indent = line[:len(line) - len(stripped)]
                lines.append(indent + "pass  # IPython line omitted for static syntax validation only\n")
                counts["ipythonLinesReplacedForStaticParsing"] += 1
            else:
                lines.append(line)
        return ast.parse("".join(lines), filename=location)

    def markdown_links(text, path, relative):
        # Conventional Markdown destinations; titles and angle-wrapped paths supported.
        for match in re.finditer(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+[\"'][^)]*[\"'])?\s*\)", text):
            destination = match.group(1).strip("<>")
            parsed = urlsplit(destination)
            if parsed.scheme in ("https", "http", "mailto") or destination.startswith("#"):
                continue
            check(not parsed.scheme and not parsed.netloc, f"Nonportable Markdown destination: {relative}")
            target = (path.parent / unquote(parsed.path)).resolve()
            safe = target.is_relative_to(ROOT.resolve())
            check(safe, f"Markdown target outside public package: {relative}")
            if safe:
                check(not excluded(target.relative_to(ROOT)), f"Markdown target references private/excluded file: {relative}")
                check(target.exists(), f"Missing relative Markdown target: {relative} -> {destination}")
            counts["relativeMarkdownLinksChecked"] += 1

    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
            check(not path.is_symlink(), f"Public symlink requires explicit review: {relative}")
            check(not re.search(r"https?://[^\s\"<>)]*(?:orbit-kaggle-v2-private-inputs|orbit-c-private-checkpoints)", text),
                  f"Private dataset link: {relative}")
            check(not re.search(r"\]\([^)]*(?:^|[/\\])(?:private|secrets)/", text), f"Private artifact link: {relative}")
            check(not re.search(r"(?:sk-[A-Za-z0-9]{20,}|e2b_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9_.-]{24,})", text),
                  f"Credential-like value: {relative}")
            if path.suffix == ".py":
                ast.parse(text, filename=relative); counts["pythonAstParsed"] += 1
            elif path.suffix == ".json":
                json.loads(text); counts["jsonParsed"] += 1
            elif path.suffix == ".md":
                markdown_links(text, path, relative)
            elif path.suffix == ".ipynb":
                notebook = json.loads(text)
                check(notebook.get("nbformat") == 4 and isinstance(notebook.get("cells"), list), f"Notebook structure: {relative}")
                counts["notebooksChecked"] += 1
                for number, cell in enumerate(notebook.get("cells", [])):
                    check(cell.get("cell_type") in ("code", "markdown", "raw"), f"Notebook cell type: {relative}/{number}")
                    if cell.get("cell_type") == "markdown":
                        markdown_source = cell.get("source", "")
                        markdown_source = "".join(markdown_source) if isinstance(markdown_source, list) else markdown_source
                        markdown_links(markdown_source, path, relative)
                    if cell.get("cell_type") != "code":
                        continue
                    check(cell.get("outputs") == [] and cell.get("execution_count") is None, f"Stored execution/output: {relative}/{number}")
                    source = cell.get("source", "")
                    source = "".join(source) if isinstance(source, list) else source
                    tree = notebook_python(source, f"{relative}/cell-{number}")
                    counts["notebookCodeCellsParsed"] += 1
                    if relative.startswith("analysis-preparation/"):
                        for node in tree.body:
                            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "source_files" for target in node.targets):
                                embedded = json.loads(ast.literal_eval(node.value.args[0]))
                                for name, contents in embedded.items():
                                    ast.parse(contents, filename=f"{relative}/embedded/{name}")
                                    check(hashlib.sha256(contents.encode()).hexdigest() == sha(ROOT / "analysis-preparation" / name),
                                          f"Embedded source mismatch: {name}")
                                    counts["embeddedSourceHashesVerified"] += 1
        except (ValueError, SyntaxError, KeyError, OSError, TypeError, AttributeError) as error:
            errors.append(f"Static parse failed: {relative}: {type(error).__name__}")

    for entry in json.loads((ROOT / "evidence/export-manifest.json").read_text(encoding="utf-8"))["exports"]:
        check(sha(ROOT / entry["exportPath"]) == entry["exportSha256"], f"Export hash mismatch: {entry['exportPath']}")
        if entry.get("transformation", "").startswith("none"):
            check(entry["sourceSha256"] == entry["exportSha256"], f"Exact export provenance mismatch: {entry['exportPath']}")
        counts["exportHashesVerified"] += 1
    for entry in json.loads((ROOT / "pilot/provenance.json").read_text(encoding="utf-8"))["exports"]:
        check(sha(ROOT / "pilot" / entry["file"]) == entry["sha256"], f"Pilot provenance mismatch: {entry['file']}")
        counts["pilotHashesVerified"] += 1
    replay_provenance = ROOT / "harness/kaggle-replay/provenance.json"
    if replay_provenance.is_file():
        replay = json.loads(replay_provenance.read_text(encoding="utf-8"))
        for entry in replay.get("inputs", []):
            check(sha(ROOT / entry["path"]) == entry["sha256"], f"Replay input provenance mismatch: {entry['path']}")
            counts["newPreparationHashesVerified"] += 1
        for name, field in (("run_replay.py", "scriptSha256"), ("orbit-synthetic-replay.ipynb", "notebookSha256")):
            check(sha(replay_provenance.parent / name) == replay[field], f"Replay preparation mismatch: {name}")
            counts["newPreparationHashesVerified"] += 1
        replay_tree = ast.parse((replay_provenance.parent / "run_replay.py").read_text(encoding="utf-8"))
        embedded_files = ast.literal_eval(assignment(replay_tree, "FILES"))
        for relative, item in embedded_files.items():
            decoded = base64.b64decode(item["base64"], validate=True)
            check(hashlib.sha256(decoded).hexdigest() == item["sha256"] == sha(ROOT / relative),
                  f"Replay embedded bytes mismatch: {relative}")
            counts["embeddedReplayBytesVerified"] += 1
        replay_notebook = json.loads((replay_provenance.parent / "orbit-synthetic-replay.ipynb").read_text(encoding="utf-8"))
        for cell in replay_notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            source_tree = ast.parse(source)
            encoded_source = ast.literal_eval(assignment(source_tree, "source").args[0])
            check(hashlib.sha256(base64.b64decode(encoded_source, validate=True)).hexdigest() == replay["scriptSha256"],
                  "Replay notebook embedded script mismatch")
            counts["embeddedReplayBytesVerified"] += 1
    native_manifest = ROOT / "pilot/native-pass-fail/manifest.json"
    if native_manifest.is_file():
        native = json.loads(native_manifest.read_text(encoding="utf-8"))
        for name, expected in native.get("files", {}).items():
            check(sha(native_manifest.parent / name) == expected, f"Native preparation hash mismatch: {name}")
            counts["newPreparationHashesVerified"] += 1
        for path, field in ((ROOT / "pilot/task.py", "historicalTaskSha256"),
                            (ROOT / "pilot/orbit-kaggle-pilot.ipynb", "historicalNotebookSha256")):
            check(sha(path) == native[field], f"Native historical-source mismatch: {field}")
            counts["newPreparationHashesVerified"] += 1
        task_tree = ast.parse((native_manifest.parent / "task.py").read_text(encoding="utf-8"))
        contract_tree = ast.parse((native_manifest.parent / "contract.py").read_text(encoding="utf-8"))
        task_functions = {node.name: ast.dump(node) for node in task_tree.body if isinstance(node, ast.FunctionDef)}
        for node in contract_tree.body:
            if isinstance(node, ast.FunctionDef):
                check(task_functions.get(node.name) == ast.dump(node), f"Native embedded contract differs: {node.name}")
                counts["nativeContractFunctionsVerified"] += 1
        prompt = ast.literal_eval(assignment(task_tree, "PROMPT"))
        engine_bytes = base64.b64decode(ast.literal_eval(assignment(task_tree, "ENGINE_BYTES").args[0]), validate=True)
        check(hashlib.sha256(prompt.encode()).hexdigest() == native["historicalPromptSha256"], "Native prompt identity differs")
        check(hashlib.sha256(engine_bytes).hexdigest() == native["historicalEngineSha256"], "Native embedded engine identity differs")
        counts["newPreparationHashesVerified"] += 2
    analysis_directory = ROOT / "evidence/analysis-20261005"
    if analysis_directory.is_dir():
        for name, identity, archive_hash in (
                ("c-resumption-analysis.json", "0d433497a1e6fa7810c68a51709e821d204f3241707e39850e45b2ce6283ad85",
                 "55276f8c2d772d1c87caec867e0678a7d16d9eec2b97e09beea1ba471c0f3116"),
                ("c4-complement-analysis.json", "feb51fee0843163946fa85f39e1d450db5960a0375c9c989f60a55c86e433177",
                 "3d5ae48fb3900fe04eab8b2a625fee49301adf4d787a9f3079c2ec485ee8326b")):
            result = json.loads((analysis_directory / name).read_text(encoding="utf-8"))
            check(result["host"] == "Kaggle" and result["modelCallsDuringAnalysis"] == 0,
                  f"Analysis host/model-call scope differs: {name}")
            check(result["configurationSha256"] == identity and result["sourceArchiveSha256"] == archive_hash,
                  f"Analysis retained identity differs: {name}")
            counts["executedAnalysisScopeChecks"] += 2
        summary = json.loads((analysis_directory / "analysis-summary.json").read_text(encoding="utf-8"))
        check(summary["host"] == "Kaggle" and summary["modelCallsDuringAnalysis"] == 0
              and summary["pooledAsOneExecution"] is False and summary["realQuestionsPendingHuman"] == 24,
              "Analysis summary pooling/reference scope differs")
        counts["executedAnalysisScopeChecks"] += 1
    catalog = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
    catalog_paths = [entry["path"] for entry in catalog["artifacts"]]
    check(len(catalog_paths) == len(set(catalog_paths)), "Duplicate catalog paths")
    check(set(catalog_paths) == {path.relative_to(ROOT).as_posix() for path in files}, "Catalog public-file coverage mismatch")
    for entry in catalog["artifacts"]:
        check(not excluded(entry["path"]) and entry["path"] not in (CATALOG, RECEIPT), f"Catalog exclusion violation: {entry['path']}")
        check(sha(ROOT / entry["path"]) == entry["sha256"], f"Catalog hash mismatch: {entry['path']}")
        check(set(entry["tags"]).issubset(LABELS), f"Unknown catalog tag: {entry['path']}")
        counts["catalogHashesVerified"] += 1
    check((ROOT / ".gitattributes").read_text(encoding="utf-8").strip() == "* -text", "Frozen-byte Git attributes missing")
    ignore_lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    check(all(required in ignore_lines for required in ("private/", "outputs/", ".env", "secrets/")), "Required private ignore rule missing")
    git_check = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=False)
    if git_check.returncode == 0:
        tracked = set(filter(None, git_check.stdout.decode().split("\0")))
        for name in filter(None, tracked):
            check(not excluded(name), f"Private/excluded tracked file: {name}")
        expected_public = {path.relative_to(ROOT).as_posix() for path in files} | {CATALOG, RECEIPT}
        for name in sorted(expected_public - tracked):
            check(False, f"Public artifact not tracked: {name}")
        for name in sorted(tracked - expected_public):
            check(False, f"Tracked file missing from public inventory: {name}")
        tracking = "verified"
    else:
        tracking = "unavailable-not-a-git-repository"
        warnings.append("Tracked-file inventory is unavailable until Git is initialized; rerun before publication.")
    return {"format": "orbit-static-package-validation-v1", "observedAtUtc": datetime.now(timezone.utc).isoformat(),
            "state": "FAIL" if errors else "PASS_WITH_LIMITATION" if warnings else "PASS", "counts": counts,
            "errors": errors, "warnings": warnings, "trackedFileCheck": tracking,
            "pythonVersion": sys.version.split()[0], "benchmarkModulesImported": False,
            "benchmarkRunsExecuted": 0, "modelCalls": 0,
            "scope": "Static file, syntax, notebook-output, byte-provenance and public-boundary checks only."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-catalog", action="store_true", help="Regenerate artifact hashes after public edits settle.")
    parser.add_argument("--search", help="Print catalog entries whose tag or path contains this text; no checks run.")
    arguments = parser.parse_args()
    if arguments.search:
        catalog = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
        print(json.dumps([entry for entry in catalog["artifacts"] if arguments.search.lower() in
                         " ".join([entry["path"], *entry["tags"]]).lower()], indent=2))
        return
    files = public_files()
    if arguments.refresh_catalog:
        refresh_catalog(files)
    report = validate(files)
    (ROOT / RECEIPT).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / RECEIPT).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
