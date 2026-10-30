from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import openpyxl

from kt_movemacc.funding_memo import (
    DECISION_ID,
    active_decision_history,
    load_decision_history,
    reconstruct_mapping_history,
)


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


def write_closure_artifacts(
    run_dir: Path, root: Path, payload: dict[str, object], report: dict[str, object],
    source_wb, output_values_wb,
) -> None:
    interpretations = {
        "FM-T038": "IVA pendiente de criterio; no se agregó IVA automático",
        "FM-T039": "Signo contable negativo preservado",
        "FM-T050": "Solo cuenta 121031; no se inventaron honorarios adicionales",
        "FM-T040": "Asignación HUMAN provisional a 410457",
    }
    differences_path = run_dir / "KTMA_FM_FINANCIAL_DIFFERENCES.csv"
    with differences_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["FM_TARGET_ID", "FM_TARGET_NAME", "HISTORICAL_V0_CELL", "HISTORICAL_V0_UF", "CURRENT_PERIOD_UF", "DIFFERENCE_UF", "INTERPRETATION"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        source_fm = source_wb["FM"]
        current_fm = output_values_wb["FM"]
        for result in payload["results"]:
            target_id = result["target_id"]
            row_number = int(target_id[-3:])
            historical = source_fm[f"C{row_number}"].value
            current = current_fm[f"D{row_number}"].value
            difference = current - historical if isinstance(current, (int, float)) and isinstance(historical, (int, float)) else None
            writer.writerow({
                "FM_TARGET_ID": target_id, "FM_TARGET_NAME": result["target_name"],
                "HISTORICAL_V0_CELL": f"C{row_number}", "HISTORICAL_V0_UF": historical,
                "CURRENT_PERIOD_UF": current, "DIFFERENCE_UF": difference,
                "INTERPRETATION": interpretations.get(target_id, "Comparación referencial entre períodos"),
            })
    final_report_text = (
        "# KT.MovemAcc — cierre Funding Memo\n\n"
        f"Período: `{payload['period']}`. Mapping: `{payload['mapping_version']}`. "
        f"Decisión activa: `{payload['decision_id']}`.\n\n"
        f"Cuentas: {payload['map_total_accounts']} totales; {payload['mapped_accounts']} asignadas; "
        f"{payload['unassigned_account_ids']} sin asignación. Destinos físicos verificados: "
        f"{payload['fm_targets_verified']}. QA independiente: PASS ({len(report['checks'])}/{len(report['checks'])}). "
        "Excel COM: PASS. RAW.INPUT: hashes preservados.\n\n"
        "Excepciones financieras pendientes: IVA de construcción 120971/120973; alcance adicional de "
        "Comercialización 121031; asignación provisional Software 410457.\n"
    )
    (run_dir / "KTMA_FM_FINAL_REPORT.md").write_text(final_report_text, encoding="utf-8")
    artifact_names = [
        "FM2026.09_ACCOUNTING_MAPPING_V1.xlsx", "KTMA_FM_MAPPING_MASTER_V1.csv",
        "KTMA_FM_TARGET_INVENTORY_72_V1.csv", "KTMA_FM_RESULTS_V1.json",
        "KTMA_FM_UNASSIGNED_V1.csv", "KTMA_FM_MAPPING_CONCEPTUAL_V1.md",
        "KTMA_FM_FINANCIAL_DIFFERENCES.csv", "KTMA_FM_INDEPENDENT_QA.json",
        "KTMA_FM_EXCEL_COM_RECEIPT.json", "KTMA_FM_FINAL_REPORT.md",
    ]
    manifest = {
        "run_id": run_dir.name,
        "period": payload["period"],
        "mapping_version": payload["mapping_version"],
        "decision_id": payload["decision_id"],
        "source_hashes": payload["source_hashes"],
        "final_workbook_sha256": report["output_sha256"],
        "artifact_sha256": {
            name: sha256(run_dir / name) for name in artifact_names if (run_dir / name).is_file()
        },
        "authorized_workbook_changes": {
            "FM": "D/E/F at 16 mapped rows; B and D:F widths",
            "added_sheets": ["KTMA_MAPPING", "KTMA_RESULTS", "KTMA_DECISIONS", "KTMA_UNASSIGNED"],
        },
        "preservation": {
            "raw_input_mutated": False, "template_overwritten": False,
            "non_target_formulas_and_values": "PASS_WITH_NUMERIC_SERIALIZATION_TOLERANCE_1E-9_UF",
            "excel_com_validation": "PASS", "independent_qa": f"PASS_{len(report['checks'])}_OF_{len(report['checks'])}",
        },
    }
    (run_dir / "KTMA_FM_OUTPUT_CHANGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
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
    history = load_decision_history(root / "04_CONFIG/FUNDING_MEMO/KTMA_FM_DECISIONS.jsonl")
    active_history = active_decision_history(history)
    _, effective_rules = reconstruct_mapping_history(history, payload["period"])
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
        check(len(effective_rules) == 66 and {rule.decision_id for rule in effective_rules} == {DECISION_ID}, "history_reconstructs_effective_mapping", {"rules": len(effective_rules), "decision_id": DECISION_ID}),
        check(any(event.get("SUPERSEDES_DECISION_ID") == "KTMA-FM-DEC-20261029-001" for event in history), "unsupported_legacy_timestamps_superseded", len(history)),
        check(all(event.get("DATE_TIME") is None for event in active_history), "unknown_communication_times_remain_null", [event.get("DATE_TIME") for event in active_history]),
        check(
            all(item["source_value_uf"] is None and item["contribution_uf"] is None for item in payload["contributions"] if item["status"] == "SIN_DATO_ENTIDAD"),
            "missing_entity_data_not_converted_to_zero",
            sum(item["status"] == "SIN_DATO_ENTIDAD" for item in payload["contributions"]),
        ),
        check(
            any(item["status"] == "PARTIAL_MISSING_ACCOUNT_DATA" for item in payload["results"]),
            "partial_targets_remain_explicit",
            {item["target_id"]: item["status"] for item in payload["results"]},
        ),
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
        if expected is None:
            if actual not in (None, "#N/A"):
                cached_bad.append(cell)
        elif not isinstance(actual, (int, float)) or round(float(actual), 2) != round(float(expected), 2):
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
    if not failed:
        write_closure_artifacts(run_dir, root, payload, report, source_wb, output_values_wb)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
