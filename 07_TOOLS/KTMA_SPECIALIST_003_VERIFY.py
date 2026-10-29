from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook


TASK = "KTMA_SPECIALIST_003"
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "08_EVIDENCE" / "REPORTS"
MAPPING = REPORTS / f"{TASK}_UNIFIED_72_TARGET_MAPPING.csv"
ACCOUNTS = REPORTS / f"{TASK}_ACCOUNT_SOURCE_RECONCILIATION.csv"
EXCEPTIONS = REPORTS / f"{TASK}_AMBIGUITY_EXCEPTIONS.csv"
BRIEF = REPORTS / f"{TASK}_FINANCIAL_RULE_DECISION_BRIEF.md"
QA = REPORTS / f"{TASK}_INDEPENDENT_QA_VERDICT.json"
HYGIENE = REPORTS / f"{TASK}_ROOT_HYGIENE_DELTA_MANIFEST.json"
CLASSIFICATION = REPORTS / "KTMA_SPECIALIST_002_FM_TARGET_CLASSIFICATION.csv"
FAILURES = REPORTS / "KTMA_SPECIALIST_002_FAILURE_CLASSIFICATION.csv"
FM = ROOT / "OUTPUT" / "2026.08" / "FM2026.08_VALIDATION.xlsx"

PROTECTED_EXPECTED = {
    "04_CONFIG/CRITERIA/PH1_CRITERIA_REGISTER.json": "38f81996d5c7f2674ba1fe1bf8020108697be41d54e91075e684f5e876f283b0",
    "10_LEGACY/HISTORICAL_REFERENCES/test.PH02.xlsx": "eda935a5f0e80a5f33ab04fd6b95ed3365d35fb1e0422cbe7b8a54a8f833ee6b",
    "DATA/KTMA.sqlite": "b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0",
    "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx": "5acba7c7c09b743f53b7d5734a9042712d8116a1aaab9df0d54349218dbce5ec",
    "OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx": "eda935a5f0e80a5f33ab04fd6b95ed3365d35fb1e0422cbe7b8a54a8f833ee6b",
    "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb": "b074626b2380646b5c563492e66b4d0a19714d817e4e9c1f52ba310cadd1de43",
    "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb": "bca421c1a730fee0d44607d9bb0af49bea0407345d852e96c7135508585025c5",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def check(condition: bool, name: str, detail: object) -> dict[str, object]:
    return {"check": name, "status": "PASS" if condition else "FAIL", "detail": detail}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def main() -> int:
    refresh = os.environ.get("KTMA_SPECIALIST_003_REFRESH") == "1"
    if (QA.exists() or HYGIENE.exists()) and not refresh:
        raise FileExistsError("refusing to overwrite QA or hygiene output")
    mapping = read_csv(MAPPING)
    accounts = read_csv(ACCOUNTS)
    exceptions = read_csv(EXCEPTIONS)
    source_targets = read_csv(CLASSIFICATION)
    failures = read_csv(FAILURES)
    checks: list[dict[str, object]] = []

    expected_destinations = {f"FM!{r['target_cell']}" for r in source_targets}
    actual_destinations = {r["fm_destination"] for r in mapping}
    checks.append(check(len(mapping) == 72 and actual_destinations == expected_destinations,
                        "coverage_72_exact_set", {"rows": len(mapping), "unique": len(actual_destinations)}))
    accounting = [r for r in mapping if r["destination_class"] == "ACCOUNTING_INPUT"]
    non_accounting = [r for r in mapping if r["destination_class"] != "ACCOUNTING_INPUT"]
    checks.append(check(len(accounting) == 42 and len(non_accounting) == 30,
                        "classification_denominators", {"accounting": len(accounting), "non_accounting": len(non_accounting)}))
    accounting_states = Counter(r["mapping_state"] for r in accounting)
    checks.append(check(accounting_states == {"VERIFIED_TECHNICAL": 15, "AMBIGUOUS": 18, "UNMAPPED": 9},
                        "accounting_state_counts", dict(accounting_states)))

    source_classes = Counter(r["intended_source_class"] for r in non_accounting)
    checks.append(check(source_classes == {"EXTERNAL_BUSINESS_SOURCE": 20, "UNKNOWN": 8, "DERIVED_FINANCIAL_RESULT": 2},
                        "non_accounting_source_classes", dict(source_classes)))
    checks.append(check(all(r["human_approval_status"] == "PENDING_NOT_INFERRED" for r in mapping),
                        "no_human_approval_inferred", Counter(r["human_approval_status"] for r in mapping)))
    checks.append(check(all(r["qa_outcome"].startswith("I2_PASS_") for r in mapping),
                        "row_level_qa_outcomes_recorded", Counter(r["qa_outcome"] for r in mapping)))

    # Independent workbook oracle: inspect the actual E/F cells and preserved formulas.
    wb_formula = load_workbook(FM, data_only=False, read_only=True)
    wb_values = load_workbook(FM, data_only=True, read_only=True)
    ws_f = wb_formula["FM"]
    ws_v = wb_values["FM"]
    target_cells = [r["fm_destination"].split("!")[1] for r in mapping]
    blank_cells = [c for c in target_cells if ws_f[c].value is None and ws_v[c].value is None]
    checks.append(check(len(blank_cells) == 72, "all_destination_cells_physically_blank", {"blank": len(blank_cells), "total": 72}))
    expected_formulas = {
        "E63": "=E22-E59", "F63": "=F22-F59", "E67": "=E63-E65", "F67": "=F63-F65",
        "E70": "=E67-E69", "F70": "=F67-F69", "E73": "=E63/E59", "F73": "=F63/F59",
    }
    observed_formulas = {cell: ws_f[cell].value for cell in expected_formulas}
    checks.append(check(observed_formulas == expected_formulas, "formula_preservation", observed_formulas))
    checks.append(check(ws_f["E61"].value is None and ws_f["F61"].value is None,
                        "iva_not_existing_formula", {"E61": ws_f["E61"].value, "F61": ws_f["F61"].value}))
    wb_formula.close()
    wb_values.close()

    # Separate arithmetic/provenance oracle over the account-level evidence.
    balance_failures = []
    source_hash_failures = []
    seen_by_destination: dict[str, set[str]] = defaultdict(set)
    for row in accounts:
        uf_ok = abs((Decimal(row["debit_uf"]) - Decimal(row["credit_uf"])) - Decimal(row["balance_uf"])) <= Decimal("0.01")
        clp_ok = abs((Decimal(row["debit_clp"]) - Decimal(row["credit_clp"])) - Decimal(row["balance_clp"])) <= Decimal("0.01")
        if not (uf_ok and clp_ok):
            balance_failures.append({"destination": row["fm_destination"], "account": row["account_code"]})
        raw_name = row["raw_workbook"].replace("\\", "/").split("/")[-1]
        raw_path = ROOT / "RAW.INPUT" / "2026.08" / raw_name
        if sha256(raw_path) != row["raw_sha256"]:
            source_hash_failures.append(str(raw_path.relative_to(ROOT)))
        key = f"{row['entity']}:{row['account_code']}"
        if key in seen_by_destination[row["fm_destination"]]:
            balance_failures.append({"destination": row["fm_destination"], "account": row["account_code"], "cause": "DUPLICATE_ACCOUNT_ROW"})
        seen_by_destination[row["fm_destination"]].add(key)
    checks.append(check(not balance_failures, "account_debit_minus_credit_identity", {"rows": len(accounts), "failures": balance_failures}))
    checks.append(check(not source_hash_failures, "raw_source_provenance_hash", {"failures": source_hash_failures}))

    verified = [r for r in accounting if r["mapping_state"] == "VERIFIED_TECHNICAL"]
    verified_members = defaultdict(list)
    for row in accounts:
        if row["mapping_state"] == "VERIFIED_TECHNICAL":
            verified_members[f"{row['entity']}:{row['account_code']}"] .append(row["fm_destination"])
    overlaps = {k: v for k, v in verified_members.items() if len(v) > 1}
    checks.append(check(len(verified) == 15 and not overlaps, "verified_mapping_non_overlap", {"verified": len(verified), "overlaps": overlaps}))
    checks.append(check(len(exceptions) == 27 and Counter(r["state"] for r in exceptions) == {"AMBIGUOUS": 18, "UNMAPPED": 9},
                        "accounting_exception_coverage", Counter(r["state"] for r in exceptions)))

    fail_causes = Counter(r["likely_root_cause"] for r in failures)
    retained = all(r["retained_status"] == "FAIL_NOT_RECLASSIFIED" for r in failures)
    checks.append(check(len(failures) == 32 and fail_causes == {"SOURCE_SEMANTIC_MISMATCH": 32} and retained,
                        "ph1_semantic_failures_preserved", {"rows": len(failures), "causes": dict(fail_causes), "retained": retained}))

    protected_actual = {path: sha256(ROOT / path) for path in PROTECTED_EXPECTED}
    checks.append(check(protected_actual == PROTECTED_EXPECTED, "protected_financial_hashes_preserved",
                        {"expected": PROTECTED_EXPECTED, "actual": protected_actual}))
    failed = [c for c in checks if c["status"] != "PASS"]
    qa_verdict = {
        "task_id": TASK,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "independence": "I2_SEPARATE_READ_ONLY_ORACLE; SAME_ORGANIZATIONAL_EXECUTOR; NOT_EXTERNAL_AUDIT",
        "method": ["exact-set CSV reconciliation", "actual XLSX formula/value inspection", "independent debit-credit identities", "source/protected SHA256", "verified-account overlap oracle"],
        "checks": checks,
        "verdict": "PARTIAL_PASS" if not failed else "FAIL",
        "interpretation": "Evidence package is internally consistent and preserves sources; goal remains PARTIAL_MAPPING because 18 accounting mappings are ambiguous, 9 are unmapped, 28 non-accounting inputs are unmapped and no HUMAN approval exists.",
        "mapping_state_counts": dict(Counter(r["mapping_state"] for r in mapping)),
        "failures": failed,
    }
    QA.write_text(json.dumps(qa_verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    malformed_tree = ROOT / "C\uf03a"
    malformed_files = [p for p in malformed_tree.rglob("*") if p.is_file()] if malformed_tree.exists() else []
    odd_files = [p for p in ROOT.iterdir() if p.is_file() and "KTMA_TASK062_STRUCTURAL_HIERARCHY_RECONCILIATION_REPORT.md" in p.name]
    lock_files = list((ROOT / "RAW.INPUT").rglob("~$*")) + list((ROOT / "OUTPUT").rglob("~$*"))
    backup_tests = [p for p in (ROOT / "08_EVIDENCE" / "BACKUPS").rglob("*") if p.is_file() and any(part in {"test_n9a", "test_output"} for part in p.parts)]
    durable = [
        ROOT / "07_TOOLS" / f"{TASK}_ANALYZER.py", ROOT / "07_TOOLS" / f"{TASK}_VERIFY.py",
        MAPPING, ACCOUNTS, EXCEPTIONS, BRIEF, QA,
    ]
    artifact_entries = [{
        "path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(p), "bytes": p.stat().st_size,
        "purpose": "REPRODUCIBLE_EVIDENCE_TOOL" if p.suffix == ".py" else "IMMUTABLE_DURABLE_TASK_EVIDENCE",
        "owner": "KTMA_SPECIALIST_003/SPECIALIST_TO_MORCH", "retention": "PRESERVE_UNTIL_MORCH_OR_HUMAN_DISPOSITION",
        "canonical_financial_source": False,
    } for p in durable]
    cache_path = ROOT / "07_TOOLS" / "__pycache__" / "KTMA_SPECIALIST_003_ANALYZER.cpython-313.pyc"
    hygiene = {
        "task_id": TASK,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
        "root_hygiene_status": "PARTIAL_COVERAGE_BLOCKED_BY_AUTHORIZATION_NOT_CLEAN_VERIFIED",
        "durable_new_artifacts": artifact_entries,
        "self_manifest_hash": "NOT_RECORDED_TO_AVOID_SELF_REFERENCE",
        "misplaced_artifacts": {"malformed_tree_files": len(malformed_files), "malformed_root_name_files": len(odd_files), "total": len(malformed_files) + len(odd_files), "classification": "UNKNOWN_HOLD_NO_MOVE_NO_DELETE"},
        "backups_test_files": {"count": len(backup_tests), "classification": "PRE_EXISTING_TEST_FILES_IN_BACKUPS_REQUIRE_AUTHORIZED_DISPOSITION"},
        "excel_lock_snapshot": {"count": len(lock_files), "paths": [str(p.relative_to(ROOT)) for p in lock_files], "interpretation": "SNAPSHOT_ONLY; absence is not deletion authority"},
        "qa_skill_authority": "HUMAN_APPROVAL_CONFIRMED_BY_CURRENT_DIRECTIVE_AND_03_DOCS/HUMAN/UseCase_PHASE1.md:204; FILE_PLACEMENT_OBSERVED; KTMA_DISCOVERY_INSTALLATION_RUNTIME_ENFORCEMENT_NOT_PROVEN; EMBEDDED_CANDIDATE_STATUS_CONFLICTS",
        "protected_hashes": protected_actual,
        "unexpected_mutations": ([{"path": str(cache_path.relative_to(ROOT)), "classification": "UNEXPECTED_PYTHON_BYTECODE_RESIDUE", "action": "RETAINED_DUE_TO_NO_CLEANUP_PROHIBITION"}] if cache_path.exists() else []),
        "unauthorized_financial_mutations": [],
        "cleanup_actions": [],
        "git_status_short_after": git("status", "--short"),
    }
    HYGIENE.write_text(json.dumps(hygiene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"qa_verdict": qa_verdict["verdict"], "checks": Counter(c["status"] for c in checks), "manifest": str(HYGIENE)} , default=dict))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
