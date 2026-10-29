from dataclasses import replace
from decimal import Decimal

import pytest

from kt_movemacc.funding_memo import (
    AccountValue,
    FM_TARGET_CELL_INVENTORY,
    GROUPS,
    MISSING,
    MappingRule,
    calculate,
    apply_mapping_change,
    effective_rules_for_period,
    mapping_rules,
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
    assert rule.version == "1.0.0"


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
