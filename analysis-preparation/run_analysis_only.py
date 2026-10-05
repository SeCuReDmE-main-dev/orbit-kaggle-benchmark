"""Kaggle-only analysis of two retained identities; no model or network calls.

Supply private attached input paths at runtime. This source contains no private
dataset identifiers, answers, snapshots or operational credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

import analyze_kaggle_campaign_results as analysis
from orbit_campaign_checkpoint import campaign_identity, digest

C_ID = "0d433497a1e6fa7810c68a51709e821d204f3241707e39850e45b2ce6283ad85"
C4_ID = "feb51fee0843163946fa85f39e1d450db5960a0375c9c989f60a55c86e433177"
C_ARCHIVE_SHA = "55276f8c2d772d1c87caec867e0678a7d16d9eec2b97e09beea1ba471c0f3116"
C4_ARCHIVE_SHA = "3d5ae48fb3900fe04eab8b2a625fee49301adf4d787a9f3079c2ec485ee8326b"
CORPUS_SHA = "c8d7f865ba2c9667f43759a053174e3250150704746141e52fc0dca236190f5a"
GOLD_SHA = "a0fffdf104aa36b3e994c57902ffc7a76f2d1a1fd143cc821ca60a4c88e93b23"
ANALYZER_SHA = "1ae7a80aaf7fcfbec2e1121af6a73f30777b26976400308bedb7d5e30ecc21d3"
EXTRACTION_KEY = "3c3161accc4df1068312b3d1395c5017bdee9fe3a4c7223ceeb290c855113196"
EXTRACTION_RAW_SHA = "6fc132ef4784e4345e09d87f5b94fc7989f3d871d4b9a986211d8807ab6731bb"


def private_input(variable):
    path = Path(os.environ[variable]).resolve()
    if not path.is_relative_to(Path("/kaggle/input")) or not path.is_file():
        raise RuntimeError("PRIVATE_ATTACHED_INPUT_REQUIRED")
    return path


def verified_json(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("INPUT_FINGERPRINT_MISMATCH")
    return json.loads(data)


def open_archive(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError("ARCHIVE_FINGERPRINT_MISMATCH")
    archive = zipfile.ZipFile(path)
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError("DUPLICATE_ARCHIVE_MEMBER")
    if sum(item.file_size for item in archive.infolist()) > 100_000_000:
        raise RuntimeError("ARCHIVE_EXPANSION_BOUND_EXCEEDED")
    for name in names:
        parts = PurePosixPath(name).parts
        if name.startswith("/") or "\\" in name or ".." in parts or ":" in name:
            raise RuntimeError("UNSAFE_ARCHIVE_MEMBER")
    return archive


def projected_ledger(archive, prefix, identity, directory):
    """Retain only numeric usage and categorical answers in temporary files."""
    rows = []
    for name in archive.namelist():
        relative = name.removeprefix(prefix + "/")
        if not name.startswith(prefix + "/") or not relative.endswith(".json"):
            continue
        row = json.loads(archive.read(name))
        if row.get("suite") != "C" or row.get("configurationSha256") != identity:
            continue
        result = row.get("result") or {}
        projection = {key: row.get(key) for key in (
            "key", "configurationSha256", "campaignId", "suite", "parameters",
            "attempt", "state", "observedAtUnix")}
        usage = result.get("usage")
        safe_usage = ({key: value for key, value in usage.items()
                       if key in ("observedAtUnix", "input_tokens", "output_tokens",
                                  "input_tokens_cost_nanodollars", "output_tokens_cost_nanodollars",
                                  "total_backend_latency_ms")}
                      if isinstance(usage, dict) else None)
        safe_result = {"status": result.get("status"), "usage": safe_usage}
        safe_result["answer"] = {"results": [
            {"questionId": value.get("questionId"), "decision": value.get("decision")}
            for value in (result.get("answer") or {}).get("results", [])
            if isinstance(value, dict)
        ]}
        projection["result"] = safe_result
        rows.append(projection)
    current = {}
    for row in rows:
        key = row["key"]
        if not isinstance(key, str) or not isinstance(row["attempt"], int):
            raise RuntimeError("CHECKPOINT_IDENTITY_REQUIRED")
        rank = (row["attempt"], row.get("observedAtUnix") or 0)
        if key not in current or rank > current[key][0]:
            current[key] = (rank, row)
    (directory / "attempts").mkdir(parents=True)
    for index, row in enumerate(rows):
        (directory / "attempts" / f"{index}.json").write_text(json.dumps(row), encoding="utf-8")
    for key, (_, row) in current.items():
        (directory / f"{key}.json").write_text(json.dumps(row), encoding="utf-8")
    return [row for _, row in current.values()]


def run():
    if not Path("/kaggle/working").is_dir():
        raise RuntimeError("KAGGLE_ANALYSIS_REQUIRED")
    if hashlib.sha256(Path(analysis.__file__).read_bytes()).hexdigest() != ANALYZER_SHA:
        raise RuntimeError("ANALYZER_SOURCE_MISMATCH")
    config = json.loads(private_input("ORBIT_C_CONFIG").read_bytes())
    if campaign_identity(config) != C_ID:
        raise RuntimeError("C_CONFIGURATION_MISMATCH")
    public = verified_json(private_input("ORBIT_PUBLIC_INPUT"), CORPUS_SHA)
    gold = verified_json(private_input("ORBIT_PRIVATE_GOLD"), GOLD_SHA)
    if len(public["questions"]) != 60 or len(gold) != 36:
        raise RuntimeError("REFERENCE_SCOPE_MISMATCH")
    output = Path("/kaggle/working/orbit-analysis-public")
    output.mkdir(exist_ok=True)
    with open_archive(private_input("ORBIT_C_ARCHIVE"), C_ARCHIVE_SHA) as parent_archive, \
         open_archive(private_input("ORBIT_C4_ARCHIVE"), C4_ARCHIVE_SHA) as complement_archive, \
         tempfile.TemporaryDirectory(prefix="orbit-analysis-", dir="/kaggle/temp") as temporary:
        extraction = json.loads(parent_archive.read(f"orbit-campaign-v2/C/{EXTRACTION_KEY}.json"))
        if (extraction.get("configurationSha256") != C_ID or extraction.get("state") != "completed"
                or hashlib.sha256(extraction["result"]["raw"].encode()).hexdigest() != EXTRACTION_RAW_SHA):
            raise RuntimeError("SHARED_EXTRACTION_MISMATCH")
        c4_config = json.loads(complement_archive.read("complement-manifest.json"))
        if campaign_identity(c4_config) != C4_ID:
            raise RuntimeError("C4_CONFIGURATION_MISMATCH")
        if c4_config["complement"]["parentConfigurationSha256"] != C_ID:
            raise RuntimeError("C4_PARENT_MISMATCH")
        c_directory, c4_directory = Path(temporary) / "C", Path(temporary) / "C4"
        c_directory.mkdir(); c4_directory.mkdir()
        projected_ledger(parent_archive, "orbit-campaign-v2/C", C_ID, c_directory)
        c4_rows = projected_ledger(complement_archive, "C", C4_ID, c4_directory)
        c_result = analysis.analyze_c(config, public, gold, c_directory)
        if (c_result["execution"]["observedExtractions"] != 60
                or c_result["execution"]["observedProductions"] != 236
                or c_result["execution"]["completedPackets"] != 59):
            raise RuntimeError("C_RECEIPT_COVERAGE_MISMATCH")
        target = c4_config["complement"]["target"]
        for row in c4_rows:
            if any(row["parameters"].get(key) != value for key, value in target.items()):
                raise RuntimeError("C4_OUTSIDE_DECLARED_TARGET")
        c4_base = analysis.analyze_c(c4_config, public, gold, c4_directory)
        if (c4_base["execution"]["observedProductions"] != 4
                or c4_base["execution"]["completedPackets"] != 1):
            raise RuntimeError("C4_RECEIPT_COVERAGE_MISMATCH")
        if len([question for question in public["questions"]
                if question["packet"] == target["packet"] and question["id"] in gold]) != 6:
            raise RuntimeError("C4_REFERENCE_SCOPE_MISMATCH")
        c4_metrics = []
        for metric in c4_base["metrics"]:
            if metric["model"] != target["model"]:
                continue
            scoped_counts = {key: value for key, value in metric["counts"].items()
                             if key not in ("missingProductions", "neverRunProductions",
                                            "failedProductions", "inProgressProductions",
                                            "uninterpretedProductions")}
            c4_metrics.append({"model": metric["model"], "condition": metric["condition"],
                               "counts": scoped_counts, "confusion": metric["confusion"],
                               "syntheticAccuracyObserved": metric["syntheticAccuracyObserved"],
                               "plannedProductionsWithinComplement": 1,
                               "plannedSyntheticDecisionsWithinComplement": 6,
                               "completeWithinComplement": scoped_counts.get("observedProductions") == 1})
        c4_result = {"format": "orbit-c4-analysis-v1", "host": "Kaggle",
                     "modelCallsDuringAnalysis": 0, "configurationSha256": C4_ID,
                     "parentConfigurationSha256": C_ID, "target": target,
                     "execution": {"newExtractions": 0, "productions": 4, "completedPackets": 1},
                     "metrics": c4_metrics, "observedCosts": c4_base["observedCosts"],
                     "limitations": ["One synthetic packet; no standalone population-level comparison.",
                                     "Separate complement identity; not pooled into historical C."]}
        c_result["sourceArchiveSha256"] = C_ARCHIVE_SHA
        c4_result["sourceArchiveSha256"] = C4_ARCHIVE_SHA
        (output / "c-resumption-analysis.json").write_text(json.dumps(c_result, indent=2) + "\n")
        (output / "c4-complement-analysis.json").write_text(json.dumps(c4_result, indent=2) + "\n")
        summary = {"host": "Kaggle", "modelCallsDuringAnalysis": 0, "pooledAsOneExecution": False,
                   "C": c_result["execution"], "C4": c4_result["execution"],
                   "realQuestionsPendingHuman": 24,
                   "accuracyByIdentity": {"C": [
                       {key: metric[key] for key in ("model", "condition", "syntheticAccuracyObserved", "counts")}
                       for metric in c_result["metrics"]], "C4": c4_metrics}}
        (output / "analysis-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run()
