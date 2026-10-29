"""TASK070 isolated LAB_ONLY authorization helpers for financial regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import uuid

from kt_movemacc.trusted_authorization import (
    AUDIENCE,
    GRANT_SCHEMA,
    InMemoryReplayRegistry,
    LabHmacSha256Verifier,
    SetRevocationProvider,
    VerificationPolicy,
    make_lab_envelope,
    verify_envelope,
)


ROOT = Path(__file__).resolve().parents[1]
import re
_run_id = os.environ.get("KTMA_RUN_ID", "").strip()
if not re.match(r"^RUN_\d{3}$", _run_id):
    raise RuntimeError(f"KTMA_RUN_ID environment variable missing or invalid: {_run_id!r}")
RUN_ROOT = (ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS" / _run_id).resolve()
_expected_base = (ROOT / "90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS").resolve()
if _expected_base not in RUN_ROOT.parents and RUN_ROOT.parent != _expected_base:
    raise RuntimeError(f"RUN_ROOT traversal violation: {RUN_ROOT}")
TASK_ID = "KTMA_TASK070"
LAB_KEY_ID = "task070-fixture-key"
LAB_ONLY_TEST_KEY = b"KTMA_TASK070_LAB_ONLY_NON_PRODUCTIVE_TEST_KEY_V1"

PH15_CASES = (
    "schema",
    "idempotency",
    "rollback",
    "source_hash_change",
    "missing_inputs",
    "repeated_titles",
    "multiple_periods",
    "foreign_keys",
    "financial_matrices",
    "integrity",
    "source_hashes",
)
WRITER_CASES = (
    "linux_canonical",
    "windows_canonical",
    "readonly",
    "disposable",
    "backup_canonical",
    "backup_source",
)

_prepared = False


def runtime_name() -> str:
    return "windows" if os.name == "nt" else "wsl2"


def ensure_run_layout() -> Path:
    """Create the exact RUN_001 directory set once and reject collisions."""

    global _prepared
    if _prepared:
        return RUN_ROOT
    if RUN_ROOT.exists():
        raise RuntimeError(f"TASK070 fixture collision; refusing overwrite: {RUN_ROOT}")
    directories = [RUN_ROOT / "ph1", RUN_ROOT / "temp"]
    directories += [RUN_ROOT / "ph15" / name for name in PH15_CASES]
    directories += [RUN_ROOT / "writer" / name for name in WRITER_CASES]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=False)
    _prepared = True
    return RUN_ROOT


def sqlite_sidecars(path: Path) -> tuple[Path, Path, Path]:
    return tuple(Path(f"{path}{suffix}") for suffix in ("-journal", "-wal", "-shm"))


def _lab_guard(
    *,
    targets: tuple[Path, ...],
    indirect: tuple[Path, ...] = (),
    operations: tuple[str, ...] = ("create", "overwrite"),
):
    now = datetime.now(timezone.utc)
    nonce = uuid.uuid4().hex
    normalized_targets = tuple(path.resolve(strict=False) for path in targets)
    material = "|".join(sorted(map(str, normalized_targets))) + "|" + nonce
    grant_id = "KTMA070-LAB-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    grant = {
        "SCHEMA": GRANT_SCHEMA,
        "GRANT_ID": grant_id,
        "ISSUER": "KTMA_TASK070_LAB_TEST_ISSUER_NOT_AUTHORITY",
        "SUBJECT": "pytest-fixture-process",
        "AUDIENCE": AUDIENCE,
        "ACTIVE_PROJECT": "KT.MovemAcc",
        "AUTHORIZED_ROOT": str(ROOT.resolve()),
        "TASK_ID": TASK_ID,
        "EXECUTION_RUNTIME": runtime_name(),
        "AUTHORIZED_OPERATIONS": list(operations),
        "EXACT_TARGET_ALLOWLIST": [str(path) for path in normalized_targets],
        "DECLARED_INDIRECT_OUTPUTS": [str(path.resolve(strict=False)) for path in indirect],
        "ISSUED_AT": (now - timedelta(minutes=2)).isoformat(),
        "NOT_BEFORE": (now - timedelta(minutes=1)).isoformat(),
        "EXPIRES_AT": (now + timedelta(hours=2)).isoformat(),
        "NONCE": nonce,
        "DELEGATION_DEPTH": 0,
        "MAX_DELEGATION_DEPTH": 0,
        "PARENT_GRANT_SHA256": None,
        "LAB_ONLY": True,
    }
    envelope = make_lab_envelope(grant, key_id=LAB_KEY_ID, key=LAB_ONLY_TEST_KEY)
    verified = verify_envelope(
        envelope,
        policy=VerificationPolicy(
            expected_project="KT.MovemAcc",
            expected_root=ROOT.resolve(),
            expected_task=TASK_ID,
            expected_audience=AUDIENCE,
            expected_runtime=runtime_name(),
            allow_lab=True,
            now=now,
        ),
        signature_verifier=LabHmacSha256Verifier({LAB_KEY_ID: LAB_ONLY_TEST_KEY}),
        replay_registry=InMemoryReplayRegistry(),
        revocation_provider=SetRevocationProvider(),
    )
    assert verified.verification_receipt["verification_mode"] == "LAB_ONLY"
    assert verified.verification_receipt["productive_trust"] is False
    return verified.boundary_guard()


def ph1_guard():
    ensure_run_layout()
    outputs = (
        RUN_ROOT / "ph1/CAM2026.08_CONSOL.ALIGN.xlsx",
        RUN_ROOT / "ph1/KTMA_PH1_REPORT.json",
        RUN_ROOT / "ph1/KTMA_TASK031_SPECIALIST_PH1_FINANCIAL_CONVERGENCE_REPORT.json",
    )
    return _lab_guard(targets=outputs)


def database_path(case: str) -> Path:
    if case not in PH15_CASES:
        raise ValueError(f"Unknown PH1.5 fixture case: {case}")
    ensure_run_layout()
    return RUN_ROOT / "ph15" / case / "KTMA.sqlite"


def database_guard(path: Path):
    sidecars = sqlite_sidecars(path)
    return _lab_guard(targets=(path, *sidecars), indirect=sidecars)


def writer_database(case: str, filename: str = "KTMA.sqlite") -> Path:
    if case not in WRITER_CASES:
        raise ValueError(f"Unknown writer fixture case: {case}")
    ensure_run_layout()
    return RUN_ROOT / "writer" / case / filename


def file_guard(path: Path, *, with_sqlite_sidecars: bool = False):
    sidecars = sqlite_sidecars(path) if with_sqlite_sidecars else ()
    return _lab_guard(targets=(path, *sidecars), indirect=sidecars)

