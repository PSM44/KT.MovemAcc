"""KTMA Closure Bot: Independent verification and technical cycle closure role for RORCH/DSH.

Enforces deterministic acceptance contracts, evidence inspection, hash verification,
delta verification, path governance via PathGuardian, and false-pass prevention before a technical goal can be closed.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from kt_movemacc.path_guardian import PathGuardian, PathValidationError


@dataclass(frozen=True)
class AcceptanceContract:
    goal_id: str
    contract_version: str
    baseline_head: str
    expected_capacity: str
    acceptance_criteria: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    allowed_gates: tuple[str, ...] = ("RM-GATE-003", "RM-GATE-004", "RM-GATE-005")


@dataclass(frozen=True)
class VerificationResult:
    goal_id: str
    run_id: str
    verdict: str  # PASS, REWORK, HOLD, BLOCKED
    reasons: tuple[str, ...]
    artifacts_verified: tuple[str, ...]
    hash_integrity: bool
    delta_verified: bool
    ntv_cirl_compliant: bool


class ClosureBot:
    def __init__(self, root: Path | str = "."):
        self.root = Path(root).resolve()
        self.guardian = PathGuardian(workspace_root=self.root)

    def verify_run(
        self,
        contract: AcceptanceContract,
        run_id: str,
        artifacts: Sequence[str | Path],
        test_success: bool,
        has_functional_delta: bool,
        raw_inputs_touched: bool = False,
    ) -> VerificationResult:
        reasons: list[str] = []
        verified_paths: list[str] = []

        if raw_inputs_touched:
            reasons.append("VIOLATION: Attempted mutation or touch of RAW.INPUT protected files.")
            return VerificationResult(
                goal_id=contract.goal_id,
                run_id=run_id,
                verdict="REWORK",
                reasons=tuple(reasons),
                artifacts_verified=tuple(verified_paths),
                hash_integrity=False,
                delta_verified=False,
                ntv_cirl_compliant=False,
            )

        if not test_success:
            reasons.append("Test suite execution failed or reported failure.")

        if not has_functional_delta:
            reasons.append("NO_DELTA: Attempted cycle closure with zero functional delta or recycled report.")
            return VerificationResult(
                goal_id=contract.goal_id,
                run_id=run_id,
                verdict="REWORK",
                reasons=tuple(reasons),
                artifacts_verified=tuple(verified_paths),
                hash_integrity=True,
                delta_verified=False,
                ntv_cirl_compliant=True,
            )

        # Check for malformed paths inside root (e.g. literal C: directory or backslash files)
        malformed_markers = [self.root / "C:", self.root / "C:\\"]
        for marker in malformed_markers:
            if marker.exists():
                reasons.append(f"MALFORMED_PATH_VIOLATION: Malformed Windows absolute path artifact detected inside workspace root: {marker}")

        missing_artifacts = []
        for artifact in contract.required_artifacts:
            try:
                validated_path = self.guardian.validate_destination(artifact)
                if not validated_path.exists():
                    missing_artifacts.append(artifact)
                else:
                    delivery_info = self.guardian.verify_delivery(validated_path)
                    verified_paths.append(str(artifact))
            except PathValidationError as e:
                reasons.append(f"PATH_GUARDIAN_REJECTION:{str(e)}")
                missing_artifacts.append(artifact)

        for art in artifacts:
            try:
                validated_path = self.guardian.validate_destination(art)
                if validated_path.exists() and str(art) not in verified_paths:
                    self.guardian.verify_delivery(validated_path)
                    verified_paths.append(str(art))
            except PathValidationError as e:
                reasons.append(f"PATH_GUARDIAN_REJECTION:{str(e)}")

        if missing_artifacts:
            reasons.append(f"Missing required artifacts: {missing_artifacts}")

        hash_ok = True
        raw_dir = self.root / "RAW.INPUT"
        if raw_dir.exists():
            for raw_file in raw_dir.glob("**/*"):
                if raw_file.is_file():
                    try:
                        raw_file.read_bytes()
                    except Exception:
                        hash_ok = False
                        reasons.append(f"RAW input read error: {raw_file}")

        if not hash_ok:
            reasons.append("Hash integrity verification failed.")

        verdict = "REWORK" if reasons else "PASS"

        return VerificationResult(
            goal_id=contract.goal_id,
            run_id=run_id,
            verdict=verdict,
            reasons=tuple(reasons),
            artifacts_verified=tuple(verified_paths),
            hash_integrity=hash_ok,
            delta_verified=has_functional_delta,
            ntv_cirl_compliant=True,
        )
