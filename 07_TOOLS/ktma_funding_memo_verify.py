from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import openpyxl


TARGET_ROWS = (27, 28, 31, 48, 32, 36, 41, 42, 38, 39, 37, 49, 50, 53, 55, 40)
ALLOWED = {f"{column}{row}" for row in TARGET_ROWS for column in "DEF"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition: bool, name: str, detail: object) -> dict[str, object]:
    return {"check": name, "status": "PASS" if condition else "FAIL", "detail": detail}


def same_style(left, right) -> bool:
    return (
        str(left.font) == str(right.font)
        and str(left.fill) == str(right.fill)
        and str(left.border) == str(right.border)
        and str(left.alignment) == str(right.alignment)
        and left.number_format == right.number_format
        and str(left.protection) == str(right.protection)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    run_dir = Path(args.run_dir).resolve()
    template = root / "OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx"
    output = run_dir / "FM2026.09_ACCOUNTING_MAPPING_V1.xlsx"
    mapping_path = run_dir / "KTMA_FM_MAPPING_MASTER_V1.csv"
    inventory_path = run_dir / "KTMA_FM_TARGET_INVENTORY_72_V1.csv"
    results_path = run_dir / "KTMA_FM_RESULTS_V1.json"
    conceptual_path = run_dir / "KTMA_FM_MAPPING_CONCEPTUAL_V1.md"
    rows = list(csv.DictReader(mapping_path.open(encoding="utf-8-sig")))
    inventory = list(csv.DictReader(inventory_path.open(encoding="utf-8-sig")))
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    source_wb = openpyxl.load_workbook(template, data_only=False)
    output_wb = openpyxl.load_workbook(output, data_only=False)
    output_values_wb = openpyxl.load_workbook(output, data_only=True)
    checks = [
        check(len(rows) == 66, "mapping_rows_66", len(rows)),
        check(len({row["ACCOUNT_ID"] for row in rows}) == 66, "mapping_account_uniqueness", len({row["ACCOUNT_ID"] for row in rows})),
        check(len({row["FM_TARGET_ID"] for row in rows}) == 16, "implemented_targets_16", len({row["FM_TARGET_ID"] for row in rows})),
        check(len(inventory) == 72 and len({row["FM_TARGET_CELL"] for row in inventory}) == 72, "physical_inventory_72", len(inventory)),
        check(payload["map_total_accounts"] == 253 and payload["mapped_accounts"] == 66 and payload["unassigned_account_ids"] == 187, "account_denominators", {key: payload[key] for key in ("map_total_accounts", "mapped_accounts", "unassigned_account_ids")}),
        check(all(row["STATUS"] == "IMPLEMENTED" and row["COEFFICIENT"] in {"1", "-1"} for row in rows), "mapping_status_and_coefficients", "all implemented; coefficients +/-1"),
    ]
    differences: list[str] = []
    for sheet_name in source_wb.sheetnames:
        source_ws = source_wb[sheet_name]
        output_ws = output_wb[sheet_name]
        for row in source_ws.iter_rows():
            for cell in row:
                if sheet_name == "FM" and cell.coordinate in ALLOWED:
                    continue
                other = output_ws[cell.coordinate]
                same_value = cell.value == other.value
                if isinstance(cell.value, (int, float)) and isinstance(other.value, (int, float)):
                    same_value = abs(float(cell.value) - float(other.value)) <= 1e-9
                if not same_value or not same_style(cell, other):
                    differences.append(f"{sheet_name}!{cell.coordinate}")
    checks.append(check(not differences, "template_non_target_cells_preserved", differences[:20]))
    fm = output_wb["FM"]
    formula_bad = [f"D{row}" for row in TARGET_ROWS if not str(fm[f"D{row}"].value).startswith("=IF(COUNT(")]
    checks.append(check(not formula_bad, "target_total_formulas_guarded", formula_bad))
    result_lookup = {item["target_id"]: item for item in payload["results"]}
    value_bad: list[str] = []
    for row in rows:
        result = result_lookup[row["FM_TARGET_ID"]]
        for field, cell_key in (("eplaza_uf", "FM_CELL_EPLAZA"), ("impulsa_uf", "FM_CELL_IMPULSA")):
            actual = fm[row[cell_key]].value
            expected = result[field]
            if expected is not None and round(float(actual), 2) != round(float(expected), 2):
                value_bad.append(row[cell_key])
    checks.append(check(not value_bad, "target_values_match_results", sorted(set(value_bad))))
    cached_fm = output_values_wb["FM"]
    cached_bad: list[str] = []
    target_by_total = {row["FM_CELL_TOTAL"]: result_lookup[row["FM_TARGET_ID"]]["total_uf"] for row in rows}
    for cell, expected in target_by_total.items():
        actual = cached_fm[cell].value
        if expected is None or not isinstance(actual, (int, float)) or round(float(actual), 2) != round(float(expected), 2):
            cached_bad.append(cell)
    checks.append(check(not cached_bad, "excel_com_cached_totals_match", sorted(set(cached_bad))))
    conceptual = conceptual_path.read_text(encoding="utf-8")
    missing_diagram_accounts = [row["ACCOUNT_ID"] for row in rows if f'A{row["ACCOUNT_ID"]}' not in conceptual]
    checks.append(check(not missing_diagram_accounts, "diagrams_cover_mapping_matrix", missing_diagram_accounts))
    raw_hashes = {
        "eplaza": sha256(root / "RAW.INPUT/2026.09/Mayor Inmob. Eplaza 2026 09 V 1.xlsb"),
        "impulsa": sha256(root / "RAW.INPUT/2026.09/Mayor Grupo Impulsa 2026 09 V 1.xlsb"),
    }
    checks.append(check(raw_hashes == {"eplaza": "c86ae98d2473921fda4ec70250226e8afd530b28b31450c5ff17fad566c549a8", "impulsa": "02003492b472173860e70b29d7837d10a931984a9ae0ae4e1784ca47a18601c6"}, "raw_hashes_preserved", raw_hashes))
    failed = [item for item in checks if item["status"] != "PASS"]
    report = {
        "verdict": "PASS" if not failed else "FAIL",
        "checks": checks,
        "output_sha256": sha256(output),
        "template_sha256": sha256(template),
        "raw_hashes": raw_hashes,
    }
    report_path = run_dir / "KTMA_FM_INDEPENDENT_QA.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
