import argparse
import json
from pathlib import Path
from kt_movemacc.engine import run_ph1
from kt_movemacc.root_boundary import BoundaryGuard, BoundaryViolation
from kt_movemacc.trusted_authorization import (
    AuthorizationVerificationError,
    create_lab_review_guard,
    verify_productive_grant_files,
)


def _standard_raw_paths(root: Path, period: str) -> tuple[Path, Path]:
    year, month = period.split(".")
    raw_input = root / "RAW.INPUT" / period
    suffix = f"{year} {month} V 1.xlsb"
    return (
        raw_input / f"Mayor Inmob. Eplaza {suffix}",
        raw_input / f"Mayor Grupo Impulsa {suffix}",
    )


def _load_mutation_guard(
    authorization_file: str | None,
    grant_file: str | None,
    trust_config: str,
    root: Path,
) -> BoundaryGuard:
    if authorization_file:
        raise SystemExit(
            "ROOT_BOUNDARY_DENIED: unsigned --authorization-file payloads cannot authorize financial mutations"
        )
    if not grant_file:
        raise SystemExit("ROOT_BOUNDARY_DENIED: --grant-file is required for mutating commands")
    try:
        verified = verify_productive_grant_files(
            grant_file=grant_file,
            trust_config_file=trust_config,
            expected_task="PRODUCTIVE_TASK_UNAVAILABLE",
            expected_runtime="windows" if __import__("os").name == "nt" else "wsl2",
        )
        guard = verified.boundary_guard()
        guard.assert_authorized_root(root)
        return guard
    except (
        AuthorizationVerificationError,
        BoundaryViolation,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise SystemExit(f"ROOT_BOUNDARY_DENIED: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description="KT.MovemAcc CLI")
    subparsers = parser.add_subparsers(dest="command")

    ph1_parser = subparsers.add_parser("ph1", help="PH1 Accounting Consolidation")
    ph1_parser.add_argument("--period", required=True, help="Period (e.g., 2026.08)")
    ph1_parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph1_parser.add_argument("--raw-eplaza", help="Explicit EPLAZA XLSB path.")
    ph1_parser.add_argument("--raw-impulsa", help="Explicit IMPULSA XLSB path.")
    ph1_parser.add_argument("--out-dir", help="Explicit output directory.")
    ph1_parser.add_argument("--authorization-file", help="Deprecated unsigned payload; always denied for financial mutation.")
    ph1_parser.add_argument("--grant-file", help="Productive signed grant envelope. Verification currently fails closed.")
    ph1_parser.add_argument("--trust-config", default="04_CONFIG/SECURITY/KTMA_AUTHORIZATION_TRUST.json")
    ph1_parser.add_argument(
        "--lab-review",
        action="store_true",
        help="LAB_ONLY review under 90_RUNTIME/PH1_REVIEW/<period>/RUN_NNN; never productive publication.",
    )

    ph15_parser = subparsers.add_parser("ph15-db", help="PH1.5 SQLite financial database foundation")
    ph15_parser.add_argument("--period", required=True, help="Period (e.g., 2026.08)")
    ph15_parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph15_parser.add_argument("--db-path", default=None, help="SQLite database path. Defaults to DATA/KTMA.sqlite under root.")
    ph15_parser.add_argument("--raw-eplaza", help="Explicit EPLAZA XLSB path.")
    ph15_parser.add_argument("--raw-impulsa", help="Explicit IMPULSA XLSB path.")
    ph15_parser.add_argument("--allow-hash-change", action="store_true", help="Reserved for future versioning policy; current PH1.5 source policy is REJECT.")
    ph15_parser.add_argument("--print-lineage", action="store_true", help="Print Hernando de Aguirre lineage JSON after import.")
    ph15_parser.add_argument("--authorization-file", help="Deprecated unsigned payload; always denied for financial mutation.")
    ph15_parser.add_argument("--grant-file", help="Productive signed grant envelope. Verification currently fails closed.")
    ph15_parser.add_argument("--trust-config", default="04_CONFIG/SECURITY/KTMA_AUTHORIZATION_TRUST.json")

    ph15_query = subparsers.add_parser("ph15-query", help="Read-only PH1.5 database query contract")
    ph15_query.add_argument("query", choices=["periods", "entities", "source-files", "runs", "account", "consolidated", "rule-versions", "discrepancies", "hernando"])
    ph15_query.add_argument("--period", default="2026.08", help="Period scope for period-bound queries.")
    ph15_query.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph15_query.add_argument("--db-path", default=None, help="SQLite database path. Defaults to DATA/KTMA.sqlite under root.")
    ph15_query.add_argument("--account-code", help="Account code for account/consolidated lookups.")
    ph15_query.add_argument("--semantic-key", help="Semantic key for consolidated lookups.")

    fm_parser = subparsers.add_parser("funding-memo", help="Build the controlled accounting-to-Funding-Memo product")
    fm_parser.add_argument("--period", required=True)
    fm_parser.add_argument("--root", default=".")
    fm_parser.add_argument("--template", required=True, help="Funding Memo template; never overwritten")
    fm_parser.add_argument("--consolidated", required=True, help="Real CAM workbook providing TOTAL.VALORES_UF")
    fm_parser.add_argument("--raw-eplaza")
    fm_parser.add_argument("--raw-impulsa")
    fm_parser.add_argument("--out-dir", required=True, help="New non-colliding output directory under project root")

    fm_decision_parser = subparsers.add_parser(
        "funding-memo-decision", help="Append one validated Funding Memo mapping decision"
    )
    fm_decision_parser.add_argument("--root", default=".")
    fm_decision_parser.add_argument("--event", required=True, help="Complete decision event JSON")
    fm_decision_parser.add_argument(
        "--history", default="04_CONFIG/FUNDING_MEMO/KTMA_FM_DECISIONS.jsonl"
    )

    args = parser.parse_args()

    if args.command == "ph1":
        root = Path(args.root).resolve()
        eplaza, impulsa = _standard_raw_paths(root, args.period)
        if args.raw_eplaza:
            eplaza = Path(args.raw_eplaza).resolve()
        if args.raw_impulsa:
            impulsa = Path(args.raw_impulsa).resolve()
        out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "OUTPUT" / args.period

        if args.lab_review:
            if not eplaza.exists() or not impulsa.exists():
                raise SystemExit(f"Error: RAW inputs not found: {eplaza} | {impulsa}")
            if args.authorization_file or args.grant_file:
                raise SystemExit("ROOT_BOUNDARY_DENIED: --lab-review cannot be combined with authorization files")
            if not args.out_dir:
                raise SystemExit("ROOT_BOUNDARY_DENIED: --lab-review requires an explicit --out-dir")
            try:
                guard = create_lab_review_guard(root=root, out_dir=out_dir, period=args.period)
                out_dir.mkdir(parents=True, exist_ok=False)
            except (AuthorizationVerificationError, BoundaryViolation, OSError, ValueError) as exc:
                raise SystemExit(f"ROOT_BOUNDARY_DENIED: {exc}") from exc
        else:
            guard = _load_mutation_guard(args.authorization_file, args.grant_file, args.trust_config, root)
        if not eplaza.exists() or not impulsa.exists():
            raise SystemExit(f"Error: RAW inputs not found: {eplaza} | {impulsa}")

        run_ph1(eplaza, impulsa, out_dir, period=args.period, boundary_guard=guard)
    elif args.command == "ph15-db":
        from kt_movemacc.ph15_database import DEFAULT_DB_PATH, database_summary, import_period, lineage_for_hernando

        root = Path(args.root).resolve()
        db_path = Path(args.db_path).resolve() if args.db_path else root / DEFAULT_DB_PATH
        guard = _load_mutation_guard(args.authorization_file, args.grant_file, args.trust_config, root)
        result = import_period(
            db_path,
            root=root,
            period=args.period,
            raw_eplaza=Path(args.raw_eplaza).resolve() if args.raw_eplaza else None,
            raw_impulsa=Path(args.raw_impulsa).resolve() if args.raw_impulsa else None,
            allow_hash_change=args.allow_hash_change,
            boundary_guard=guard,
        )
        summary = database_summary(db_path)
        print("[PH1.5] SQLite import complete")
        print(f"      Database: {db_path}")
        print(f"      Run ID: {result.run_id}")
        print(f"      Status: {result.reconciliation_status}")
        print(f"      Source rows inserted this run: {result.source_rows}")
        print(f"      Observations persisted: {summary['observations']}")
        print(f"      Rule checks persisted: {result.rule_checks}")
        if args.print_lineage:
            print(json.dumps(lineage_for_hernando(db_path, args.period), indent=2, ensure_ascii=False))
    elif args.command == "ph15-query":
        from kt_movemacc.ph15_database import DEFAULT_DB_PATH, read_contract_query

        root = Path(args.root).resolve()
        db_path = Path(args.db_path).resolve() if args.db_path else root / DEFAULT_DB_PATH
        result = read_contract_query(
            db_path,
            args.query,
            period=args.period,
            account_code=args.account_code,
            semantic_key=args.semantic_key,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "funding-memo-decision":
        from kt_movemacc.funding_memo import append_decision_event

        root = Path(args.root).resolve()
        history_arg = Path(args.history)
        history = history_arg.resolve() if history_arg.is_absolute() else (root / history_arg).resolve()
        try:
            history.relative_to(root)
        except ValueError as exc:
            raise SystemExit("ROOT_BOUNDARY_DENIED: decision history must remain under project root") from exc
        event = json.loads(Path(args.event).resolve().read_text(encoding="utf-8-sig"))
        append_decision_event(history, event)
        print(json.dumps({"status": "APPENDED", "event_id": event["EVENT_ID"]}, ensure_ascii=False))
    elif args.command == "funding-memo":
        from kt_movemacc.funding_memo import build_funding_memo, load_decision_history, reconstruct_mapping_history

        root = Path(args.root).resolve()
        out_dir = Path(args.out_dir).resolve()
        try:
            out_dir.relative_to(root)
        except ValueError as exc:
            raise SystemExit("ROOT_BOUNDARY_DENIED: Funding Memo output must remain under project root") from exc
        if out_dir.exists():
            raise SystemExit(f"OUTPUT_COLLISION_DENIED: {out_dir}")
        template = Path(args.template).resolve()
        consolidated = Path(args.consolidated).resolve()
        eplaza, impulsa = _standard_raw_paths(root, args.period)
        if args.raw_eplaza:
            eplaza = Path(args.raw_eplaza).resolve()
        if args.raw_impulsa:
            impulsa = Path(args.raw_impulsa).resolve()
        for source in (template, consolidated, eplaza, impulsa):
            if not source.is_file():
                raise SystemExit(f"SOURCE_NOT_FOUND: {source}")
        decision_path = root / "04_CONFIG" / "FUNDING_MEMO" / "KTMA_FM_DECISIONS.jsonl"
        decisions = load_decision_history(decision_path)
        _, effective_rules = reconstruct_mapping_history(decisions, args.period)
        out_dir.mkdir(parents=True, exist_ok=False)
        payload = build_funding_memo(
            template=template,
            consolidated=consolidated,
            output=out_dir / f"FM{args.period}_ACCOUNTING_MAPPING_V1.xlsx",
            period=args.period,
            raw_eplaza=eplaza,
            raw_impulsa=impulsa,
            mapping_csv=out_dir / "KTMA_FM_MAPPING_MASTER_V1.csv",
            results_json=out_dir / "KTMA_FM_RESULTS_V1.json",
            unassigned_csv=out_dir / "KTMA_FM_UNASSIGNED_V1.csv",
            conceptual_md=out_dir / "KTMA_FM_MAPPING_CONCEPTUAL_V1.md",
            rules=effective_rules,
            decision_records=decisions,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
        raise SystemExit(2)

if __name__ == "__main__":
    main()
