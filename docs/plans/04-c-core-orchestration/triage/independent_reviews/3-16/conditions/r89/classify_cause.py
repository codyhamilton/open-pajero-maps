#!/usr/bin/env python3
"""Plan 47 Phase 3: per-key cause for the 89 (R-G8-2-e / R-G8-3-b).

For each key:
  - legacy records from disc 013586b5 covering the target cell
  - source rings from the extract_timing spool that bbox-meet the cell
  - EO (even-odd) pip of legacy identity-bearing vertices against the union of
    source rings (xor of per-ring EO)

Labels (DESIGN):
  - chord-artefact: ≥1 legacy IB vertex outside source EO interior
  - valid-lost: all legacy IB vertices inside source EO, and stitch omits
    (baseline_target_records == 0 in the TSV)
  - residual: otherwise (no legacy verts / no sources / inconclusive)

R-DVD limb: recorded as unverifiable when the reference disc is not mounted.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[8]
sys.path[:0] = [
    str(ROOT / "parser"),
    str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
]

from leaf_io import (  # noqa: E402
    cell_b4,
    frames,
    latlon_to_raw,
    leaf_records,
    leaf_rect_raw,
    spool_candidates,
)
from kiwiw.spool import SpoolReader  # noqa: E402

TSV = ROOT / "docs/plans/04-c-core-orchestration/triage/completeness_3-16_outcomes.tsv"
LEGACY = ROOT / "output/scratch-36/E_pre314/ALLDATA.KWI"
SPOOL = ROOT / "output/extract_timing/spool"
OUT = Path(__file__).resolve().parent


def eo_pip(ring_xy: list[tuple[float, float]], px: float, py: float) -> bool:
    """Even-odd point-in-polygon; ring as [(x,y),...] possibly open or closed."""
    if len(ring_xy) < 3:
        return False
    xs = [p[0] for p in ring_xy]
    ys = [p[1] for p in ring_xy]
    if xs[0] != xs[-1] or ys[0] != ys[-1]:
        xs = xs + [xs[0]]
        ys = ys + [ys[0]]
    n = len(xs) - 1
    inside = False
    j = n - 1
    for i in range(n):
        yi, yj = ys[i], ys[j]
        xi, xj = xs[i], xs[j]
        if (yi > py) != (yj > py):
            xinters = (xj - xi) * (py - yi) / (yj - yi + 0.0) + xi
            if px < xinters:
                inside = not inside
        j = i
    return inside


def load_tsv():
    rows = []
    with TSV.open() as f:
        hdr = f.readline().rstrip("\n").split("\t")
        for line in f:
            d = dict(zip(hdr, line.rstrip("\n").split("\t")))
            rows.append({
                "ordinal": int(d["ordinal"]),
                "level": int(d["level"]),
                "ix": int(d["ix"]),
                "iy": int(d["iy"]),
                "code": int(d["code"]),
                "baseline_target_records": int(d["baseline_target_records"]),
                "legacy_spool_degree_records_max": int(d["legacy_spool_degree_records_max"]),
                "sources": d["sources"],
            })
    return rows


def main() -> int:
    rows = load_tsv()
    cells = {(r["level"], r["ix"], r["iy"]) for r in rows}
    print(f"keys={len(rows)} legacy={LEGACY}", flush=True)
    fr = frames(str(LEGACY), cells)
    spool = SpoolReader(str(SPOOL))
    results = []
    counts = {"chord-artefact": 0, "valid-lost": 0, "residual": 0}

    with open(LEGACY, "rb") as fh:
        for r in rows:
            level, ix, iy = r["level"], r["ix"], r["iy"]
            # undivided leaf path ()
            key = (level, ix, iy, ())
            if key not in fr:
                hits = [k for k in fr if k[0] == level and k[1] == ix and k[2] == iy]
                if len(hits) == 1:
                    key = hits[0]
                else:
                    rec = {**r, "label": "residual", "reason": "legacy_leaf_missing_or_ambiguous",
                           "n_legacy_verts": 0, "n_outside": 0, "n_sources": 0,
                           "r_dvd": "unverifiable:reference_disc_not_mounted"}
                    results.append(rec)
                    counts["residual"] += 1
                    continue
            legacy_verts = []
            for _s, code, _wire, verts in leaf_records(fh, fr[key]):
                if int(code) != int(r["code"]):
                    continue
                for x, y in verts:
                    legacy_verts.append((float(x), float(y), int(code)))

            b4, cr = cell_b4(level, ix, iy)
            rect = leaf_rect_raw(level, 0)
            # Prefer TSV-named sources (ix,iy,record_ordinal); fall back to
            # Moore-1 spool_candidates. Rings from spool_candidates are already
            # in this cell's raw frame coords (do NOT re-project).
            rings_xy = []
            src_note = []
            for part in (r.get("sources") or "").split(";"):
                part = part.strip()
                if not part:
                    continue
                bits = part.split(",")
                if len(bits) < 3:
                    continue
                sx, sy, sord = int(bits[0]), int(bits[1]), int(bits[2])
                content = None
                try:
                    from leaf_io import _spool_cell
                    content = _spool_cell(spool, level, sx, sy)
                except Exception:
                    content = None
                if not content:
                    continue
                bgs = content.get("backgrounds") or []
                if sord < 0 or sord >= len(bgs):
                    continue
                bg = bgs[sord]
                coords = getattr(bg, "coords", None) or []
                if len(coords) < 3:
                    continue
                ring = [latlon_to_raw(lat, lon, b4, cr) for lat, lon in coords]
                if ring and ring[0] != ring[-1]:
                    ring = ring + [ring[0]]
                rings_xy.append(ring)
                src_note.append((sx, sy, sord))
            if not rings_xy:
                # fallback Moore-1 (sources often live in a neighbour)
                cands = list(spool_candidates(spool, level, ix, iy, rect, b4, cr,
                                              neighbourhood=1))
                for cid, ring in cands:
                    rings_xy.append(ring)  # already raw
                    src_note.append(cid[:3] if isinstance(cid, tuple) else cid)

            n_out = 0
            n_in = 0
            for x, y, _c in legacy_verts:
                # EO union via xor of per-ring EO (same rule the clipper uses
                # for multi-ring coverage at a point)
                eo = False
                for ring in rings_xy:
                    if eo_pip(ring, x, y):
                        eo = not eo
                if eo:
                    n_in += 1
                else:
                    n_out += 1

            if not legacy_verts:
                label, reason = "residual", "no_legacy_bg_verts"
            elif not rings_xy:
                label, reason = "residual", "no_spool_sources"
            elif n_out > 0:
                label, reason = "chord-artefact", "legacy_ib_vertex_outside_source_eo"
            elif r["baseline_target_records"] == 0:
                label, reason = "valid-lost", "all_inside_eo_stitch_omits"
            else:
                label, reason = "residual", "inside_eo_but_stitch_has_records"

            counts[label] += 1
            results.append({
                "ordinal": r["ordinal"], "level": level, "ix": ix, "iy": iy,
                "code": r["code"], "label": label, "reason": reason,
                "n_legacy_verts": len(legacy_verts), "n_inside": n_in,
                "n_outside": n_out, "n_sources": len(rings_xy),
                "sources_used": [list(s) if isinstance(s, tuple) else s for s in src_note],
                "baseline_target_records": r["baseline_target_records"],
                "legacy_spool_degree_records_max": r["legacy_spool_degree_records_max"],
                "r_dvd": "unverifiable:reference_disc_not_mounted",
            })

    summary = {
        "n_keys": len(rows),
        "counts": counts,
        "baseline_match": "see baseline_match.json (89/89)",
        "r_dvd_limb": "unverifiable:reference_disc_not_mounted",
        "residuals_targeted": ["R-G8-2-e", "R-G8-3-b"],
        "legacy_disc": str(LEGACY),
        "spool": str(SPOOL),
    }
    (OUT / "cause_labels.json").write_text(
        json.dumps({"summary": summary, "rows": results}, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
