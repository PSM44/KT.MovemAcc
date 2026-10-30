"""TASK067 trusted-root and supported-entrypoint security regressions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kt_movemacc import engine
from kt_movemacc import ph15_database
from kt_movemacc.root_boundary import (
    AuthorizationContext,
    BoundaryGuard,
    BoundaryViolation,
    GuardedFilesystem,
    reconcile_failed_mutation,
    reconcile_side_effects,
    snapshot_tree_metadata,
    trusted_project_root,
)


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "08_EVIDENCE" / "TASK067_ROOT_AUTHORITY_LAB" / "SECURITY_RUN_001"
CANARY = LAB / "positive_canary.txt"


def _wsl(path: Path) -> str:
    resolved = path.resolve(strict=False)
    return f"/mnt/{resolved.drive[0].lower()}{resolved.as_posix()[2:]}"


def _payload(
    *,
    root: Path | str = ROOT,
    operations: tuple[str, ...] = ("create", "overwrite"),
    allowlist: tuple[Path | str, ...] = (CANARY,),
    indirect: tuple[Path | str, ...] = (),
    runtime: str = "windows",
) -> dict[str, object]:
    return {
        "ACTIVE_PROJECT": "KT.MovemAcc",
        "AUTHORIZED_ROOT": str(root),
        "TASK_ID": "KTMA_TASK067_PROJECT_ROOT_AUTHORITY_HARDENING",
        "AUTHORIZED_OPERATIONS": list(operations),
        "EXACT_TARGET_ALLOWLIST": [str(path) for path in allowlist],
        "DECLARED_INDIRECT_OUTPUTS": [str(path) for path in indirect],
        "EXTERNAL_REPOSITORY_ROOTS": [],
        "EXECUTION_RUNTIME": runtime,
    }


def _decision_code(exc: pytest.ExceptionInfo[BoundaryViolation]) -> str:
    return exc.value.decision.code


def test_trusted_root_is_anchored_to_module_and_project_identity():
    assert trusted_project_root() == ROOT.resolve()


def test_forged_root_matching_real_skillsmachine_is_rejected_without_write():
    skills_root = Path(r"C:\01. GitHub\Skills")
    if not skills_root.is_dir():
        pytest.skip("SkillsMachine root is not present on this host")
    target = skills_root / "TASK067_MUST_NOT_EXIST.txt"
    assert not target.exists()
    with pytest.raises(BoundaryViolation) as caught:
        AuthorizationContext.from_dict(_payload(root=skills_root, allowlist=(target,)))
    assert _decision_code(caught) == "PROJECT_ROOT_BINDING_MISMATCH"
    assert not target.exists()


def test_alternate_git_root_inside_fixture_is_rejected():
    alternate = LAB / "alternate_repository"
    (alternate / ".git").mkdir(parents=True, exist_ok=True)
    (alternate / "pyproject.toml").write_text('[project]\nname = "kt_movemacc"\n', encoding="utf-8")
    target = alternate / "forged.txt"
    with pytest.raises(BoundaryViolation) as caught:
        AuthorizationContext.from_dict(_payload(root=alternate, allowlist=(target,)))
    assert _decision_code(caught) == "PROJECT_ROOT_BINDING_MISMATCH"
    assert not target.exists()


def test_forged_project_identity_is_rejected():
    payload = _payload()
    payload["ACTIVE_PROJECT"] = "SkillsMachine"
    with pytest.raises(BoundaryViolation) as caught:
        AuthorizationContext.from_dict(payload)
    assert _decision_code(caught) == "ACTIVE_PROJECT_MISMATCH"


def test_self_declared_trusted_authorization_is_rejected():
    payload = _payload()
    payload["TRUSTED_ISSUER"] = "HUMAN"
    with pytest.raises(BoundaryViolation) as caught:
        AuthorizationContext.from_dict(payload)
    assert _decision_code(caught) == "UNSUPPORTED_TRUST_CLAIM"


def test_untrusted_payload_is_explicitly_not_authenticated():
    context = AuthorizationContext.from_dict(_payload())
    assert context.authorization_provenance == "NOT_ENFORCED_UNAUTHENTICATED_PAYLOAD"


def test_delegation_cannot_expand_operations_or_targets():
    internal = LAB / "delegated.txt"
    context = AuthorizationContext.from_dict(_payload(allowlist=(internal,)))
    with pytest.raises(BoundaryViolation) as operation:
        context.narrowed(operations=("create", "delete"), allowlist=(internal,))
    assert _decision_code(operation) == "DELEGATION_OPERATION_EXPANSION"
    with pytest.raises(BoundaryViolation) as target:
        context.narrowed(operations=("create",), allowlist=(LAB / "broader.txt",))
    assert _decision_code(target) == "DELEGATION_TARGET_EXPANSION"


def test_direct_engine_bypass_is_rejected_before_input_or_output_access():
    target_dir = LAB / "engine_bypass"
    with pytest.raises(BoundaryViolation) as caught:
        engine.run_ph1(LAB / "missing-eplaza.xlsb", LAB / "missing-impulsa.xlsb", target_dir, period="2099.01")
    assert _decision_code(caught) == "MUTATION_GUARD_REQUIRED"
    assert not target_dir.exists()


def test_direct_database_importer_bypass_is_rejected_before_sqlite_access():
    target = LAB / "database_bypass.sqlite"
    with pytest.raises(BoundaryViolation) as caught:
        ph15_database.import_period(target, root=ROOT, period="2099.01")
    assert _decision_code(caught) == "MUTATION_GUARD_REQUIRED"
    assert not target.exists()


@pytest.mark.parametrize("entrypoint", ["connect", "initialize_database", "backup_database"])
def test_public_sqlite_write_helpers_require_guard(entrypoint: str):
    target = LAB / f"{entrypoint}.sqlite"
    with pytest.raises(BoundaryViolation) as caught:
        if entrypoint == "connect":
            ph15_database.connect(target)
        elif entrypoint == "initialize_database":
            ph15_database.initialize_database(target)
        else:
            ph15_database.backup_database(ROOT / "DATA/KTMA.sqlite", target)
    assert _decision_code(caught) == "MUTATION_GUARD_REQUIRED"
    assert not target.exists()


@pytest.mark.parametrize("launcher", ["run_ph1.py", "run_ph1_v2.py"])
def test_legacy_financial_launchers_converge_on_guarded_cli(launcher: str):
    workbook = ROOT / "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"
    before = hashlib.sha256(workbook.read_bytes()).hexdigest()
    inherited_pythonpath = os.environ.get("PYTHONPATH")
    child_pythonpath = os.pathsep.join(
        part for part in (str(ROOT / "src"), inherited_pythonpath) if part
    )
    completed = subprocess.run(
        [sys.executable, str(ROOT / launcher)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": child_pythonpath},
    )
    assert completed.returncode != 0
    assert "ROOT_BOUNDARY_DENIED" in completed.stderr
    assert hashlib.sha256(workbook.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "target",
    [ROOT / "OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx", ROOT / "DATA/KTMA.sqlite"],
)
def test_protected_financial_targets_are_not_mutable_by_json_payload(target: Path):
    context = AuthorizationContext.from_dict(_payload(operations=("overwrite",), allowlist=(target,)))
    guard = BoundaryGuard(context)
    with pytest.raises(BoundaryViolation) as caught:
        guard.authorize(
            operation="overwrite",
            requested_target=target,
            resolved_physical_destination=target,
        )
    assert _decision_code(caught) == "PROTECTED_FINANCIAL_TARGET"


def test_hidden_indirect_destination_outside_root_is_rejected():
    external = ROOT.parent / "KTMA_TASK067_EXTERNAL_SIMULATION" / "hidden.log"
    with pytest.raises(BoundaryViolation) as caught:
        AuthorizationContext.from_dict(_payload(allowlist=(CANARY, external), indirect=(external,)))
    assert _decision_code(caught) == "ALLOWLIST_OUTSIDE_ROOT"
    assert not external.exists()


def test_windows_and_wsl_interpretations_bind_to_same_root():
    if os.name != "nt":
        pytest.skip("Native Windows round-trip assertion")
    windows_context = AuthorizationContext.from_dict(_payload())
    wsl_context = AuthorizationContext.from_dict(
        _payload(root=_wsl(ROOT), allowlist=(_wsl(CANARY),), runtime="wsl2")
    )
    assert windows_context.authorized_root == wsl_context.authorized_root == ROOT.resolve()
    assert windows_context.exact_target_allowlist == wsl_context.exact_target_allowlist


def test_prewrite_authorization_followed_by_missing_output_fails_postcheck():
    target = LAB / "missing_after_authorize.txt"
    context = AuthorizationContext.from_dict(_payload(allowlist=(target,)))
    guard = BoundaryGuard(context)
    guard.authorize(operation="create", requested_target=target, resolved_physical_destination=target)
    with pytest.raises(BoundaryViolation) as caught:
        guard.verify_post_write(target)
    assert _decision_code(caught) == "POSTWRITE_FILE_MISSING"
    assert not target.exists()


def test_real_post_effect_failure_is_classified_uncertain_without_blind_retry():
    target = LAB / "post_effect_failure.txt"
    context = AuthorizationContext.from_dict(_payload(allowlist=(target,)))
    guard = BoundaryGuard(context)
    before = snapshot_tree_metadata(LAB)
    GuardedFilesystem(guard).write_text(target, target, "synthetic durable effect before failure\n")
    with pytest.raises(BoundaryViolation) as caught:
        reconcile_failed_mutation(
            before=before,
            root=LAB,
            allowed_changed_paths=(str(target.resolve()),),
            entrypoint="synthetic-supported-write",
            cause=RuntimeError("fault injected after write"),
        )
    assert _decision_code(caught) == "INCOMPLETE_MUTATION_EFFECT_DETECTED"
    assert caught.value.decision.status == "UNCERTAIN_EFFECT"
    assert caught.value.decision.evidence["retry_allowed"] is False
    assert target.read_text(encoding="utf-8") == "synthetic durable effect before failure\n"


def test_unexpected_external_side_effect_is_rejected_by_reconciler():
    external = str(ROOT.parent / "KTMA_TASK067_EXTERNAL_SIMULATION" / "unexpected.txt")
    with pytest.raises(BoundaryViolation) as caught:
        reconcile_side_effects({}, {external: "1:1:1"}, ())
    assert _decision_code(caught) == "UNEXPECTED_SIDE_EFFECT"


def test_non_financial_positive_canary_has_exact_path_size_and_hash():
    LAB.mkdir(parents=True, exist_ok=True)
    context = AuthorizationContext.from_dict(_payload())
    receipt = GuardedFilesystem(BoundaryGuard(context)).write_text(CANARY, CANARY, "TASK067 authorized canary\n")
    expected = b"TASK067 authorized canary\n"
    assert receipt["path"] == str(CANARY.resolve())
    assert receipt["size_bytes"] == len(expected)
    assert receipt["sha256"] == hashlib.sha256(expected).hexdigest()
    assert CANARY.read_bytes() == expected
