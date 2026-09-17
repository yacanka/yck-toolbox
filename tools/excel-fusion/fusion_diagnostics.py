"""Stable sample settings for tests and the isolated packaged-app smoke check.

These values describe the synthetic workbooks, not application defaults. Keep
changes here tied to test scenarios; user CONFIG/COLUMN_SCHEMA edits are separate.
"""

import copy
from contextlib import contextmanager
from pathlib import Path

import excel_fusion as core
from excel_fusion import ColumnSpec

SAMPLE_CONFIG = {
    "INPUT_DIR": Path("kaynaklar"),
    "OUTPUT_FILE": Path("rapor.xlsx"),
    "OVERWRITE": False,
    "REPORT_GROUP_MODE": "subfolder",
    "EXPECTED_HEADER_ROW": 12,
    "HEADER_SEARCH_START": 1,
    "HEADER_SEARCH_END": 40,
    "HEADER_HEIGHTS": (1, 2),
    "HEADER_TEXT_MODE": "smart",
    "HEADER_MAX_PREFIX_LINES": 3,
    "MIN_HEADER_MATCHES": 3,
    "HEADER_ANCHORS": ("No.", "Entity", "Panel", "ATA", "Reviewer Name"),
    "MIN_HEADER_ANCHORS": 2,
    "FUZZY_THRESHOLD": 84.0,
    "AMBIGUITY_MARGIN": 7.0,
    "SHORT_ALIAS_MAX_LENGTH": 3,
    "EXTRA_PREFIX": "Ek | ",
    "INCLUDE_ROOT_FILES": False,
    "ROOT_GROUP_NAME": "Kök Dosyalar",
    "EXTENSIONS": (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls", ".xlsb"),
    "EXCLUDE_DIRS": (".git", ".venv", "venv", "__pycache__"),
    "EXCLUDE_FILES": ("~$*", ".~*", "*.tmp.xlsx"),
    "EXCLUDE_SHEETS": (),
    "INCLUDE_HIDDEN_SHEETS": True,
    "ROW_REQUIRED_COLUMNS": (),
    "MIN_ROW_VALUES": 2,
    "ROW_REQUIRE_ANY": ("No.", "Entity", "Panel", "ATA", "Reviewer Name"),
    "ROW_ID_COLUMN": "No.",
    "ROW_ID_REGEX": None,
    "FOOTER_LABELS": (
        "total",
        "grand total",
        "toplam",
        "genel toplam",
        "signature",
        "imza",
        "prepared by",
        "hazirlayan",
        "approved by",
        "onaylayan",
    ),
    "TRIM_TEXT": True,
    "FILL_DOWN_COLUMNS": (),
    "DROP_DUPLICATES": False,
    "DEDUP_KEYS": (),
    "PRESERVE_SIMPLE_ZERO_FORMATS": True,
    "REPORT_TITLE": "BİRLEŞTİRİLMİŞ EXCEL RAPORU",
    "SUMMARY_SHEET": "Özet & Dashboard",
    "DASHBOARD_TOP_N": 10,
    "WORKFLOW_SUMMARY": {
        "ENABLED": True,
        "STATUS_COLUMN": "Open / Closed",
        "COMPANY_COLUMN": "My Company",
        "OPEN_PREFIX": "open",
        "CLOSED_PREFIX": "closed",
    },
    "CHARTS": (
        ("Klasör", "bar"),
        ("ATA", "column"),
        ("Panel", "doughnut"),
        ("Reviewer Name", "bar"),
    ),
    "MAX_ROWS_PER_SHEET": 1048000,
    "DATE_FORMAT": "dd.mm.yyyy",
    "DATETIME_FORMAT": "dd.mm.yyyy hh:mm",
    "FAIL_ON_FILE_ERROR": False,
}

SAMPLE_SCHEMA = [
    ColumnSpec(
        name="No.",
        aliases=(
            "No",
            "Number",
            "Item No",
            "Item Number",
            "Sıra No",
            "Sıra Numarası",
            "Numara",
        ),
        required=False,
        threshold=None,
        width=11,
    ),
    ColumnSpec(
        name="Entity",
        aliases=("Entitiy", "Entiy", "Varlık", "Kurum"),
        required=False,
        threshold=None,
        width=27,
    ),
    ColumnSpec(
        name="Panel",
        aliases=("Panel Name", "Panel Adı", "Pannel"),
        required=False,
        threshold=None,
        width=22,
    ),
    ColumnSpec(
        name="ATA",
        aliases=("ATA No", "ATA Number", "ATA Chapter", "ATA Kodu"),
        required=False,
        threshold=None,
        width=14,
    ),
    ColumnSpec(
        name="Reviewer Name",
        aliases=(
            "Reviever Name",
            "Rewiever Name",
            "Reviwer Name",
            "Name of Reviewer",
            "Reviewer",
            "İnceleyen",
            "İnceleyen Adı",
            "Değerlendiren",
        ),
        required=False,
        threshold=None,
        width=28,
    ),
    ColumnSpec(
        name="Open / Closed",
        aliases=("Open Closed", "Open/Closed"),
        required=False,
        threshold=None,
        width=30,
    ),
    ColumnSpec(name="My Company", aliases=(), required=False, threshold=None, width=30),
]


@contextmanager
def sample_configuration():
    """Temporarily select sample settings, restoring user objects even on failure.

    Only for serial tests and --smoke-test before the GUI event loop starts.
    Never use while a report worker is running.
    """
    config, schema = core.CONFIG, core.COLUMN_SCHEMA
    try:
        core.CONFIG = copy.deepcopy(SAMPLE_CONFIG)
        core.COLUMN_SCHEMA = copy.deepcopy(SAMPLE_SCHEMA)
        yield
    finally:
        core.CONFIG, core.COLUMN_SCHEMA = config, schema
