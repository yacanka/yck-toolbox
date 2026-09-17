"""Packaged-app health check using generated, non-sensitive workbook data."""
import json
import tempfile
import time
from pathlib import Path


def check(destination: Path, started: float) -> None:
    """Write a machine-readable result, including real read/write verification."""
    result = {"ok": False, "ui_ready_seconds": round(time.perf_counter() - started, 3)}
    try:
        import openpyxl
        import python_calamine
        import xlsxwriter

        import excel_fusion as core
        from fusion_diagnostics import sample_configuration
        from fusion_service import RunOptions, run_report

        # The sample is independent of user rules, but invalid real settings still fail the build.
        core.validate(core.CONFIG, core.COLUMN_SCHEMA)
        # Confirm the native legacy reader is present in the frozen package too.
        if not callable(python_calamine.CalamineWorkbook.from_path):
            raise TypeError("Legacy reader unavailable")
        with tempfile.TemporaryDirectory(prefix="fusion_smoke_") as directory:
            root = Path(directory)
            source = root / "kaynak" / "Grup"
            source.mkdir(parents=True)
            with xlsxwriter.Workbook(source / "test.xlsx") as workbook:
                sheet = workbook.add_worksheet("Data")
                sheet.write_row(0, 0, ["No.", "Entity", "Panel"])
                sheet.write_row(1, 0, [1, "E1", "P1"])
            with sample_configuration():
                report = run_report(RunOptions(str(source.parent), str(root / "rapor.xlsx")))
            if report.records != 1 or report.errors:
                raise RuntimeError("Report generation failed")
            workbook = openpyxl.load_workbook(report.output, data_only=True)
            try:
                if workbook["Grup"]["A8"].value != 1:
                    raise RuntimeError("Report content mismatch")
            finally:
                workbook.close()
        result["ok"] = True
    except Exception as exc:  # noqa: BLE001 -- serialize failure for the packaging process.
        result["error"] = f"{type(exc).__name__}: {exc}"
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not result["ok"]:
        raise SystemExit(1)
