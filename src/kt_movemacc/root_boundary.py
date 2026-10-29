"""Project-local, fail-closed filesystem write boundary for KT.MovemAcc.

This module enforces explicit mutation authorization for supported callers.  It is
not an operating-system sandbox and cannot intercept direct writes that bypass it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ID = "KT.MovemAcc"
PROJECT_PACKAGE_NAME = "kt_movemacc"
SUPPORTED_RUNTIMES = frozenset({"windows", "wsl2"})
SUPPORTED_OPERATIONS = frozenset(
    {"check", "create", "overwrite", "delete", "copy", "move", "git", "verify"}
)
_VERIFIED_AUTHORIZATION_BINDING = object()
PROTECTED_FINANCIAL_RELATIVE_PATHS = frozenset(
    {
        Path("OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx"),
        Path("OUTPUT/2026.08/KTMA_PH1_REPORT.json"),
        Path("OUTPUT/2026.08/KTMA_TASK031_SPECIALIST_PH1_FINANCIAL_CONVERGENCE_REPORT.json"),
        Path("DATA/KTMA.sqlite"),
    }
)
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_DRIVE_RELATIVE = re.compile(r"^[A-Za-z]:(?![\\/])")
_WSL_ABSOLUTE = re.compile(r"^/mnt/([A-Za-z])(?:/|$)")


def trusted_project_root() -> Path:
    """Return the project root anchored to this module, or fail closed.

    The task-supplied authorization payload is deliberately not consulted. An
    editable checkout is the supported deployment for mutating entrypoints; a
    copied module or wheel without project identity files cannot authorize writes.
    """

    candidate = Path(__file__).resolve(strict=True).parents[2]
    pyproject = candidate / "pyproject.toml"
    git_directory = candidate / ".git"
    if candidate.name != PROJECT_ID or not pyproject.is_file() or not git_directory.is_dir():
        raise _deny(
            "TRUSTED_ROOT_IDENTITY_UNAVAILABLE",
            "Module origin is not a verified KT.MovemAcc project checkout",
            "context",
            str(candidate),
            resolved=candidate,
        )
    try:
        project_text = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        raise _deny(
            "TRUSTED_ROOT_IDENTITY_UNAVAILABLE",
            f"Project identity file cannot be read: {exc}",
            "context",
            str(candidate),
            resolved=candidate,
        ) from exc
    if not re.search(r'(?m)^name\s*=\s*["\']kt_movemacc["\']\s*$', project_text):
        raise _deny(
            "TRUSTED_ROOT_IDENTITY_MISMATCH",
            "pyproject.toml does not identify the kt_movemacc package",
            "context",
            str(candidate),
            resolved=candidate,
        )
    _reject_redirection(candidate, candidate, "context", str(candidate))
    return _canonical_local(candidate)


def _same_physical_path(left: Path, right: Path) -> bool:
    left_resolved = _canonical_local(left)
    right_resolved = _canonical_local(right)
    if left_resolved == right_resolved:
        return True
    try:
        return left_resolved.samefile(right_resolved)
    except OSError:
        return False


class BoundaryViolation(PermissionError):
    """Raised before a supported mutation when authorization is not satisfied."""

    def __init__(self, decision: "BoundaryDecision") -> None:
        super().__init__(f"{decision.code}: {decision.message}")
        self.decision = decision


@dataclass(frozen=True)
class BoundaryDecision:
    status: str
    code: str
    message: str
    operation: str
    requested_target: str
    resolved_physical_destination: str | None = None
    source: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "operation": self.operation,
            "requested_target": self.requested_target,
            "resolved_physical_destination": self.resolved_physical_destination,
            "source": self.source,
            "evidence": dict(self.evidence),
        }


def _deny(
    code: str,
    message: str,
    operation: str,
    requested_target: str,
    *,
    resolved: Path | None = None,
    source: str | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> BoundaryViolation:
    return BoundaryViolation(
        BoundaryDecision(
            status="DENIED",
            code=code,
            message=message,
            operation=operation,
            requested_target=requested_target,
            resolved_physical_destination=str(resolved) if resolved else None,
            source=source,
            evidence=evidence or {},
        )
    )


def _contains_private_use(text: str) -> bool:
    return any(0xE000 <= ord(character) <= 0xF8FF for character in text)


def _validate_path_text(text: str, operation: str) -> None:
    if not text or not text.strip():
        raise _deny("PATH_EMPTY", "Path is empty", operation, text)
    if _contains_private_use(text):
        raise _deny(
            "PATH_PRIVATE_USE_UNICODE",
            "Private-use Unicode code points are forbidden in filesystem paths",
            operation,
            text,
            evidence={"codepoints": [f"U+{ord(ch):04X}" for ch in text if 0xE000 <= ord(ch) <= 0xF8FF]},
        )
    if any(ord(character) < 32 for character in text):
        raise _deny("PATH_CONTROL_CHARACTER", "Control character in path", operation, text)
    if _WINDOWS_DRIVE_RELATIVE.match(text):
        raise _deny("PATH_DRIVE_RELATIVE", "Windows drive-relative path is ambiguous", operation, text)
    if text.startswith("\\\\") or text.startswith("//"):
        raise _deny("PATH_UNC_UNSUPPORTED", "UNC/device paths are not supported", operation, text)
    components = re.split(r"[\\/]", text)
    if ".." in components:
        raise _deny("PATH_TRAVERSAL", "Parent traversal is forbidden", operation, text)


def _runtime_name(runtime: str) -> str:
    normalized = runtime.strip().lower()
    if normalized not in SUPPORTED_RUNTIMES:
        raise _deny("RUNTIME_UNSUPPORTED", f"Unsupported execution runtime: {runtime}", "context", runtime)
    return normalized


def _localize_path(text: str, runtime: str, base: Path | None = None) -> Path:
    """Translate supported Windows/WSL syntax into the current host's local syntax."""

    _validate_path_text(text, "resolve")
    runtime = _runtime_name(runtime)
    wsl_match = _WSL_ABSOLUTE.match(text)

    if os.name == "nt":
        if wsl_match:
            drive = wsl_match.group(1).upper()
            remainder = PurePosixPath(text).parts[3:]
            return Path(f"{drive}:\\", *remainder)
        if _WINDOWS_ABSOLUTE.match(text):
            return Path(PureWindowsPath(text))
    else:
        if _WINDOWS_ABSOLUTE.match(text):
            windows = PureWindowsPath(text)
            drive = windows.drive[0].lower()
            return Path("/mnt", drive, *windows.parts[1:])
        if wsl_match:
            return Path(PurePosixPath(text))

    candidate = Path(text)
    if candidate.is_absolute():
        if runtime == "windows" and os.name != "nt":
            raise _deny("PATH_RUNTIME_MISMATCH", "POSIX absolute path supplied to Windows runtime", "resolve", text)
        if runtime == "wsl2" and os.name == "nt" and not wsl_match:
            raise _deny("PATH_RUNTIME_MISMATCH", "Non-WSL absolute path supplied to WSL2 runtime", "resolve", text)
        return candidate
    if base is None:
        raise _deny("PATH_RELATIVE_WITHOUT_BASE", "Relative path has no authorized base", "resolve", text)
    return base / candidate


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode) or path.is_symlink():
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _existing_chain(path: Path) -> list[Path]:
    current = Path(os.path.abspath(path))
    chain: list[Path] = []
    while True:
        if current.exists() or current.is_symlink():
            chain.append(current)
        if current.parent == current:
            break
        current = current.parent
    chain.reverse()
    return chain


def _reject_redirection(path: Path, root: Path, operation: str, requested: str) -> None:
    root_abs = Path(os.path.abspath(root))
    path_abs = Path(os.path.abspath(path))
    for member in _existing_chain(path_abs):
        try:
            if os.path.commonpath([str(member), str(root_abs)]) != str(root_abs):
                continue
        except ValueError:
            continue
        if _is_reparse_or_symlink(member):
            raise _deny(
                "PATH_REDIRECTION",
                f"Symlink, junction or reparse-point ancestor is forbidden: {member}",
                operation,
                requested,
                resolved=path_abs,
                evidence={"redirecting_ancestor": str(member)},
            )
        if member != root_abs and os.path.ismount(member):
            raise _deny(
                "PATH_MOUNT_ESCAPE",
                f"Nested mount point is forbidden: {member}",
                operation,
                requested,
                resolved=path_abs,
            )


def _canonical_local(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def _is_protected_financial_target(path: Path, root: Path) -> bool:
    resolved = _canonical_local(path)
    raw_root = _canonical_local(root / "RAW.INPUT")
    if _is_within(resolved, raw_root):
        return True
    return any(
        _same_physical_path(resolved, _canonical_local(root / relative))
        for relative in PROTECTED_FINANCIAL_RELATIVE_PATHS
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_tree_metadata(root: Path | str) -> dict[str, str]:
    """Snapshot regular files without following symlink/reparse directories.

    This detects durable additions, removals and metadata-visible changes. It is
    deliberately not represented as complete operating-system monitoring.
    """

    root_path = Path(root).resolve(strict=True)
    snapshot: dict[str, str] = {}
    for current, directories, files in os.walk(root_path, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if not _is_reparse_or_symlink(current_path / name)
        ]
        for name in files:
            path = current_path / name
            absolute = str(Path(os.path.abspath(path)))
            try:
                if _is_reparse_or_symlink(path):
                    snapshot[absolute] = "REDIRECTION_SKIPPED"
                    continue
                info = path.stat()
                snapshot[str(path.resolve(strict=True))] = f"{info.st_size}:{info.st_mtime_ns}:{getattr(info, 'st_ino', 0)}"
            except OSError as exc:
                snapshot[absolute] = f"INACCESSIBLE:{getattr(exc, 'winerror', None)}:{exc.errno}"
    return snapshot


@dataclass(frozen=True)
class AuthorizationContext:
    active_project: str
    authorized_root: Path
    task_id: str
    authorized_operations: frozenset[str]
    exact_target_allowlist: frozenset[Path]
    execution_runtime: str
    declared_indirect_outputs: frozenset[Path] = field(default_factory=frozenset)
    external_repository_roots: frozenset[Path] = field(default_factory=frozenset)
    project_root_binding: str = field(default="MODULE_ORIGIN_AND_PROJECT_IDENTITY", init=False)
    authorization_provenance: str = field(default="NOT_ENFORCED_UNAUTHENTICATED_PAYLOAD", repr=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorizationContext":
        reserved_trust_claims = {
            "AUTHORIZATION_PROVENANCE",
            "TRUSTED_AUTHORIZATION",
            "TRUSTED_ISSUER",
            "AUTHORIZATION_SIGNATURE",
        }
        claimed = sorted(reserved_trust_claims & set(payload))
        if claimed:
            raise _deny(
                "UNSUPPORTED_TRUST_CLAIM",
                "JSON payloads cannot self-declare trusted authorization provenance",
                "context",
                "<authorization-context>",
                evidence={"rejected_fields": claimed, "trusted_issuer": "NOT_AVAILABLE"},
            )
        required = {
            "ACTIVE_PROJECT",
            "AUTHORIZED_ROOT",
            "TASK_ID",
            "AUTHORIZED_OPERATIONS",
            "EXACT_TARGET_ALLOWLIST",
            "EXECUTION_RUNTIME",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise _deny(
                "AUTH_CONTEXT_INCOMPLETE",
                f"Missing authorization fields: {', '.join(missing)}",
                "context",
                "<authorization-context>",
            )
        active_project = str(payload["ACTIVE_PROJECT"]).strip()
        if active_project != PROJECT_ID:
            raise _deny(
                "ACTIVE_PROJECT_MISMATCH",
                f"Expected {PROJECT_ID}, observed {active_project or '<empty>'}",
                "context",
                active_project,
            )
        task_id = str(payload["TASK_ID"]).strip()
        if not task_id:
            raise _deny("TASK_ID_MISSING", "TASK_ID is required", "context", "<authorization-context>")
        runtime = _runtime_name(str(payload["EXECUTION_RUNTIME"]))
        root_requested = str(payload["AUTHORIZED_ROOT"])
        root_local = _localize_path(root_requested, runtime)
        _reject_redirection(root_local, root_local, "context", root_requested)
        root = _canonical_local(root_local)
        if not root.is_dir():
            raise _deny("AUTHORIZED_ROOT_INVALID", "Authorized root is not an existing directory", "context", root_requested, resolved=root)
        trusted_root = trusted_project_root()
        if not _same_physical_path(root, trusted_root):
            raise _deny(
                "PROJECT_ROOT_BINDING_MISMATCH",
                "Authorization payload root does not match the trusted KT.MovemAcc module root",
                "context",
                root_requested,
                resolved=root,
                evidence={"trusted_root": str(trusted_root)},
            )

        operations = frozenset(str(item).strip().lower() for item in payload["AUTHORIZED_OPERATIONS"])
        if not operations or not operations <= SUPPORTED_OPERATIONS:
            raise _deny(
                "OPERATION_SET_INVALID",
                "Authorization contains missing or unsupported operations",
                "context",
                root_requested,
                evidence={"operations": sorted(operations)},
            )

        def canonicalize_many(values: Iterable[Any], label: str) -> frozenset[Path]:
            result: set[Path] = set()
            for value in values:
                requested = str(value)
                local = _localize_path(requested, runtime, root)
                _reject_redirection(local, root, "context", requested)
                resolved = _canonical_local(local)
                if not _is_within(resolved, root):
                    raise _deny(
                        "ALLOWLIST_OUTSIDE_ROOT",
                        f"{label} entry resolves outside authorized root",
                        "context",
                        requested,
                        resolved=resolved,
                    )
                result.add(resolved)
            return frozenset(result)

        allowlist = canonicalize_many(payload["EXACT_TARGET_ALLOWLIST"], "allowlist")
        if not allowlist:
            raise _deny("ALLOWLIST_EMPTY", "Exact target allowlist is required", "context", root_requested)
        indirect = canonicalize_many(payload.get("DECLARED_INDIRECT_OUTPUTS", []), "indirect output")
        if not indirect <= allowlist:
            raise _deny("INDIRECT_OUTPUT_NOT_ALLOWLISTED", "Every indirect output must be exactly allowlisted", "context", root_requested)

        external_roots: set[Path] = set()
        for value in payload.get("EXTERNAL_REPOSITORY_ROOTS", []):
            requested = str(value)
            local = _localize_path(requested, runtime, root)
            external_roots.add(_canonical_local(local))

        return cls(
            active_project=active_project,
            authorized_root=root,
            task_id=task_id,
            authorized_operations=operations,
            exact_target_allowlist=allowlist,
            execution_runtime=runtime,
            declared_indirect_outputs=indirect,
            external_repository_roots=frozenset(external_roots),
        )

    @classmethod
    def from_json_file(cls, path: Path | str) -> "AuthorizationContext":
        trusted_root = trusted_project_root()
        source = _canonical_local(Path(path))
        _reject_redirection(source, trusted_root, "context", str(path))
        if not _is_within(source, trusted_root):
            raise _deny(
                "AUTHORIZATION_FILE_OUTSIDE_TRUSTED_ROOT",
                "Authorization files for supported entrypoints must be project-local",
                "context",
                str(path),
                resolved=source,
            )
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))

    def narrowed(
        self,
        *,
        operations: Iterable[str],
        allowlist: Iterable[Path | str],
    ) -> "AuthorizationContext":
        new_operations = frozenset(str(item).lower() for item in operations)
        if not new_operations <= self.authorized_operations:
            raise _deny("DELEGATION_OPERATION_EXPANSION", "Delegation cannot expand operations", "delegate", "<delegation>")
        resolved_allowlist = frozenset(
            self._resolve_delegated_target(item)
            for item in allowlist
        )
        if not resolved_allowlist <= self.exact_target_allowlist:
            raise _deny("DELEGATION_TARGET_EXPANSION", "Delegation cannot expand target allowlist", "delegate", "<delegation>")
        return AuthorizationContext(
            active_project=self.active_project,
            authorized_root=self.authorized_root,
            task_id=self.task_id,
            authorized_operations=new_operations,
            exact_target_allowlist=resolved_allowlist,
            execution_runtime=self.execution_runtime,
            declared_indirect_outputs=self.declared_indirect_outputs & resolved_allowlist,
            external_repository_roots=self.external_repository_roots,
            authorization_provenance=self.authorization_provenance,
        )

    def _resolve_delegated_target(self, item: Path | str) -> Path:
        requested = str(item)
        local = _localize_path(requested, self.execution_runtime, self.authorized_root)
        _reject_redirection(local, self.authorized_root, "delegate", requested)
        resolved = _canonical_local(local)
        if not _is_within(resolved, self.authorized_root):
            raise _deny(
                "DELEGATION_TARGET_EXPANSION",
                "Delegation target resolves outside the trusted project root",
                "delegate",
                requested,
                resolved=resolved,
            )
        return resolved


class BoundaryGuard:
    def __init__(self, context: AuthorizationContext) -> None:
        trusted_root = trusted_project_root()
        if not _same_physical_path(context.authorized_root, trusted_root):
            raise _deny(
                "PROJECT_ROOT_BINDING_MISMATCH",
                "BoundaryGuard refuses a context not bound to the trusted project root",
                "context",
                str(context.authorized_root),
                resolved=context.authorized_root,
                evidence={"trusted_root": str(trusted_root)},
            )
        self.context = context
        self._verified_authorization: Mapping[str, Any] | None = None

    def _bind_verified_authorization(
        self,
        *,
        binding_token: object,
        receipt: Mapping[str, Any],
    ) -> None:
        """Attach a verifier receipt for supported mutating entrypoints.

        This is a project-local application binding, not an OS security
        primitive.  Only ``trusted_authorization`` receives the in-process
        token; productive trust still depends on an external issuer and an
        independently protected trust anchor.
        """

        if binding_token is not _VERIFIED_AUTHORIZATION_BINDING:
            raise _deny(
                "VERIFIER_BINDING_REJECTED",
                "Only the project-local authorization verifier may bind a grant",
                "context",
                self.context.task_id,
            )
        required = {"grant_id", "grant_sha256", "verification_mode", "verified_at"}
        if not required <= set(receipt):
            raise _deny(
                "VERIFIER_RECEIPT_INCOMPLETE",
                "Verifier receipt is missing mandatory fields",
                "context",
                self.context.task_id,
                evidence={"missing": sorted(required - set(receipt))},
            )
        self._verified_authorization = dict(receipt)

    @property
    def verified_authorization(self) -> Mapping[str, Any] | None:
        return dict(self._verified_authorization) if self._verified_authorization else None

    def resolve(self, requested: Path | str, *, operation: str = "check") -> Path:
        text = str(requested)
        local = _localize_path(text, self.context.execution_runtime, self.context.authorized_root)
        _reject_redirection(local, self.context.authorized_root, operation, text)
        resolved = _canonical_local(local)
        if not _is_within(resolved, self.context.authorized_root):
            raise _deny("TARGET_OUTSIDE_ROOT", "Target resolves outside authorized root", operation, text, resolved=resolved)
        for external_root in self.context.external_repository_roots:
            if _is_within(resolved, external_root):
                raise _deny(
                    "EXTERNAL_REPOSITORY_DENIED",
                    f"Target resolves inside protected external repository: {external_root}",
                    operation,
                    text,
                    resolved=resolved,
                )
        return resolved

    def assert_authorized_root(self, observed_root: Path | str) -> None:
        resolved = self.resolve(observed_root, operation="check")
        if resolved != self.context.authorized_root:
            raise _deny(
                "AUTHORIZED_ROOT_MISMATCH",
                "Entrypoint root differs from authorization context root",
                "check",
                str(observed_root),
                resolved=resolved,
            )

    def authorize(
        self,
        *,
        operation: str,
        requested_target: Path | str,
        resolved_physical_destination: Path | str,
        source: Path | str | None = None,
        resolved_source: Path | str | None = None,
        indirect_outputs: Iterable[Path | str] = (),
    ) -> BoundaryDecision:
        operation = operation.lower()
        requested_text = str(requested_target)
        if operation not in self.context.authorized_operations:
            raise _deny("OPERATION_NOT_AUTHORIZED", f"Operation is not authorized: {operation}", operation, requested_text)
        resolved = self.resolve(requested_target, operation=operation)
        supplied_resolved = self.resolve(resolved_physical_destination, operation=operation)
        if supplied_resolved != resolved:
            raise _deny(
                "RESOLVED_DESTINATION_MISMATCH",
                "Caller-supplied physical destination does not match native resolution",
                operation,
                requested_text,
                resolved=resolved,
                evidence={"caller_supplied": str(supplied_resolved)},
            )
        if operation in {"create", "overwrite", "delete", "copy", "move"} and _is_protected_financial_target(
            resolved, self.context.authorized_root
        ):
            raise _deny(
                "PROTECTED_FINANCIAL_TARGET",
                "Protected financial artifacts are not mutable through an unauthenticated payload",
                operation,
                requested_text,
                resolved=resolved,
                evidence={"trusted_authorization_issuer": "NOT_AVAILABLE"},
            )
        if resolved not in self.context.exact_target_allowlist:
            raise _deny("TARGET_NOT_ALLOWLISTED", "Target is not in exact allowlist", operation, requested_text, resolved=resolved)
        if operation in {"create", "overwrite", "copy", "move"} and not resolved.parent.is_dir():
            raise _deny(
                "DESTINATION_PARENT_MISSING",
                "Destination parent must already exist; implicit directory creation is forbidden",
                operation,
                requested_text,
                resolved=resolved,
            )

        source_resolved: Path | None = None
        if source is not None:
            source_resolved = self.resolve(source, operation=operation)
            if resolved_source is None:
                raise _deny("RESOLVED_SOURCE_MISSING", "Resolved source is required", operation, requested_text, source=str(source))
            supplied_source = self.resolve(resolved_source, operation=operation)
            if supplied_source != source_resolved:
                raise _deny("RESOLVED_SOURCE_MISMATCH", "Caller-supplied source does not match native resolution", operation, requested_text, source=str(source))
            if source_resolved not in self.context.exact_target_allowlist:
                raise _deny("SOURCE_NOT_ALLOWLISTED", "Source is not in exact allowlist", operation, requested_text, source=str(source))

        observed_indirect = {self.resolve(item, operation=operation) for item in indirect_outputs}
        if observed_indirect != set(self.context.declared_indirect_outputs):
            raise _deny(
                "INDIRECT_OUTPUT_SET_MISMATCH",
                "Observed indirect outputs must exactly match declared indirect outputs",
                operation,
                requested_text,
                resolved=resolved,
                evidence={
                    "declared": sorted(map(str, self.context.declared_indirect_outputs)),
                    "observed": sorted(map(str, observed_indirect)),
                },
            )

        if operation in {"create", "copy", "move"} and resolved.exists():
            raise _deny("DESTINATION_COLLISION", "Destination already exists", operation, requested_text, resolved=resolved)
        if operation in {"overwrite", "delete"} and not resolved.exists():
            raise _deny("DESTINATION_MISSING", "Destination does not exist", operation, requested_text, resolved=resolved)
        if operation in {"copy", "move"} and (source_resolved is None or not source_resolved.is_file()):
            raise _deny("SOURCE_MISSING", "Source file does not exist", operation, requested_text, source=str(source))

        return BoundaryDecision(
            status="AUTHORIZED",
            code="WRITE_ATTEMPT_AUTHORIZED",
            message="Authorization context and physical destination verified",
            operation=operation,
            requested_target=requested_text,
            resolved_physical_destination=str(resolved),
            source=str(source_resolved) if source_resolved else None,
            evidence={
                "active_project": self.context.active_project,
                "task_id": self.context.task_id,
                "execution_runtime": self.context.execution_runtime,
                "authorization_provenance": self.context.authorization_provenance,
                "verified_grant": dict(self._verified_authorization or {}),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def verify_post_write(self, target: Path | str) -> dict[str, Any]:
        resolved = self.resolve(target, operation="verify")
        if resolved not in self.context.exact_target_allowlist:
            raise _deny("POSTWRITE_TARGET_NOT_ALLOWLISTED", "Post-write target is not allowlisted", "verify", str(target), resolved=resolved)
        if not resolved.is_file():
            raise _deny("POSTWRITE_FILE_MISSING", "Expected post-write file is missing", "verify", str(target), resolved=resolved)
        return {
            "path": str(resolved),
            "size_bytes": resolved.stat().st_size,
            "sha256": sha256_file(resolved),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def validate_command(
        self,
        *,
        command: Sequence[str],
        cwd: Path | str,
        declared_outputs: Iterable[Path | str] = (),
        observed_outputs: Iterable[Path | str] = (),
    ) -> BoundaryDecision:
        if "git" not in self.context.authorized_operations:
            raise _deny("COMMAND_OPERATION_NOT_AUTHORIZED", "Command execution is not authorized", "git", " ".join(command))
        cwd_resolved = self.resolve(cwd, operation="git")
        arguments = list(command)
        path_arguments: list[str] = []
        for index, argument in enumerate(arguments):
            if argument == "-C" and index + 1 < len(arguments):
                path_arguments.append(arguments[index + 1])
            elif argument.startswith("--work-tree=") or argument.startswith("--git-dir="):
                path_arguments.append(argument.split("=", 1)[1])
            elif argument in {"--work-tree", "--git-dir"} and index + 1 < len(arguments):
                path_arguments.append(arguments[index + 1])
        for argument in path_arguments:
            self.resolve(argument, operation="git")

        declared = {self.resolve(item, operation="git") for item in declared_outputs}
        observed = {self.resolve(item, operation="git") for item in observed_outputs}
        if observed != declared or not observed <= self.context.exact_target_allowlist:
            raise _deny(
                "COMMAND_OUTPUT_MISMATCH",
                "Observed command outputs differ from exact declared allowlist",
                "git",
                " ".join(command),
                evidence={"declared": sorted(map(str, declared)), "observed": sorted(map(str, observed))},
            )
        return BoundaryDecision(
            status="AUTHORIZED",
            code="COMMAND_AUTHORIZED",
            message="Command paths and outputs are within scope",
            operation="git",
            requested_target=" ".join(command),
            resolved_physical_destination=str(cwd_resolved),
        )


def require_boundary_guard(guard: BoundaryGuard | None, entrypoint: str) -> BoundaryGuard:
    """Reject direct mutating entrypoint calls that omit the boundary guard."""

    if not isinstance(guard, BoundaryGuard):
        raise _deny(
            "MUTATION_GUARD_REQUIRED",
            f"{entrypoint} requires an initialized BoundaryGuard",
            "context",
            entrypoint,
            evidence={"authorization_provenance": "NOT_ENFORCED_UNAUTHENTICATED_PAYLOAD"},
        )
    if guard.verified_authorization is None:
        raise _deny(
            "TRUSTED_AUTHORIZATION_REQUIRED",
            f"{entrypoint} requires a verifier-bound authorization grant",
            "context",
            entrypoint,
            evidence={
                "authorization_provenance": guard.context.authorization_provenance,
                "productive_trust": "NOT_ENFORCED",
            },
        )
    # Re-evaluate the trusted binding at every supported mutating entrypoint.
    trusted_root = trusted_project_root()
    if not _same_physical_path(guard.context.authorized_root, trusted_root):
        raise _deny(
            "PROJECT_ROOT_BINDING_MISMATCH",
            "Guard root no longer matches the trusted project root",
            "context",
            entrypoint,
            resolved=guard.context.authorized_root,
            evidence={"trusted_root": str(trusted_root)},
        )
    return guard


class GuardedFilesystem:
    def __init__(self, guard: BoundaryGuard) -> None:
        self.guard = guard

    def write_text(self, target: Path | str, resolved_target: Path | str, text: str) -> dict[str, Any]:
        target_path = self.guard.resolve(target, operation="check")
        operation = "overwrite" if target_path.exists() else "create"
        self.guard.authorize(
            operation=operation,
            requested_target=target,
            resolved_physical_destination=resolved_target,
        )
        flags = os.O_WRONLY | (os.O_TRUNC if operation == "overwrite" else os.O_CREAT | os.O_EXCL)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target_path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        return self.guard.verify_post_write(target_path)

    def copy_file(
        self,
        source: Path | str,
        resolved_source: Path | str,
        target: Path | str,
        resolved_target: Path | str,
    ) -> dict[str, Any]:
        decision = self.guard.authorize(
            operation="copy",
            requested_target=target,
            resolved_physical_destination=resolved_target,
            source=source,
            resolved_source=resolved_source,
        )
        destination = Path(decision.resolved_physical_destination or "")
        with Path(decision.source or "").open("rb") as source_handle:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(destination, flags, 0o600)
            with os.fdopen(descriptor, "wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
        return self.guard.verify_post_write(destination)

    def move_file(
        self,
        source: Path | str,
        resolved_source: Path | str,
        target: Path | str,
        resolved_target: Path | str,
    ) -> dict[str, Any]:
        decision = self.guard.authorize(
            operation="move",
            requested_target=target,
            resolved_physical_destination=resolved_target,
            source=source,
            resolved_source=resolved_source,
        )
        destination = Path(decision.resolved_physical_destination or "")
        os.rename(Path(decision.source or ""), destination)
        return self.guard.verify_post_write(destination)

    def delete_file(self, target: Path | str, resolved_target: Path | str) -> dict[str, Any]:
        decision = self.guard.authorize(
            operation="delete",
            requested_target=target,
            resolved_physical_destination=resolved_target,
        )
        destination = Path(decision.resolved_physical_destination or "")
        before_hash = sha256_file(destination)
        destination.unlink()
        if destination.exists():
            raise _deny("POSTDELETE_TARGET_EXISTS", "Deleted target still exists", "delete", str(target), resolved=destination)
        return {"path": str(destination), "deleted": True, "sha256_before": before_hash}


def reconcile_side_effects(
    before: Mapping[str, str],
    after: Mapping[str, str],
    allowed_changed_paths: Iterable[str],
) -> BoundaryDecision:
    changed = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    allowed = set(allowed_changed_paths)
    unexpected = sorted(changed - allowed)
    if unexpected:
        raise _deny(
            "UNEXPECTED_SIDE_EFFECT",
            "Post-write audit found unexpected filesystem effects",
            "verify",
            "<side-effect-audit>",
            evidence={"changed": sorted(changed), "unexpected": unexpected},
        )
    return BoundaryDecision(
        status="VERIFIED",
        code="SIDE_EFFECTS_RECONCILED",
        message="Observed changes are within the exact side-effect allowlist",
        operation="verify",
        requested_target="<side-effect-audit>",
        evidence={"changed": sorted(changed)},
    )


def reconcile_failed_mutation(
    *,
    before: Mapping[str, str],
    root: Path | str,
    allowed_changed_paths: Iterable[str],
    entrypoint: str,
    cause: BaseException,
) -> None:
    """Audit a failed mutation and classify any durable effect as uncertain.

    This does not claim transactional rollback. It prevents an exception after a
    write from bypassing reconciliation or being reported as a clean denial.
    """

    after = snapshot_tree_metadata(root)
    allowed = set(allowed_changed_paths)
    changed = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    unexpected = sorted(changed - allowed)
    if unexpected:
        raise _deny(
            "UNEXPECTED_SIDE_EFFECT_AFTER_FAILURE",
            "Failed mutation produced effects outside its exact allowlist",
            "verify",
            entrypoint,
            evidence={
                "changed": sorted(changed),
                "unexpected": unexpected,
                "cause_type": type(cause).__name__,
                "retry_allowed": False,
            },
        ) from cause
    if changed:
        raise BoundaryViolation(
            BoundaryDecision(
                status="UNCERTAIN_EFFECT",
                code="INCOMPLETE_MUTATION_EFFECT_DETECTED",
                message="Mutation failed after a durable allowlisted effect; reconciliation is required",
                operation="verify",
                requested_target=entrypoint,
                evidence={
                    "changed": sorted(changed),
                    "cause_type": type(cause).__name__,
                    "retry_allowed": False,
                    "rollback_authorized": False,
                },
            )
        ) from cause


def uncertain_incident(requested_target: str, reason: str) -> BoundaryDecision:
    return BoundaryDecision(
        status="UNCERTAIN_EFFECT",
        code="INCIDENT_RECONCILIATION_REQUIRED",
        message=reason,
        operation="verify",
        requested_target=requested_target,
        evidence={
            "retry_allowed": False,
            "rollback_authorized": False,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
