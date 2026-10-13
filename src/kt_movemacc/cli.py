import argparse
import json
from pathlib import Path
from kt_movemacc.engine import run_ph1


def _standard_raw_paths(root: Path, period: str) -> tuple[Path, Path]:
    year, month = period.split(".")
    raw_input = root / "RAW.INPUT" / period
    suffix = f"{year} {month} V 1.xlsb"
    return (
        raw_input / f"Mayor Inmob. Eplaza {suffix}",
        raw_input / f"Mayor Grupo Impulsa {suffix}",
    )


def main():
    parser = argparse.ArgumentParser(description="KT.MovemAcc CLI")
    subparsers = parser.add_subparsers(dest="command")

    ph1_parser = subparsers.add_parser("ph1", help="PH1 Accounting Consolidation")
    ph1_parser.add_argument("--period", required=True, help="Period (e.g., 2026.08)")
    ph1_parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph1_parser.add_argument("--raw-eplaza", help="Explicit EPLAZA XLSB path.")
    ph1_parser.add_argument("--raw-impulsa", help="Explicit IMPULSA XLSB path.")
    ph1_parser.add_argument("--out-dir", help="Explicit output directory.")

    ph15_parser = subparsers.add_parser("ph15-db", help="PH1.5 SQLite financial database foundation")
    ph15_parser.add_argument("--period", required=True, help="Period (e.g., 2026.08)")
    ph15_parser.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph15_parser.add_argument("--db-path", default=None, help="SQLite database path. Defaults to DATA/KTMA.sqlite under root.")
    ph15_parser.add_argument("--raw-eplaza", help="Explicit EPLAZA XLSB path.")
    ph15_parser.add_argument("--raw-impulsa", help="Explicit IMPULSA XLSB path.")
    ph15_parser.add_argument("--allow-hash-change", action="store_true", help="Reserved for future versioning policy; current PH1.5 source policy is REJECT.")
    ph15_parser.add_argument("--print-lineage", action="store_true", help="Print Hernando de Aguirre lineage JSON after import.")

    ph15_query = subparsers.add_parser("ph15-query", help="Read-only PH1.5 database query contract")
    ph15_query.add_argument("query", choices=["periods", "entities", "source-files", "runs", "account", "consolidated", "rule-versions", "discrepancies", "hernando"])
    ph15_query.add_argument("--period", default="2026.08", help="Period scope for period-bound queries.")
    ph15_query.add_argument("--root", default=".", help="Project root. Defaults to current directory.")
    ph15_query.add_argument("--db-path", default=None, help="SQLite database path. Defaults to DATA/KTMA.sqlite under root.")
    ph15_query.add_argument("--account-code", help="Account code for account/consolidated lookups.")
    ph15_query.add_argument("--semantic-key", help="Semantic key for consolidated lookups.")

    args = parser.parse_args()

    if args.command == "ph1":
        root = Path(args.root).resolve()
        eplaza, impulsa = _standard_raw_paths(root, args.period)
        if args.raw_eplaza:
            eplaza = Path(args.raw_eplaza).resolve()
        if args.raw_impulsa:
            impulsa = Path(args.raw_impulsa).resolve()
        out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "OUTPUT" / args.period

        if not eplaza.exists() or not impulsa.exists():
            raise SystemExit(f"Error: RAW inputs not found: {eplaza} | {impulsa}")

        run_ph1(eplaza, impulsa, out_dir, period=args.period)
    elif args.command == "ph15-db":
        from kt_movemacc.ph15_database import DEFAULT_DB_PATH, database_summary, import_period, lineage_for_hernando

        root = Path(args.root).resolve()
        db_path = Path(args.db_path).resolve() if args.db_path else root / DEFAULT_DB_PATH
        result = import_period(
            db_path,
            root=root,
            period=args.period,
            raw_eplaza=Path(args.raw_eplaza).resolve() if args.raw_eplaza else None,
            raw_impulsa=Path(args.raw_impulsa).resolve() if args.raw_impulsa else None,
            allow_hash_change=args.allow_hash_change,
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
    else:
        parser.print_help()
        raise SystemExit(2)

if __name__ == "__main__":
    main()
