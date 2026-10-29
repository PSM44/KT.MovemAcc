"""Terminal Convergence Verifier for KTMA (F4).

Evaluates explicit acceptance contracts for multiple scope levels:
TASK, AGENT / BOT, LOOP, FRONT, GOAL, GLOBAL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ConvergenceEvaluation:
    scope: str
    scope_id: str
    converged: bool
    reasons: List[str] = field(default_factory=list)


class TerminalConvergenceVerifier:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()

    def evaluate_scope(self, scope: str, scope_id: str, criteria: dict) -> ConvergenceEvaluation:
        reasons = []
        tests_passed = criteria.get("tests_passed", False)
        outputs_verified = criteria.get("outputs_verified", False)
        dependencies_reconciled = criteria.get("dependencies_reconciled", True)
        no_unauthorized_mutations = criteria.get("no_unauthorized_mutations", True)
        human_approved = criteria.get("human_approved", True)

        if not tests_passed:
            reasons.append("Required tests not passed.")
        if not outputs_verified:
            reasons.append("Required outputs not verified.")
        if not dependencies_reconciled:
            reasons.append("Dependencies not fully reconciled.")
        if not no_unauthorized_mutations:
            reasons.append("Unauthorized mutations detected.")
        if not human_approved and scope in ("GOAL", "GLOBAL"):
            reasons.append("Required human approval gate is open.")

        converged = len(reasons) == 0
        return ConvergenceEvaluation(
            scope=scope,
            scope_id=scope_id,
            converged=converged,
            reasons=reasons
        )
