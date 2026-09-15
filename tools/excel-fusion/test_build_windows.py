"""Packaging flow checks that run without a Windows host or PyInstaller build."""
import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_windows as packaging


class PackagingTests(unittest.TestCase):
    def test_command_preserves_spaces_and_metacharacters(self):
        executable = Path("C:/Project & Tools/python.exe")
        with patch.object(packaging.subprocess, "run") as command:
            packaging.run(executable, "a b.py", timeout=120)
        command.assert_called_once_with(
            [str(executable), "a b.py"],
            cwd=packaging.PROJECT, check=True, timeout=120,
        )

    def test_failed_command_stops_build_before_archive(self):
        failure = subprocess.CalledProcessError(1, ["pip"])
        with (patch.object(packaging, "run", side_effect=failure) as command,
              patch.object(packaging, "archive_bundle") as archive,
              self.assertRaises(subprocess.CalledProcessError)):
            packaging.build(Path("build"), Path("dist"))
        self.assertEqual(command.call_count, 1)
        archive.assert_not_called()

    def test_smoke_failure_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "smoke.json"
            destination.write_text('{"ok": false}', encoding="utf-8")
            with patch.object(packaging, "run"), self.assertRaises(RuntimeError):
                packaging.check_bundle(Path(directory), destination)

    def test_smoke_uses_timeout_and_reads_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "smoke.json"
            destination.write_text('{"ok": true, "ui_ready_seconds": 0.5}', encoding="utf-8")
            with patch.object(packaging, "run") as command:
                health, elapsed = packaging.check_bundle(root, destination)
            command.assert_called_once_with(root / "ExcelFusion.exe", "--smoke-test", destination, timeout=120)
            self.assertTrue(health["ok"])
            self.assertGreaterEqual(elapsed, 0)

    def test_archive_includes_complete_bundle_and_correct_metrics(self):
        with tempfile.TemporaryDirectory(prefix="fusion build ") as directory:
            bundle = Path(directory) / "ExcelFusion"
            internal = bundle / "_internal"
            internal.mkdir(parents=True)
            (bundle / "ExcelFusion.exe").write_bytes(b"fixture")
            (internal / "runtime.dll").write_bytes(b"fixture runtime")
            with patch("builtins.print"):
                archive = packaging.archive_bundle(bundle, {"ui_ready_seconds": 0.5}, 1.25)
            with zipfile.ZipFile(archive) as contents:
                self.assertIn("ExcelFusion/ExcelFusion.exe", contents.namelist())
                self.assertIn("ExcelFusion/_internal/runtime.dll", contents.namelist())
                self.assertIsNone(contents.testzip())
            metrics = json.loads((Path(directory) / "build-metrics.json").read_text())
            self.assertEqual(metrics["bundle_bytes"], 22)
            self.assertEqual(metrics["zip_bytes"], archive.stat().st_size)
            self.assertEqual(metrics["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(metrics["launch_and_report_smoke_seconds"], 1.25)

    def test_non_windows_fails_before_creating_environment(self):
        with (patch.object(packaging.sys, "platform", "darwin"),
              patch.object(packaging.venv, "EnvBuilder") as environment,
              patch("sys.stderr")):
            self.assertEqual(packaging.main(), 1)
        environment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
