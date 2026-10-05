"""Canonical seven-state IDX partition table (SADSR/POISR suffixes 201–207).

Loaded from ``parser/refdata/state_partitions.json``. This is the offline
source of truth for fixture naming and parameterized search tests. It does
**not** implement OSM admin_level=4 containment (that is WP3 product work)
and does **not** prove WP3 generation completeness.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

_REFDATA = Path(__file__).resolve().parent.parent / "refdata" / "state_partitions.json"

# Schema row must stay aligned with docs/schema/index-idx.md.
EXPECTED_ROWS: Tuple[Tuple[int, str], ...] = (
    (201, "WA"),
    (202, "NT"),
    (203, "SA"),
    (204, "QLD"),
    (205, "NSW"),
    (206, "VIC"),
    (207, "TAS"),
)


@dataclass(frozen=True)
class StatePartition:
    suffix: int
    code: str
    name: str

    @property
    def sadsr_basename(self) -> str:
        return f"SADSR{self.suffix}.IDX"

    @property
    def poisr_basename(self) -> str:
        return f"POISR{self.suffix}.IDX"


@lru_cache(maxsize=1)
def load_partitions() -> Tuple[StatePartition, ...]:
    """Return the seven partitions in suffix order."""
    raw = json.loads(_REFDATA.read_text(encoding="utf-8"))
    rows = [
        StatePartition(
            suffix=int(p["suffix"]),
            code=str(p["code"]),
            name=str(p["name"]),
        )
        for p in raw["partitions"]
    ]
    return tuple(sorted(rows, key=lambda r: r.suffix))


def suffix_to_code() -> Dict[int, str]:
    return {p.suffix: p.code for p in load_partitions()}


def code_to_suffix() -> Dict[str, int]:
    return {p.code: p.suffix for p in load_partitions()}


def all_suffixes() -> List[int]:
    return [p.suffix for p in load_partitions()]


def resolve_suffix(state: str | int | None = None, *, default: int = 201) -> int:
    """Resolve a CLI state code (``WA``) or suffix (``201``) to an IDX suffix.

    Default 201 (WA) preserves demo back-compat; callers must document that
    default-WA is not Australia-wide search proof.
    """
    if state is None or state == "":
        return default
    if isinstance(state, int):
        suffix = state
    else:
        text = str(state).strip().upper()
        if text.isdigit():
            suffix = int(text)
        else:
            mapping = code_to_suffix()
            if text not in mapping:
                raise ValueError(
                    f"unknown state {state!r}; expected one of "
                    f"{sorted(mapping)} or suffix 201..207"
                )
            suffix = mapping[text]
    known = set(all_suffixes())
    if suffix not in known:
        raise ValueError(f"suffix {suffix} not in {sorted(known)}")
    return suffix
