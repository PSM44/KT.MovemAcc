"""Project-local authorization-grant verification for KT.MovemAcc.

The module supplies deterministic grant validation and a signature-verifier
abstraction.  The bundled positive verifier is deliberately LAB_ONLY.  No
productive issuer, private key, trust-anchor custody, replay service, or
revocation service is provided by this repository.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
from typing import Any, Mapping, Protocol

from kt_movemacc.root_boundary import (
    AuthorizationContext,
    BoundaryGuard,
    BoundaryViolation,
    PROJECT_ID,
    _VERIFIED_AUTHORIZATION_BINDING,
    trusted_project_root,
)


GRANT_SCHEMA = "ktma.authorization-grant.v1"
ENVELOPE_SCHEMA = "ktma.authorization-envelope.v1"
AUDIENCE = "kt_movemacc.mutation"
LAB_SIGNATURE_ALGORITHM = "LAB-HMAC-SHA256"
PRODUCTIVE_TRUST_STATUS = "DENY_UNAVAILABLE"

_GRANT_FIELDS = frozenset(
    {
        "SCHEMA",
        "GRANT_ID",
        "ISSUER",
        "SUBJECT",
        "AUDIENCE",
        "ACTIVE_PROJECT",
        "AUTHORIZED_ROOT",
        "TASK_ID",
        "EXECUTION_RUNTIME",
        "AUTHORIZED_OPERATIONS",
        "EXACT_TARGET_ALLOWLIST",
        "DECLARED_INDIRECT_OUTPUTS",
        "ISSUED_AT",
        "NOT_BEFORE",
        "EXPIRES_AT",
        "NONCE",
        "DELEGATION_DEPTH",
        "MAX_DELEGATION_DEPTH",
        "PARENT_GRANT_SHA256",
        "LAB_ONLY",
    }
)
_ENVELOPE_FIELDS = frozenset(
    {"SCHEMA", "GRANT", "SIGNATURE_ALGORITHM", "KEY_ID", "SIGNATURE"}
)


class AuthorizationVerificationError(PermissionError):
    def __init__(self, code: str, message: str, **evidence: Any) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.evidence = evidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "DENIED",
            "code": self.code,
            "message": self.message,
            "evidence": self.evidence,
        }


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the deterministic UTF-8 representation used for signatures."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def grant_sha256(grant: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(grant)).hexdigest()


class SignatureVerifier(Protocol):
    verification_mode: str

    def verify(
        self,
        *,
        key_id: str,
        algorithm: str,
        message: bytes,
        signature: str,
    ) -> bool: ...


class ReplayRegistry(Protocol):
    productive: bool

    def consume(self, *, nonce: str, grant_id: str) -> bool: ...


class RevocationProvider(Protocol):
    productive: bool

    def is_revoked(self, *, grant_id: str, grant_hash: str) -> bool: ...


class DenyUnavailableSignatureVerifier:
    verification_mode = "DENY_UNAVAILABLE"

    def verify(
        self,
        *,
        key_id: str,
        algorithm: str,
        message: bytes,
        signature: str,
    ) -> bool:
        raise AuthorizationVerificationError(
            "PRODUCTIVE_TRUST_UNAVAILABLE",
            "No productive signature verifier or independently protected trust anchor is configured",
            key_id=key_id,
            algorithm=algorithm,
        )


class LabHmacSha256Verifier:
    """Explicitly non-productive verifier used only by isolated test vectors."""

    verification_mode = "LAB_ONLY"

    def __init__(self, keys: Mapping[str, bytes]) -> None:
        if not keys or any(not key for key in keys.values()):
            raise ValueError("LAB_ONLY verifier requires non-empty test keys")
        self._keys = dict(keys)

    def verify(
        self,
        *,
        key_id: str,
        algorithm: str,
        message: bytes,
        signature: str,
    ) -> bool:
        if algorithm != LAB_SIGNATURE_ALGORITHM or key_id not in self._keys:
            return False
        try:
            observed = base64.b64decode(signature, validate=True)
        except (ValueError, TypeError):
            return False
        expected = hmac.new(self._keys[key_id], message, hashlib.sha256).digest()
        return hmac.compare_digest(observed, expected)


class InMemoryReplayRegistry:
    """Process-local LAB_ONLY replay detector; never productive enforcement."""

    productive = False

    def __init__(self) -> None:
        self._consumed: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def consume(self, *, nonce: str, grant_id: str) -> bool:
        identity = (nonce, grant_id)
        with self._lock:
            if identity in self._consumed:
                return False
            self._consumed.add(identity)
            return True


class SetRevocationProvider:
    """Process-local LAB_ONLY revocation test double."""

    productive = False

    def __init__(self, revoked: set[str] | frozenset[str] = frozenset()) -> None:
        self._revoked = frozenset(revoked)

    def is_revoked(self, *, grant_id: str, grant_hash: str) -> bool:
        return grant_id in self._revoked or grant_hash in self._revoked


@dataclass(frozen=True)
class VerificationPolicy:
    expected_project: str
    expected_root: Path
    expected_task: str
    expected_audience: str
    expected_runtime: str
    allow_lab: bool = False
    now: datetime | None = None


@dataclass(frozen=True)
class VerifiedGrant:
    grant: Mapping[str, Any]
    grant_hash: str
    authorization_context: AuthorizationContext
    verification_receipt: Mapping[str, Any]

    def boundary_guard(self) -> BoundaryGuard:
        guard = BoundaryGuard(self.authorization_context)
        guard._bind_verified_authorization(
            binding_token=_VERIFIED_AUTHORIZATION_BINDING,
            receipt=self.verification_receipt,
        )
        return guard


def _fail(code: str, message: str, **evidence: Any) -> None:
    raise AuthorizationVerificationError(code, message, **evidence)


def _require_exact_fields(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    observed = set(value)
    if observed != set(expected):
        _fail(
            f"{label}_SCHEMA_INVALID",
            f"{label} fields do not match the canonical schema",
            missing=sorted(set(expected) - observed),
            unexpected=sorted(observed - set(expected)),
        )


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("GRANT_FIELD_INVALID", f"{field} must be a non-empty string", field=field)
    return value.strip()


def _timestamp(value: Any, field: str) -> datetime:
    text = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorizationVerificationError(
            "GRANT_TIME_INVALID", f"{field} is not an RFC3339 timestamp", field=field
        ) from exc
    if parsed.tzinfo is None:
        _fail("GRANT_TIME_INVALID", f"{field} must include a timezone", field=field)
    return parsed.astimezone(timezone.utc)


def _list_of_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        _fail("GRANT_FIELD_INVALID", f"{field} must be a list of non-empty strings", field=field)
    if len(value) != len(set(value)):
        _fail("GRANT_FIELD_INVALID", f"{field} must not contain duplicates", field=field)
    return list(value)


def _verify_delegation(grant: Mapping[str, Any], parent: VerifiedGrant | None) -> None:
    depth = grant["DELEGATION_DEPTH"]
    maximum = grant["MAX_DELEGATION_DEPTH"]
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        _fail("DELEGATION_INVALID", "DELEGATION_DEPTH must be a non-negative integer")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
        _fail("DELEGATION_INVALID", "MAX_DELEGATION_DEPTH must be a non-negative integer")
    parent_hash = grant["PARENT_GRANT_SHA256"]
    if depth == 0:
        if parent is not None or parent_hash is not None:
            _fail("DELEGATION_INVALID", "A root grant cannot declare a parent")
        return
    if parent is None:
        _fail("DELEGATION_PARENT_REQUIRED", "Delegated grants require a verified parent")
    assert parent is not None
    if parent_hash != parent.grant_hash:
        _fail("DELEGATION_PARENT_MISMATCH", "Parent grant hash does not match")
    parent_grant = parent.grant
    if (
        depth != parent_grant["DELEGATION_DEPTH"] + 1
        or depth > parent_grant["MAX_DELEGATION_DEPTH"]
        or maximum > parent_grant["MAX_DELEGATION_DEPTH"]
    ):
        _fail("DELEGATION_DEPTH_EXPANSION", "Delegation depth exceeds the parent grant")
    for field in ("ACTIVE_PROJECT", "AUTHORIZED_ROOT", "TASK_ID", "AUDIENCE", "EXECUTION_RUNTIME"):
        if grant[field] != parent_grant[field]:
            _fail("DELEGATION_BINDING_EXPANSION", f"Delegation changed {field}", field=field)
    for field in ("AUTHORIZED_OPERATIONS", "EXACT_TARGET_ALLOWLIST", "DECLARED_INDIRECT_OUTPUTS"):
        if not set(grant[field]) <= set(parent_grant[field]):
            _fail("DELEGATION_SCOPE_EXPANSION", f"Delegation expanded {field}", field=field)
    if _timestamp(grant["EXPIRES_AT"], "EXPIRES_AT") > _timestamp(parent_grant["EXPIRES_AT"], "EXPIRES_AT"):
        _fail("DELEGATION_TIME_EXPANSION", "Delegation expires after its parent")
    if _timestamp(grant["NOT_BEFORE"], "NOT_BEFORE") < _timestamp(parent_grant["NOT_BEFORE"], "NOT_BEFORE"):
        _fail("DELEGATION_TIME_EXPANSION", "Delegation becomes valid before its parent")


def verify_envelope(
    envelope: Mapping[str, Any],
    *,
    policy: VerificationPolicy,
    signature_verifier: SignatureVerifier,
    replay_registry: ReplayRegistry,
    revocation_provider: RevocationProvider,
    parent: VerifiedGrant | None = None,
) -> VerifiedGrant:
    """Verify one grant and bind it to a project-local ``BoundaryGuard`` context."""

    _require_exact_fields(envelope, _ENVELOPE_FIELDS, "ENVELOPE")
    if envelope["SCHEMA"] != ENVELOPE_SCHEMA or not isinstance(envelope["GRANT"], Mapping):
        _fail("ENVELOPE_SCHEMA_INVALID", "Unsupported authorization envelope")
    grant = dict(envelope["GRANT"])
    _require_exact_fields(grant, _GRANT_FIELDS, "GRANT")
    if grant["SCHEMA"] != GRANT_SCHEMA:
        _fail("GRANT_SCHEMA_INVALID", "Unsupported authorization grant schema")

    for field in (
        "GRANT_ID", "ISSUER", "SUBJECT", "AUDIENCE", "ACTIVE_PROJECT", "AUTHORIZED_ROOT",
        "TASK_ID", "EXECUTION_RUNTIME", "ISSUED_AT", "NOT_BEFORE", "EXPIRES_AT", "NONCE",
    ):
        _text(grant[field], field)
    for field in ("AUTHORIZED_OPERATIONS", "EXACT_TARGET_ALLOWLIST", "DECLARED_INDIRECT_OUTPUTS"):
        _list_of_strings(grant[field], field)
    if not isinstance(grant["LAB_ONLY"], bool):
        _fail("GRANT_FIELD_INVALID", "LAB_ONLY must be a boolean", field="LAB_ONLY")

    message = canonical_json_bytes(grant)
    if not signature_verifier.verify(
        key_id=_text(envelope["KEY_ID"], "KEY_ID"),
        algorithm=_text(envelope["SIGNATURE_ALGORITHM"], "SIGNATURE_ALGORITHM"),
        message=message,
        signature=_text(envelope["SIGNATURE"], "SIGNATURE"),
    ):
        _fail("SIGNATURE_INVALID", "Grant signature verification failed")

    mode = signature_verifier.verification_mode
    if grant["LAB_ONLY"]:
        if not policy.allow_lab or mode != "LAB_ONLY":
            _fail("LAB_GRANT_NOT_AUTHORIZED", "LAB_ONLY grants are isolated from productive verification")
    elif mode != "PRODUCTIVE":
        _fail("PRODUCTIVE_TRUST_UNAVAILABLE", "A LAB_ONLY verifier cannot authorize a productive grant")

    observed_hash = grant_sha256(grant)
    if revocation_provider.is_revoked(grant_id=grant["GRANT_ID"], grant_hash=observed_hash):
        _fail("GRANT_REVOKED", "Grant is revoked", grant_id=grant["GRANT_ID"])

    now = (policy.now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued_at = _timestamp(grant["ISSUED_AT"], "ISSUED_AT")
    not_before = _timestamp(grant["NOT_BEFORE"], "NOT_BEFORE")
    expires_at = _timestamp(grant["EXPIRES_AT"], "EXPIRES_AT")
    if not issued_at <= not_before < expires_at:
        _fail("GRANT_TIME_INVALID", "Grant time ordering is invalid")
    if now < not_before:
        _fail("GRANT_NOT_YET_VALID", "Grant is not yet valid")
    if now >= expires_at:
        _fail("GRANT_EXPIRED", "Grant has expired")

    expected = {
        "ACTIVE_PROJECT": policy.expected_project,
        "AUTHORIZED_ROOT": str(policy.expected_root),
        "TASK_ID": policy.expected_task,
        "AUDIENCE": policy.expected_audience,
        "EXECUTION_RUNTIME": policy.expected_runtime,
    }
    for field, value in expected.items():
        if grant[field] != value:
            _fail("GRANT_BINDING_MISMATCH", f"Grant {field} does not match execution policy", field=field)

    _verify_delegation(grant, parent)

    context_payload = {
        "ACTIVE_PROJECT": grant["ACTIVE_PROJECT"],
        "AUTHORIZED_ROOT": grant["AUTHORIZED_ROOT"],
        "TASK_ID": grant["TASK_ID"],
        "AUTHORIZED_OPERATIONS": grant["AUTHORIZED_OPERATIONS"],
        "EXACT_TARGET_ALLOWLIST": grant["EXACT_TARGET_ALLOWLIST"],
        "EXECUTION_RUNTIME": grant["EXECUTION_RUNTIME"],
        "DECLARED_INDIRECT_OUTPUTS": grant["DECLARED_INDIRECT_OUTPUTS"],
    }
    try:
        context = AuthorizationContext.from_dict(context_payload)
    except BoundaryViolation as exc:
        _fail(
            "GRANT_CONTEXT_INVALID",
            "Grant cannot be converted into a bounded authorization context",
            boundary_code=exc.decision.code,
        )
    if context.authorized_root.resolve() != policy.expected_root.resolve():
        _fail("GRANT_ROOT_MISMATCH", "Grant root does not match the trusted physical project root")

    if not replay_registry.consume(nonce=grant["NONCE"], grant_id=grant["GRANT_ID"]):
        _fail("GRANT_REPLAYED", "Grant nonce has already been consumed", nonce=grant["NONCE"])

    provenance = "LAB_ONLY_VERIFIED_GRANT" if mode == "LAB_ONLY" else "PRODUCTIVE_VERIFIED_GRANT"
    context = replace(context, authorization_provenance=provenance)
    verified_at = now.isoformat()
    receipt = {
        "schema": "ktma.authorization-receipt.v1",
        "status": "VERIFIED",
        "verification_mode": mode,
        "productive_trust": mode == "PRODUCTIVE",
        "grant_id": grant["GRANT_ID"],
        "grant_sha256": observed_hash,
        "issuer": grant["ISSUER"],
        "subject": grant["SUBJECT"],
        "task_id": grant["TASK_ID"],
        "authorized_root": str(context.authorized_root),
        "verified_at": verified_at,
        "expires_at": expires_at.isoformat(),
        "replay_provider_productive": bool(replay_registry.productive),
        "revocation_provider_productive": bool(revocation_provider.productive),
    }
    return VerifiedGrant(grant, observed_hash, context, receipt)


def make_lab_envelope(
    grant: Mapping[str, Any],
    *,
    key_id: str,
    key: bytes,
) -> dict[str, Any]:
    """Sign a non-authoritative test vector; refuses non-LAB grants."""

    if grant.get("LAB_ONLY") is not True:
        _fail("LAB_VECTOR_REQUIRED", "The bundled signer may sign LAB_ONLY grants only")
    signature = hmac.new(key, canonical_json_bytes(grant), hashlib.sha256).digest()
    return {
        "SCHEMA": ENVELOPE_SCHEMA,
        "GRANT": dict(grant),
        "SIGNATURE_ALGORITHM": LAB_SIGNATURE_ALGORITHM,
        "KEY_ID": key_id,
        "SIGNATURE": base64.b64encode(signature).decode("ascii"),
    }


def create_lab_review_guard(
    *,
    root: Path | str,
    out_dir: Path | str,
    period: str,
) -> BoundaryGuard:
    """Create an ephemeral LAB_ONLY guard for one isolated PH1 review run.

    The grant is self-issued in memory and is therefore never productive
    authority.  Its destinations are restricted to the exact three PH1 files
    beneath ``90_RUNTIME/PH1_REVIEW/<period>/RUN_NNN``.
    """

    trusted_root = trusted_project_root()
    observed_root = Path(root).resolve()
    if observed_root != trusted_root.resolve():
        _fail("LAB_ROOT_MISMATCH", "LAB review root does not match the trusted project root")
    if not re.fullmatch(r"\d{4}\.\d{2}", period):
        _fail("LAB_PERIOD_INVALID", "LAB review period must use YYYY.MM")

    destination = Path(out_dir).resolve(strict=False)
    lab_root = (trusted_root / "90_RUNTIME/PH1_REVIEW").resolve(strict=False)
    try:
        relative = destination.relative_to(lab_root)
    except ValueError:
        _fail(
            "LAB_DESTINATION_OUTSIDE_RUNTIME",
            "LAB review destination must be beneath project-local 90_RUNTIME/PH1_REVIEW",
            destination=str(destination),
        )
    if len(relative.parts) != 2 or relative.parts[0] != period or not re.fullmatch(r"RUN_\d{3}", relative.parts[1]):
        _fail(
            "LAB_DESTINATION_INVALID",
            "LAB review destination must be 90_RUNTIME/PH1_REVIEW/<period>/RUN_NNN",
            destination=str(destination),
        )
    if destination.exists():
        _fail("LAB_DESTINATION_COLLISION", "LAB review destination already exists", destination=str(destination))

    outputs = (
        destination / f"CAM{period}_CONSOL.ALIGN.xlsx",
        destination / "KTMA_PH1_REPORT.json",
        destination / "KTMA_TASK031_SPECIALIST_PH1_FINANCIAL_CONVERGENCE_REPORT.json",
    )
    now = datetime.now(timezone.utc)
    key_id = "ephemeral-lab-review-key"
    ephemeral_key = secrets.token_bytes(32)
    grant = {
        "SCHEMA": GRANT_SCHEMA,
        "GRANT_ID": f"KTMA-LAB-PH1-{period}-{relative.parts[1]}",
        "ISSUER": "LOCAL_EPHEMERAL_LAB_REVIEW_NOT_AUTHORITY",
        "SUBJECT": "kt_movemacc.cli.ph1.lab-review",
        "AUDIENCE": AUDIENCE,
        "ACTIVE_PROJECT": PROJECT_ID,
        "AUTHORIZED_ROOT": str(trusted_root),
        "TASK_ID": f"KTMA_PH1_LAB_REVIEW_{period}",
        "EXECUTION_RUNTIME": "windows" if os.name == "nt" else "wsl2",
        "AUTHORIZED_OPERATIONS": ["create"],
        "EXACT_TARGET_ALLOWLIST": [str(path) for path in outputs],
        "DECLARED_INDIRECT_OUTPUTS": [],
        "ISSUED_AT": (now - timedelta(seconds=1)).isoformat(),
        "NOT_BEFORE": now.isoformat(),
        "EXPIRES_AT": (now + timedelta(minutes=30)).isoformat(),
        "NONCE": secrets.token_hex(16),
        "DELEGATION_DEPTH": 0,
        "MAX_DELEGATION_DEPTH": 0,
        "PARENT_GRANT_SHA256": None,
        "LAB_ONLY": True,
    }
    envelope = make_lab_envelope(grant, key_id=key_id, key=ephemeral_key)
    verified = verify_envelope(
        envelope,
        policy=VerificationPolicy(
            expected_project=PROJECT_ID,
            expected_root=trusted_root,
            expected_task=grant["TASK_ID"],
            expected_audience=AUDIENCE,
            expected_runtime=grant["EXECUTION_RUNTIME"],
            allow_lab=True,
            now=now,
        ),
        signature_verifier=LabHmacSha256Verifier({key_id: ephemeral_key}),
        replay_registry=InMemoryReplayRegistry(),
        revocation_provider=SetRevocationProvider(),
    )
    return verified.boundary_guard()


def verify_productive_grant_files(
    *,
    grant_file: Path | str,
    trust_config_file: Path | str,
    expected_task: str,
    expected_runtime: str,
) -> VerifiedGrant:
    """Fail closed until an externally protected productive verifier exists."""

    root = trusted_project_root()
    config_path = Path(trust_config_file).resolve()
    grant_path = Path(grant_file).resolve()
    for path in (config_path, grant_path):
        if root != path and root not in path.parents:
            _fail("AUTHORIZATION_FILE_OUTSIDE_ROOT", "Authorization inputs must be project-local", path=str(path))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("productive_verification") != PRODUCTIVE_TRUST_STATUS:
        _fail("TRUST_CONFIGURATION_INVALID", "Unsupported productive trust configuration")
    _fail(
        "PRODUCTIVE_TRUST_UNAVAILABLE",
        "External trusted issuance, custody, replay, and revocation are not configured",
        trust_config=str(config_path),
        grant_file=str(grant_path),
        expected_task=expected_task,
        expected_runtime=expected_runtime,
    )

