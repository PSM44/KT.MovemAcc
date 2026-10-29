"""DSH Controlled Execution Wrapper & Terminal Convergence Integrator (F1 & F2).

Integrates the QA Engine and Terminal Convergence verifier with a controlled execution runner
that evaluates completion candidates and returns blocking nonzero exit codes for rejections.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kt_movemacc.qa_engine import QAEngine, VerificationResult
from kt_movemacc.terminal_convergence import TerminalConvergenceVerifier, ConvergenceEvaluation


@dataclass
class DSHExecutionResult:
    task_id: str
    status: str  # VERIFIED, PARTIAL, FAIL, BLOCKED, UNKNOWN
    exit_code: int
    reasons: List[str] = field(default_factory=list)
    summary: str = ""


class DSHControlledWrapper:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()
        self.qa_engine = QAEngine(self.root_dir)
        self.convergence_verifier = TerminalConvergenceVerifier(self.root_dir)

    def evaluate_candidate(self, candidate_path: Path) -> DSHExecutionResult:
        if not candidate_path.exists():
            return DSHExecutionResult(
                task_id="UNKNOWN",
                status="BLOCKED",
                exit_code=1,
                reasons=[f"Completion candidate file missing: {candidate_path}"],
                summary="Execution blocked: missing completion candidate."
            )

        try:
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        except Exception as e:
            return DSHExecutionResult(
                task_id="UNKNOWN",
                status="FAIL",
                exit_code=2,
                reasons=[f"Invalid candidate JSON: {e}"],
                summary="Execution failed: unparsable candidate."
            )

        task_id = candidate.get("task_id", "KTMA_TASK")
        scope = candidate.get("scope", "TASK")
        contract_path_str = candidate.get("contract_path")
        criteria = candidate.get("criteria", {})

        reasons = []
        status = "VERIFIED"
        exit_code = 0

        # 1. Evaluate QA contract if provided
        if contract_path_str:
            contract_path = self.root_dir / contract_path_str
            vr = self.qa_engine.verify_contract(contract_path)
            if vr.status != "PASS":
                status = vr.status
                reasons.extend(vr.findings)
                exit_code = 10

        # 2. Evaluate Terminal Convergence criteria
        ev = self.convergence_verifier.evaluate_scope(scope, task_id, criteria)
        if not ev.converged:
            status = "BLOCKED" if status == "VERIFIED" else status
            reasons.extend(ev.reasons)
            exit_code = max(exit_code, 20)

        # 3. Check adversarial flags or fake success
        if candidate.get("fake_completed_success", False):
            status = "FAIL"
            reasons.append("Adversarial injection: fake completed success rejected.")
            exit_code = 30

        if candidate.get("financial_mutation_concealed", False):
            status = "FAIL"
            reasons.append("Adversarial injection: financial mutation concealed rejected.")
            exit_code = 31

        if candidate.get("open_human_gate_claimed_closed", False):
            status = "BLOCKED"
            reasons.append("Adversarial injection: open human gate cannot be bypassed.")
            exit_code = 32

        if exit_code > 0:
            summary = f"Execution REJECTED for {task_id} [{status}]: {'; '.join(reasons)}"
        else:
            summary = f"Execution ACCEPTED and VERIFIED for {task_id}."

        return DSHExecutionResult(
            task_id=task_id,
            status=status,
            exit_code=exit_code,
            reasons=reasons,
            summary=summary
        )
