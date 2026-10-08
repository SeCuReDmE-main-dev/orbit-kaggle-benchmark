"""Pure regression tests. Providers, SDK assertions and engine processes are doubles."""
import ast
import copy
from contextvars import ContextVar
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "pilot/native-pass-fail-hardened"
CONTRACT = runpy.run_path(str(DIRECTORY / "contract.py"), run_name="pure_contract_test")
BUILDER = runpy.run_path(str(ROOT / "tools/build_native_pilot_hardened.py"), run_name="pure_builder_test")
TASK = (DIRECTORY / "task.py").read_text(encoding="utf-8")
TREE = ast.parse(TASK)
ASSIGNMENTS = {n.targets[0].id: n for n in TREE.body if isinstance(n, ast.Assign)
               and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
PUBLIC = json.loads(ast.literal_eval(ASSIGNMENTS["PUBLIC"].value.args[0]))
GOLD = json.loads(ast.literal_eval(ASSIGNMENTS["GOLD"].value.args[0]))


def fixture():
    # Structural fixture only. Fake engine results never claim semantic validation.
    return {"results": [{"questionId": q["id"], "decision": GOLD[q["id"]],
        "evidence": [{"sourceId": "d01", "quote": PUBLIC["documents"][0]["text"],
                      "relation": "contextualizes"}], "excluded": [], "uncertainties": [],
        "justification": "Synthetic structural unit fixture."} for q in PUBLIC["questions"]]}


def runtime():
    env = dict(CONTRACT)
    env.update({"json": json, "math": math, "Path": Path, "re": re, "uuid": uuid,
                "hashlib": hashlib, "sys": sys, "CAMPAIGN_ID": BUILDER["CAMPAIGN_ID"],
                "_ATTEMPT_CAPTURE": ContextVar("test_attempt_capture", default=None),
                "PUBLIC": PUBLIC, "GOLD": GOLD,
                "PROMPT": ast.literal_eval(ASSIGNMENTS["PROMPT"].value),
                "ENGINE_SHA256": ast.literal_eval(ASSIGNMENTS["ENGINE_SHA256"].value),
                "ENGINE_PATH": Path("fake-engine-not-executed"), "NODE": "fake-node-not-executed",
                "node_version": "v22.20.0", "NODE_SOURCE": "system-path",
                "kbench": SimpleNamespace(assertions=SimpleNamespace(assert_true=Mock(), assert_equal=Mock()))})
    definitions = []
    for node in copy.deepcopy(TREE.body):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            node.decorator_list = []
            definitions.append(node)
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "<selected-pure-task-definitions>", "exec"), env)

    def fake_engine(*args, **kwargs):
        requests = [json.loads(line) for line in kwargs["input"].splitlines()]
        results = [{"ok": True, "result": [{"claimId": r["dossier"]["id"],
                    "decision": GOLD[r["dossier"]["id"]]}]} for r in requests]
        return SimpleNamespace(returncode=0, stdout="\n".join(json.dumps(r) for r in results))

    env["subprocess"] = SimpleNamespace(run=Mock(side_effect=fake_engine))
    env["_save_diagnostics"] = Mock()
    env["_report_diagnostic_failure"] = Mock()
    return env


class ContractTests(unittest.TestCase):
    def assert_invalid_json(self, text):
        with self.assertRaises(CONTRACT["InvalidModelOutput"]):
            CONTRACT["parse_answer"](text)

    def test_plain_and_fenced_json(self):
        for text in ('{"results":[]}', '```json\n{"results":[]}\n```', '```\n{"results":[]}\n```'):
            self.assertEqual(CONTRACT["parse_answer"](text), {"results": []})

    def test_bad_json_fences_duplicates_and_constants(self):
        for text in ("", " ", "```js\n{}\n```", "```json\n{}", '{"a":1,"a":2}',
                     '{"a":', '{"a":NaN}', '{"a":Infinity}', '{"a":1e9999}'):
            with self.subTest(text=text):
                self.assert_invalid_json(text)

    def test_large_integer_is_invalid_not_technical(self):
        self.assert_invalid_json('{"results":' + "9" * 5000 + "}")

    def test_decoder_value_error_is_normalized(self):
        with patch.object(CONTRACT["json"], "loads", side_effect=ValueError("decoder cap")):
            self.assert_invalid_json("{}")

    def test_utf8_byte_boundary_and_nonencodable_raw_text(self):
        limit = CONTRACT["MAX_RESPONSE_BYTES"]
        boundary = '"' + "é" * ((limit - 2) // 2) + '"'
        self.assertEqual(len(boundary.encode("utf-8")), limit)
        self.assertIsInstance(CONTRACT["parse_answer"](boundary), str)
        self.assert_invalid_json(boundary[:-1] + "é\"")
        self.assert_invalid_json('"\ud800"')

    def test_six_rows_and_required_fields(self):
        for mutation in (lambda a: a["results"].pop(),
                         lambda a: a["results"][0].pop("uncertainties"),
                         lambda a: a["results"][0].update(questionId="unknown"),
                         lambda a: a["results"][0].update(questionId="q02")):
            answer = fixture(); mutation(answer)
            result = CONTRACT["validate_answer"](answer, PUBLIC, GOLD)
            self.assertFalse(result["valid"])
            self.assertEqual(result["outcome"], "invalid-model-output")

    def test_evidence_shape_and_source_claims_are_distinct(self):
        for key, value, expected in (("sourceId", 42, "invalid-model-output"),
                                     ("sourceId", None, "invalid-model-output"),
                                     ("sourceId", "missing", "contract-fail"),
                                     ("quote", "", "invalid-model-output"),
                                     ("quote", "not present", "contract-fail"),
                                     ("relation", "maybe", "invalid-model-output")):
            with self.subTest(key=key, value=value):
                answer = fixture(); answer["results"][0]["evidence"][0][key] = value
                self.assertEqual(CONTRACT["validate_answer"](answer, PUBLIC, GOLD)["outcome"], expected)

    def test_scope_bounds_match_engine(self):
        for key, maximum in (("subject", 300), ("property", 300), ("value", 1000), ("mode", 500)):
            for size, valid in ((maximum, True), (maximum + 1, False)):
                with self.subTest(key=key, size=size):
                    answer = fixture()
                    scope = {"subject": "Aster", "property": "supported", "value": "yes", key: "x" * size}
                    answer["results"][0]["evidence"][0]["scope"] = scope
                    self.assertEqual(CONTRACT["validate_answer"](answer, PUBLIC, GOLD)["valid"], valid)

    def test_quote_bound_independent_of_literal_presence(self):
        for size, expected in ((2000, "pass"), (2001, "invalid-model-output")):
            public = copy.deepcopy(PUBLIC); public["documents"][0]["text"] = "x" * size
            answer = fixture()
            for row in answer["results"]:
                row["evidence"][0]["quote"] = "x" * size
            self.assertEqual(CONTRACT["validate_answer"](answer, public, GOLD)["outcome"], expected)

    def test_scope_bound_uses_javascript_utf16_units(self):
        for count, valid in ((150, True), (151, False)):
            answer = fixture()
            answer["results"][0]["evidence"][0]["scope"] = {
                "subject": "\U0001f600" * count, "property": "supported", "value": "yes"}
            self.assertEqual(CONTRACT["validate_answer"](answer, PUBLIC, GOLD)["valid"], valid)

    def test_incorrect_decision_preserves_valid_shape(self):
        answer = fixture(); answer["results"][0]["decision"] = "HOLD"
        result = CONTRACT["validate_answer"](answer, PUBLIC, GOLD)
        self.assertTrue(result["valid"])
        self.assertEqual(result["outcome"], "contract-fail")

    def test_required_text_uses_ecmascript_trim_not_python_whitespace(self):
        # ECMA-262 WhiteSpace + LineTerminator, then characters it does not trim.
        trimmed = [0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0xA0, 0x1680,
                   *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF]
        retained = [0x1C, 0x1D, 0x1E, 0x1F, 0x85, 0x180E, 0x200B, 0x2060]
        for codepoint, valid in [(cp, False) for cp in trimmed] + [(cp, True) for cp in retained]:
            with self.subTest(codepoint=hex(codepoint)):
                value = chr(codepoint)
                self.assertEqual(CONTRACT["_text"](value, 300), valid)
                self.assertTrue(CONTRACT["_text"](value + "x" + value, 300))
                for field in ("subject", "property", "value"):
                    answer = fixture()
                    answer["results"][0]["evidence"][0]["scope"] = {
                        "subject": "Aster", "property": "supported", "value": "yes", field: value}
                    result = CONTRACT["validate_answer"](answer, PUBLIC, GOLD)
                    self.assertEqual(result["valid"], valid)
                    self.assertEqual(result["outcome"], "pass" if valid else "invalid-model-output")
        self.assertFalse(CONTRACT["_text"](" x ", 2))  # Original length is still bounded.


class RuntimeTests(unittest.TestCase):
    def test_report_records_runtime_version_and_explicit_source_without_local_path(self):
        for source, version in (("system-path", "v20.0.0"), ("verified-official-archive", "v22.20.0")):
            with self.subTest(source=source):
                env = runtime()
                env["NODE_SOURCE"] = source
                env["node_version"] = version
                env["NODE"] = "C:/private-fixture/node.exe"
                llm = SimpleNamespace(name="fake", prompt=Mock(return_value='{"results":[]}'))
                self.assertIs(env["orbit_native_pass_fail_hardened"](llm), False)
                report = env["_save_diagnostics"].call_args.args[0]
                self.assertEqual(report.get("nodeSource"), source)
                self.assertEqual(report.get("nodeVersion"), version)
                self.assertNotIn(env["NODE"], json.dumps(report))
                env["subprocess"].run.assert_not_called()

    def test_feff_only_scope_is_invalid_before_engine_dispatch(self):
        env = runtime(); answer = fixture()
        answer["results"][0]["evidence"][0]["scope"] = {
            "subject": "\ufeff", "property": "supported", "value": "yes"}
        llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(answer)))
        self.assertIs(env["orbit_native_pass_fail_hardened"](llm), False)
        self.assertEqual(env["_save_diagnostics"].call_args.args[0]["outcome"], "invalid-model-output")
        env["subprocess"].run.assert_not_called()
        llm.prompt.assert_called_once()

    def test_true_and_false_results_each_use_one_provider_attempt(self):
        for answer, outcome, expected in ((fixture(), "pass", True),
                    ({"results": []}, "invalid-model-output", False)):
            env = runtime(); llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(answer)))
            self.assertIs(env["orbit_native_pass_fail_hardened"](llm), expected)
            llm.prompt.assert_called_once()
            report = env["_save_diagnostics"].call_args.args[0]
            self.assertEqual(report["outcome"], outcome)
            self.assertEqual(report["providerAttempts"], 1)

    def test_wrong_decision_does_not_become_technical_error(self):
        env = runtime(); answer = fixture(); answer["results"][0]["decision"] = "HOLD"
        llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(answer)))
        self.assertIs(env["orbit_native_pass_fail_hardened"](llm), False)
        self.assertEqual(env["_save_diagnostics"].call_args.args[0]["outcome"], "contract-fail")

    def test_provider_error_preserved_even_if_diagnostics_fail(self):
        for diagnostic_failure in (False, True):
            env = runtime(); original = TimeoutError("synthetic provider failure")
            llm = SimpleNamespace(name="fake", prompt=Mock(side_effect=original))
            if diagnostic_failure:
                env["_save_diagnostics"].side_effect = OSError("synthetic storage failure")
            with self.assertRaises(TimeoutError) as context:
                env["orbit_native_pass_fail_hardened"](llm)
            self.assertIs(context.exception, original)
            llm.prompt.assert_called_once()
            self.assertEqual(env["_save_diagnostics"].call_args.args[0]["outcome"], "technical-error")

    def test_diagnostic_failure_retains_computed_result_and_forbids_retry(self):
        for answer, expected in ((fixture(), True), ({"results": []}, False)):
            env = runtime(); env["_save_diagnostics"].side_effect = OSError("storage fixture")
            llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(answer)))
            with self.assertRaises(env["DiagnosticPersistenceError"]) as context:
                env["orbit_native_pass_fail_hardened"](llm)
            self.assertIs(context.exception.computedResult, expected)
            self.assertFalse(context.exception.retryEligible)
            self.assertEqual(context.exception.phase, "diagnostics")

    def test_engine_process_protocol_and_incomplete_output_are_technical(self):
        responses = (SimpleNamespace(returncode=1, stdout=""),
                     SimpleNamespace(returncode=0, stdout="not-json"),
                     SimpleNamespace(returncode=0, stdout="{}"),
                     SimpleNamespace(returncode=0, stdout="\n".join(['{"ok":1}'] * 18)))
        for response in responses:
            env = runtime(); env["subprocess"].run = Mock(return_value=response)
            llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(fixture())))
            with self.assertRaises(RuntimeError):
                env["orbit_native_pass_fail_hardened"](llm)
            llm.prompt.assert_called_once()
            self.assertEqual(env["_save_diagnostics"].call_args.args[0]["outcome"], "technical-error")

    def test_next_model_attempted_once_after_failure(self):
        env = runtime(); env["SELECTED_MODELS"] = ["first", "second"]
        env["kbench"].llms = {"first": "fake-a", "second": "fake-b"}
        run = Mock(side_effect=[TimeoutError("fixture"), SimpleNamespace(result=False)])
        env["orbit_native_pass_fail_hardened"] = SimpleNamespace(run=run)
        result = env["run_planned_models"]()
        self.assertEqual(run.call_count, 2)
        self.assertEqual([r["state"] for r in result], ["technical-error", "completed"])
        self.assertIs(result[1]["result"], False)
        self.assertIsNone(env["_ATTEMPT_CAPTURE"].get())

    def test_sdk_swallowed_diagnostic_error_retains_verdict_without_cache_leak(self):
        # SDK 0.6.1 Task.run executes self.func synchronously. At root with
        # continue_with_exceptions it can return a FAILED sentinel after swallowing
        # the exception. Its cache path returns without calling the task at all.
        for answer, expected in ((fixture(), True), ({"results": []}, False)):
            env = runtime()
            function = env["orbit_native_pass_fail_hardened"]
            llm = SimpleNamespace(name="same-model", prompt=Mock(return_value=json.dumps(answer)))
            env["SELECTED_MODELS"] = ["first", "cached-second"]
            env["kbench"].llms = {"first": llm, "cached-second": llm}
            env["_save_diagnostics"].side_effect = OSError("synthetic receipt failure")
            failed_sentinel = object()
            calls = []

            def sdk_run_double(model):
                calls.append(model)
                if len(calls) == 2:
                    return SimpleNamespace(result=False, status="SUCCESS", cached=True)
                try:
                    return SimpleNamespace(result=function(model), status="SUCCESS", cached=False)
                except Exception:
                    return SimpleNamespace(result=failed_sentinel, status="FAILED", cached=False)

            env["orbit_native_pass_fail_hardened"] = SimpleNamespace(run=sdk_run_double)
            observations = env["run_planned_models"]()
            self.assertEqual(observations[0]["state"], "technical-error")
            self.assertIs(observations[0]["computedResult"], expected)
            self.assertEqual(observations[0]["computedOutcome"], "pass" if expected else "invalid-model-output")
            self.assertEqual(observations[0]["technicalPhase"], "diagnostics")
            self.assertFalse(observations[0]["retryEligible"])
            self.assertEqual(observations[1]["state"], "completed")
            self.assertNotIn("computedResult", observations[1])
            self.assertIsNone(env["_ATTEMPT_CAPTURE"].get())
            self.assertEqual(len(calls), 2)
            llm.prompt.assert_called_once()

    def test_sdk_swallowed_primary_errors_keep_phase_even_when_storage_fails(self):
        for phase, error_type in (("provider", "TimeoutError"), ("engine", "RuntimeError")):
            for storage_failure in (False, True):
                with self.subTest(phase=phase, storage_failure=storage_failure):
                    env = runtime()
                    function = env["orbit_native_pass_fail_hardened"]
                    llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(fixture())))
                    if phase == "provider":
                        llm.prompt.side_effect = TimeoutError("synthetic provider failure")
                    else:
                        env["subprocess"].run.return_value = SimpleNamespace(returncode=1, stdout="")
                        env["subprocess"].run.side_effect = None
                    if storage_failure:
                        env["_save_diagnostics"].side_effect = OSError("synthetic storage failure")
                    env["SELECTED_MODELS"] = ["only"]
                    env["kbench"].llms = {"only": llm}
                    failed_sentinel = object()

                    def sdk_run_double(model):
                        try:
                            return SimpleNamespace(result=function(model), status="SUCCESS", cached=False)
                        except Exception:
                            return SimpleNamespace(result=failed_sentinel, status="FAILED", cached=False)

                    run = Mock(side_effect=sdk_run_double)
                    env["orbit_native_pass_fail_hardened"] = SimpleNamespace(run=run)
                    observation, = env["run_planned_models"]()
                    self.assertEqual(observation["state"], "technical-error")
                    self.assertEqual(observation["technicalPhase"], phase)
                    self.assertEqual(observation["errorType"], error_type)
                    self.assertIsNone(observation["result"])
                    self.assertEqual(observation["providerAttempts"], 1)
                    self.assertRegex(observation["observationId"], r"^[0-9a-f]{32}$")
                    self.assertFalse(observation["retryEligible"])
                    self.assertNotIn("computedResult", observation)
                    self.assertIsNone(env["_ATTEMPT_CAPTURE"].get())
                    run.assert_called_once_with(llm)
                    llm.prompt.assert_called_once()
                    self.assertEqual(env["subprocess"].run.call_count, int(phase == "engine"))
                    self.assertEqual(env["_report_diagnostic_failure"].call_count, int(storage_failure))

    def test_engine_internal_rejection_is_technical_not_a_model_failure(self):
        env = runtime()
        response = {"ok": False, "error": "ReferenceError: synthetic engine defect"}
        env["subprocess"].run = Mock(return_value=SimpleNamespace(
            returncode=0, stdout="\n".join([json.dumps(response)] * 18)))
        llm = SimpleNamespace(name="fake", prompt=Mock(return_value=json.dumps(fixture())))
        with self.assertRaisesRegex(RuntimeError, "SHARED_ENGINE_REJECTED_VALIDATED_INPUT"):
            env["orbit_native_pass_fail_hardened"](llm)
        report = env["_save_diagnostics"].call_args.args[0]
        self.assertEqual(report["outcome"], "technical-error")
        self.assertEqual(report["technicalPhase"], "engine")
        self.assertIsNone(report["result"])
        self.assertFalse(report["engineEvaluations"][0]["ok"])
        llm.prompt.assert_called_once()

    def test_aggregate_replace_failure_retains_observations_and_existing_receipt(self):
        env = runtime()
        env["SELECTED_MODELS"] = ["first", "second"]
        env["kbench"].llms = {"first": "fake-a", "second": "fake-b"}
        run = Mock(side_effect=[SimpleNamespace(result=True), SimpleNamespace(result=False)])
        env["orbit_native_pass_fail_hardened"] = SimpleNamespace(run=run)
        env["RUN_MODELS"] = True
        cell = TASK.split("# %%\n")[4]
        with tempfile.TemporaryDirectory() as directory:
            env["DIAGNOSTIC_DIR"] = Path(directory)
            target = Path(directory) / "model-observations.json"
            before = b'[{"previous":true}]\n'
            target.write_bytes(before)
            with patch.object(Path, "replace", side_effect=OSError("replace fixture")), patch("sys.stderr"):
                with self.assertRaises(RuntimeError) as context:
                    exec(compile(cell, "<aggregate-save>", "exec"), env)
            self.assertEqual(type(context.exception).__name__, "AggregateDiagnosticPersistenceError")
            self.assertEqual([row["result"] for row in context.exception.computedObservations], [True, False])
            self.assertFalse(context.exception.retryEligible)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            self.assertEqual(run.call_count, 2)

    def test_atomic_diagnostic_encoding_and_replace_failure(self):
        env = runtime()
        # Restore the real pure filesystem helper from the selected definitions, not SDK code.
        function = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "_save_diagnostics")
        exec(compile(ast.Module(body=[function], type_ignores=[]), "<diagnostic-helper>", "exec"), env)
        report = {"model": "fixture", "observationId": "one", "answer": "\ud800"}
        with tempfile.TemporaryDirectory() as directory:
            env["DIAGNOSTIC_DIR"] = Path(directory)
            env["_save_diagnostics"](report)
            target = Path(directory) / "fixture-one.json"
            before = target.read_bytes()
            self.assertEqual(json.loads(before)["answer"], "\ud800")
            with patch.object(Path, "replace", side_effect=OSError("replace fixture")):
                with self.assertRaises(OSError):
                    env["_save_diagnostics"]({**report, "answer": "new"})
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


class GenerationTests(unittest.TestCase):
    def test_builder_rejects_model_selection_drift(self):
        template_path = DIRECTORY / "task-template.py.in"
        original_read = Path.read_bytes
        template = original_read(template_path)
        selection = next(line for line in template.splitlines() if line.startswith(b"SELECTED_MODELS="))
        mutations = (b"SELECTED_MODELS=['unapproved/model']",
                     b"SELECTED_MODELS=['google/gemini-3.1-pro-preview','google/gemini-3.8-flash']",
                     selection + b"\n" + selection,
                     b"# SELECTED_MODELS assignment removed")
        for replacement in mutations:
            with self.subTest(replacement=replacement):
                def read_mutated(path):
                    return template.replace(selection, replacement) if path == template_path else original_read(path)
                with patch.object(Path, "read_bytes", new=read_mutated):
                    with self.assertRaisesRegex(ValueError, "Selected models"):
                        BUILDER["expected_artifacts"]()

    def test_deterministic_builder_matches_delivered_bytes(self):
        expected = BUILDER["expected_artifacts"]()
        self.assertEqual(expected, BUILDER["expected_artifacts"]())
        for name, data in expected.items():
            self.assertEqual((DIRECTORY / name).read_bytes(), data, name)

    def test_check_mode_preserves_bytes(self):
        paths = list(DIRECTORY.iterdir())
        before = {p.name: p.read_bytes() for p in paths if p.is_file()}
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/build_native_pilot_hardened.py"), "--check"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in paths if p.is_file()})

    def test_notebook_cells_and_disabled_dispatch(self):
        notebook = json.loads((DIRECTORY / "orbit-native-pass-fail-hardened.ipynb").read_text())
        codes = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual([c["source"] for c in codes], TASK.split("# %%\n")[1:])
        self.assertTrue(all(c["outputs"] == [] and c["execution_count"] is None for c in codes))
        self.assertIs(ast.literal_eval(ASSIGNMENTS["RUN_MODELS"].value), False)
        # Execute only the two gated final cells with no SDK/process globals available.
        events = []
        env = {"RUN_MODELS": False, "print": lambda *args: events.append(args)}
        exec(compile(codes[3]["source"], "<disabled-dispatch>", "exec"), env)
        exec(compile(codes[4]["source"], "<disabled-archive>", "exec"), env)
        self.assertEqual(env["MODEL_OBSERVATIONS"], [])
        self.assertEqual(len(events), 2)

    def test_historical_bytes_unchanged(self):
        frozen = json.loads((ROOT / "metadata/frozen-history.json").read_text())
        for relative, expected in frozen["files"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)


if __name__ == "__main__":
    unittest.main()
