from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
from pathlib import Path

import pytest

from kt_movemacc.root_boundary import AuthorizationContext, BoundaryGuard, BoundaryViolation
from kt_movemacc.trusted_authorization import (
    AUDIENCE,
    GRANT_SCHEMA,
    AuthorizationVerificationError,
    InMemoryReplayRegistry,
    LabHmacSha256Verifier,
    SetRevocationProvider,
    VerificationPolicy,
    canonical_json_bytes,
    create_lab_review_guard,
    grant_sha256,
    make_lab_envelope,
    verify_envelope,
    verify_productive_grant_files,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 28, 15, 0, tzinfo=timezone.utc)
KEY_ID = "task070-lab-vector"
LAB_KEY = b"TASK070_LAB_ONLY_VECTOR_KEY_NOT_PRODUCTIVE"
TARGET_A = ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS/RUN_001/lab/a.txt"
TARGET_B = ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS/RUN_001/lab/b.txt"


def _grant(**changes):
    grant = {
        "SCHEMA": GRANT_SCHEMA,
        "GRANT_ID": "KTMA070-LAB-GRANT-001",
        "ISSUER": "TASK070_LAB_TEST_ISSUER_NOT_AUTHORITY",
        "SUBJECT": "pytest",
        "AUDIENCE": AUDIENCE,
        "ACTIVE_PROJECT": "KT.MovemAcc",
        "AUTHORIZED_ROOT": str(ROOT.resolve()),
        "TASK_ID": "KTMA_TASK070",
        "EXECUTION_RUNTIME": "windows" if __import__("os").name == "nt" else "wsl2",
        "AUTHORIZED_OPERATIONS": ["create", "overwrite"],
        "EXACT_TARGET_ALLOWLIST": [str(TARGET_A.resolve(strict=False)), str(TARGET_B.resolve(strict=False))],
        "DECLARED_INDIRECT_OUTPUTS": [],
        "ISSUED_AT": (NOW - timedelta(minutes=2)).isoformat(),
        "NOT_BEFORE": (NOW - timedelta(minutes=1)).isoformat(),
        "EXPIRES_AT": (NOW + timedelta(minutes=10)).isoformat(),
        "NONCE": "task070-lab-nonce-001",
        "DELEGATION_DEPTH": 0,
        "MAX_DELEGATION_DEPTH": 1,
        "PARENT_GRANT_SHA256": None,
        "LAB_ONLY": True,
    }
    grant.update(changes)
    return grant


def _policy(**changes):
    values = {
        "expected_project": "KT.MovemAcc",
        "expected_root": ROOT.resolve(),
        "expected_task": "KTMA_TASK070",
        "expected_audience": AUDIENCE,
        "expected_runtime": "windows" if __import__("os").name == "nt" else "wsl2",
        "allow_lab": True,
        "now": NOW,
    }
    values.update(changes)
    return VerificationPolicy(**values)


def _envelope(grant=None):
    return make_lab_envelope(grant or _grant(), key_id=KEY_ID, key=LAB_KEY)


def _verify(envelope=None, *, replay=None, revoked=frozenset(), parent=None, policy=None):
    return verify_envelope(
        envelope or _envelope(),
        policy=policy or _policy(),
        signature_verifier=LabHmacSha256Verifier({KEY_ID: LAB_KEY}),
        replay_registry=replay or InMemoryReplayRegistry(),
        revocation_provider=SetRevocationProvider(set(revoked)),
        parent=parent,
    )


def _assert_code(expected, callable_):
    with pytest.raises(AuthorizationVerificationError) as caught:
        callable_()
    assert caught.value.code == expected


def test_canonical_serialization_is_deterministic_and_hash_bound():
    grant = _grant()
    reordered = dict(reversed(list(grant.items())))
    assert canonical_json_bytes(grant) == canonical_json_bytes(reordered)
    assert grant_sha256(grant) == grant_sha256(reordered)


def test_positive_lab_grant_binds_non_productive_guard():
    verified = _verify()
    guard = verified.boundary_guard()
    assert verified.verification_receipt["verification_mode"] == "LAB_ONLY"
    assert verified.verification_receipt["productive_trust"] is False
    assert guard.verified_authorization["grant_sha256"] == verified.grant_hash
    assert guard.context.authorization_provenance == "LAB_ONLY_VERIFIED_GRANT"


def test_forged_signature_is_rejected():
    envelope = _envelope()
    envelope["SIGNATURE"] = "Zm9yZ2Vk"
    _assert_code("SIGNATURE_INVALID", lambda: _verify(envelope))


def test_altered_signed_grant_is_rejected():
    envelope = _envelope()
    envelope["GRANT"]["AUTHORIZED_OPERATIONS"] = ["create"]
    _assert_code("SIGNATURE_INVALID", lambda: _verify(envelope))


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"EXPIRES_AT": (NOW - timedelta(seconds=1)).isoformat()}, "GRANT_EXPIRED"),
        ({"NOT_BEFORE": (NOW + timedelta(minutes=1)).isoformat(), "EXPIRES_AT": (NOW + timedelta(minutes=2)).isoformat()}, "GRANT_NOT_YET_VALID"),
        ({"ACTIVE_PROJECT": "SkillsMachine"}, "GRANT_BINDING_MISMATCH"),
        ({"AUTHORIZED_ROOT": str(ROOT.parent.resolve())}, "GRANT_BINDING_MISMATCH"),
        ({"AUDIENCE": "different.application"}, "GRANT_BINDING_MISMATCH"),
        ({"TASK_ID": "KTMA_TASK999"}, "GRANT_BINDING_MISMATCH"),
        ({"EXECUTION_RUNTIME": "wsl2" if __import__("os").name == "nt" else "windows"}, "GRANT_BINDING_MISMATCH"),
    ],
)
def test_time_and_execution_bindings_fail_closed(changes, code):
    _assert_code(code, lambda: _verify(_envelope(_grant(**changes))))


def test_revoked_grant_is_rejected():
    _assert_code(
        "GRANT_REVOKED",
        lambda: _verify(_envelope(), revoked={"KTMA070-LAB-GRANT-001"}),
    )


def test_replayed_nonce_is_rejected():
    registry = InMemoryReplayRegistry()
    _verify(_envelope(), replay=registry)
    _assert_code("GRANT_REPLAYED", lambda: _verify(_envelope(), replay=registry))


def test_expanded_delegation_is_rejected():
    parent = _verify(_envelope())
    child_grant = _grant(
        GRANT_ID="KTMA070-LAB-GRANT-CHILD",
        NONCE="task070-lab-nonce-child",
        AUTHORIZED_OPERATIONS=["create"],
        EXACT_TARGET_ALLOWLIST=[
            str(TARGET_A.resolve(strict=False)),
            str((ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS/RUN_001/lab/outside-parent.txt").resolve(strict=False)),
        ],
        DELEGATION_DEPTH=1,
        MAX_DELEGATION_DEPTH=1,
        PARENT_GRANT_SHA256=parent.grant_hash,
    )
    _assert_code(
        "DELEGATION_SCOPE_EXPANSION",
        lambda: _verify(_envelope(child_grant), parent=parent),
    )


def test_narrow_delegation_is_accepted():
    parent = _verify(_envelope())
    child_grant = _grant(
        GRANT_ID="KTMA070-LAB-GRANT-CHILD-OK",
        NONCE="task070-lab-nonce-child-ok",
        AUTHORIZED_OPERATIONS=["create"],
        EXACT_TARGET_ALLOWLIST=[str(TARGET_A.resolve(strict=False))],
        DELEGATION_DEPTH=1,
        MAX_DELEGATION_DEPTH=1,
        PARENT_GRANT_SHA256=parent.grant_hash,
    )
    child = _verify(_envelope(child_grant), parent=parent)
    assert child.authorization_context.authorized_operations == frozenset({"create"})


def test_lab_vector_cannot_claim_productive_authority():
    productive_claim = _grant(LAB_ONLY=False)
    _assert_code(
        "LAB_VECTOR_REQUIRED",
        lambda: _envelope(productive_claim),
    )

    signature = hmac.new(LAB_KEY, canonical_json_bytes(productive_claim), hashlib.sha256).digest()
    forged_envelope = {
        "SCHEMA": "ktma.authorization-envelope.v1",
        "GRANT": productive_claim,
        "SIGNATURE_ALGORITHM": "LAB-HMAC-SHA256",
        "KEY_ID": KEY_ID,
        "SIGNATURE": base64.b64encode(signature).decode("ascii"),
    }
    _assert_code(
        "PRODUCTIVE_TRUST_UNAVAILABLE",
        lambda: _verify(forged_envelope),
    )


def test_unsigned_context_cannot_enter_financial_entrypoint():
    payload = {
        "ACTIVE_PROJECT": "KT.MovemAcc",
        "AUTHORIZED_ROOT": str(ROOT.resolve()),
        "TASK_ID": "KTMA_TASK070",
        "AUTHORIZED_OPERATIONS": ["create"],
        "EXACT_TARGET_ALLOWLIST": [str(TARGET_A.resolve(strict=False))],
        "EXECUTION_RUNTIME": "windows" if __import__("os").name == "nt" else "wsl2",
    }
    guard = BoundaryGuard(AuthorizationContext.from_dict(payload))
    from kt_movemacc.root_boundary import require_boundary_guard

    with pytest.raises(BoundaryViolation) as caught:
        require_boundary_guard(guard, "synthetic.financial.entrypoint")
    assert caught.value.decision.code == "TRUSTED_AUTHORIZATION_REQUIRED"


def test_productive_configuration_defaults_to_deny_unavailable():
    config = ROOT / "04_CONFIG/SECURITY/KTMA_AUTHORIZATION_TRUST.json"
    missing_grant = ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS/never-created-grant.json"
    _assert_code(
        "PRODUCTIVE_TRUST_UNAVAILABLE",
        lambda: verify_productive_grant_files(
            grant_file=missing_grant,
            trust_config_file=config,
            expected_task="KTMA_TASK070",
            expected_runtime=_policy().expected_runtime,
        ),
    )


def test_lab_review_guard_is_ephemeral_and_non_productive():
    destination = ROOT / "90_RUNTIME/PH1_REVIEW/2099.01/RUN_999"
    guard = create_lab_review_guard(root=ROOT, out_dir=destination, period="2099.01")
    assert guard.verified_authorization["verification_mode"] == "LAB_ONLY"
    assert guard.verified_authorization["productive_trust"] is False
    assert all(destination in path.parents for path in guard.context.exact_target_allowlist)


@pytest.mark.parametrize(
    "destination",
    [
        ROOT / "OUTPUT/2026.09/RUN_001",
        ROOT / "90_RUNTIME/PH1_REVIEW/2026.09/not-a-run",
    ],
)
def test_lab_review_guard_rejects_non_fixture_destinations(destination):
    _assert_code(
        "LAB_DESTINATION_OUTSIDE_RUNTIME" if "OUTPUT" in destination.parts else "LAB_DESTINATION_INVALID",
        lambda: create_lab_review_guard(root=ROOT, out_dir=destination, period="2026.09"),
    )
