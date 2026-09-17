"""Packaging flow checks that run without a Windows host or PyInstaller build."""
import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        with (patch.object(packaging, "install_dependencies"),
              patch.object(packaging, "run", side_effect=failure) as command,
              patch.object(packaging, "archive_bundle") as archive,
              self.assertRaises(subprocess.CalledProcessError)):
            packaging.build(Path("build"), Path("dist"))
        self.assertEqual(command.call_count, 1)
        archive.assert_not_called()

    def test_offline_install_requires_local_wheels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(packaging, "PROJECT", root), patch.object(packaging, "run") as command:
                for create_directory in (False, True):
                    if create_directory:
                        (root / "wheelhouse").mkdir()
                    with self.subTest(directory_exists=create_directory), self.assertRaisesRegex(
                        RuntimeError, "Offline packages are missing"
                    ):
                        packaging.install_dependencies(Path("python.exe"))
            command.assert_not_called()

    def test_offline_install_has_no_network_fallback(self):
        with tempfile.TemporaryDirectory(prefix="fusion packages ") as directory:
            root = Path(directory)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            (wheelhouse / "fixture.whl").touch()
            for failure in (None, subprocess.CalledProcessError(1, ["pip"])):
                with (self.subTest(failure=failure), patch.object(packaging, "PROJECT", root),
                      patch.object(packaging, "run", side_effect=failure) as command):
                    if failure:
                        with self.assertRaisesRegex(RuntimeError, "No online fallback"):
                            packaging.install_dependencies(Path("python.exe"))
                    else:
                        packaging.install_dependencies(Path("python.exe"))
                    command.assert_called_once_with(
                        Path("python.exe"), "-m", "pip", "--isolated", "--disable-pip-version-check",
                        "install", "--no-index", "--find-links", wheelhouse,
                        "--only-binary=:all:", "-r", "requirements-build.txt",
                    )

    def test_install_failure_stops_before_tests_and_packaging(self):
        with (patch.object(packaging, "install_dependencies", side_effect=RuntimeError("missing wheel")),
              patch.object(packaging, "run") as command,
              patch.object(packaging, "archive_bundle") as archive,
              self.assertRaisesRegex(RuntimeError, "missing wheel")):
            packaging.build(Path("build"), Path("dist"))
        command.assert_not_called()
        archive.assert_not_called()

    def test_build_creates_onefile_with_embedded_notices_before_smoke_and_archive(self):
        with tempfile.TemporaryDirectory(prefix="fusion build ") as directory:
            root = Path(directory)
            dist = root / "dist"
            bundle = dist / "ExcelFusion"
            health = {"ok": True, "ui_ready_seconds": 0.5}
            with (patch.object(packaging, "install_dependencies"),
                  patch.object(packaging, "run") as command,
                  patch.object(packaging, "check_bundle", return_value=(health, 1.25)) as smoke,
                  patch.object(packaging, "archive_bundle") as archive):
                packaging.build(root / "build", dist)
            calls = [call.args for call in command.call_args_list]
            self.assertEqual(calls[0][1:], ("-m", "unittest", "discover", "-v"))
            self.assertEqual(calls[-2][1:], ("collect_licenses.py", bundle))
            freeze = calls[-1]
            self.assertIn("--onefile", freeze)
            self.assertNotIn("--onedir", freeze)
            self.assertEqual(freeze[freeze.index("--distpath") + 1], bundle)
            self.assertIn(f"{bundle / 'licenses'};licenses", freeze)
            self.assertIn(f"{bundle / 'README.md'};.", freeze)
            self.assertTrue((bundle / "README.md").is_file())
            smoke.assert_called_once_with(bundle, dist / "smoke-result.json")
            archive.assert_called_once_with(bundle, health, 1.25)

    def test_windows_requires_python_311_x64(self):
        tkinter = MagicMock()
        with (patch.object(packaging.sys, "platform", "win32"),
              patch.object(packaging.platform, "machine", return_value="AMD64"),
              patch.object(packaging.struct, "calcsize", return_value=8),
              patch.dict("sys.modules", {"tkinter": tkinter})):
            for version in ((3, 10), (3, 12), (3, 14)):
                with (patch.object(packaging.sys, "version_info", version),
                      self.subTest(version=version), self.assertRaisesRegex(RuntimeError, "3.11")):
                    packaging.validate_environment()
            tkinter.Tk.assert_not_called()
            with patch.object(packaging.sys, "version_info", (3, 11)):
                packaging.validate_environment()
                tkinter.Tk.return_value.destroy.assert_called_once()
                with (patch.object(packaging.struct, "calcsize", return_value=4),
                      self.assertRaisesRegex(RuntimeError, "x64")):
                    packaging.validate_environment()

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
            notices = bundle / "licenses"
            notices.mkdir(parents=True)
            (bundle / "ExcelFusion.exe").write_bytes(b"fixture")
            (notices / "Python-LICENSE.txt").write_bytes(b"fixture license")
            with patch("builtins.print"):
                archive = packaging.archive_bundle(bundle, {"ui_ready_seconds": 0.5}, 1.25)
            with zipfile.ZipFile(archive) as contents:
                self.assertIn("ExcelFusion/ExcelFusion.exe", contents.namelist())
                self.assertIn("ExcelFusion/licenses/Python-LICENSE.txt", contents.namelist())
                self.assertFalse(any("_internal" in name for name in contents.namelist()))
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
