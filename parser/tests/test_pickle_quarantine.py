"""Plan 24: offline pickle.load allowlist oracle + production import freeze.

Fails if any tracked parser/**/*.py outside the quarantine allowlist contains a
``pickle.load`` / ``pickle.loads`` call. Sketch CI (``.github/workflows/
security-sketch.yml``) runs only this module — not the full pytest suite (plan
06 is not a work unit).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import spool_legacy as legacy

# Quarantine allowlist: the only parser files permitted to call pickle.load/loads.
# Paths are repo-relative from repository root (open-pajero-maps/).
PICKLE_LOAD_ALLOWLIST = frozenset(
    {
        "parser/kiwiw/spool_legacy.py",
    }
)

# Production / extract / harness entry modules must stay import-free of spool_legacy.
PRODUCTION_FREEZE_MODULES = (
    "parser/build_alldata.py",
    "parser/osm_to_parcel_geometry.py",
    "parser/tools/quantisation_roundtrip.py",
    "parser/tools/golden_capture.py",
    "parser/tools/parcel_occupancy.py",
)


def _repo_root() -> Path:
    # parser/tests/this_file.py → repo root
    return Path(__file__).resolve().parents[2]


def _parser_py_files() -> list[Path]:
    root = _repo_root() / "parser"
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _rel(path: Path) -> str:
    return path.resolve().relative_to(_repo_root()).as_posix()


def _pickle_load_call_lines(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, kind) for pickle.load / pickle.loads Call nodes via AST."""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return [(-1, "syntax-error")]
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ("load", "loads"):
            val = func.value
            if isinstance(val, ast.Name) and val.id == "pickle":
                hits.append((getattr(node, "lineno", -1), f"pickle.{func.attr}"))
    return hits


def test_pickle_load_allowlist_oracle():
    offenders: list[str] = []
    for path in _parser_py_files():
        rel = _rel(path)
        hits = _pickle_load_call_lines(path)
        if not hits:
            continue
        if rel in PICKLE_LOAD_ALLOWLIST:
            continue
        for lineno, kind in hits:
            offenders.append(f"{rel}:{lineno}: {kind}")
    assert not offenders, (
        "pickle.load/loads outside quarantine allowlist "
        f"{sorted(PICKLE_LOAD_ALLOWLIST)}:\n  " + "\n  ".join(offenders)
    )


def test_allowlist_paths_exist_and_do_load():
    """Allowlist entries must exist and actually contain a gated load."""
    root = _repo_root()
    for rel in sorted(PICKLE_LOAD_ALLOWLIST):
        path = root / rel
        assert path.is_file(), f"allowlist path missing: {rel}"
        hits = _pickle_load_call_lines(path)
        assert hits, f"allowlist path has no pickle.load/loads: {rel}"


def test_production_modules_do_not_import_spool_legacy():
    root = _repo_root()
    bad: list[str] = []
    for rel in PRODUCTION_FREEZE_MODULES:
        path = root / rel
        assert path.is_file(), f"freeze module missing: {rel}"
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "kiwiw.spool_legacy" or mod.endswith(".spool_legacy"):
                    bad.append(f"{rel}: from {mod}")
                if mod == "kiwiw" and any(
                    alias.name == "spool_legacy" for alias in node.names
                ):
                    bad.append(f"{rel}: from kiwiw import spool_legacy")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "spool_legacy" in alias.name:
                        bad.append(f"{rel}: import {alias.name}")
        # Also catch string-free textual imports that AST might miss in unusual forms
        if "spool_legacy" in src and "kiwiw.spool_legacy" in src.replace(" ", ""):
            # Already covered by AST; keep soft
            pass
    assert not bad, "production freeze import of spool_legacy:\n  " + "\n  ".join(bad)


def test_legacy_load_refused_without_trust(tmp_path):
    import pickle

    legacy.reset_legacy_pickle_trust()
    assert not legacy.is_legacy_pickle_trusted()
    # Hand-write a minimal legacy idx; reading it must refuse without trust.
    idx = {
        "cells": [],
        "totals": {"parcels": 0, "roads": 0, "backgrounds": 0, "names": 0},
    }
    with open(tmp_path / "level_0.idx", "wb") as fh:
        pickle.dump(idx, fh, protocol=4)
    (tmp_path / "level_0.data").write_bytes(b"")
    rd = legacy.SpoolReader(tmp_path)
    with pytest.raises(legacy.LegacyPickleTrustError):
        rd.stats(0)


def test_enable_trust_requires_reason():
    legacy.reset_legacy_pickle_trust()
    with pytest.raises(ValueError):
        legacy.enable_legacy_pickle_trust("")
    with pytest.raises(ValueError):
        legacy.enable_legacy_pickle_trust("   ")
    legacy.enable_legacy_pickle_trust("unit-test reason")
    assert legacy.is_legacy_pickle_trusted()
    legacy.reset_legacy_pickle_trust()


def test_convert_spool_refuses_without_trust_flag(tmp_path):
    sys.path.insert(0, str(_repo_root() / "parser" / "tools"))
    import convert_spool

    with pytest.raises(SystemExit) as ei:
        convert_spool.convert(str(tmp_path / "a"), str(tmp_path / "b"), verbose=False)
    assert "i-trust-this-pickle" in str(ei.value).lower() or "trusted" in str(ei.value).lower()
