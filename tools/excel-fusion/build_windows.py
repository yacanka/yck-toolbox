"""Windows packaging, invoked by build_windows.bat; no PowerShell required."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import struct
import subprocess
import sys
import time
import venv
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def run(*args: str | Path, timeout: float | None = None) -> None:
    """Keep paths as individual arguments; stop immediately when a command fails."""
    subprocess.run([str(arg) for arg in args], cwd=PROJECT, check=True, timeout=timeout)


def validate_environment() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Windows EXE must be built on Windows; this environment is unsupported.")
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Install Python 3.11 x64 with Tcl/Tk support.")
    if platform.machine().upper() not in ("AMD64", "X86_64") or struct.calcsize("P") != 8:
        raise RuntimeError("The Windows x64 Python installer is required.")
    import tkinter

    try:
        window = tkinter.Tk()
        window.withdraw()
        window.update()
        window.destroy()
    except tkinter.TclError as exc:
        raise RuntimeError("Tcl/Tk could not open a window. Check the Python installation and desktop session.") from exc


def check_bundle(bundle: Path, destination: Path) -> tuple[dict, float]:
    """Test the actual frozen executable before creating a distributable ZIP."""
    started = time.perf_counter()
    run(bundle / "ExcelFusion.exe", "--smoke-test", destination, timeout=120)
    elapsed = time.perf_counter() - started
    health = json.loads(destination.read_text(encoding="utf-8"))
    if health.get("ok") is not True:
        raise RuntimeError("Packaged Excel read/write test failed.")
    return health, elapsed


def archive_bundle(bundle: Path, health: dict, elapsed: float) -> Path:
    archive = Path(shutil.make_archive(
        str(bundle.parent / "ExcelFusion-Windows-x64"), "zip",
        root_dir=bundle.parent, base_dir=bundle.name,
    ))
    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    metrics = {
        "bundle_bytes": sum(path.stat().st_size for path in bundle.rglob("*") if path.is_file()),
        "zip_bytes": archive.stat().st_size,
        "ui_ready_seconds_after_python_entry": health["ui_ready_seconds"],
        "launch_and_report_smoke_seconds": round(elapsed, 3),
        "sha256": checksum,
        "python": platform.python_version(),
    }
    (bundle.parent / "build-metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8",
    )
    print(f"Ready: {archive}")
    print(json.dumps(metrics, indent=2))
    return archive


def install_dependencies(python: Path) -> None:
    """Prefer local wheels; download missing dependencies for this and future builds."""
    wheelhouse = PROJECT / "wheelhouse"
    pip = (python, "-m", "pip", "--isolated", "--disable-pip-version-check")
    install = (*pip, "install", "--no-index", "--find-links", wheelhouse,
               "--only-binary=:all:", "-r", "requirements-build.txt")
    if wheelhouse.is_dir() and any(wheelhouse.glob("*.whl")):
        try:
            run(*install)
            return
        except subprocess.CalledProcessError:
            print("Offline dependency installation failed; trying an online download.")
    else:
        print("Offline packages are missing; trying an online download.")
    wheelhouse.mkdir(parents=True, exist_ok=True)
    try:
        run(*pip, "download", "--index-url", "https://pypi.org/simple",
            "--find-links", wheelhouse, "--only-binary=:all:", "--dest", wheelhouse,
            "-r", "requirements-build.txt")
        run(*install)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Build dependency installation failed after online fallback. Check the pip output, "
            "network access to PyPI, and wheelhouse for compatible Python 3.11 Windows x64 wheels."
        ) from exc


def tk_data_arguments() -> list[str]:
    """Bundle the script libraries loaded by Tk, including their startup files."""
    import tkinter

    window = tkinter.Tk()
    try:
        window.withdraw()
        libraries = (
            (Path(window.tk.call("info", "library")), "init.tcl", "_tcl_data"),
            (Path(window.tk.call("set", "tk_library")), "tk.tcl", "_tk_data"),
        )
        arguments = []
        for directory, startup, destination in libraries:
            if not (directory / startup).is_file():
                raise RuntimeError(f"Tcl/Tk startup file missing: {directory / startup}")
            # These destinations match PyInstaller's built-in tkinter runtime hook.
            arguments.extend(("--add-data", f"{directory};{destination}"))
        return arguments
    finally:
        window.destroy()


def build(build_root: Path, dist: Path) -> None:
    python = Path(sys.executable)
    install_dependencies(python)
    run(python, "-m", "unittest", "discover", "-v")
    run(python, "-m", "compileall", "-q", "excel_fusion.py", "fusion_service.py",
        "excel_fusion_gui.py", "fusion_settings.py", "fusion_settings_ui.py",
        "fusion_smoke.py", "fusion_diagnostics.py",
        "collect_licenses.py", "build_windows.py")
    tk_data = tk_data_arguments()
    bundle = dist / "ExcelFusion"
    bundle.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT / "README.md", bundle / "README.md")
    run(python, "collect_licenses.py", bundle)
    run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--noupx", "--name", "ExcelFusion", "--distpath", bundle,
        "--workpath", build_root / "pyinstaller", "--specpath", build_root,
        "--add-data", f"{bundle / 'licenses'};licenses",
        "--add-data", f"{bundle / 'README.md'};.",
        *tk_data,
        "--exclude-module", "numpy", "--exclude-module", "pandas",
        "--exclude-module", "matplotlib", "--exclude-module", "PIL",
        "--exclude-module", "lxml", "--hidden-import", "python_calamine", "excel_fusion_gui.py")
    health, elapsed = check_bundle(bundle, dist / "smoke-result.json")
    archive_bundle(bundle, health, elapsed)


def main() -> int:
    try:
        validate_environment()
        if len(sys.argv) == 4 and sys.argv[1] == "--build-in-venv":
            build(Path(sys.argv[2]), Path(sys.argv[3]))
            return 0
        if len(sys.argv) != 1:
            raise ValueError("Use build_windows.bat or python build_windows.py without arguments.")
        # Preserve previous distributions and isolate unrelated installed libraries.
        build_id = datetime.now(UTC).strftime("windows-%Y%m%d-%H%M%S-%f")
        build_root = PROJECT / "build" / build_id
        dist = PROJECT / "dist" / build_id
        environment = build_root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        run(environment / "Scripts" / "python.exe", Path(__file__).resolve(),
            "--build-in-venv", build_root, dist)
        return 0
    except (ImportError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Build cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
