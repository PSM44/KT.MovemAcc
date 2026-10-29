"""Supported command-line entrypoint for the KT.MovemAcc root-boundary guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kt_movemacc.root_boundary import (  # noqa: E402
    AuthorizationContext,
    BoundaryGuard,
    BoundaryViolation,
    GuardedFilesystem,
    reconcile_side_effects,
    uncertain_incident,
)


def _json(value: str):
    return json.loads(value)


def _context(value: str) -> AuthorizationContext:
    return AuthorizationContext.from_dict(_json(value))


def _emit(payload: dict, exit_code: int) -> int:
    # Keep denials printable even when a malformed path contains characters
    # that the active Windows console code page cannot encode.
    print(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KT.MovemAcc project-root write guard")
    parser.add_argument("--authorization-json", required=True, help="Complete authorization context as JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--operation", required=True)
    check.add_argument("--target", required=True)
    check.add_argument("--resolved-target", required=True)
    check.add_argument("--source")
    check.add_argument("--resolved-source")
    check.add_argument("--indirect-output", action="append", default=[])

    write = sub.add_parser("write-text")
    write.add_argument("--target", required=True)
    write.add_argument("--resolved-target", required=True)
    write.add_argument("--text", required=True)

    delete = sub.add_parser("delete")
    delete.add_argument("--target", required=True)
    delete.add_argument("--resolved-target", required=True)

    for name in ("copy", "move"):
        command = sub.add_parser(name)
        command.add_argument("--source", required=True)
        command.add_argument("--resolved-source", required=True)
        command.add_argument("--target", required=True)
        command.add_argument("--resolved-target", required=True)

    validate = sub.add_parser("validate-command")
    validate.add_argument("--cwd", required=True)
    validate.add_argument("--command-json", required=True)
    validate.add_argument("--declared-output", action="append", default=[])
    validate.add_argument("--observed-output", action="append", default=[])

    delegate = sub.add_parser("delegate-check")
    delegate.add_argument("--operations-json", required=True)
    delegate.add_argument("--allowlist-json", required=True)

    delta = sub.add_parser("verify-delta")
    delta.add_argument("--before-json", required=True)
    delta.add_argument("--after-json", required=True)
    delta.add_argument("--allowed-json", required=True)

    incident = sub.add_parser("incident")
    incident.add_argument("--target", required=True)
    incident.add_argument("--reason", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        context = _context(args.authorization_json)
        guard = BoundaryGuard(context)
        filesystem = GuardedFilesystem(guard)

        if args.command == "check":
            decision = guard.authorize(
                operation=args.operation,
                requested_target=args.target,
                resolved_physical_destination=args.resolved_target,
                source=args.source,
                resolved_source=args.resolved_source,
                indirect_outputs=args.indirect_output,
            )
            return _emit(decision.as_dict(), 0)
        if args.command == "write-text":
            receipt = filesystem.write_text(args.target, args.resolved_target, args.text)
            return _emit({"status": "VERIFIED", "code": "WRITE_VERIFIED", "receipt": receipt}, 0)
        if args.command == "delete":
            receipt = filesystem.delete_file(args.target, args.resolved_target)
            return _emit({"status": "VERIFIED", "code": "DELETE_VERIFIED", "receipt": receipt}, 0)
        if args.command == "copy":
            receipt = filesystem.copy_file(args.source, args.resolved_source, args.target, args.resolved_target)
            return _emit({"status": "VERIFIED", "code": "COPY_VERIFIED", "receipt": receipt}, 0)
        if args.command == "move":
            receipt = filesystem.move_file(args.source, args.resolved_source, args.target, args.resolved_target)
            return _emit({"status": "VERIFIED", "code": "MOVE_VERIFIED", "receipt": receipt}, 0)
        if args.command == "validate-command":
            decision = guard.validate_command(
                command=_json(args.command_json),
                cwd=args.cwd,
                declared_outputs=args.declared_output,
                observed_outputs=args.observed_output,
            )
            return _emit(decision.as_dict(), 0)
        if args.command == "delegate-check":
            narrowed = context.narrowed(
                operations=_json(args.operations_json),
                allowlist=_json(args.allowlist_json),
            )
            return _emit(
                {
                    "status": "AUTHORIZED",
                    "code": "DELEGATION_NARROWED",
                    "operations": sorted(narrowed.authorized_operations),
                    "allowlist": sorted(map(str, narrowed.exact_target_allowlist)),
                },
                0,
            )
        if args.command == "verify-delta":
            decision = reconcile_side_effects(
                _json(args.before_json),
                _json(args.after_json),
                _json(args.allowed_json),
            )
            return _emit(decision.as_dict(), 0)
        if args.command == "incident":
            decision = uncertain_incident(args.target, args.reason)
            return _emit(decision.as_dict(), 4)
        raise AssertionError(f"Unhandled command: {args.command}")
    except BoundaryViolation as exc:
        return _emit(exc.decision.as_dict(), 3)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _emit(
            {
                "status": "DENIED",
                "code": "GUARD_INPUT_OR_FILESYSTEM_ERROR",
                "message": str(exc),
                "command": getattr(args, "command", None),
            },
            3,
        )


if __name__ == "__main__":
    raise SystemExit(main())
