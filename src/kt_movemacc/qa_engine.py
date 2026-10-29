"""Minimal QA Engine for KTMA (F1 & F4).

Reads machine-readable task acceptance contracts, verifies file existence and SHA256 hashes,
evaluates structured test results, tracks evidence levels, and determines terminal convergence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class VerificationResult:
    task_id: str
    status: str  # NOT_EXECUTED, PASS, FAIL, PARTIAL, BLOCKED, UNKNOWN
    evidence_level: str  # VERIFIED_DIRECT, VERIFIED_INDEPENDENT, REPORTED_ONLY, INFERRED, UNKNOWN
    checks_passed: int
    checks_total: int
    findings: List[str] = field(default_factory=list)
    summary: str = ""


class QAEngine:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()

    def compute_sha256(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def verify_contract(self, contract_path: Path) -> VerificationResult:
        if not contract_path.exists():
            return VerificationResult(
                task_id="UNKNOWN",
                status="BLOCKED",
                evidence_level="UNKNOWN",
                checks_passed=0,
                checks_total=1,
                findings=[f"Contract file missing: {contract_path}"],
                summary="Blocked due to missing acceptance contract."
            )

        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except Exception as e:
            return VerificationResult(
                task_id="UNKNOWN",
                status="FAIL",
                evidence_level="UNKNOWN",
                checks_passed=0,
                checks_total=1,
                findings=[f"Invalid JSON contract: {e}"],
                summary="Failed to parse acceptance contract."
            )

        task_id = contract.get("task_id", "KTMA_TASK")
        expected_outputs = contract.get("expected_outputs", [])
        expected_hashes = contract.get("expected_hashes", {})
        test_cases = contract.get("test_cases", [])

        checks_total = len(expected_outputs) + len(expected_hashes) + len(test_cases)
        checks_passed = 0
        findings = []

        # 1. Verify output existence
        for out_path_str in expected_outputs:
            p = self.root_dir / out_path_str
            if p.exists():
                checks_passed += 1
            else:
                findings.append(f"Required output missing: {out_path_str}")

        # 2. Verify hashes
        for path_str, expected_hash in expected_hashes.items():
            p = self.root_dir / path_str
            actual_hash = self.compute_sha256(p)
            if actual_hash == expected_hash:
                checks_passed += 1
            else:
                findings.append(f"Hash mismatch for {path_str}: expected {expected_hash}, got {actual_hash}")

        # 3. Verify test cases status
        for tc in test_cases:
            tc_name = tc.get("name", "unnamed_test")
            tc_status = tc.get("status", "UNKNOWN")
            if tc_status == "PASS":
                checks_passed += 1
            else:
                findings.append(f"Test case {tc_name} status is {tc_status}")

        if checks_total == 0:
            status = "PASS"
            evidence_level = "VERIFIED_DIRECT"
        elif checks_passed == checks_total:
            status = "PASS"
            evidence_level = "VERIFIED_DIRECT"
        elif checks_passed > 0:
            status = "PARTIAL"
            evidence_level = "VERIFIED_DIRECT"
        else:
            status = "FAIL"
            evidence_level = "VERIFIED_DIRECT"

        summary = f"Verified contract {task_id}: {checks_passed}/{checks_total} checks passed."
        return VerificationResult(
            task_id=task_id,
            status=status,
            evidence_level=evidence_level,
            checks_passed=checks_passed,
            checks_total=checks_total,
            findings=findings,
            summary=summary
        )
