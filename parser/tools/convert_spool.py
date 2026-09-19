#!/usr/bin/env python3
"""One-time converter: legacy pickle spool -> binary columnar spool (plan 02).

    .venv-rp/bin/python parser/tools/convert_spool.py output/spool output/spool_bin

Reads `SpoolReader` (legacy, `kiwiw.spool_legacy`) and writes the new format with
`kiwiw.spool.SpoolWriter`, then checks that per-level `stats()` totals match.
`raw_bytes`/`raw_offset` (never read downstream) are dropped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import spool as new
from kiwiw import spool_legacy as old


def convert(src: str, dst: str, verbose: bool = True) -> None:
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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
