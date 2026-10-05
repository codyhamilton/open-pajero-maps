"""Plan 23: copy-through graphics cmp contracts (synthetic disc trees)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from harness import registry
from harness.checks.copy_through import COPY_THROUGH_BASENAMES
from harness.context import CheckResult, Context
from compare_disc import _resolve_disc_paths


EXPECTED = (
    "LOADING.KWI",
    "DICVCE56.KWI",
    "GRA256D.KWI",
    "KGRA256.KWI",
    "PCT256D.KWI",
    "KPCT256.KWI",
    "PCT2DAT.KWI",
    "KPCT2DT.KWI",
    "KGRPDAT.KWI",
    "VAR256D.KWI",
)


def _stub_tree(root: Path, *, mutate: str | None = None,
               omit: str | None = None, content: bytes = b"stub-v1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "ALLDATA.KWI").write_bytes(b"ALLDATA-stub")
    for name in EXPECTED:
        if name == omit:
            continue
        payload = content
        if name == mutate:
            # Same length, one byte flipped — content mismatch, not size.
            buf = bytearray(content)
            buf[0] = (buf[0] ^ 0xFF) & 0xFF
            payload = bytes(buf)
        (root / name).write_bytes(payload)


def _ctx(r_root: Path, g_root: Path, layers: list[str]) -> Context:
    return Context(
        reference=str(r_root / "ALLDATA.KWI"),
        generated=str(g_root / "ALLDATA.KWI"),
        config={"layers_present": layers},
        reference_root=str(r_root),
        generated_root=str(g_root),
    )


def test_copy_through_basenames_match_target_disc():
    assert COPY_THROUGH_BASENAMES == EXPECTED
    assert len(COPY_THROUGH_BASENAMES) == 10


def test_copy_through_graphics_discovered_on_meta():
    by_id = {c.id: c for c in registry.discover()}
    assert "copy_through_graphics" in by_id
    assert by_id["copy_through_graphics"].layer == "meta"
    assert "wp5_meta" not in by_id  # subsumed


def test_na_under_map_only_layers():
    cfg = {"layers_present": ["map"]}
    ctx = Context(reference=None, generated="/dev/null", config=cfg)
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    assert check.layer == "meta"
    assert not ctx.layer_present(check.layer)


def test_pass_identical_stubs(tmp_path):
    r = tmp_path / "R"
    g = tmp_path / "G"
    _stub_tree(r)
    _stub_tree(g)
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    result = check.run(_ctx(r, g, ["map", "meta"]))
    assert isinstance(result, CheckResult)
    assert result.status == "PASS"
    assert result.details["checked"] == list(EXPECTED)


def test_fail_missing_generated_basename(tmp_path):
    r = tmp_path / "R"
    g = tmp_path / "G"
    _stub_tree(r)
    _stub_tree(g, omit="GRA256D.KWI")
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    result = check.run(_ctx(r, g, ["map", "meta"]))
    assert result.status == "FAIL"
    assert "GRA256D.KWI" in result.message
    kinds = {f["basename"]: f["kind"] for f in result.details["failures"]}
    assert kinds["GRA256D.KWI"] == "missing_generated"


def test_fail_content_mismatch(tmp_path):
    r = tmp_path / "R"
    g = tmp_path / "G"
    _stub_tree(r)
    _stub_tree(g, mutate="KGRA256.KWI")
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    result = check.run(_ctx(r, g, ["map", "meta"]))
    assert result.status == "FAIL"
    assert "KGRA256.KWI" in result.message
    fail = result.details["failures"][0]
    assert fail["basename"] == "KGRA256.KWI"
    assert fail["kind"] == "content_mismatch"
    assert "first_diff_offset" in fail


def test_fail_size_mismatch(tmp_path):
    r = tmp_path / "R"
    g = tmp_path / "G"
    _stub_tree(r, content=b"aaaa")
    _stub_tree(g, content=b"aa")  # shorter stubs for all — size mismatch
    # Make nine match by rewriting G to match R, leave one short
    for name in EXPECTED:
        if name == "VAR256D.KWI":
            (g / name).write_bytes(b"aa")
        else:
            (g / name).write_bytes(b"aaaa")
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    result = check.run(_ctx(r, g, ["map", "meta"]))
    assert result.status == "FAIL"
    assert "VAR256D.KWI" in result.message
    fail = next(f for f in result.details["failures"] if f["basename"] == "VAR256D.KWI")
    assert fail["kind"] == "size_mismatch"
    assert fail["reference_size"] == 4
    assert fail["generated_size"] == 2


def test_na_without_reference_root(tmp_path):
    g = tmp_path / "G"
    _stub_tree(g)
    check = next(c for c in registry.discover() if c.id == "copy_through_graphics")
    ctx = Context(
        reference=None,
        generated=str(g / "ALLDATA.KWI"),
        config={"layers_present": ["meta"]},
        reference_root=None,
        generated_root=str(g),
    )
    result = check.run(ctx)
    assert result.status == "NA"


def test_disc_root_resolution_preserves_siblings(tmp_path):
    disc = tmp_path / "disc"
    disc.mkdir()
    (disc / "ALLDATA.KWI").write_bytes(b"x")
    (disc / "GRA256D.KWI").write_bytes(b"y")

    alldata, root = _resolve_disc_paths(str(disc))
    assert Path(alldata) == disc / "ALLDATA.KWI"
    assert Path(root) == disc

    alldata2, root2 = _resolve_disc_paths(str(disc / "ALLDATA.KWI"))
    assert Path(alldata2) == disc / "ALLDATA.KWI"
    assert Path(root2) == disc

    lone = tmp_path / "other.bin"
    lone.write_bytes(b"z")
    alldata3, root3 = _resolve_disc_paths(str(lone))
    assert Path(alldata3) == lone
    assert root3 is None
