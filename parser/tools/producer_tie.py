"""Plan 63: pure helpers for the producer-tie census (T0 / T1 / T2) and duplicate-record pairing.

T1 proven-producer-tied: >=2 same-type hits, whole clip blobs byte-identical AND identical decide verdict
   for every hit (lowest (level,hx,hy,ri) is the identity column; all candidate IDs are recorded).
T2 open: >=2 hits and the blobs differ, or identical blobs but differing decide verdicts.
T0 reclassified: fewer than 2 same-type hits under the plan-46 scan.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence


def tie_class(hits: Sequence[dict]) -> tuple[str, str]:
    """hits: [{"cid": [h,x,y,ri...], "clip_blob_sha256": str, "decide": str}, ...] -> (class, reason)."""
    if len(hits) < 2:
        return "T0", f"{len(hits)} same-type hit(s) under the plan-46 scan"
    blobs = {h["clip_blob_sha256"] for h in hits}
    verdicts = {h["decide"] for h in hits}
    if len(blobs) > 1:
        return "T2", "clip blobs differ"
    if len(verdicts) > 1:
        return "T2", "identical clip blobs but decide verdicts differ: " + ",".join(sorted(verdicts))
    return "T1", "identical clip blobs and identical decide verdict " + next(iter(verdicts))


def lowest_key(hits: Sequence[dict]):
    return min((tuple(h["cid"][:3]) for h in hits), default=None)


def duplicate_pairs(records: Iterable[tuple[int, int, bytes]], shapes: Iterable[int]) -> list[list[int]]:
    """records: (shape, code, wire) of the whole leaf. For each ambiguous shape, the set of leaf shapes with the
    same (code, wire) bytes (the full-record duplicate class). Returns sorted unique classes of size >= 1."""
    by = defaultdict(list)
    for s, c, w in records:
        by[(c, w)].append(s)
    want = set(shapes)
    out = {tuple(sorted(v)) for v in by.values() if want & set(v)}
    return [list(t) for t in sorted(out)]
