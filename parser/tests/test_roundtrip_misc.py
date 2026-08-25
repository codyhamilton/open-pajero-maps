"""Phase 2 round-trip regression tests for the small metadata/coverage
files (see docs/phases/02-roundtrip.md).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as test_mesh.py.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import misc, misc_writer

ROOT = "/run/media/codyh/464210-8480"


def _roundtrip(relpath, parse_fn, write_fn):
    path = os.path.join(ROOT, relpath)
    if not os.path.exists(path):
        print(f"SKIP: {relpath} not present (disc not mounted)")
        return None
    raw = open(path, "rb").read()
    rebuilt = write_fn(parse_fn(raw))
    return raw, rebuilt


def test_pct2mng_byte_identical():
    result = _roundtrip("PCT2MNG.KWI", misc.parse_pct2mng, misc_writer.write_pct2mng)
    if result is None:
        return
    raw, rebuilt = result
    assert raw == rebuilt
    print("PASS: PCT2MNG.KWI round-trips byte-identical")


def test_coverage_bin_byte_identical():
    result = _roundtrip("COVERAGE.BIN", misc.parse_coverage_bin, misc_writer.write_coverage_bin)
    if result is None:
        return
    raw, rebuilt = result
    assert raw == rebuilt
    print("PASS: COVERAGE.BIN round-trips byte-identical")


def test_cluster_dat_byte_identical():
    result = _roundtrip("DN/CLUSTER.DAT", misc.parse_cluster_dat, misc_writer.write_cluster_dat)
    if result is None:
        return
    raw, rebuilt = result
    assert raw == rebuilt
    print("PASS: DN/CLUSTER.DAT round-trips byte-identical")


def test_country_kwi_byte_identical():
    result = _roundtrip("COUNTRY.KWI", misc.parse_country_kwi, misc_writer.write_country_kwi)
    if result is None:
        return
    raw, rebuilt = result
    assert raw == rebuilt
    print("PASS: COUNTRY.KWI round-trips byte-identical")


def test_version_txt_byte_identical():
    result = _roundtrip("VERSION.TXT", misc.parse_version_txt, misc_writer.write_version_txt)
    if result is None:
        return
    raw, rebuilt = result
    assert raw == rebuilt
    print("PASS: VERSION.TXT round-trips byte-identical")


def test_spec_kwi_known_lossy():
    """Documented negative result: parse_bnf_metadata discards whitespace
    formatting, so SPEC.KWI/METADATA.KWI do NOT round-trip byte-identical
    from that intermediate representation. This test asserts the *known*
    failure mode so a future fix to the parser (e.g. capturing raw
    statement text) is caught as a welcome change, not a silent regression.
    """
    result = _roundtrip("SPEC.KWI", misc.parse_bnf_metadata, misc_writer.write_bnf_metadata)
    if result is None:
        return
    raw, rebuilt = result
    assert raw != rebuilt, (
        "SPEC.KWI now round-trips byte-identical -- update this test and "
        "docs/phases/02-roundtrip.md, the known whitespace-loss gap seems fixed"
    )
    print("EXPECTED FAIL (documented): SPEC.KWI does not round-trip byte-identical")


if __name__ == "__main__":
    test_pct2mng_byte_identical()
    test_coverage_bin_byte_identical()
    test_cluster_dat_byte_identical()
    test_country_kwi_byte_identical()
    test_version_txt_byte_identical()
    test_spec_kwi_known_lossy()
