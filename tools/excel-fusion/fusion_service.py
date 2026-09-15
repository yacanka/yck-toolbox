"""GUI adapter: independent configuration, original report engine, no global edits."""
from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import excel_fusion as core


@dataclass(frozen=True)
class RunOptions:
    source: str
    output: str
    group_mode: str = "subfolder"
    include_root: bool = False
    overwrite: bool = False
    dry_run: bool = False
    header_row: int = 12
    search_end: int = 40
    fail_on_error: bool = False

    def config(self) -> dict:
        cfg = copy.deepcopy(core.CONFIG)
        cfg.update(REPORT_GROUP_MODE=self.group_mode, INCLUDE_ROOT_FILES=self.include_root,
                   OVERWRITE=self.overwrite, EXPECTED_HEADER_ROW=self.header_row,
                   HEADER_SEARCH_END=self.search_end, FAIL_ON_FILE_ERROR=self.fail_on_error)
        if not 1 <= self.header_row <= self.search_end <= 1_048_576:
            raise ValueError("Başlık satırı 1 ile arama sonu arasında olmalı; üst sınır 1048576.")
        core.validate(cfg, core.COLUMN_SCHEMA)
        return cfg


@dataclass(frozen=True)
class RunResult:
    output: Path | None
    audit: Path
    records: int
    groups: int
    warnings: int
    errors: int
    quarantined: int


def validate_paths(options: RunOptions) -> tuple[Path, Path]:
    """Resolve user paths without depending on the bundled source directory."""
    if not options.source.strip() or not options.output.strip():
        raise ValueError("Kaynak klasörünü ve çıktı dosyasını seçin.")
    root = Path(options.source).expanduser().resolve()
    output = Path(options.output).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Kaynak klasör bulunamadı.")
    if output.suffix.lower() != ".xlsx":
        raise ValueError("Çıktı dosyasının uzantısı .xlsx olmalı.")
    if output.exists():
        if not output.is_file():
            raise ValueError("Çıktı yolu bir dosya olmalı.")
        if not options.dry_run and not options.overwrite:
            raise FileExistsError("Çıktı zaten var. Başka bir ad seçin veya rapor yenilemeyi etkinleştirin.")
        if options.overwrite and not core.is_own_report(output):
            raise ValueError("Mevcut dosya Excel Fusion raporu değil. Başka bir çıktı adı seçin.")
    return root, output


def run_report(options: RunOptions, progress: Callable[[str], None] = lambda _: None) -> RunResult:
    """Run on one worker thread. Errors propagate; handlers always close.

    Dry runs still write audit and log files, matching the original CLI.
    The caller must serialize runs because the engine owns a shared logger.
    """
    cfg = options.config()
    root, output = validate_paths(options)
    output.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(output.with_suffix(".log"), encoding="utf-8", mode="w")
    handler.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    old_level = core.LOG.level
    core.LOG.addHandler(handler)
    core.LOG.setLevel(logging.INFO)
    try:
        report = core.Report(root, output)
        progress("Kaynak dosyalar taranıyor…")
        core.discover(report, cfg)
        count = (len(report.source_files) if options.group_mode == "sheet_name"
                 else sum(len(group.files) for group in report.groups))
        progress(f"{count} dosya bulundu. Başlıklar eşleştiriliyor ve veriler birleştiriliyor…")
        core.collect(report, cfg, core.COLUMN_SCHEMA)
        progress("Denetim dosyası yazılıyor…")
        audit = core.save_json_audit(report)
        errors = sum(event["Seviye"] == "ERROR" for event in report.events)
        if options.fail_on_error and errors:
            raise RuntimeError(f"{errors} kaynak hatası nedeniyle rapor üretilmedi. Denetim: {audit}")
        if not options.dry_run:
            progress("Excel raporu ve grafikler oluşturuluyor…")
            core.save_report(report, cfg, core.COLUMN_SCHEMA)
        return RunResult(None if options.dry_run else output, audit,
                         sum(len(group.records) for group in report.groups), len(report.groups),
                         sum(event["Seviye"] == "WARNING" for event in report.events),
                         errors, len(report.quarantine))
    finally:
        core.LOG.removeHandler(handler)
        handler.close()
        core.LOG.setLevel(old_level)
