import argparse
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
    else:
        parser.print_help()
        raise SystemExit(2)

if __name__ == "__main__":
    main()
