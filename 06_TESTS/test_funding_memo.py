from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import openpyxl
import kt_movemacc.funding_memo as funding_memo_module

from kt_movemacc.funding_memo import (
    AccountValue,
    FM_TARGET_CELL_INVENTORY,
    GROUPS,
    MISSING,
    MappingRule,
    calculate,
    apply_mapping_change,
    append_decision_event,
    effective_rules_for_period,
    load_decision_history,
    load_consolidated_values,
    mapping_rules,
    reconstruct_mapping_history,
    validate_decision_event,
    validate_rules,
)


def value(entity: str, account: str, amount: str) -> AccountValue:
    return AccountValue(entity, account, account, Decimal(amount), "SOURCE", 1, "a" * 64)


def test_mapping_has_66_accounts_and_16_targets():
    rules = mapping_rules()
    assert len(rules) == 66
    assert len({rule.account_id for rule in rules}) == 66
    assert len({rule.fm_target_id for rule in rules}) == 16
    assert sum(len(accounts) for accounts in GROUPS.values()) == 66
    assert len(FM_TARGET_CELL_INVENTORY) == 72


def test_account_assigned_to_two_targets_is_rejected():
    rule = mapping_rules()[0]
    with pytest.raises(ValueError, match="ACCOUNT_MULTIPLE_TARGETS"):
        validate_rules([rule, replace(rule, mapping_id="other", fm_target_id="FM-T028")])


def test_multiple_accounts_sum_and_entities_remain_separate():
    rules = [rule for rule in mapping_rules() if rule.fm_target_id == "FM-T036"]
    values = {
        "EPLAZA": {r.account_id: value("EPLAZA", r.account_id, str(i + 1)) for i, r in enumerate(rules)},
        "IMPULSA": {r.account_id: value("IMPULSA", r.account_id, "10") for r in rules},
    }
    _, results, _ = calculate(rules, values)
    assert results[0].eplaza_uf == Decimal("6")
    assert results[0].impulsa_uf == Decimal("30")
    assert results[0].total_uf == Decimal("36")


def test_minus_coefficient_and_negative_source_preserve_original():
    rule = replace(mapping_rules()[0], coefficient=-1)
    values = {"EPLAZA": {rule.account_id: value("EPLAZA", rule.account_id, "-7")}, "IMPULSA": {}}
    contributions, results, _ = calculate([rule], values)
    assert contributions[0].source_value_uf == Decimal("-7")
    assert contributions[0].contribution_uf == Decimal("7")
    assert results[0].eplaza_uf == Decimal("7")
    assert results[0].impulsa_uf is None
    assert results[0].total_uf is None


def test_missing_entity_is_explicit_not_zero():
    rule = mapping_rules()[0]
    contributions, results, _ = calculate(
        [rule], {"EPLAZA": {rule.account_id: value("EPLAZA", rule.account_id, "0")}, "IMPULSA": {}}
    )
    missing = next(c for c in contributions if c.entity == "IMPULSA")
    assert missing.status == MISSING
    assert missing.source_value_uf is None
    assert results[0].eplaza_uf == Decimal("0")
    assert results[0].impulsa_uf is None


def test_unmapped_account_is_visible():
    rule = mapping_rules()[0]
    _, _, unassigned = calculate(
        [rule], {"EPLAZA": {"999999": value("EPLAZA", "999999", "12")}, "IMPULSA": {}}
    )
    assert unassigned[0]["STATUS"] == "SIN_ASIGNACION_FM"


def test_monthly_values_change_without_mapping_change():
    rule = mapping_rules()[0]
    first = calculate([rule], {"EPLAZA": {rule.account_id: value("EPLAZA", rule.account_id, "1")}, "IMPULSA": {rule.account_id: value("IMPULSA", rule.account_id, "2")}})[1][0]
    second = calculate([rule], {"EPLAZA": {rule.account_id: value("EPLAZA", rule.account_id, "3")}, "IMPULSA": {rule.account_id: value("IMPULSA", rule.account_id, "4")}})[1][0]
    assert first.total_uf == Decimal("3")
    assert second.total_uf == Decimal("7")
    assert rule.version == "1.0.1"


def test_exact_duplicate_mapping_is_rejected():
    rule = mapping_rules()[0]
    with pytest.raises(ValueError, match="ACCOUNT_MULTIPLE_TARGETS"):
        validate_rules([rule, replace(rule, mapping_id="duplicate")])


def test_partial_missing_account_data_is_not_summed_as_zero():
    rules = [rule for rule in mapping_rules() if rule.fm_target_id == "FM-T036"]
    values = {
        "EPLAZA": {rules[0].account_id: value("EPLAZA", rules[0].account_id, "10")},
        "IMPULSA": {rules[0].account_id: value("IMPULSA", rules[0].account_id, "20")},
    }
    _, results, _ = calculate(rules, values)
    assert results[0].eplaza_uf is None
    assert results[0].impulsa_uf is None
    assert results[0].total_uf is None
    assert results[0].status == "PARTIAL_MISSING_ACCOUNT_DATA"


def test_consolidated_blank_entity_description_is_absence_not_zero(tmp_path):
    path = tmp_path / "cam.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONSOL.ALIGN"
    ws.append([
        "ACCOUNT_CODE", "EPLAZA.DESCRIPTION", "IMPULSA.DESCRIPTION",
        "EPLAZA.VALORES_UF", "IMPULSA.VALORES_UF", "TOTAL.VALORES_UF",
    ])
    ws.append(["120911", "Terreno", None, 10, 0, "=D2+E2"])
    wb.save(path)
    values = load_consolidated_values(path)
    assert values["EPLAZA"]["120911"].value_uf == Decimal("10.00")
    assert "120911" not in values["IMPULSA"]


def test_full_raw_coverage_proves_absent_entity_contribution_is_zero(tmp_path, monkeypatch):
    path = tmp_path / "cam.xlsx"
    raw_eplaza = tmp_path / "eplaza.xlsb"
    raw_impulsa = tmp_path / "impulsa.xlsb"
    raw_eplaza.write_bytes(b"eplaza-complete")
    raw_impulsa.write_bytes(b"impulsa-complete")
    eplaza_account = AccountValue(
        "EPLAZA", "120911", "Terreno", Decimal("10.00"), "RAW", 1,
        funding_memo_module._sha256(raw_eplaza), "VALUE", "RAW_ACCOUNT_PRESENT",
    )
    monkeypatch.setattr(
        funding_memo_module, "load_entity_values",
        lambda raw_path, entity: {"120911": eplaza_account} if entity == "EPLAZA" else {},
    )
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONSOL.ALIGN"
    ws.append([
        "ACCOUNT_CODE", "EPLAZA.DESCRIPTION", "IMPULSA.DESCRIPTION",
        "EPLAZA.VALORES_UF", "IMPULSA.VALORES_UF", "TOTAL.VALORES_UF", "CONTROL",
    ])
    ws.append(["120911", "Terreno", None, 10, 0, "=D2+E2", "EPLAZA_ONLY"])
    control = wb.create_sheet("CONTROL")
    control.append(["CONTROL_KEY", "VALUE", "DETAIL"])
    control.append(["PERIOD", "2026.09", None])
    control.append(["EPLAZA_RAW", raw_eplaza.name, funding_memo_module._sha256(raw_eplaza)])
    control.append(["IMPULSA_RAW", raw_impulsa.name, funding_memo_module._sha256(raw_impulsa)])
    control.append(["EPLAZA_ACCOUNTS", 1, None])
    control.append(["IMPULSA_ACCOUNTS", 0, None])
    wb.save(path)
    values = load_consolidated_values(
        path, period="2026.09", raw_eplaza=raw_eplaza, raw_impulsa=raw_impulsa,
    )
    absent = values["IMPULSA"]["120911"]
    assert absent.value_uf == Decimal("0.00")
    assert absent.value_state == "ZERO_VERIFIED"
    assert "RAW_FULL_COVERAGE_ABSENCE" in absent.evidence
    _, results, _ = calculate([mapping_rules()[0]], values)
    assert results[0].total_uf == Decimal("10.00")


def test_raw_coverage_hash_mismatch_is_rejected(tmp_path):
    path = tmp_path / "cam.xlsx"
    raw_eplaza = tmp_path / "eplaza.xlsb"
    raw_impulsa = tmp_path / "impulsa.xlsb"
    raw_eplaza.write_bytes(b"e")
    raw_impulsa.write_bytes(b"i")
    wb = openpyxl.Workbook()
    wb.active.title = "CONSOL.ALIGN"
    wb.active.append([
        "ACCOUNT_CODE", "EPLAZA.DESCRIPTION", "IMPULSA.DESCRIPTION",
        "EPLAZA.VALORES_UF", "IMPULSA.VALORES_UF", "TOTAL.VALORES_UF", "CONTROL",
    ])
    control = wb.create_sheet("CONTROL")
    control.append(["CONTROL_KEY", "VALUE", "DETAIL"])
    control.append(["PERIOD", "2026.09", None])
    control.append(["EPLAZA_RAW", raw_eplaza.name, "0" * 64])
    control.append(["IMPULSA_RAW", raw_impulsa.name, funding_memo_module._sha256(raw_impulsa)])
    wb.save(path)
    with pytest.raises(ValueError, match="CONSOLIDATED_RAW_HASH_MISMATCH:EPLAZA"):
        load_consolidated_values(
            path, period="2026.09", raw_eplaza=raw_eplaza, raw_impulsa=raw_impulsa,
        )


def test_invalid_coefficient_rejected():
    with pytest.raises(ValueError, match="COEFFICIENT_INVALID"):
        validate_rules([replace(mapping_rules()[0], coefficient=2)])


def test_unapproved_change_is_not_applied():
    rules = mapping_rules()
    rule = rules[0]
    decision = {
        "DECISION_ID": "D2", "ACCOUNT_ID": rule.account_id,
        "PREVIOUS_FM_TARGET": rule.fm_target_id, "NEW_FM_TARGET": "FM-T028",
        "PREVIOUS_COEFFICIENT": 1, "NEW_COEFFICIENT": 1,
        "EFFECTIVE_PERIOD": "2026.10", "STATUS": "PROPOSED",
    }
    assert apply_mapping_change(rules, decision, new_version="1.1.0") == rules


def test_authorized_future_change_versions_history_and_preserves_prior_period():
    rules = mapping_rules()
    rule = rules[0]
    decision = {
        "DECISION_ID": "D2", "ACCOUNT_ID": rule.account_id,
        "PREVIOUS_FM_TARGET": rule.fm_target_id, "NEW_FM_TARGET": "FM-T028",
        "PREVIOUS_COEFFICIENT": 1, "NEW_COEFFICIENT": -1,
        "EFFECTIVE_PERIOD": "2026.10", "STATUS": "APPROVED",
    }
    updated = apply_mapping_change(rules, decision, new_version="1.1.0")
    september = next(r for r in effective_rules_for_period(updated, "2026.09") if r.account_id == rule.account_id)
    october = next(r for r in effective_rules_for_period(updated, "2026.10") if r.account_id == rule.account_id)
    assert september.fm_target_id == "FM-T027"
    assert october.fm_target_id == "FM-T028"
    assert october.coefficient == -1
    assert october.version == "1.1.0"


def test_retroactive_change_requires_explicit_authorization():
    rule = mapping_rules()[0]
    decision = {
        "DECISION_ID": "D3", "ACCOUNT_ID": rule.account_id,
        "PREVIOUS_FM_TARGET": rule.fm_target_id, "NEW_FM_TARGET": "FM-T028",
        "PREVIOUS_COEFFICIENT": 1, "NEW_COEFFICIENT": 1,
        "EFFECTIVE_PERIOD": "2026.08", "STATUS": "APPROVED",
    }
    with pytest.raises(ValueError, match="RETROACTIVE_AUTHORIZATION_REQUIRED"):
        apply_mapping_change(mapping_rules(), decision, new_version="1.1.0")


def test_persisted_history_supersedes_unsupported_legacy_record_and_reconstructs_base():
    history_path = Path(__file__).parents[1] / "04_CONFIG/FUNDING_MEMO/KTMA_FM_DECISIONS.jsonl"
    events = load_decision_history(history_path)
    _, effective = reconstruct_mapping_history(events, "2026.09")
    assert len(events) == 3
    assert len(effective) == 66
    assert {rule.decision_id for rule in effective} == {"KTMA-FM-DEC-20261030-001"}


def test_append_only_future_change_preserves_prior_period(tmp_path):
    source = Path(__file__).parents[1] / "04_CONFIG/FUNDING_MEMO/KTMA_FM_DECISIONS.jsonl"
    history = tmp_path / "history.jsonl"
    original = source.read_bytes()
    history.write_bytes(original)
    rule = mapping_rules()[0]
    event = {
        "EVENT_ID": "TEST-EVENT-001", "DECISION_ID": "TEST-DECISION-001",
        "DATE_TIME": None, "TIMEZONE": "America/Santiago",
        "DECISION_AUTHORITY": "HUMAN", "DECISION_AUTHORITY_TYPE": "HUMAN_DIRECT",
        "REPORTED_BY": None, "DECISION_SOURCE": "test evidence",
        "ORIGINAL_INSTRUCTION": "Move account for the future test period.",
        "ACCOUNT_ID": rule.account_id, "PREVIOUS_FM_TARGET": rule.fm_target_id,
        "NEW_FM_TARGET": "FM-T028", "PREVIOUS_COEFFICIENT": 1,
        "NEW_COEFFICIENT": -1, "REASON": "test", "EFFECTIVE_PERIOD": "2026.10",
        "RECORDED_AT": None, "IMPLEMENTED_AT": None, "STATUS": "IMPLEMENTED",
        "EVIDENCE_REFERENCE": "test", "PREVIOUS_VERSION": "1.0.1",
        "NEW_VERSION": "1.1.0", "RETROACTIVE_AUTHORIZED": False,
    }
    append_decision_event(history, event)
    assert history.read_bytes().startswith(original)
    events = load_decision_history(history)
    _, september = reconstruct_mapping_history(events, "2026.09")
    _, october = reconstruct_mapping_history(events, "2026.10")
    assert next(r for r in september if r.account_id == rule.account_id).fm_target_id == "FM-T027"
    october_rule = next(r for r in october if r.account_id == rule.account_id)
    assert october_rule.fm_target_id == "FM-T028"
    assert october_rule.coefficient == -1
    assert october_rule.version == "1.1.0"
    with pytest.raises(ValueError, match="DECISION_EVENT_DUPLICATE"):
        append_decision_event(history, event)


def test_retroactive_event_requires_explicit_human_evidence():
    event = {
        "EVENT_ID": "TEST-RETRO", "DECISION_ID": "TEST-RETRO", "DATE_TIME": None,
        "TIMEZONE": "America/Santiago", "DECISION_AUTHORITY": "HUMAN",
        "DECISION_AUTHORITY_TYPE": "HUMAN_DIRECT", "REPORTED_BY": None,
        "DECISION_SOURCE": "test", "ORIGINAL_INSTRUCTION": "test",
        "ACCOUNT_ID": "120911", "PREVIOUS_FM_TARGET": "FM-T027",
        "NEW_FM_TARGET": "FM-T028", "PREVIOUS_COEFFICIENT": 1,
        "NEW_COEFFICIENT": 1, "REASON": "test", "EFFECTIVE_PERIOD": "2026.08",
        "RECORDED_AT": None, "IMPLEMENTED_AT": None, "STATUS": "IMPLEMENTED",
        "EVIDENCE_REFERENCE": "test", "PREVIOUS_VERSION": "1.0.1",
        "NEW_VERSION": "1.1.0", "RETROACTIVE_AUTHORIZED": True,
    }
    with pytest.raises(ValueError, match="RETROACTIVE_AUTHORIZATION_EVIDENCE_REQUIRED"):
        validate_decision_event(event)
