from pathlib import Path
import json
import tempfile
from kt_movemacc.qa_engine import QAEngine, VerificationResult

def test_qa_engine_missing_contract():
    engine = QAEngine()
    res = engine.verify_contract(Path("non_existent_contract.json"))
    assert res.status == "BLOCKED"
    assert res.evidence_level == "UNKNOWN"

def test_qa_engine_valid_contract(tmp_path):
    contract_file = tmp_path / "contract.json"
    dummy_output = tmp_path / "output.txt"
    dummy_output.write_text("hello")
    h = hashlib_sha256(dummy_output.read_bytes())

    contract = {
        "task_id": "TEST_TASK_001",
        "expected_outputs": [str(dummy_output.relative_to(tmp_path))],
        "expected_hashes": {str(dummy_output.relative_to(tmp_path)): h},
        "test_cases": [{"name": "test_1", "status": "PASS"}]
    }
    contract_file.write_text(json.dumps(contract))

    engine = QAEngine(root_dir=tmp_path)
    res = engine.verify_contract(contract_file)
    assert res.status == "PASS"
    assert res.checks_passed == 3
    assert res.checks_total == 3

def hashlib_sha256(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()
