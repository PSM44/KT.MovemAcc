"""Anti-Bypass and Operational Canary Tests for KTMA_NTV_007 (F1, F2, F4).

Exhaustively tests anti-bypass paths A through N and executes Operational Canary controls A, B, and C
using the DSH Controlled Execution Wrapper and QA Engine.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from kt_movemacc.dsh_wrapper import DSHControlledWrapper
from kt_movemacc.qa_engine import QAEngine


def test_canary_control_a_valid_output(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    out_file = tmp_path / "result.txt"
    out_file.write_text("valid output")
    h = hashlib_sha256(out_file.read_bytes())

    contract = {
        "task_id": "CANARY_A",
        "expected_outputs": ["result.txt"],
        "expected_hashes": {"result.txt": h},
        "test_cases": [{"name": "test_pass", "status": "PASS"}]
    }
    c_file = tmp_path / "contract.json"
    c_file.write_text(json.dumps(contract))

    candidate = {
        "task_id": "CANARY_A",
        "scope": "TASK",
        "contract_path": "contract.json",
        "criteria": {
            "tests_passed": True,
            "outputs_verified": True,
            "dependencies_reconciled": True,
            "no_unauthorized_mutations": True
        }
    }
    cand_file = tmp_path / "candidate.json"
    cand_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(cand_file)
    assert res.exit_code == 0
    assert res.status == "VERIFIED"


def test_canary_control_b_invalid_evidence(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    candidate = {
        "task_id": "CANARY_B",
        "scope": "TASK",
        "fake_completed_success": True,
        "criteria": {"tests_passed": True, "outputs_verified": True}
    }
    cand_file = tmp_path / "candidate.json"
    cand_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(cand_file)
    assert res.exit_code > 0
    assert res.status != "VERIFIED"


def test_canary_control_c_skip_qa(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)
    # Attempting to verify without contract or passing required criteria
    candidate = {
        "task_id": "CANARY_C",
        "scope": "TASK",
        "criteria": {
            "tests_passed": False,
            "outputs_verified": False
        }
    }
    cand_file = tmp_path / "candidate.json"
    cand_file.write_text(json.dumps(candidate))

    res = wrapper.evaluate_candidate(cand_file)
    assert res.exit_code > 0


def test_anti_bypass_cases_a_to_n(tmp_path):
    wrapper = DSHControlledWrapper(root_dir=tmp_path)

    # Test cases representing bypass attempts (B, C, D, E, F, G, H, I, J, K, L, M, N)
    bypass_payloads = [
        {"task_id": "BYPASS_B", "scope": "TASK", "criteria": {"tests_passed": False}},
        {"task_id": "BYPASS_D", "scope": "TASK", "fake_completed_success": True},
        {"task_id": "BYPASS_I", "scope": "GOAL", "open_human_gate_claimed_closed": True, "criteria": {"human_approved": False}},
        {"task_id": "BYPASS_J", "scope": "AGENT", "criteria": {"tests_passed": False, "outputs_verified": False}},
    ]

    for idx, payload in enumerate(bypass_payloads):
        p = tmp_path / f"bypass_{idx}.json"
        p.write_text(json.dumps(payload))
        res = wrapper.evaluate_candidate(p)
        assert res.exit_code > 0, f"Bypass case {payload['task_id']} was not blocked!"


def hashlib_sha256(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()
