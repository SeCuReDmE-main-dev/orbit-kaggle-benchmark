"""Result-reader regression checks; no engine/model execution or private inputs."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("replay_checker", ROOT / "tools/check_replay_result.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def valid_result():
    return checker.read_json(ROOT / "evidence/replay-20261005/synthetic-replay.json")


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
        self.assertEqual(len(report["failures"]), 0)  # Payload passes; its recorded flag was falsified.
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

    def test_forged_original_decision_or_origins_cannot_pass(self):
        for field, value, summary_field in (("decision", "HOLD", "decision"),
                                           ("independentSources", 99, "origins")):
            with self.subTest(field=field):
                result = valid_result()
                result["rows"][0]["result"][0][field] = value
                result["rows"][0]["summary"][summary_field] = value
                report = checker.check_result(result)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["summary"]["baseline"]["correct"], 35)

    def test_metamorphic_payload_is_compared_to_recorded_original(self):
        for operation in ("order", "duplicate", "unrelated"):
            with self.subTest(operation=operation):
                result = valid_result()
                row = next(x for x in result["rows"] if x["operation"] == operation)
                row["result"][0]["truth"] = []
                row["summary"]["T"] = 0
                report = checker.check_result(result)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["summary"]["baseline"]["invariantsPassed"], 107)

    def test_relation_payload_cannot_hide_behind_true_flag(self):
        result = valid_result()
        row = next(x for x in result["rows"] if x["operation"] == "relation")
        for item in row["result"]:
            item.update(kind="none", kinds=[])
        report = checker.check_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["baseline"]["relationPassed"], 17)

    def test_malformed_result_payloads_rejected(self):
        for payload in (None, "invaliddata", {}, ["invaliddata"], []):
            with self.subTest(payload=payload):
                result = valid_result()
                result["rows"][0]["result"] = payload
                with self.assertRaises(checker.InvalidResult):
                    checker.check_result(result)

    def test_forged_row_summary_rejected(self):
        result = valid_result()
        result["rows"][0]["summary"]["T"] = 99
        self.assertEqual(checker.check_result(result)["status"], "failed")

    def test_row_order_does_not_change_recorded_semantics(self):
        result = valid_result()
        result["rows"].reverse()
        self.assertEqual(checker.check_result(result)["status"], "passed")

    def test_result_size_limit_bounds_the_read_itself(self):
        source = MagicMock()
        source.open.return_value.__enter__.return_value.read.return_value = b"x" * 65
        with patch.object(checker, "MAX_RESULT_BYTES", 64, create=True):
            with self.assertRaises(checker.InvalidResult):
                checker.read_json(source)
        source.open.assert_called_once_with("rb")
        source.open.return_value.__enter__.return_value.read.assert_called_once_with(65)
        source.read_bytes.assert_not_called()

    def test_deep_json_is_a_controlled_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text("[" * 1200 + "0" + "]" * 1200, encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(checker.main([str(path)]), 2)
            self.assertEqual(json.loads(output.getvalue())["status"], "invalid-input")

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
