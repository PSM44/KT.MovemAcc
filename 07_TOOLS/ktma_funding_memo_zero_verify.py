from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import openpyxl

from kt_movemacc.engine import parse_xlsb


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    run_dir = Path(args.run_dir).resolve()
    cam_path = root / "90_RUNTIME/PH1_REVIEW/2026.09/RUN_002/CAM2026.09_CONSOL.ALIGN.xlsx"
    raw_paths = {
        "EPLAZA": root / "RAW.INPUT/2026.09/Mayor Inmob. Eplaza 2026 09 V 1.xlsb",
        "IMPULSA": root / "RAW.INPUT/2026.09/Mayor Grupo Impulsa 2026 09 V 1.xlsb",
    }
    raw = {
        entity: {row.code: row for row in parse_xlsb(path) if row.code}
        for entity, path in raw_paths.items()
    }
    mapping = list(csv.DictReader((run_dir / "KTMA_FM_MAPPING_MASTER_V1.csv").open(encoding="utf-8-sig")))
    coverage = list(csv.DictReader((run_dir / "KTMA_FM_ZERO_COVERAGE_V1.csv").open(encoding="utf-8-sig")))
    coverage_by_key = {(row["ACCOUNT_ID"], row["ENTITY"]): row for row in coverage}
    results = json.loads((run_dir / "KTMA_FM_RESULTS_V1.json").read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(cam_path, read_only=True, data_only=False)
    control_ws = wb["CONTROL"]
    control = {
        str(control_ws.cell(row, 1).value): (control_ws.cell(row, 2).value, str(control_ws.cell(row, 3).value or "").lower())
        for row in range(2, control_ws.max_row + 1)
    }
    cam_ws = next(wb[name] for name in wb.sheetnames if "CONSOL.ALIGN" in name)
    headers = {str(cell.value or "").strip(): cell.column for cell in cam_ws[1]}
    cam_rows = {
        str(cam_ws.cell(row, headers["ACCOUNT_CODE"]).value).strip(): row
        for row in range(2, cam_ws.max_row + 1)
        if cam_ws.cell(row, headers["ACCOUNT_CODE"]).value not in (None, "")
    }
    errors: list[str] = []
    for entity, path in raw_paths.items():
        if control.get(f"{entity}_RAW", (None, ""))[1] != sha256(path):
            errors.append(f"RAW_HASH_MISMATCH:{entity}")
        if int(control.get(f"{entity}_ACCOUNTS", (-1, ""))[0]) != len(raw[entity]):
            errors.append(f"RAW_COUNT_MISMATCH:{entity}")
    states = Counter()
    target_totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"EPLAZA": Decimal("0"), "IMPULSA": Decimal("0")})
    for rule in mapping:
        account_id = rule["ACCOUNT_ID"]
        cam_row = cam_rows[account_id]
        coefficient = Decimal(rule["COEFFICIENT"])
        for entity, description_col, value_col, absent_control in (
            ("EPLAZA", "EPLAZA.DESCRIPTION", "EPLAZA.VALORES_UF", "IMPULSA_ONLY"),
            ("IMPULSA", "IMPULSA.DESCRIPTION", "IMPULSA.VALORES_UF", "EPLAZA_ONLY"),
        ):
            source = raw[entity].get(account_id)
            cam_value = Decimal(str(cam_ws.cell(cam_row, headers[value_col]).value)).quantize(Decimal("0.01"))
            description = str(cam_ws.cell(cam_row, headers[description_col]).value or "").strip()
            row_control = str(cam_ws.cell(cam_row, headers["CONTROL"]).value or "")
            if source is None:
                expected_state = "ZERO_VERIFIED"
                if description or cam_value != 0 or row_control != absent_control:
                    errors.append(f"ABSENCE_EVIDENCE_INVALID:{account_id}:{entity}")
                source_value = Decimal("0.00")
            else:
                source_value = Decimal(str(source.bal_uf)).quantize(Decimal("0.01"))
                expected_state = "ZERO_VERIFIED" if source_value == 0 else "VALUE"
                if not description or cam_value != source_value:
                    errors.append(f"RAW_CAM_VALUE_MISMATCH:{account_id}:{entity}")
            evidence_row = coverage_by_key.get((account_id, entity))
            if evidence_row is None or evidence_row["SOURCE_STATE"] != expected_state:
                errors.append(f"COVERAGE_STATE_MISMATCH:{account_id}:{entity}")
            else:
                expected_contribution = source_value * coefficient
                if Decimal(evidence_row["CONTRIBUTION_UF"]) != expected_contribution:
                    errors.append(f"CONTRIBUTION_MISMATCH:{account_id}:{entity}")
                target_totals[rule["FM_TARGET_ID"]][entity] += expected_contribution
            states[expected_state] += 1
    result_by_target = {row["target_id"]: row for row in results["results"]}
    for target_id, entity_values in target_totals.items():
        expected_total = entity_values["EPLAZA"] + entity_values["IMPULSA"]
        result = result_by_target[target_id]
        if any(Decimal(result[field]) != expected for field, expected in (
            ("eplaza_uf", entity_values["EPLAZA"]),
            ("impulsa_uf", entity_values["IMPULSA"]),
            ("total_uf", expected_total),
        )):
            errors.append(f"TARGET_TOTAL_MISMATCH:{target_id}")
    checks = {
        "mapping_rows": len(mapping),
        "coverage_rows": len(coverage),
        "target_count": len(target_totals),
        "states": dict(states),
        "unknown": 0,
        "errors": errors,
    }
    report = {"verdict": "PASS" if not errors and len(mapping) == 66 and len(coverage) == 132 and len(target_totals) == 16 else "FAIL", "checks": checks}
    (run_dir / "KTMA_FM_ZERO_COVERAGE_INDEPENDENT_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
