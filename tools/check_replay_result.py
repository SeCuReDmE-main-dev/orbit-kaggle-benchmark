"""Check an existing public replay result without executing an engine or model.

Exit 0 means the recorded rows and counters pass the frozen replay contract;
exit 1 means failed/incomplete checks; exit 2 means unreadable or invalid input.
This checks the reported observations, not the semantic validity of the engine.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ("baseline", "n", "p")
OPERATIONS = ("original", "order", "duplicate", "unrelated", "relation")
INPUT_HASHES = {
    "oracleSha256": "aabe0f8b121f32a5eda7795dfe730f70993829a30b18c1857974b5cdf4e6fcd0",
    "engineSha256": "230a5f494e64f86428aa3f26b6cfe6ab0d42c78d47f758419bfe76f7f22019ae",
    "relationEngineSha256": "d5da24352b213c55cede9559e2faa48b3b8451c57a3257b882c77ff82ee495a4",
}
METRICS = ("questions", "correct", "invariantsPassed", "invariantsTotal",
           "relationPassed", "relationTotal")


class InvalidResult(ValueError):
    """The supplied JSON cannot represent a replay result."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidResult("Duplicate JSON object key")
        result[key] = value
    return result


def _constant(_value):
    raise InvalidResult("Non-finite JSON number")


def read_json(path):
    data = path.read_bytes()
    if len(data) > 64 * 1024 * 1024:
        raise InvalidResult("Replay result exceeds 64 MiB")
    return json.loads(data, object_pairs_hook=_object, parse_constant=_constant)


def expected_rows():
    data = (ROOT / "harness/synthetic/reference-cases.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != INPUT_HASHES["oracleSha256"]:
        raise InvalidResult("Frozen reference corpus fingerprint mismatch")
    cases = json.loads(data)
    return {(case["id"], engine, operation): case["packet"]
            for case in cases for engine in ENGINES
            for operation in OPERATIONS
            if operation != "relation" or case["expected"].get("relation")}


def check_result(result):
    if not isinstance(result, dict) or not isinstance(result.get("rows"), list):
        raise InvalidResult("Expected a replay object with a rows array")
    summary = result.get("summary")
    if not isinstance(summary, dict):
        raise InvalidResult("Expected a per-engine summary object")
    errors = []
    if result.get("format") != "orbit-benchmark-results-v1" or result.get("suite") != "A":
        errors.append("Unexpected replay format or suite")
    for field, expected in INPUT_HASHES.items():
        if result.get(field) != expected:
            errors.append("Input fingerprint differs: " + field)
    expected = expected_rows()
    seen = set()
    counters = {engine: Counter({metric: 0 for metric in METRICS}) for engine in ENGINES}
    failed = []
    for index, row in enumerate(result["rows"]):
        if (not isinstance(row, dict)
                or any(not isinstance(row.get(key), str) for key in ("caseId", "engine", "operation"))
                or type(row.get("packet")) is not int
                or type(row.get("pass")) is not bool
                or type(row.get("ok")) is not bool):
            raise InvalidResult(f"Invalid row structure or Boolean at index {index}")
        key = (row["caseId"], row["engine"], row["operation"])
        if key in seen:
            errors.append(f"Duplicate row identity at index {index}")
        seen.add(key)
        if key not in expected:
            errors.append(f"Unexpected row identity at index {index}")
            continue
        if row["packet"] != expected[key]:
            errors.append(f"Incorrect packet at index {index}")
        if row["pass"] and not row["ok"]:
            errors.append(f"Passing row reports an engine error at index {index}")
        if not row["pass"]:
            failed.append({"caseId": key[0], "engine": key[1], "operation": key[2]})
        counts = counters[row["engine"]]
        total, passed = (("questions", "correct") if row["operation"] == "original"
                         else ("relationTotal", "relationPassed") if row["operation"] == "relation"
                         else ("invariantsTotal", "invariantsPassed"))
        counts[total] += 1
        counts[passed] += int(row["pass"])
    if set(expected) != seen or len(result["rows"]) != 486:
        errors.append("Incomplete or extra replay rows; expected the 486 frozen identities")
    if set(summary) != set(ENGINES):
        errors.append("Summary must contain exactly baseline, n and p")
    for engine, counts in counters.items():
        reported = summary.get(engine)
        if not isinstance(reported, dict):
            errors.append("Missing summary for " + engine)
            continue
        if set(reported) != set(METRICS) or any(type(value) is not int for value in reported.values()):
            raise InvalidResult("Invalid summary counters for " + engine)
        if reported != dict(counts):
            errors.append("Summary differs from recomputed rows for " + engine)
        if any(counts[metric] != count for metric, count in
               (("questions", 36), ("invariantsTotal", 108), ("relationTotal", 18))):
            errors.append("Coverage differs for " + engine)
    if failed:
        errors.append("Recorded replay checks failed")
    return {"status": "failed" if errors else "passed", "errors": errors,
            "failures": failed, "summary": {k: dict(v) for k, v in counters.items()},
            "rowsChecked": len(result["rows"]), "benchmarkRunsExecuted": 0, "modelCalls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Existing synthetic-replay.json to inspect")
    args = parser.parse_args(argv)
    try:
        report = check_result(read_json(args.result))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "invalid-input", "errorType": type(error).__name__,
                          "benchmarkRunsExecuted": 0, "modelCalls": 0}))
        return 2
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
