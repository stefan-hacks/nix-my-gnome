from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .emit import render_single, render_split
from .parser import parse_dconf_ini


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nmg",
        description=(
            "nix-my-gnome (nmg): convert a dconf dump into a home-manager "
            "compatible dconf.settings Nix module."
        ),
    )
    p.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        help="Read a saved dconf dump from FILE instead of stdin.",
    )
    p.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help=(
            "Where to write output. In single-file mode (default) this is a "
            "file path (or '-' / omitted for stdout). In split mode (-s) "
            "this is a directory (default: ./nmg-out)."
        ),
    )
    p.add_argument(
        "-s",
        "--split",
        action="store_true",
        help=(
            "Split output into logical per-app Nix files (shell-extensions, "
            "gtk, evolution, virt-manager, etc.) plus a default.nix that "
            "imports them all."
        ),
    )
    p.add_argument(
        "--no-header",
        action="store_true",
        help="Omit the generated-file comment header and `{ lib, ... }:` function head "
        "(single-file mode only; useful when splicing into an existing module).",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def _read_input(args: argparse.Namespace) -> str:
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return f.read()
    if sys.stdin.isatty():
        print(
            "nmg: no input file given and stdin is a terminal.\n"
            "Pipe a dconf dump in, e.g.:\n"
            "  dconf dump / | nmg -o home.nix\n"
            "or point at a saved dump with -i:\n"
            "  nmg -i dconf.ini -o home.nix",
            file=sys.stderr,
        )
        sys.exit(2)
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = _read_input(args)
    doc = parse_dconf_ini(text)

    if doc.errors:
        for err in doc.errors:
            print(f"nmg: warning: could not fully parse {err}", file=sys.stderr)

    if not doc.order:
        print("nmg: no dconf sections found in input.", file=sys.stderr)
        return 1

    if args.split:
        out_dir = args.output or "nmg-out"
        os.makedirs(out_dir, exist_ok=True)
        files = render_split(doc)
        for name, content in files.items():
            path = os.path.join(out_dir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        print(f"nmg: wrote {len(files)} files to {out_dir}/", file=sys.stderr)
        for name in sorted(files):
            print(f"  {out_dir}/{name}", file=sys.stderr)
        return 0

    content = render_single(doc, module_header=not args.no_header)
    if args.output and args.output != "-":
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"nmg: wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
