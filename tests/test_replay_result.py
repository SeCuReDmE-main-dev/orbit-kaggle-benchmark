"""Result-reader regression checks; no engine/model execution or private inputs."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("replay_checker", ROOT / "tools/check_replay_result.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def valid_result():
    rows = [{"caseId": case, "engine": engine, "operation": operation, "packet": packet,
             "ok": True, "pass": True}
            for (case, engine, operation), packet in checker.expected_rows().items()]
    return {"format": "orbit-benchmark-results-v1", "suite": "A", **checker.INPUT_HASHES,
            "rows": rows, "summary": {engine: {"questions": 36, "correct": 36,
            "invariantsPassed": 108, "invariantsTotal": 108,
            "relationPassed": 18, "relationTotal": 18} for engine in checker.ENGINES}}


class ReplayResultTests(unittest.TestCase):
    def test_complete_recorded_result_passes(self):
        result = checker.check_result(valid_result())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["rowsChecked"], 486)
        self.assertEqual(result["modelCalls"], 0)

    def test_retained_public_result_passes_without_rerunning(self):
        result = checker.read_json(ROOT / "evidence/replay-20261005/synthetic-replay.json")
        self.assertEqual(checker.check_result(result)["status"], "passed")

    def test_failed_row_cannot_hide_behind_passing_summary(self):
        result = valid_result()
        result["rows"][0]["pass"] = False
        report = checker.check_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["failures"]), 1)
        self.assertTrue(any("recomputed" in error for error in report["errors"]))

    def test_consistent_failed_summary_still_fails(self):
        result = valid_result()
        result["rows"][0]["pass"] = False
        result["summary"]["baseline"]["correct"] -= 1
        self.assertEqual(checker.check_result(result)["status"], "failed")

    def test_duplicate_identity_cannot_replace_missing_row(self):
        result = valid_result()
        result["rows"][1] = copy.deepcopy(result["rows"][0])
        self.assertEqual(len(result["rows"]), 486)
        self.assertTrue(any("Duplicate" in error for error in checker.check_result(result)["errors"]))

    def test_missing_extra_or_unknown_rows_fail(self):
        for change in (lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[0])),
                       lambda rows: rows[0].update(caseId="unrecognized-case"),
                       lambda rows: rows[0].update(packet=999)):
            with self.subTest(change=change):
                result = valid_result()
                change(result["rows"])
                self.assertEqual(checker.check_result(result)["status"], "failed")

    def test_real_booleans_required(self):
        for field in ("pass", "ok"):
            for bad in (1, 0, "true", None):
                with self.subTest(field=field, bad=bad):
                    result = valid_result()
                    result["rows"][0][field] = bad
                    with self.assertRaises(checker.InvalidResult):
                        checker.check_result(result)

    def test_engine_error_cannot_be_recorded_as_pass(self):
        result = valid_result()
        result["rows"][0]["ok"] = False
        self.assertEqual(checker.check_result(result)["status"], "failed")

    def test_summary_engine_set_and_counters_checked(self):
        result = valid_result()
        del result["summary"]["p"]
        self.assertEqual(checker.check_result(result)["status"], "failed")
        result = valid_result()
        result["summary"]["p"]["correct"] = 35
        self.assertEqual(checker.check_result(result)["status"], "failed")
        result["summary"]["p"]["correct"] = True
        with self.assertRaises(checker.InvalidResult):
            checker.check_result(result)

    def test_wrong_input_fingerprint_fails(self):
        result = valid_result()
        result["oracleSha256"] = "0" * 64
        self.assertEqual(checker.check_result(result)["status"], "failed")

    def test_cli_exit_codes_and_no_input_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            for payload, code in ((json.dumps(valid_result()), 0),
                                  (json.dumps({**valid_result(), "rows": []}), 1),
                                  ("{malformed", 2), ("{\"rows\":[],\"rows\":[]}", 2),
                                  ("{\"rows\":[],\"value\":NaN}", 2)):
                path.write_text(payload, encoding="utf-8")
                before = path.read_bytes()
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(checker.main([str(path)]), code)
                self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
