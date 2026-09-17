"""Regression checks for diagnostics with customized application settings."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import excel_fusion as core
import fusion_smoke
from fusion_diagnostics import sample_configuration


class DiagnosticTests(unittest.TestCase):
    def test_sample_settings_are_independent_and_restore_user_objects(self):
        config = {"ROW_REQUIRED_COLUMNS": ("Notes",)}
        schema = [core.ColumnSpec("Custom")]
        with patch.object(core, "CONFIG", config), patch.object(core, "COLUMN_SCHEMA", schema):
            for fail in (False, True):
                with self.subTest(fail=fail):
                    try:
                        with sample_configuration():
                            self.assertEqual(core.CONFIG["ROW_REQUIRED_COLUMNS"], ())
                            self.assertEqual(core.COLUMN_SCHEMA[0].name, "No.")
                            core.CONFIG["WORKFLOW_SUMMARY"]["OPEN_PREFIX"] = "changed"
                            core.COLUMN_SCHEMA.clear()
                            if fail:
                                raise RuntimeError("diagnostic failure")
                    except RuntimeError as exc:
                        self.assertEqual(str(exc), "diagnostic failure")
                    self.assertIs(core.CONFIG, config)
                    self.assertIs(core.COLUMN_SCHEMA, schema)
            with sample_configuration():
                self.assertEqual(core.CONFIG["WORKFLOW_SUMMARY"]["OPEN_PREFIX"], "open")
                self.assertEqual(len(core.COLUMN_SCHEMA), 7)

    def test_smoke_accepts_custom_rules_without_changing_them(self):
        with sample_configuration():
            config = copy.deepcopy(core.CONFIG)
            schema = [core.ColumnSpec("Custom", required=True), *reversed(core.COLUMN_SCHEMA)]
        config["ROW_REQUIRED_COLUMNS"] = ("Notes",)
        config["WORKFLOW_SUMMARY"] = {"ENABLED": False}
        config["CHARTS"] = ()
        original = copy.deepcopy(config)
        with (tempfile.TemporaryDirectory() as directory,
              patch.object(core, "CONFIG", config), patch.object(core, "COLUMN_SCHEMA", schema),
              patch.dict("sys.modules", {"python_calamine": MagicMock()})):
            # Native reader loading is verified separately by the real EXE smoke check.
            destination = Path(directory) / "smoke.json"
            fusion_smoke.check(destination, time.perf_counter())
            self.assertTrue(json.loads(destination.read_text())["ok"])
            self.assertIs(core.CONFIG, config)
            self.assertEqual(config, original)
            self.assertIs(core.COLUMN_SCHEMA, schema)

    def test_smoke_still_rejects_invalid_user_settings(self):
        with sample_configuration():
            core.CONFIG["REPORT_GROUP_MODE"] = "invalid"
            with (tempfile.TemporaryDirectory() as directory,
                  patch.dict("sys.modules", {"python_calamine": MagicMock()})):
                destination = Path(directory) / "smoke.json"
                with self.assertRaises(SystemExit):
                    fusion_smoke.check(destination, time.perf_counter())
                result = json.loads(destination.read_text())
                self.assertFalse(result["ok"])
                self.assertIn("REPORT_GROUP_MODE", result["error"])


if __name__ == "__main__":
    unittest.main()
