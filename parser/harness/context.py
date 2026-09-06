"""Shared state handed to every check: which files to compare, the config,
the lazily-loaded reference profile, and a memoised walk summary so several
checks don't each re-walk the whole disc."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk

_PACKAGE_DIR = Path(__file__).resolve().parent
_REFDATA_DIR = _PACKAGE_DIR.parent / "refdata"
PROFILE_DIR = _REFDATA_DIR / "profile"


@dataclass
class CheckResult:
    status: str  # "PASS" | "FAIL" | "NA"
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class Check:
    id: str
    layer: str
    description: str
    run: "callable"  # Context -> CheckResult


@dataclass
class WalkSummary:
    """Lightweight, non-retaining aggregate of one full `iter_parcels()`
    pass: per-level leaf counts (all decoded parcel types), the count of
    whole-block parse failures, and the first 20 errors (block- or
    leaf-level) with enough identifying detail to report."""
    per_level_leaf_counts: dict
    per_level_type_counts: dict  # level -> {parcel_type: count}
    block_error_count: int
    leaf_error_count: int
    errors: list


def _compute_walk_summary(path: str) -> WalkSummary:
    per_level_leaf_counts: dict = {}
    per_level_type_counts: dict = {}
    block_errors = 0
    leaf_errors = 0
    errors: list = []
    for wp in walk.iter_parcels(path):
        is_block_error = wp.leaf_path == ()
        if wp.error is not None:
            if is_block_error:
                block_errors += 1
            else:
                leaf_errors += 1
            if len(errors) < 20:
                errors.append({
                    "level": wp.level,
                    "blockset_index": wp.blockset_index,
                    "block_index": wp.block_index,
                    "leaf_path": list(wp.leaf_path),
                    "error": wp.error,
                })
            continue
        per_level_leaf_counts[wp.level] = per_level_leaf_counts.get(wp.level, 0) + 1
        type_counts = per_level_type_counts.setdefault(wp.level, {})
        type_counts[wp.parcel_type] = type_counts.get(wp.parcel_type, 0) + 1
    return WalkSummary(
        per_level_leaf_counts=per_level_leaf_counts,
        per_level_type_counts=per_level_type_counts,
        block_error_count=block_errors,
        leaf_error_count=leaf_errors,
        errors=errors,
    )


class Context:
    def __init__(self, reference: Optional[str], generated: str, config: dict):
        self.reference = reference
        self.generated = generated
        self.config = config
        self._profile_cache: dict = {}
        self._walk_summary_cache: dict = {}

    def profile(self, layer: str) -> Optional[dict]:
        """Lazily load `parser/refdata/profile/<layer>.json`; `None` if
        that layer's profile file doesn't exist (unit 03 populates these;
        until then every profile-consuming check treats absence as
        "no census available", not an error)."""
        if layer in self._profile_cache:
            return self._profile_cache[layer]
        p = PROFILE_DIR / f"{layer}.json"
        data = None
        if p.exists():
            with open(p, "r") as f:
                data = json.load(f)
        self._profile_cache[layer] = data
        return data

    def walk_summary(self, path: str) -> WalkSummary:
        """One full `iter_parcels()` pass over `path`, memoised so that
        e.g. the `decode` check and any later check needing the same
        per-level counts don't each re-walk the whole disc."""
        if path not in self._walk_summary_cache:
            self._walk_summary_cache[path] = _compute_walk_summary(path)
        return self._walk_summary_cache[path]

    def layer_present(self, layer: str) -> bool:
        return layer in self.config.get("layers_present", [])
