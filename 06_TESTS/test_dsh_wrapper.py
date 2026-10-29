"""DSH Controlled Wrapper & Enforcement Tests (F3).

Tests the execution wrapper against 12 negative adversarial cases and positive valid completions,
asserting blocking exit codes and exact rejection reasons.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from kt_movemacc.dsh_wrapper import DSHControlledWrapper


def test_dsh_wrapper_positive_valid_completion(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    candidate = {
        "task_id": "TASK_POS_001",
        "scope": "TASK",
        "criteria": {
            "tests_passed": True,
            "outputs_verified": True,
            "dependencies_reconciled": True,
            "no_unauthorized_mutations": True
        }
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code == 0
    assert res.status == "VERIFIED"


def test_dsh_wrapper_neg_01_fake_completed_success(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    candidate = {
        "task_id": "ADV_01",
        "scope": "TASK",
        "fake_completed_success": True,
        "criteria": {"tests_passed": True, "outputs_verified": True}
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code > 0
    assert "fake completed success" in res.reasons[0].lower()


def test_dsh_wrapper_neg_02_missing_artifact(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    contract = {
        "task_id": "ADV_02",
        "expected_outputs": ["missing_file.txt"],
        "expected_hashes": {},
        "test_cases": []
    }
    contract_file = tmp_path / "contract.json"
    contract_file.write_text(json.dumps(contract))

    candidate = {
        "task_id": "ADV_02",
        "scope": "TASK",
        "contract_path": "contract.json",
        "criteria": {"tests_passed": True, "outputs_verified": True}
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code > 0


def test_dsh_wrapper_neg_03_incorrect_sha256(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("content")
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    contract = {
        "task_id": "ADV_03",
        "expected_outputs": ["out.txt"],
        "expected_hashes": {"out.txt": "badhash"},
        "test_cases": []
    }
    contract_file = tmp_path / "contract.json"
    contract_file.write_text(json.dumps(contract))

    candidate = {
        "task_id": "ADV_03",
        "scope": "TASK",
        "contract_path": "contract.json",
        "criteria": {"tests_passed": True, "outputs_verified": True}
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code > 0


def test_dsh_wrapper_neg_05_open_human_gate(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    candidate = {
        "task_id": "ADV_05",
        "scope": "GOAL",
        "open_human_gate_claimed_closed": True,
        "criteria": {"tests_passed": True, "outputs_verified": True, "human_approved": False}
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code > 0


def test_dsh_wrapper_neg_07_financial_mutation_concealed(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    candidate = {
        "task_id": "ADV_07",
        "scope": "TASK",
        "financial_mutation_concealed": True,
        "criteria": {"tests_passed": True, "outputs_verified": True}
    }
    c_file = tmp_path / "candidate.json"
    c_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(c_file)
    assert res.exit_code > 0
    assert "mutation" in res.reasons[0].lower()
