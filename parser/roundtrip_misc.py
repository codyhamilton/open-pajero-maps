#!/usr/bin/env python3
"""Phase 2 round-trip harness for the small metadata/coverage files.

Reads each target file from the real disc (mounted, or pass --root to point
at an extracted copy / ISO mount point), parses it with `kiwiw.misc`,
re-serializes it with `kiwiw.misc_writer`, and byte-diffs the result against
the original. Prints PASS (exact match) or FAIL (with the first differing
offset, expected/actual bytes, and a byte-length comparison) per file.

Usage:
    python3 parser/roundtrip_misc.py [--root /run/media/codyh/464210-8480]

See docs/phases/02-roundtrip.md for the methodology and results this
produced.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from kiwiw import misc, misc_writer


def diff_report(name: str, original: bytes, rebuilt: bytes) -> bool:
    if original == rebuilt:
        print(f"PASS  {name}: byte-identical ({len(original)} bytes)")
        return True

    print(f"FAIL  {name}: original {len(original)} bytes, rebuilt {len(rebuilt)} bytes")
    n = min(len(original), len(rebuilt))
    first_diff = None
    for i in range(n):
        if original[i] != rebuilt[i]:
            first_diff = i
            break
    if first_diff is None:
        first_diff = n
        print(f"      bytes match up to the shorter length ({n}); "
              f"the {'original' if len(original) > n else 'rebuilt'} has extra trailing bytes")
    else:
        lo = max(0, first_diff - 4)
        hi = min(n, first_diff + 12)
        print(f"      first difference at offset {first_diff}")
        print(f"      expected: {original[lo:hi].hex(' ')}")
        print(f"      actual:   {rebuilt[lo:hi].hex(' ')}")
    return False


def check_pct2mng(root: str) -> bool:
    path = os.path.join(root, "PCT2MNG.KWI")
    raw = open(path, "rb").read()
    parsed = misc.parse_pct2mng(raw)
    rebuilt = misc_writer.write_pct2mng(parsed)
    return diff_report("PCT2MNG.KWI", raw, rebuilt)


def check_coverage_bin(root: str) -> bool:
    path = os.path.join(root, "COVERAGE.BIN")
    raw = open(path, "rb").read()
    parsed = misc.parse_coverage_bin(raw)
    rebuilt = misc_writer.write_coverage_bin(parsed)
    return diff_report("COVERAGE.BIN", raw, rebuilt)


def check_cluster_dat(root: str) -> bool:
    path = os.path.join(root, "DN", "CLUSTER.DAT")
    raw = open(path, "rb").read()
    parsed = misc.parse_cluster_dat(raw)
    rebuilt = misc_writer.write_cluster_dat(parsed)
    return diff_report("DN/CLUSTER.DAT", raw, rebuilt)


def check_country_kwi(root: str) -> bool:
    path = os.path.join(root, "COUNTRY.KWI")
    raw = open(path, "rb").read()
    parsed = misc.parse_country_kwi(raw)
    rebuilt = misc_writer.write_country_kwi(parsed)
    return diff_report("COUNTRY.KWI", raw, rebuilt)


def check_spec_kwi(root: str) -> bool:
    path = os.path.join(root, "SPEC.KWI")
    raw = open(path, "rb").read()
    parsed = misc.parse_bnf_metadata(raw)
    rebuilt = misc_writer.write_bnf_metadata(parsed)
    return diff_report("SPEC.KWI", raw, rebuilt)


def check_metadata_kwi(root: str) -> bool:
    path = os.path.join(root, "METADATA.KWI")
    raw = open(path, "rb").read()
    parsed = misc.parse_bnf_metadata(raw)
    rebuilt = misc_writer.write_bnf_metadata(parsed)
    return diff_report("METADATA.KWI", raw, rebuilt)


def check_version_txt(root: str) -> bool:
    path = os.path.join(root, "VERSION.TXT")
    raw = open(path, "rb").read()
    parsed = misc.parse_version_txt(raw)
    rebuilt = misc_writer.write_version_txt(parsed)
    return diff_report("VERSION.TXT", raw, rebuilt)


CHECKS = [
    check_pct2mng,
    check_coverage_bin,
    check_cluster_dat,
    check_country_kwi,
    check_spec_kwi,
    check_metadata_kwi,
    check_version_txt,
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/run/media/codyh/464210-8480",
                     help="path to the mounted/extracted disc root")
    args = ap.parse_args()

    results = [check(args.root) for check in CHECKS]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} files byte-identical")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
