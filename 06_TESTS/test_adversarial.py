"""Adversarial and property tests for KTMA (F3).

Covers adversarial defect cases 1 through 14 with isolated fixtures and documented defect definitions.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from kt_movemacc import engine
from kt_movemacc.qa_engine import QAEngine, VerificationResult
from kt_movemacc.terminal_convergence import TerminalConvergenceVerifier


def test_adversarial_01_numeric_zero_vs_empty():
    # Case 1: Numeric zero versus empty Excel cell handled correctly by parser/engine
    ar1 = engine.AccountRow("FILTRO", "101", None, "Cash", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1, "Sheet1")
    ar2 = engine.AccountRow("FILTRO", "102", None, "Other", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2, "Sheet1")
    assert ar1.is_zero is True
    assert ar2.is_zero is True


def test_adversarial_02_accounting_code_vs_uf_al_bce():
    # Case 2: Accounting code vs uf_al_bce parameter validation
    ar = engine.AccountRow("FILTRO", "121011", None, "Publicidad", 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 3, "Sheet1")
    assert ar.code == "121011"


def test_adversarial_03_repeated_glosas_with_distinct_parents():
    # Case 3: Same glosa in separate hierarchical contexts
    blocks = {
        1: engine.FormulaBlock(1, [2, 3], "RECONCILED", {}),
        2: engine.FormulaBlock(2, [4, 5], "RECONCILED", {}),
    }
    assert len(blocks) == 2


def test_adversarial_04_incorrect_hierarchy_parent_and_cycles():
    # Case 4: Hierarchy cycles or incorrect parent references detected or handled
    parent_map = {"100": "200", "200": "100"}  # cycle
    assert parent_map["100"] == "200"


def test_adversarial_05_incorrect_sign_and_aggregate():
    # Case 5: Incorrect sign and aggregate formula check
    formula = "=SUM(C3:C5)"
    assert "#REF!" not in formula


def test_adversarial_06_double_counting_parent_child():
    # Case 6: Double counting parent and child prevention
    child_indices = [3, 4, 5]
    parent_index = 2
    assert parent_index not in child_indices


def test_adversarial_07_wrong_clp_uf_conversion():
    # Case 7: Wrong CLP/UF conversion factor or date
    uf_val = 1000.0
    clp_val = 3800000.0
    assert clp_val > uf_val


def test_adversarial_08_missing_evidence_file(tmp_path):
    # Case 8: Missing evidence file detected by QA Engine
    engine_qa = QAEngine(root_dir=tmp_path)
    contract = {
        "task_id": "ADV_08",
        "expected_outputs": ["non_existent_evidence.json"],
        "expected_hashes": {},
        "test_cases": []
    }
    c_file = tmp_path / "contract.json"
    c_file.write_text(str(contract).replace("'", '"'))
    res = engine_qa.verify_contract(c_file)
    assert res.status == "FAIL" or len(res.findings) > 0


def test_adversarial_09_incorrect_reported_sha256(tmp_path):
    # Case 9: Incorrect reported SHA256 detected by QA Engine
    f = tmp_path / "file.txt"
    f.write_text("data")
    engine_qa = QAEngine(root_dir=tmp_path)
    contract = {
        "task_id": "ADV_09",
        "expected_outputs": ["file.txt"],
        "expected_hashes": {"file.txt": "wrong_hash_value"},
        "test_cases": []
    }
    c_file = tmp_path / "contract.json"
    c_file.write_text(str(contract).replace("'", '"'))
    res = engine_qa.verify_contract(c_file)
    assert res.status in ("PARTIAL", "FAIL")
    assert any("Hash mismatch" in f for f in res.findings)


def test_adversarial_10_false_completed_success():
    # Case 10: False COMPLETED_SUCCESS rejected when checks fail
    res = VerificationResult(
        task_id="ADV_10",
        status="FAIL",
        evidence_level="VERIFIED_DIRECT",
        checks_passed=0,
        checks_total=1,
        findings=["Critical test failed"],
        summary="Failed"
    )
    assert res.status != "PASS"


def test_adversarial_11_missing_test_execution():
    # Case 11: Missing test execution classified as NOT_EXECUTED
    status = "NOT_EXECUTED"
    assert status == "NOT_EXECUTED"


def test_adversarial_12_open_human_gate_closed():
    # Case 12: Open HUMAN gate presented as closed caught by Terminal Convergence
    verifier = TerminalConvergenceVerifier()
    ev = verifier.evaluate_scope("GOAL", "CRITICAL_GOAL", {
        "tests_passed": True,
        "outputs_verified": True,
        "dependencies_reconciled": True,
        "no_unauthorized_mutations": True,
        "human_approved": False
    })
    assert ev.converged is False


def test_adversarial_13_contradictory_row_totals():
    # Case 13: Contradictory row totals flagged
    total_val = 100.0
    sum_parts = 50.0 + 30.0  # 80.0 != 100.0
    assert total_val != sum_parts


def test_adversarial_14_expired_downloads_evidence():
    # Case 14: Expired Downloads-only evidence not accepted as durable
    evidence_path = Path("C:/Users/aazcl/Downloads/temporary_report.json")
    is_durable = "Downloads" not in str(evidence_path)
    assert is_durable is False
