"""Plan 62: R01 residual re-decide under the plan-46 producer, with single-fix ablation.

The plan-46 producer (bg_producer_scan) differs from plan 44's (p5_owner_exclusive/mass_decide.py)
by five fixes (docs/plans/46-bg-producer-scan-rebuild.md):
  RC2 per-piece byte match (find_producer piecewise=True; decide side compares each clip piece),
  RC3 far producers: Moore(R=8) U FarHomes (K1 tall bbox-meet),
  RC4 divided-leaf clip rect (leaf_clip_geometry; plan 44 skipped divided leaves),
  RC5 same-type candidate filter,
  RC6 raw-unit ring stats (mechanism bit only; cannot move a decision class).
A config switches each of RC2..RC5 on or off. FULL = plan 46; PLAN44 = all off with plan 44's own
neighbourhood (recover_r, 16 for widen-saturated rows). A transition old->new is attributed to every
fix whose single removal (FULL minus that fix) reverts the row to its old class; if none does, the
transition is "joint" (needs two or more fixes together).

Pure helpers live here (unit-tested in parser/tests/test_r01_redecide.py); the disc/spool driver is
docs/plans/04-c-core-orchestration/triage/historical_bg/p9_r01_residual/redecide.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

FIXES = ("RC2", "RC3", "RC4", "RC5")


@dataclass(frozen=True)
class Config:
    name: str
    piecewise: bool   # RC2
    far: bool         # RC3
    divided: bool     # RC4
    same_type: bool   # RC5
    p44_neigh: bool = False  # Moore radius = plan 44's (recover_r / 16) instead of 8


CONFIGS = {
    "FULL": Config("FULL", True, True, True, True),
    "-RC2": Config("-RC2", False, True, True, True),
    "-RC3": Config("-RC3", True, False, True, True),  # pure: Moore(8), no FarHomes
    "-RC4": Config("-RC4", True, True, False, True),
    "-RC5": Config("-RC5", True, True, True, False),
    "PLAN44": Config("PLAN44", False, False, False, False, p44_neigh=True),
}

# plan-44 decision -> comparable class
OLD_CLASS = {
    "build:eo_bg_stitch": "build",
    "disagree_no_oe": "no_oe",
    "disagree_source_removed": "source-removed",
    "producer_ambiguous": "ambiguous",
    "producer_home_outside_R_cap": "outside",
    "producer_home_outside_R_cap@16(p45)": "outside",
    "skip_divided_leaf": "skip",
}


def old_class(p44_decision: str) -> str:
    try:
        return OLD_CLASS[p44_decision]
    except KeyError:
        raise ValueError(f"unknown plan-44 decision {p44_decision!r}") from None


def p44_radius(p44_cls: str, recover_r: str | int | None) -> int:
    """Plan 44's Moore radius for a row: widen@16 for the outside set, else the recovering R (>=1)."""
    if p44_cls == "outside":
        return 16
    try:
        r = int(recover_r)
    except (TypeError, ValueError):
        return 8
    return r if r >= 1 else 8


def radius(cfg: Config, p44_cls: str, recover_r) -> int:
    return p44_radius(p44_cls, recover_r) if cfg.p44_neigh else 8


def filter_type(cands: Iterable, code: int, same_type: bool) -> list:
    """cands: (cid=(hx,hy,ri,tc), ring, ...) -> [(cid, ring)] (RC5 keeps tc == code)."""
    return [(c[0], c[1]) for c in cands if not same_type or int(c[0][3]) == int(code)]


def producer_class(status: str) -> str:
    return {"unique-byte": "unique", "unique-fragment": "unique",
            "producer-ambiguous": "ambiguous", "producer_none": "outside"}[status]


def decide_class(*, producer_status: str, leaf_on_new: bool, clip_size: Optional[int],
                 byte_hit: bool, vert_hit: bool) -> str:
    """Design-44 decide limb as a class (plan 44 / phase23 decide)."""
    pc = producer_class(producer_status)
    if pc != "unique":
        return pc
    if not leaf_on_new:
        return "removed"
    if clip_size is None or clip_size <= 0:
        return "source-removed"
    return "build" if (byte_hit or vert_hit) else "no_oe"


def byte_hit(clip_pieces: Sequence[bytes], clip_blob: bytes, new_wires: set, piecewise: bool) -> bool:
    if piecewise:
        return any(p in new_wires for p in clip_pieces)
    return clip_blob in new_wires


def attribute(old: str, full: str, ablated: dict) -> list[str]:
    """Fixes whose single removal reverts FULL's class to the old class.

    old: plan-44 class; full: FULL class; ablated: {"RC2": cls, ...} (missing fix = not run).
    Returns [] when old == full (no transition), ["joint"] when no single fix reverts.
    "skip" (plan 44 never decided divided leaves) is RC4 by construction.
    """
    if old == full:
        return []
    if old == "skip":
        return ["RC4"]
    hit = [f for f in FIXES if ablated.get(f) == old]
    return hit or ["joint"]


def rect_intersection(a: Sequence[float], b: Sequence[float]) -> Optional[tuple]:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def strictly_inside(p: Sequence[int], rect: Sequence[float]) -> bool:
    """Point inside rect and off its boundary (owner-exclusive vertices are never on a leaf edge)."""
    return rect[0] < p[0] < rect[2] and rect[1] < p[1] < rect[3]


def covering_leaves(old_rect: Sequence[float], new_leaves: dict) -> list:
    """new_leaves: {key: rect}; keys whose rect meets old_rect with positive area, sorted."""
    return sorted(k for k, r in new_leaves.items() if rect_intersection(old_rect, r) is not None)


SENTINEL = -2147483648


def src_known_answer(src: tuple, producer: Optional[tuple]) -> str:
    """G-c3: compare the K1 dump src (nearest same-type shape within 64 raw, brief 3-03) to the producer."""
    if src[0] == SENTINEL or src[1] == SENTINEL or src[2] < 0:
        return "src_sentinel"
    if producer is None:
        return "no_producer"
    return "match" if tuple(src[:3]) == tuple(producer[:3]) else "mismatch"
