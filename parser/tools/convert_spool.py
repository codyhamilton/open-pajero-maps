#!/usr/bin/env python3
"""One-time converter: legacy pickle spool -> binary columnar spool (plan 02).

    .venv-rp/bin/python parser/tools/convert_spool.py \\
        --i-trust-this-pickle output/spool output/spool_bin

Reads `SpoolReader` (legacy, `kiwiw.spool_legacy`) and writes the new format with
`kiwiw.spool.SpoolWriter`, then checks that per-level `stats()` totals match.
`raw_bytes`/`raw_offset` (never read downstream) are dropped.

**Trusted input (plan 24):** `--i-trust-this-pickle` is required. Inputs must be
operator-trusted local spools, never untrusted uploads. Without the flag the
converter refuses and does not deserialize.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import spool as new
from kiwiw import spool_legacy as old


def convert(src: str, dst: str, verbose: bool = True, *, trust: bool = False) -> None:
    if not trust:
        raise SystemExit(
            "refusing to deserialize legacy pickle spool without trusted-input "
            "enablement; re-run with --i-trust-this-pickle (operator-trusted "
            "local spool only; never untrusted uploads)"
        )
    old.enable_legacy_pickle_trust(
        "convert_spool: operator-trusted local legacy spool conversion"
    )
    rd = old.SpoolReader(src)
    with new.SpoolWriter(dst, flush_threshold=200_000) as w:
        for level in rd.levels():
            n = 0
            for ix, iy, content in rd.iter_level(level):
                w.add(level, ix, iy, **content)
                n += 1
            if verbose:
                print(f"level {level}: {n} cells", flush=True)
    nr = new.SpoolReader(dst)
    for level in rd.levels():
        a, b = rd.stats(level), nr.stats(level)
        if a != b:
            raise SystemExit(f"level {level}: stats mismatch pickle={a} binary={b}")
    if verbose:
        print("stats equal for all levels")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description=(
            "Convert a legacy pickle spool to binary columnar (KWSPIDX1). "
            "Requires --i-trust-this-pickle: inputs must be operator-trusted "
            "local spools, never untrusted uploads."
        )
    )
    p.add_argument(
        "--i-trust-this-pickle",
        action="store_true",
        dest="trust",
        help="required: affirm the source spool is an operator-trusted local path",
    )
    p.add_argument("src", help="legacy pickle spool directory")
    p.add_argument("dst", help="destination binary spool directory")
    args = p.parse_args(argv)
    convert(args.src, args.dst, verbose=True, trust=args.trust)


if __name__ == "__main__":
    main()
