from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kt_movemacc import engine  # noqa: E402


class Task082WarnConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_eplaza = ROOT / "RAW.INPUT" / "2026.08" / "Mayor Inmob. Eplaza 2026 08 V 1.xlsb"
        cls.raw_impulsa = ROOT / "RAW.INPUT" / "2026.08" / "Mayor Grupo Impulsa 2026 08 V 1.xlsb"
        ep_rows = engine.parse_xlsb(cls.raw_eplaza)
        im_rows = engine.parse_xlsb(cls.raw_impulsa)
        cls.workbook, cls.metrics, cls.audit_entries = engine.write_workbook(
            "2026.08",
            ep_rows,
            im_rows,
            engine.align(ep_rows, im_rows),
            cls.raw_eplaza,
            cls.raw_impulsa,
        )
        cls.baseline = openpyxl.load_workbook(
            ROOT / "90_RUNTIME" / "KTMA_TASK080_AUDIT_IDS" / "RUN_002" / "CAM2026.08_CONSOL.ALIGN.xlsx",
            data_only=False,
        )

    def test_exact_eleven_warn_to_criterion_crosslinks(self) -> None:
        expected = {
            ("EPLAZA", "PROYECTO HERNANDO DE AGUIRRE#1"): "CR-004",
            ("EPLAZA", "GASTOS ACTIVADOS#1"): "CR-005",
            ("EPLAZA", "TOTAL ACTIVO#1"): "CR-003",
            ("EPLAZA", "TOTAL PASIVO#1"): "CR-008",
            ("EPLAZA", "ACTIVO - PASIVO#1"): "CR-010",
            ("EPLAZA", "RESULTADO#1"): "CR-012",
            ("IMPULSA", "TOTAL ACTIVO#1"): "CR-002",
            ("IMPULSA", "TOTAL PASIVO#1"): "CR-009",
            ("IMPULSA", "ACTIVO - PASIVO#1"): "CR-011",
            ("IMPULSA", "RESULTADO#1"): "CR-013",
            ("IMPULSA", "TOTALES GENERALES#1"): "CR-015",
        }
        criteria = self.metrics["approved_criteria"]
        observed = {
            (entry["COMPANY"], entry["SEMANTIC_KEY"]): entry["RULE_ID"]
            for entry in criteria["hierarchy_warn_crosswalk"]
        }
        self.assertEqual(observed, expected)
        self.assertEqual(criteria["hierarchy_warn_crosswalk_count"], 11)
        self.assertEqual(criteria["hierarchy_warn_crosswalk_unresolved_count"], 0)
        self.assertEqual(criteria["numerically_verified_count"], 15)
        self.assertEqual(criteria["blocked_count"], 0)

    def test_crosslink_retains_all_warns_and_excludes_source_subtotal_diff(self) -> None:
        warn_entries = [entry for entry in self.audit_entries if entry.severity == "WARN"]
        self.assertEqual(len(warn_entries), 29)
        self.assertEqual(
            Counter(entry.finding for entry in warn_entries),
            Counter({"CONFLICTING_DESCRIPTION": 15, "AMBIGUOUS_HIERARCHY": 11, "SOURCE_SUBTOTAL_DIFF": 3}),
        )
        crosslinks = self.metrics["approved_criteria"]["hierarchy_warn_crosswalk"]
        linked_ids = {entry["AUDIT_ID"] for entry in crosslinks}
        self.assertEqual(len(linked_ids), 11)
        self.assertFalse(
            linked_ids
            & {entry.audit_id for entry in warn_entries if entry.finding == "SOURCE_SUBTOTAL_DIFF"}
        )
        self.assertTrue(
            all(
                entry["DISPOSITION"] == "TECHNICALLY_RESOLVED_BY_APPROVED_CRITERION_WARN_RETAINED"
                and entry["FINANCIAL_VALUES_CHANGED"] is False
                and entry["FINANCIAL_FORMULAS_CHANGED_BY_CROSSLINK"] is False
                for entry in crosslinks
            )
        )

    def test_workbook_values_formulas_and_audit_ids_match_task080_baseline(self) -> None:
        for sheet_name in (
            "CAM2026.08_CONSOL.ALIGN",
            "CM2026.08_EPLAZA",
            "CM2026.08_IMPULSA",
            "AUDIT.PH1",
            "CONTROL",
        ):
            actual = self.workbook[sheet_name]
            expected = self.baseline[sheet_name]
            self.assertEqual((actual.max_row, actual.max_column), (expected.max_row, expected.max_column))
            for row in range(1, actual.max_row + 1):
                for column in range(1, actual.max_column + 1):
                    with self.subTest(sheet=sheet_name, row=row, column=column):
                        actual_cell = actual.cell(row, column)
                        expected_cell = expected.cell(row, column)
                        actual_value = actual_cell.value
                        expected_value = expected_cell.value
                        if (
                            isinstance(actual_value, (int, float))
                            and not isinstance(actual_value, bool)
                            and isinstance(expected_value, (int, float))
                            and not isinstance(expected_value, bool)
                        ):
                            self.assertAlmostEqual(actual_value, expected_value, places=6)
                        elif actual_value in (None, "") and expected_value in (None, ""):
                            pass
                        else:
                            self.assertEqual(actual_value, expected_value)
                        self.assertEqual(actual_cell.number_format, expected_cell.number_format)


if __name__ == "__main__":
    unittest.main()
