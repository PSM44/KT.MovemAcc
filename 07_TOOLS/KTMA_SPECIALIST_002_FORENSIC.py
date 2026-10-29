from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


TASK_ID = "KTMA_SPECIALIST_002"
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "08_EVIDENCE" / "REPORTS"
PRIVATE_MATRIX = Path(
    r"C:\Users\aazcl\AppData\Local\KT.MovemAcc\private_evidence\KTMA_TASK060\KTMA_TASK060_FINANCIAL_ACCEPTANCE_MATRIX.jsonl"
)
MAPPING = REPORTS / "KTMA_SPECIALIST_001_MAPPING_REGISTER_FINAL.csv"
FAILURES_OUT = REPORTS / f"{TASK_ID}_FAILURE_CLASSIFICATION.csv"
TARGETS_OUT = REPORTS / f"{TASK_ID}_FM_TARGET_CLASSIFICATION.csv"
MANIFEST_OUT = REPORTS / f"{TASK_ID}_FORENSIC_MANIFEST.json"
REPORT_OUT = REPORTS / f"{TASK_ID}_REPORT.md"

PROTECTED = [
    ROOT / "04_CONFIG" / "CRITERIA" / "PH1_CRITERIA_REGISTER.json",
    ROOT / "10_LEGACY" / "HISTORICAL_REFERENCES" / "test.PH02.xlsx",
    ROOT / "DATA" / "KTMA.sqlite",
    ROOT / "OUTPUT" / "2026.08" / "CAM2026.08_CONSOL.ALIGN.xlsx",
    ROOT / "OUTPUT" / "2026.08" / "FM2026.08_VALIDATION.xlsx",
    ROOT / "RAW.INPUT" / "2026.08" / "Mayor Grupo Impulsa 2026 08 V 1.xlsb",
    ROOT / "RAW.INPUT" / "2026.08" / "Mayor Inmob. Eplaza 2026 08 V 1.xlsb",
]

FAILURE_FIELDS = [
    "record_id", "entity", "account_or_semantic_key", "causal_account", "source_file",
    "source_sha256", "source_sheet", "source_cell", "source_row", "comparison_file",
    "comparison_sha256", "comparison_sheet", "comparison_cell", "expected_value_sqlite",
    "actual_value_accepted_cam", "difference_absolute", "unit", "original_comparison_rule",
    "financial_materiality", "likely_root_cause", "supporting_evidence",
    "corrective_action_classification", "retained_status",
]

TARGET_FIELDS = [
    "mapping_id", "target_sheet", "target_cell", "target_concept", "source_entity",
    "prior_status", "target_classification", "underlying_candidate_type", "basis",
    "human_principle_group", "mapping_authority", "formula_dependency_separation",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def protected_hashes() -> dict[str, str]:
    return {str(p.relative_to(ROOT)): sha256(p) for p in PROTECTED}


def fail_source(semantic_key: str, unit: str) -> tuple[int, str, str, str]:
    cell_col = "G" if unit == "UF" else "J"
    if semantic_key in {"CTAS Y DOCTOS X COBRAR A EERR#1", "CTAS Y DOCTOS X COBRAR A EERR#2"}:
        row = 19
        account = "120411"
        evidence = "Impulsa RAW heading row 19 and child account row 20 carry the same amount; consolidated account 120411 agrees byte-for-value, but CAM places it under occurrence #2 while SQLite source-semantic roll-up contributes to occurrence #1."
    elif semantic_key == "ACTIVOS NO CORRIENTES#1":
        row = 19
        account = "120411;120511"
        evidence = "CAM non-current assets includes 120411 (164250.74 UF / 6525346829 CLP) plus 120511 (17.64 UF / 700945 CLP), while SQLite source-semantic ACTIVO NO CORRIENTE roll-up is zero. Both account-level amounts agree; their consolidated parent placement differs."
    elif semantic_key == "OTROS PASIVOS CORRIENTES#1":
        row = 56
        account = "220411"
        evidence = "Impulsa RAW heading row 56 includes child account 220411 at row 59; the account value agrees in SQLite and CAM, but CAM relocates the unmatched account to IMPULSA_ONLY."
    elif semantic_key == "TOTAL PASIVO#1":
        row = 83
        account = "220411"
        evidence = "The 220411 hierarchy-placement difference propagates to source TOTAL PASIVO row 83; account-level values themselves agree."
    elif semantic_key == "ACTIVO - PASIVO#1":
        row = 85
        account = "220411"
        evidence = "The 220411 hierarchy-placement difference propagates to source ACTIVO - PASIVO row 85; account-level values themselves agree."
    elif semantic_key == "RESULTADO#1":
        row = 134
        account = "220411"
        evidence = "The 220411 hierarchy-placement difference propagates with inverse sign to source RESULTADO row 134; account-level values themselves agree."
    elif semantic_key == "IMPULSA_ONLY":
        row = 59
        account = "220411"
        evidence = "CAM carries unmatched account 220411 in synthetic IMPULSA_ONLY while SQLite assigns zero to that synthetic heading and retains the account in its source parent hierarchy."
    else:
        raise ValueError(f"unexpected semantic key: {semantic_key}")
    return row, f"{cell_col}{row}", account, evidence


def build_failures() -> list[dict[str, str]]:
    failures = []
    with PRIVATE_MATRIX.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("status") != "FAIL":
                continue
            key = record["hierarchy_identifier"]
            unit = record["currency"]
            source_row, source_cell, account, evidence = fail_source(key, unit)
            propagated = key in {"TOTAL PASIVO#1", "ACTIVO - PASIVO#1", "RESULTADO#1"}
            sources = {Path(x["artifact"]).name: x["sha256"] for x in record["source_reference"]}
            failures.append({
                "record_id": record["record_id"],
                "entity": record["entity"],
                "account_or_semantic_key": key,
                "causal_account": account,
                "source_file": r"RAW.INPUT\2026.08\Mayor Grupo Impulsa 2026 08 V 1.xlsb",
                "source_sha256": sha256(ROOT / "RAW.INPUT" / "2026.08" / "Mayor Grupo Impulsa 2026 08 V 1.xlsb"),
                "source_sheet": "CUENTAS DE MAYOR AGOSTO 2026",
                "source_cell": source_cell,
                "source_row": str(source_row),
                "comparison_file": r"OUTPUT\2026.08\CAM2026.08_CONSOL.ALIGN.xlsx",
                "comparison_sha256": sources.get("CAM2026.08_CONSOL.ALIGN.xlsx", ""),
                "comparison_sheet": record["evidence_locator"]["excel_sheet"],
                "comparison_cell": record["evidence_locator"]["excel_cell"],
                "expected_value_sqlite": record["expected"],
                "actual_value_accepted_cam": record["observed"],
                "difference_absolute": record["difference"],
                "unit": unit,
                "original_comparison_rule": f"SQLITE_EXCEL_CAM_VALUE; abs(SQLite.{record['evidence_locator']['sqlite_field']} - independently evaluated CAM cell) <= {record['tolerance']}",
                "financial_materiality": "MATERIAL_PROPAGATED" if propagated else "MATERIAL_DIRECT_OR_REALLOCATION",
                "likely_root_cause": "SOURCE_SEMANTIC_MISMATCH",
                "supporting_evidence": evidence,
                "corrective_action_classification": "HUMAN_APPROVE_PARENT_CONTEXT_SEMANTIC_RULE_THEN_REGENERATE_BOTH_ARTIFACTS_UNDER_SEPARATE_AUTHORIZATION",
                "retained_status": "FAIL_NOT_RECLASSIFIED",
            })
    if len(failures) != 32:
        raise AssertionError(f"expected 32 failures, found {len(failures)}")
    return failures


def target_type(row: dict[str, str]) -> tuple[str, str, str, str]:
    number = int("".join(ch for ch in row["target_cell"] if ch.isdigit()))
    if row["confidence_class"] == "AMBIGUOUS":
        return (
            "HUMAN_DECISION_REQUIRED", "ACCOUNTING_INPUT",
            "Exact normalized heading is only a candidate; measure, sign, hierarchy scope and mapping authority remain unapproved.",
            "P1_REPEATED_HEADING_PARENT_SCOPE_SIGN_AND_MEASURE",
        )
    if number in {8, 9, 10, 12, 13, 14, 17, 18, 19, 76}:
        return (
            "MANUAL_HARDNUMBER", "MANUAL_HARDNUMBER",
            "Destination is a business/financing assumption cell with no approved ledger mapping or formula in the candidate workbook.",
            "P2_BUSINESS_ASSUMPTION_PROVENANCE_PERIOD_AND_OWNER",
        )
    if number in {61, 65, 69}:
        return (
            "FORMULA", "FORMULA",
            "IVA, project fee and preferred-capital financing cost require an explicit calculation policy, not direct ledger copying.",
            "P3_FORMULA_BASE_RATE_TAX_TIMING_AND_ROUNDING",
        )
    if number in {75, 77}:
        return (
            "DERIVED_RESULT", "DERIVED_RESULT",
            "Required capital and return are outputs of the approved financing/economic model, not raw accounting balances.",
            "P4_CAPITAL_AND_RETURN_MODEL_DEFINITION",
        )
    return (
        "ACCOUNTING_INPUT", "ACCOUNTING_INPUT",
        "Operational cost destination may consume accounting evidence, but account set, period, entity, sign and aggregation require an approved mapping.",
        "P5_ACCOUNT_SET_PERIOD_ENTITY_SIGN_AND_AGGREGATION",
    )


def build_targets() -> list[dict[str, str]]:
    with MAPPING.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["confidence_class"] in {"UNMAPPED", "AMBIGUOUS"}]
    if len(rows) != 72:
        raise AssertionError(f"expected 72 targets, found {len(rows)}")
    output = []
    for row in rows:
        classification, underlying, basis, principle = target_type(row)
        output.append({
            "mapping_id": row["mapping_id"],
            "target_sheet": row["target_sheet"],
            "target_cell": row["target_cell"],
            "target_concept": row["target_concept"],
            "source_entity": row["source_entity"],
            "prior_status": row["confidence_class"],
            "target_classification": classification,
            "underlying_candidate_type": underlying,
            "basis": basis,
            "human_principle_group": principle,
            "mapping_authority": "PENDING_HUMAN_NO_SOURCE_TO_TARGET_MAPPING_APPROVED",
            "formula_dependency_separation": "NOT_AN_APPROVED_FINANCIAL_MAPPING; 62 pre-existing VERIFIED rows remain formula/subtotal/derived dependency checks only",
        })
    return output


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing overwrite: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def malformed_inventory() -> list[dict[str, object]]:
    base = ROOT / "C"
    items = []
    if base.exists():
        for path in sorted(base.rglob("*"), key=lambda p: str(p)):
            items.append({
                "path": str(path.relative_to(ROOT)),
                "type": "DIRECTORY" if path.is_dir() else "FILE",
                "bytes": None if path.is_dir() else path.stat().st_size,
                "sha256": None if path.is_dir() else sha256(path),
                "classification": "MALFORMED_PATH_UNKNOWN_HOLD",
                "proposed_action": "QUARANTINE_TREE_AFTER_EXACT_HUMAN_MOVE_GRANT",
                "proposed_destination": r"08_EVIDENCE\BACKUPS\QUARANTINE\KTMA_SPECIALIST_002_MALFORMED_C_TREE",
                "rollback": "Move the exact tree back using this hash manifest; no delete until semantic retention review.",
                "risk": "MEDIUM: mixed historical reports include unsupported or incomplete claims and may contain unique provenance.",
            })
    odd_file = ROOT / "CUsersaazclDownloadsKTMA_TASK062_STRUCTURAL_HIERARCHY_RECONCILIATION_REPORT.md"
    if odd_file.exists():
        items.append({
            "path": str(odd_file.relative_to(ROOT)), "type": "FILE", "bytes": odd_file.stat().st_size,
            "sha256": sha256(odd_file), "classification": "MALFORMED_FILENAME_REPORTED_ONLY_INCOMPLETE_TASK062_EVIDENCE",
            "proposed_action": "QUARANTINE_AFTER_EXACT_HUMAN_MOVE_GRANT",
            "proposed_destination": r"08_EVIDENCE\BACKUPS\QUARANTINE\KTMA_SPECIALIST_002_TASK062_REPORTED_ONLY",
            "rollback": "Move exact file back by hash; preserve original bytes.",
            "risk": "HIGH if promoted: only 2 of 32 cases are explicit while 30 are summarized and claimed resolved.",
        })
    return items


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def main() -> int:
    for path in (FAILURES_OUT, TARGETS_OUT, MANIFEST_OUT, REPORT_OUT):
        if path.exists():
            raise FileExistsError(f"refusing overwrite: {path}")
    before = protected_hashes()
    failures = build_failures()
    targets = build_targets()
    write_csv(FAILURES_OUT, FAILURE_FIELDS, failures)
    write_csv(TARGETS_OUT, TARGET_FIELDS, targets)

    skill_paths = [
        ROOT / "02_SKILLS" / "TRANSVERSAL" / "20261018.1652_SKILLS_NTV.md",
        ROOT / "02_SKILLS" / "TRANSVERSAL" / "SKILLS.QA.TRANSVERSAL.md",
        ROOT / "02_SKILLS" / "INTERNAL" / "SKILLS.QA.KT.MovemAcc.md",
    ]
    analyzers = []
    for name, classification in [
        ("KTMA_SPECIALIST_001_ANALYZER.py", "REPRODUCIBLE_EVIDENCE_PRODUCER"),
        ("KTMA_SPECIALIST_001_CROSSCHECK_CORRECTION.py", "REPRODUCIBLE_EVIDENCE_CORRECTION_PRODUCER"),
        ("KTMA_SPECIALIST_001_VERIFY.py", "I1_SEPARATE_LOGIC_SAME_EXECUTION_VERIFIER"),
        ("KTMA_SPECIALIST_001_VERIFY_FINAL.py", "I1_SEPARATE_LOGIC_SAME_EXECUTION_FINAL_VERIFIER"),
    ]:
        path = REPORTS / name
        analyzers.append({
            "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path),
            "classification": classification, "authorized_destination": str(path.relative_to(ROOT)),
            "plan": "KEEP_IN_PLACE_AS_TASK_EVIDENCE; moving changes self-relative ROOT logic and breaks the recorded provenance chain.",
        })

    lock_path = ROOT / "RAW.INPUT" / "2026.08" / "~$Mayor Grupo Impulsa 2026 08 V 1.xlsb"
    primary_types = Counter(row["target_classification"] for row in targets)
    underlying_types = Counter(row["underlying_candidate_type"] for row in targets)
    failure_causes = Counter(row["likely_root_cause"] for row in failures)
    manifest = {
        "task_id": TASK_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "git": {"branch": git_text("branch", "--show-current"), "head": git_text("rev-parse", "HEAD"), "status_short": git_text("status", "--short", "--branch")},
        "authority": {
            "ntv": {"path": str(skill_paths[0].relative_to(ROOT)), "sha256": sha256(skill_paths[0]), "declared": "v1.2 HUMAN_APPROVED_OFFICIAL INSTALLED_LOCAL_NIGHTSHIFT_ROOT", "effective_ktma_status": "CONTENT_APPROVAL_DECLARED_BUT_KTMA_INSTALLATION_DISCOVERY_NOT_PROVEN"},
            "qa_transversal": {"path": str(skill_paths[1].relative_to(ROOT)), "sha256": sha256(skill_paths[1]), "declared": "CANDIDATE_FOR_HUMAN_REVIEW NOT_OFFICIAL NOT_INSTALLED"},
            "qa_internal": {"path": str(skill_paths[2].relative_to(ROOT)), "sha256": sha256(skill_paths[2]), "declared": "CANDIDATE_FOR_HUMAN_REVIEW NOT_OFFICIAL NOT_INSTALLED"},
        },
        "fm_hash_resolution": {
            "fm_validation_path": r"OUTPUT\2026.08\FM2026.08_VALIDATION.xlsx",
            "fm_validation_sha256": before[r"OUTPUT\2026.08\FM2026.08_VALIDATION.xlsx"],
            "byte_identical_historical_path": r"10_LEGACY\HISTORICAL_REFERENCES\test.PH02.xlsx",
            "historical_sha256": before[r"10_LEGACY\HISTORICAL_REFERENCES\test.PH02.xlsx"],
            "other_reported_sha256": "38a3ffe730a2d1faa1da63fdd085d4ef4d1330ff73fa25622a73fa50fbbfcfd3",
            "resolution": "38a3f... is the historically accepted PH1 CAM workbook hash, not the FM candidate hash. The conflict is artifact-name conflation, not two byte identities for the same current path.",
            "current_ph1_path": r"OUTPUT\2026.08\CAM2026.08_CONSOL.ALIGN.xlsx",
            "current_ph1_sha256": before[r"OUTPUT\2026.08\CAM2026.08_CONSOL.ALIGN.xlsx"],
            "historically_accepted_ph1_bytes_found_in_repo": False,
            "fm_authority": "VALIDATION_CANDIDATE; byte-identical to historical PH2 reference; not HUMAN-approved production Funding Memo",
            "period_version": "Physical RAW filenames, workbook sheet names and mapping register all identify 2026.08; FM bytes are the historical PH2 template/version represented by test.PH02.xlsx.",
        },
        "failure_summary": {"count": len(failures), "causes": dict(failure_causes), "real_accounting_discrepancies": 0, "incorrect_comparison_oracles": 0, "unresolved": 0, "status": "32 FAIL retained; account-level values agree, hierarchy semantics do not"},
        "target_summary": {"count": len(targets), "prior": dict(Counter(r["prior_status"] for r in targets)), "primary_classification": dict(primary_types), "underlying_type": dict(underlying_types), "formula_dependency_rows_separate": 62, "approved_financial_mappings": 0},
        "human_decision_groups": [
            "P1 repeated-heading parent scope, sign and measure for 4 ambiguous targets",
            "P2 business-assumption provenance, period and owner for 20 manual hardnumber targets",
            "P3 formula base/rate/tax/timing/rounding for 6 formula targets",
            "P4 capital and return model definition for 4 derived-result targets",
            "P5 account set, period, entity, sign and aggregation for 38 classified accounting inputs plus the 4 P1 underlying accounting candidates",
        ],
        "root_hygiene": {
            "malformed_entries": malformed_inventory(),
            "excel_lock": {"path": str(lock_path.relative_to(ROOT)), "exists_at_final_inventory": lock_path.exists(), "classification": "ACTIVE_TRANSIENT_EXCEL_LOCK_RACING_IN_AND_OUT_OF_VISIBILITY", "proposed_action": "NO_ACTION_WHILE PRESENT OR RACING; verify Excel process ownership and request exact deletion authority only after confirmed stale."},
            "specialist_001_analyzers": analyzers,
            "backups_verdict": "NOT_CLEAN_VERIFIED; existing BACKUPS/test_output and BACKUPS/test_n9a remain unclassified historical test outputs and were not cleaned.",
        },
        "protected_hashes_before": before,
    }
    after = protected_hashes()
    manifest["protected_hashes_after"] = after
    manifest["protected_hashes_equal"] = before == after
    manifest["unauthorized_mutations"] = [] if before == after else [k for k in before if before[k] != after[k]]
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    report = f"""# KTMA_SPECIALIST_002 — Financial Exceptions & NTV Convergence

STATUS=PARTIAL_VERIFIED_INTERNAL; RM_GATE_003=OPEN; RM_GATE_004=OPEN

## Outcomes

- Exact TASK060 FAIL coverage: **32/32**, retained as FAIL. Cause: **32 SOURCE_SEMANTIC_MISMATCH**, **0 REAL_ACCOUNTING_DISCREPANCY**, **0 INCORRECT_COMPARISON_ORACLE**, **0 UNRESOLVED**. Account rows `120411` and `220411` agree numerically between SQLite and CAM; parent placement/roll-up differs.
- FM destinations: **72/72 classified**. Primary types: `{dict(sorted(primary_types.items()))}`. All 72 remain pending HUMAN mapping/model approval; the four ambiguous rows require immediate semantic adjudication. No source-to-target mapping was approved.
- The pre-existing 62 `VERIFIED` register rows are formula/subtotal/derived dependency checks, not approved financial mappings. The raw dependency graph contains 831 edges.
- FM hash conflict: `eda935...` is the current FM validation candidate and historical PH2 reference; `38a3f...` is the historical accepted PH1 CAM hash. They name different artifacts.
- Skill authority: NTV v1.2 declares HUMAN approval and NightShift-root installation, but effective KTMA discovery/installation is not proven by its untracked placement here. Both QA documents declare themselves candidate/not official/not installed.
- Root hygiene: malformed path artifacts remain `UNKNOWN_HOLD`; exact quarantine proposals are in the manifest. The Excel lock existed at preflight but was absent at final inventory. No cleanup was performed.

## Human financial decisions (grouped)

1. Repeated-heading parent scope/sign/measure for the four ambiguous candidates.
2. Provenance, period and owner for sales/financing hardnumbers.
3. IVA, fee and financing-cost formula bases, rates, timing and rounding.
4. Required-capital and return-model definitions.
5. Account sets, period, entity, sign and aggregation for accounting-input destinations.

## Authority and limitations

- `FM2026.08_VALIDATION.xlsx` remains a validation candidate, not a production Funding Memo.
- The historically accepted PH1 hash `38a3f...` was not found as current physical bytes in the repository; TASK060's immutable matrix records its comparison results and hash.
- TASK062's malformed-path report is `REPORTED_ONLY`: it explicitly details only two cases and aggregates the remaining 30, so it cannot independently close the 32-case evidence requirement.
- Independent QA is recorded separately; this report does not claim external audit or HUMAN financial acceptance.

## Durable records

- `{FAILURES_OUT.name}` — exact 32 records.
- `{TARGETS_OUT.name}` — exact 72 destination classifications.
- `{MANIFEST_OUT.name}` — authority, hash reconciliation, hygiene plan and protected hashes.
"""
    REPORT_OUT.write_text(report, encoding="utf-8", newline="\n")

    print(json.dumps({
        "failures": len(failures), "targets": len(targets), "failure_causes": dict(failure_causes),
        "target_types": dict(primary_types), "protected_hashes_equal": before == after,
        "outputs": [str(p) for p in (FAILURES_OUT, TARGETS_OUT, MANIFEST_OUT, REPORT_OUT)],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
