"""Fail-closed productive authorization verification entrypoint.

TASK070 intentionally ships no productive signing key or trusted issuer.  This
tool therefore reports DENY_UNAVAILABLE until those external dependencies are
separately authorized and implemented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kt_movemacc.trusted_authorization import (  # noqa: E402
    AUDIENCE,
    AuthorizationVerificationError,
    verify_productive_grant_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a productive KT.MovemAcc authorization grant")
    parser.add_argument("--grant-file", required=True)
    parser.add_argument(
        "--trust-config",
        default=str(ROOT / "04_CONFIG/SECURITY/KTMA_AUTHORIZATION_TRUST.json"),
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--runtime", choices=("windows", "wsl2"), required=True)
    args = parser.parse_args()

    try:
        verified = verify_productive_grant_files(
            grant_file=args.grant_file,
            trust_config_file=args.trust_config,
            expected_task=args.task_id,
            expected_runtime=args.runtime,
        )
    except (AuthorizationVerificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = exc.as_dict() if isinstance(exc, AuthorizationVerificationError) else {
            "status": "DENIED",
            "code": "VERIFICATION_INPUT_INVALID",
            "message": str(exc),
        }
        payload.update({"audience": AUDIENCE, "productive_trust": "NOT_ENFORCED"})
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        return 3

    print(json.dumps(dict(verified.verification_receipt), sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
