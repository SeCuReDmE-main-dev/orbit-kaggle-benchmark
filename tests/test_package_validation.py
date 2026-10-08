"""Local validator tests; all deliberately invalid data stays in temporary files."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_validator", ROOT / "tools/verify_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def fingerprints(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class PackageValidationTests(unittest.TestCase):
    def copy_successor_inputs(self, root):
        for relative in ("pilot/native-pass-fail", validator.SUCCESSOR):
            shutil.copytree(ROOT / relative, root / relative)
        (root / "tools").mkdir()
        shutil.copyfile(ROOT / "tools/build_native_pilot_hardened.py",
                        root / "tools/build_native_pilot_hardened.py")

    def refresh_fixture_hash(self, root, filename):
        directory = root / validator.SUCCESSOR
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][filename] = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_readonly_preserves_receipt_catalog_and_all_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata").mkdir()
            (root / validator.RECEIPT).write_text("receipt-before", encoding="utf-8")
            (root / validator.CATALOG).write_text("catalog-before", encoding="utf-8")
            before = fingerprints(root)
            for errors, exit_code in (([], 0), (["controlled validation failure"], 1)):
                with self.subTest(exit_code=exit_code), patch.object(validator, "ROOT", root), \
                     patch.object(validator, "public_files", return_value=[]), \
                     patch.object(validator, "validate", return_value={"errors": errors}), \
                     redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                    validator.main(["--read-only"])
                self.assertEqual(stopped.exception.code, exit_code)
                self.assertEqual(fingerprints(root), before)

    def test_readonly_rejects_catalog_refresh(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            validator.main(["--read-only", "--refresh-catalog"])
        self.assertEqual(stopped.exception.code, 2)

    def test_search_rejects_catalog_refresh(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            validator.main(["--search", "synthetic", "--refresh-catalog"])
        self.assertEqual(stopped.exception.code, 2)

    def test_historical_inventory_matches_actual_frozen_files(self):
        errors, verified = validator.validate_frozen_history(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(verified, 46)

    def test_rehashing_frozen_inventory_cannot_hide_changed_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata").mkdir()
            original = (ROOT / validator.FROZEN_HISTORY).read_bytes()
            (root / validator.FROZEN_HISTORY).write_bytes(original + b"\n")
            errors, verified = validator.validate_frozen_history(root)
            self.assertIn("Frozen history inventory fingerprint mismatch", errors)
            self.assertEqual(verified, 0)

    def test_missing_historical_file_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "metadata").mkdir()
            (root / validator.FROZEN_HISTORY).write_bytes((ROOT / validator.FROZEN_HISTORY).read_bytes())
            errors, verified = validator.validate_frozen_history(root)
            self.assertEqual(verified, 0)
            self.assertEqual(len(errors), 46)

    def test_successor_catalog_never_claims_execution(self):
        for filename in ("task.py", "manifest.json", "receipt-example.json"):
            entry = validator.describe(validator.SUCCESSOR + "/" + filename)
            self.assertFalse(entry["scope"]["executionEvidence"])
            self.assertEqual(entry["status"], "hardened-successor-prepared-not-executed")
        old = validator.describe("pilot/native-pass-fail/task.py")
        self.assertNotEqual(old["scope"]["dataset"], entry["scope"]["dataset"])

    def test_public_test_sources_are_not_model_measurements(self):
        entry = validator.describe("tests/test_package_validation.py")
        self.assertFalse(entry["scope"]["executionEvidence"])
        self.assertFalse(entry["scope"]["modelPerformanceEvidence"])

    def test_successor_local_receipt_is_only_software_test_evidence(self):
        entry = validator.describe(validator.SUCCESSOR + "/local-validation.json")
        self.assertTrue(entry["scope"]["testExecutionEvidence"])
        self.assertFalse(entry["scope"]["executionEvidence"])
        self.assertFalse(entry["scope"]["modelPerformanceEvidence"])
        self.assertEqual(entry["scope"]["nativeRunsExecuted"], 0)
        self.assertEqual(entry["scope"]["engineRuns"], 0)

    def test_local_reproduction_is_not_Kaggle_or_model_execution(self):
        entry = validator.describe("metadata/reproduction-20261008.json")
        self.assertTrue(entry["scope"]["executionEvidence"])
        self.assertFalse(entry["scope"]["modelPerformanceEvidence"])
        self.assertEqual(entry["scope"]["newModelCalls"], 0)
        self.assertIn("Kaggle-replay-20261005", entry["scope"]["distinctFrom"])
        self.assertEqual(entry["scope"]["decisions"] + entry["scope"]["metamorphicChecks"]
                         + entry["scope"]["relationChecks"], 486)

    def test_successor_sources_are_statically_consistent(self):
        errors, checks = validator.validate_successor(ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(checks, 30)

    def test_model_dispatch_cannot_be_enabled_by_rehashing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_successor_inputs(root)
            task = root / validator.SUCCESSOR / "task.py"
            task.write_text(task.read_text(encoding="utf-8").replace("RUN_MODELS = False", "RUN_MODELS = True"),
                            encoding="utf-8")
            self.refresh_fixture_hash(root, "task.py")
            errors, _ = validator.validate_successor(root)
            self.assertTrue(any("dispatch enabled" in error for error in errors), errors)

    def test_notebook_drift_detected_even_with_updated_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_successor_inputs(root)
            name = "orbit-native-pass-fail-hardened.ipynb"
            path = root / validator.SUCCESSOR / name
            notebook = json.loads(path.read_text(encoding="utf-8"))
            cell = next(cell for cell in notebook["cells"] if cell["cell_type"] == "code")
            cell["source"] = ["# Deliberate test-only notebook drift\n"]
            path.write_text(json.dumps(notebook), encoding="utf-8")
            self.refresh_fixture_hash(root, name)
            errors, _ = validator.validate_successor(root)
            self.assertTrue(any("notebook code cells differ" in error for error in errors), errors)

    def test_contract_drift_detected_even_with_updated_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_successor_inputs(root)
            path = root / validator.SUCCESSOR / "contract.py"
            path.write_text(path.read_text(encoding="utf-8") + "\ndef extra_test_function():\n    return False\n",
                            encoding="utf-8")
            self.refresh_fixture_hash(root, "contract.py")
            errors, _ = validator.validate_successor(root)
            self.assertTrue(any("embedded contract differs" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
