"""Service Factory CLI.

    python -m factory.cli compile bundle.json --targets python-fastapi,docker,openapi --out ./dist
    python -m factory.cli list
    python -m factory.cli hash bundle.json

The CLI is the only stateful thing in the factory — it decides what to run
and where to write the output. Generators themselves remain pure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import get_registry, register_default_generators
from .ir import BundleLoader


def cmd_compile(args: argparse.Namespace) -> int:
    register_default_generators()
    reg = get_registry()

    contracts_dir = Path(args.contracts) if args.contracts else Path(args.bundle).parent
    loader = BundleLoader(contracts_dir)
    bundle = loader.load(Path(args.bundle))

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    if not targets:
        print("error: --targets cannot be empty", file=sys.stderr)
        return 2

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    total_files = 0
    for target in targets:
        try:
            gen = reg.get(target)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

        files = gen.generate(bundle)
        for rel_path, content in files.items():
            dest = out_root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
            total_files += 1
            if args.verbose:
                print(f"  [{target}] wrote {rel_path} ({len(content)} bytes)")

    print(
        f"compiled bundle {bundle.name!r} (hash={bundle.contract_hash()}) "
        f"to {out_root} — {total_files} files across {len(targets)} target(s)"
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    register_default_generators()
    reg = get_registry()
    for entry in sorted(reg.list(), key=lambda e: (e["category"], e["target"])):
        print(f"{entry['category']:8s}  {entry['target']}")
    return 0


def cmd_hash(args: argparse.Namespace) -> int:
    contracts_dir = Path(args.contracts) if args.contracts else Path(args.bundle).parent
    loader = BundleLoader(contracts_dir)
    bundle = loader.load(Path(args.bundle))
    print(bundle.contract_hash())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="factory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compile = sub.add_parser("compile", help="Compile a bundle into artifacts")
    p_compile.add_argument("bundle", help="Path to bundle.json")
    p_compile.add_argument(
        "--targets",
        default="python-fastapi,docker,openapi",
        help="Comma-separated list of generator targets",
    )
    p_compile.add_argument("--out", default="./dist", help="Output directory")
    p_compile.add_argument("--contracts", help="Directory where contract files live")
    p_compile.add_argument("-v", "--verbose", action="store_true")
    p_compile.set_defaults(func=cmd_compile)

    p_list = sub.add_parser("list", help="List available generators")
    p_list.set_defaults(func=cmd_list)

    p_hash = sub.add_parser("hash", help="Print the stable hash of a bundle")
    p_hash.add_argument("bundle")
    p_hash.add_argument("--contracts", help="Directory where contract files live")
    p_hash.set_defaults(func=cmd_hash)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
