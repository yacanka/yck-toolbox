"""Çekirdek ve XLSX içe aktarma/özet regresyon testleri.

Çalıştırma: python -m unittest discover -v
XLSX testleri uygulamanın openpyxl ve xlsxwriter bağımlılıklarını kullanır.
"""
import copy
import tempfile
import unittest
from pathlib import Path

import excel_fusion as fusion


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(fusion.CONFIG)
        self.settings = self.cfg["WORKFLOW_SUMMARY"]

    def count(self, values):
        records = [fusion.Record(value, "source.xlsx", "Data", row)
                   for row, value in enumerate(values, 1)]
        return fusion.workflow_counts(records, self.settings)

    def test_status_prefix_and_company_emptiness(self):
        for status in ("open", "  OpEn uzun açıklama\nclosed daha sonra", "OPEN: açıklama", "openDevam"):
            for company in (None, "", " \t\n", "yanıt", 0, False):
                with self.subTest(status=status, company=company):
                    counts = self.count([{"Open / Closed": status, "My Company": company}])
                    turn = "our_company" if company in (None, "", " \t\n") else "other_company"
                    self.assertEqual(counts, {"open": 1, turn: 1})

    def test_closed_never_counts_a_turn(self):
        rows = [{"Open / Closed": "  CLOSED uzun metin open"}]
        rows.extend({"Open / Closed": "closed", "My Company": value}
                    for value in (None, "yanıt", fusion.MISSING_FORMULA_PREFIX + " =A1"))
        self.assertEqual(self.count(rows), {"closed": 4})

    def test_unknown_status_and_unavailable_company_are_separate(self):
        rows = [{"Open / Closed": value} for value in
                (None, "", "pending open", "reopened", 1, fusion.MISSING_FORMULA_PREFIX + " =A1")]
        rows.extend([{}, {"Open / Closed": "open"},
                     {"Open / Closed": "open", "My Company": fusion.MISSING_FORMULA_PREFIX + " =A1"}])
        self.assertEqual(self.count(rows), {"unknown_status": 7, "open": 2, "unknown_turn": 2})

    def test_empty_records(self):
        self.assertEqual(self.count([]), {})

    def test_custom_columns_and_prefixes(self):
        self.settings.update(STATUS_COLUMN="Entity", COMPANY_COLUMN="Panel",
                             OPEN_PREFIX=" Aktif ", CLOSED_PREFIX=" Bitti ")
        fusion.validate(self.cfg, fusion.COLUMN_SCHEMA)
        self.assertEqual(self.count([{"Entity": "AKTIF", "Panel": None},
                                     {"Entity": "aktif: bekliyor", "Panel": "cevap"},
                                     {"Entity": "bitti açıklama"}]),
                         {"open": 2, "our_company": 1, "other_company": 1, "closed": 1})

    def test_invalid_config(self):
        for overrides in ({"ENABLED": "yes"}, {"STATUS_COLUMN": "missing"},
                          {"COMPANY_COLUMN": "missing"}, {"COMPANY_COLUMN": "Open / Closed"},
                          {"OPEN_PREFIX": " "}, {"CLOSED_PREFIX": None},
                          {"OPEN_PREFIX": "closed"}, {"OPEN_PREFIX": "CLO"},
                          {"CLOSED_PREFIX": "op"}):
            with self.subTest(overrides=overrides):
                cfg = copy.deepcopy(self.cfg)
                cfg["WORKFLOW_SUMMARY"].update(overrides)
                with self.assertRaises(ValueError):
                    fusion.validate(cfg, fusion.COLUMN_SCHEMA)

    def test_disabled_and_legacy_config(self):
        self.cfg["WORKFLOW_SUMMARY"] = {"ENABLED": False}
        fusion.validate(self.cfg, fusion.COLUMN_SCHEMA)
        del self.cfg["WORKFLOW_SUMMARY"]
        fusion.validate(self.cfg, fusion.COLUMN_SCHEMA)

    def test_header_aliases(self):
        matcher = fusion.HeaderMatcher(fusion.COLUMN_SCHEMA, self.cfg)
        matches = matcher.match(["Open/Closed\nAçıklama", "My Company\nYanıtınızı yazın"])
        self.assertEqual([match.target for match in matches], ["Open / Closed", "My Company"])


class WorkbookTests(unittest.TestCase):
    def test_import_summary_and_disabled_layout(self):
        import openpyxl

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "kaynaklar" / "Grup A"
            source_dir.mkdir(parents=True)
            source = source_dir / "source.xlsx"
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(["No.", "Entity", "Panel", "Open/Closed\nAçıklama", "My Company"])
            for row in [(1, "E", "P", " OpEn: uzun açıklama", None),
                        (2, "E", "P", "OPEN\nclosed daha sonra", "yanıt"),
                        (3, "E", "P", "Closed: açıklama", None),
                        (4, "E", "P", "CLOSED", "yanıt"),
                        (5, "E", "P", "pending open", None),
                        (6, "E", "P", "open", "=A2"),
                        ("total", None, None, "open", None)]:
                sheet.append(row)
            missing = workbook.create_sheet("Eksik şirket")
            missing.append(["No.", "Entity", "Panel", "Open / Closed"])
            missing.append([7, "E", "P", "open"])
            workbook.save(source)
            workbook.close()
            original_bytes = source.read_bytes()

            cfg = copy.deepcopy(fusion.CONFIG)
            fusion.validate(cfg, fusion.COLUMN_SCHEMA)
            report = fusion.Report(root / "kaynaklar", root / "report.xlsx")
            fusion.discover(report, cfg)
            fusion.collect(report, cfg, fusion.COLUMN_SCHEMA)
            report.groups.append(fusion.Group("Boş grup"))
            self.assertEqual(len(report.groups[0].records), 7)
            self.assertEqual(len(report.quarantine), 1)
            self.assertFalse(any(event["Seviye"] == "ERROR" for event in report.events))
            self.assertEqual(report.groups[0].records[0].values["Open / Closed"], "OpEn: uzun açıklama")

            for enabled in (True, False):
                with self.subTest(enabled=enabled):
                    cfg["WORKFLOW_SUMMARY"]["ENABLED"] = enabled
                    cfg["OVERWRITE"] = True
                    fusion.save_report(report, cfg, fusion.COLUMN_SCHEMA)
                    result = openpyxl.load_workbook(report.output, data_only=True)
                    try:
                        summary = result[cfg["SUMMARY_SHEET"]]
                        if enabled:
                            self.assertEqual(summary["A12"].value, "AÇIK / KAPALI VE İŞ SIRASI")
                            columns = (1, 6, 8, 10, 13, 16, 19)
                            self.assertEqual([summary.cell(14, col).value for col in columns],
                                             ["GENEL TOPLAM", 4, 2, 1, 1, 1, 2])
                            self.assertEqual([summary.cell(15, col).value for col in columns],
                                             ["Grup A", 4, 2, 1, 1, 1, 2])
                            self.assertEqual([summary.cell(16, col).value for col in columns],
                                             ["Boş grup", 0, 0, 0, 0, 0, 0])
                        else:
                            self.assertIsNone(summary["A12"].value)
                        offset = len(report.groups) + 6 if enabled else 0
                        self.assertEqual(summary.cell(41 + offset, 1).value, "KLASÖR BAZINDA ÖZET")
                        self.assertEqual(summary["A6"].value, 7)
                        self.assertEqual(result["_Rapor Verisi"].sheet_state, "hidden")
                        self.assertEqual(len(summary._charts), 4)
                        self.assertEqual(summary._charts[0].anchor._from.row, 12 + offset)
                        self.assertEqual(len(result["Grup A"].tables), 1)
                    finally:
                        result.close()
            self.assertEqual(source.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
