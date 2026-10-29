"""KTMA_TASK080 stable PH1 audit identity and registry regressions."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import openpyxl
import pytest

from kt_movemacc import engine


ROOT = Path(__file__).resolve().parents[1]
PERIOD = "2026.08"
RAW_EPLAZA = ROOT / "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb"
RAW_IMPULSA = ROOT / "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb"
CANONICAL = ROOT / "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"
REGISTRY = ROOT / "04_CONFIG/CRITERIA/PH1_AUDIT_DECISIONS.json"
RUN_ROOT = ROOT / "90_RUNTIME/KTMA_TASK080_AUDIT_IDS/RUN_002"
LAB_WORKBOOK = RUN_ROOT / "CAM2026.08_CONSOL.ALIGN.xlsx"
LAB_EVIDENCE = RUN_ROOT / "TASK080_LAB_EVIDENCE.json"

PROTECTED = {
    "RAW.INPUT/2026.08/MANIFEST.json": "04a1154167649317226f3463e2c5b4ab5b828086d12ae6817b5e0ff263c6c96f",
    "RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb": "b074626b2380646b5c563492e66b4d0a19714d817e4e9c1f52ba310cadd1de43",
    "RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb": "bca421c1a730fee0d44607d9bb0af49bea0407345d852e96c7135508585025c5",
    "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx": "5acba7c7c09b743f53b7d5734a9042712d8116a1aaab9df0d54349218dbce5ec",
    "OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx": "eda935a5f0e80a5f33ab04fd6b95ed3365d35fb1e0422cbe7b8a54a8f833ee6b",
    "OUTPUT/2026.08/KTMA_PH1_REPORT.json": "eed04df319538e62bb51d596ef5bcbfcbf1f16b50997255fae3a76c1869bf04a",
    "DATA/KTMA.sqlite": "b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected_hashes() -> dict[str, str]:
    return {relative: _sha256(ROOT / relative) for relative in PROTECTED}


@pytest.fixture(scope="session")
def generated():
    protected_before = _protected_hashes()
    assert protected_before == PROTECTED
    assert not RUN_ROOT.exists(), f"TASK080 runtime collision; refusing overwrite: {RUN_ROOT}"
    RUN_ROOT.mkdir(parents=True, exist_ok=False)

    ep_rows = engine.parse_xlsb(RAW_EPLAZA)
    im_rows = engine.parse_xlsb(RAW_IMPULSA)
    aligned = engine.align(ep_rows, im_rows)
    workbook, metrics, entries = engine.write_workbook(
        PERIOD, ep_rows, im_rows, aligned, RAW_EPLAZA, RAW_IMPULSA
    )
    workbook.save(LAB_WORKBOOK)
    evidence = {
        "TASK_ID": "KTMA_TASK080",
        "LAB_ONLY": True,
        "PRODUCTIVE_TRUST": "NOT_ENFORCED",
        "workbook": str(LAB_WORKBOOK),
        "audit_rows": len(entries),
        "severity_counts": dict(Counter(entry.severity for entry in entries)),
        "unique_audit_ids": len({entry.audit_id for entry in entries}),
        "unique_observation_ids": len({entry.observation_id for entry in entries}),
        "identity_adjudication_required": sum(
            entry.identity_status == "IDENTITY_ADJUDICATION_REQUIRED" for entry in entries
        ),
        "protected_before": protected_before,
    }
    LAB_EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    yield {
        "workbook": workbook,
        "metrics": metrics,
        "entries": entries,
        "ep_rows": ep_rows,
        "im_rows": im_rows,
        "aligned": aligned,
    }
    workbook.close()
    assert _protected_hashes() == protected_before


def _cell_signature(cell):
    color = cell.fill.fgColor
    return (
        cell.value,
        cell.data_type,
        cell.number_format,
        cell.font.bold,
        cell.font.italic,
        cell.fill.fill_type,
        color.type,
        color.rgb,
        cell.alignment.horizontal,
        cell.alignment.vertical,
    )


def _sheet_signature(ws):
    return (
        ws.max_row,
        ws.max_column,
        str(ws.freeze_panes),
        ws.auto_filter.ref,
        tuple(str(item) for item in ws.merged_cells.ranges),
        tuple(tuple(_cell_signature(cell) for cell in row) for row in ws.iter_rows()),
    )


def test_every_existing_info_and_warn_has_stable_identifiers(generated):
    entries = [entry for entry in generated["entries"] if entry.severity in {"INFO", "WARN"}]
    assert len(entries) == 296
    assert all(entry.audit_id and entry.observation_id for entry in entries)
    assert all(entry.period == PERIOD for entry in entries)
    assert len({entry.audit_id for entry in entries}) == len(entries)
    assert len({entry.observation_id for entry in entries}) == len(entries)


def test_audit_sheet_layout_preserves_legacy_headers_after_metadata(generated):
    ws = generated["workbook"]["AUDIT.PH1"]
    assert [cell.value for cell in ws[1]] == [
        "AUDIT_ID",
        "OBSERVATION_ID",
        "PERIOD",
        "SEVERIDAD",
        "EMPRESA",
        "HALLAZGO",
        "CLAVE",
        "DETALLE",
        "UBICACION",
    ]
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref == f"A1:I{ws.max_row}"


def test_ids_are_repeatable_and_observations_are_period_specific(generated):
    wb_repeat, _, repeat = engine.write_workbook(
        PERIOD,
        generated["ep_rows"],
        generated["im_rows"],
        generated["aligned"],
        RAW_EPLAZA,
        RAW_IMPULSA,
    )
    wb_next, _, next_period = engine.write_workbook(
        "2026.09",
        generated["ep_rows"],
        generated["im_rows"],
        generated["aligned"],
        RAW_EPLAZA,
        RAW_IMPULSA,
    )
    try:
        assert [entry.audit_id for entry in repeat] == [entry.audit_id for entry in generated["entries"]]
        assert [entry.observation_id for entry in repeat] == [entry.observation_id for entry in generated["entries"]]
        assert [entry.audit_id for entry in next_period] == [entry.audit_id for entry in generated["entries"]]
        assert all(
            left.observation_id != right.observation_id
            for left, right in zip(generated["entries"], next_period)
        )
    finally:
        wb_repeat.close()
        wb_next.close()


def test_entity_issue_and_exact_node_boundaries_prevent_collisions():
    entries = [
        engine.AuditEntry("WARN", "EPLAZA", "CONFLICTING_DESCRIPTION", "120411", "d", "r"),
        engine.AuditEntry("WARN", "IMPULSA", "CONFLICTING_DESCRIPTION", "120411", "d", "r"),
        engine.AuditEntry("WARN", "EPLAZA", "AMBIGUOUS_HIERARCHY", "120411", "d", "r"),
        engine.AuditEntry("WARN", "EPLAZA", "CONFLICTING_DESCRIPTION", "A-B", "d", "r"),
        engine.AuditEntry("WARN", "EPLAZA", "CONFLICTING_DESCRIPTION", "A_B", "d", "r"),
    ]
    engine.assign_audit_identities(entries, PERIOD, {"a": "0" * 64, "b": "1" * 64})
    assert len({entry.audit_id for entry in entries}) == len(entries)


def test_code_less_nodes_are_semantic_or_explicitly_require_adjudication():
    stable = engine.AuditEntry(
        "WARN", "EPLAZA", "AMBIGUOUS_HIERARCHY", "TOTAL ACTIVO", "d", "row 10", node_key="TOTAL ACTIVO#1"
    )
    reordered = engine.AuditEntry(
        "WARN", "EPLAZA", "AMBIGUOUS_HIERARCHY", "TOTAL ACTIVO", "d2", "row 99", node_key="TOTAL ACTIVO#1"
    )
    unresolved = engine.AuditEntry("WARN", "EPLAZA", "AMBIGUOUS_HIERARCHY", "", "unresolved", "row 1")
    entries = [stable, reordered, unresolved]
    engine.assign_audit_identities(entries, PERIOD, {"a": "0" * 64})
    assert stable.audit_id == reordered.audit_id
    assert stable.observation_id != reordered.observation_id
    assert stable.identity_status == "STABLE_SEMANTIC_KEY"
    assert unresolved.identity_status == "IDENTITY_ADJUDICATION_REQUIRED"
    assert "IDENTITY_ADJUDICATION_REQUIRED" in unresolved.audit_id


def test_duplicate_occurrences_are_explicit_and_not_silently_merged():
    entries = [
        engine.AuditEntry("WARN", "EPLAZA", "SOURCE_SUBTOTAL_DIFF", "TOTAL", "d", "r", node_key="TOTAL#1"),
        engine.AuditEntry("WARN", "EPLAZA", "SOURCE_SUBTOTAL_DIFF", "TOTAL", "d", "r", node_key="TOTAL#1"),
    ]
    engine.assign_audit_identities(entries, PERIOD, {"a": "0" * 64})
    assert entries[0].audit_id == entries[1].audit_id
    assert entries[0].observation_id != entries[1].observation_id
    assert [(entry.duplicate_ordinal, entry.duplicate_count) for entry in entries] == [(1, 2), (2, 2)]


def test_existing_audit_counts_and_accounting_assertions_are_unchanged(generated):
    counts = Counter(entry.severity for entry in generated["entries"])
    assert counts == {"INFO": 267, "WARN": 29}
    criteria = generated["metrics"]["approved_criteria"]
    assert criteria["applied_count"] == 15
    assert criteria["blocked_count"] == 0
    assert criteria["numerically_verified_count"] == 15
    assert generated["metrics"]["eplaza"]["account_rows"] == 214
    assert generated["metrics"]["impulsa"]["account_rows"] == 100
    assert generated["metrics"]["cam"]["account_rows"] == 253


def test_financial_sheets_values_formulas_and_formats_match_protected_baseline(generated):
    canonical = openpyxl.load_workbook(CANONICAL, data_only=False)
    lab = openpyxl.load_workbook(LAB_WORKBOOK, data_only=False)
    try:
        for sheet_name in (
            "CAM2026.08_CONSOL.ALIGN",
            "CM2026.08_EPLAZA",
            "CM2026.08_IMPULSA",
            "CONTROL",
        ):
            assert _sheet_signature(lab[sheet_name]) == _sheet_signature(canonical[sheet_name])
    finally:
        lab.close()
        canonical.close()


def test_registry_is_pending_unapproved_and_catalog_is_evidence_only():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["CATALOG_CONTEXT"]["CATALOG_NODES"] == 447
    assert registry["CATALOG_CONTEXT"]["EPLAZA_MATCHED_SOURCE_ACCOUNTS"] == 179
    assert registry["CATALOG_CONTEXT"]["AUTHORITY"] == "EVIDENCE_ONLY_NOT_ACCOUNTING_AUTHORITY"
    assert len(registry["DECISIONS"]) == 29
    assert all(item["STATUS"] == "PENDING_REVIEW" for item in registry["DECISIONS"])
    assert all(item["IMPLEMENTATION_AUTHORIZATION"] == "NOT_AUTHORIZED" for item in registry["DECISIONS"])
    assert all(item["APPROVER"] is None and item["APPROVAL_TIMESTAMP"] is None for item in registry["DECISIONS"])
    required = {
        "DECISION_ID", "AUDIT_ID", "STATUS", "HUMAN_FEEDBACK", "AGREED_CRITERION",
        "APPLICABILITY_SCOPE", "CATALOG_REFERENCE", "CRITERION_VERSION", "APPROVER",
        "APPROVAL_TIMESTAMP", "IMPLEMENTATION_AUTHORIZATION", "SUPERSEDES", "EVIDENCE_REFERENCE",
    }
    assert all(required <= set(item) for item in registry["DECISIONS"])


def test_protected_financial_artifacts_match_registered_hashes_after_generation(generated):
    assert _protected_hashes() == PROTECTED
    evidence = json.loads(LAB_EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["protected_before"] == PROTECTED
    assert LAB_WORKBOOK.is_file()
