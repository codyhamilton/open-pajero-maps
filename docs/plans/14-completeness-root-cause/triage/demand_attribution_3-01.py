#!/usr/bin/env python3
"""Attribute live K1 demands using the Python oracle and production C encoder.

Run through run_heavy_python.py. Cached tall sets are built by the oracle's
Python lattice/tall mask; source identities follow spool order, including the
original zero-based background ordinal. One row per shape uses the first
matching branch (a, b, c); JSON retains every matching branch.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
TRIAGE = Path(__file__).resolve().parent
SCRATCH = ROOT / "output/scratch-14/attribution"
DISC = ROOT / "output/scratch-14/G_new/ALLDATA.KWI"
SPOOL = ROOT / "output/extract_timing/spool"
SHA = "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72"
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"), str(TRIAGE)]
import quantisation_roundtrip as qr
from kiwiw import cenc
from kiwiw.spool import SpoolReader

spec = importlib.util.spec_from_file_location("repair_2_02", TRIAGE / "complete_repair_2-02.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
from whole_file_guard import refuse_whole_file_read

FIELDS = ["dump_row", "level", "ix", "iy", "type", "block", "shape_ref", "branch",
          "c_tol_only", "mirror_emits", "c_records", "representable",
          "all_demanders_unrepresentable"]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def tall_set(reader, level, lat):
    """Same chunk conversion and tall selection as _pass1, retaining identities."""
    idx = reader._load_idx(level)
    data = SPOOL / f"level_{level}.data"
    signature = {"data_size": data.stat().st_size, "data_mtime": data.stat().st_mtime_ns,
                 "idx_sha": repair.digest(SPOOL / f"level_{level}.idx"),
                 "oracle_sha": repair.digest(Path(qr.__file__))}
    cache = SCRATCH / f"tall_{level}.npz"
    meta = SCRATCH / f"tall_{level}.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()) == signature:
        with np.load(cache, allow_pickle=False) as z:
            sh = qr.Shapes(*(z[k] for k in ("x", "y", "off", "type", "cls")))
            refs = z["refs"].tolist()
        return sh, refs
    parts, refs = [], []
    for start in range(0, idx.n, 2048):
        end = min(start + 2048, idx.n)
        cols = list(qr._read_cells(reader, level, range(start, end)))
        sh = qr._cells_to_shapes(None, cols, lat)
        counts = np.array([len(c["b_type"]) for c in cols], np.int64)
        hx = np.repeat(idx.ix[start:end], counts)
        hy = np.repeat(idx.iy[start:end], counts)
        ordinal = np.arange(sh.n) - np.repeat(np.cumsum(counts) - counts, counts)
        sel = np.nonzero(qr._tall_mask(sh, hx, hy))[0]
        if len(sel):
            parts.append(sh.take(sel))
            refs.extend([[int(hx[i]), int(hy[i]), int(ordinal[i])] for i in sel])
        if start % 32768 == 0:
            print(f"tall L{level}: {end}/{idx.n} cells", flush=True)
    sh = qr.Shapes.concat(parts)
    np.savez(cache, x=sh.x, y=sh.y, off=sh.off, type=sh.type, cls=sh.cls,
             refs=np.asarray(refs, np.int64).reshape(-1, 3))
    write_json(meta, signature)
    return sh, refs


def region_refs(reader, level, lat, tall, refs, rect):
    """Recover Region.__init__'s ordered identity mapping; assert exact geometry."""
    c0, c1, r0, r1 = rect
    idx = reader._load_idx(level)
    a = int(np.searchsorted(idx.iy, r0 - 1, "left"))
    b = int(np.searchsorted(idx.iy, r1 + 2, "left"))
    pos = a + np.nonzero((idx.ix[a:b] >= c0 - 1) & (idx.ix[a:b] <= c1 + 1))[0]
    cols = list(qr._read_cells(reader, level, pos.tolist()))
    local = qr._cells_to_shapes(None, cols, lat)
    local_refs = [(int(idx.ix[p]), int(idx.iy[p]), j, None)
                  for p, col in zip(pos, cols) for j in range(len(col["b_type"]))]
    tx0, tx1, ty0, ty1 = tall.bbox()
    sel = np.nonzero((tx1 >= c0 * qr.RAW - qr.SEARCH - 1)
                     & (tx0 <= (c1 + 1) * qr.RAW + qr.SEARCH + 1)
                     & (ty1 >= r0 * qr.RAW - qr.SEARCH - 1)
                     & (ty0 <= (r1 + 1) * qr.RAW + qr.SEARCH + 1))[0]
    if len(sel):
        hx = np.array([v[0] for v in local_refs])
        hy = np.array([v[1] for v in local_refs])
        keep = np.nonzero(~qr._tall_mask(local, hx, hy))[0]
        local_refs = [local_refs[i] for i in keep]
        local = local.take(keep)
    expected = qr.Shapes.concat([local, tall.take(sel)])
    identities = local_refs + [(*refs[i], int(i)) for i in sel]
    return expected, identities


def inside_shape(sh, cy, cx, tc):
    region = qr.Region.__new__(qr.Region)
    region.shapes, region._polys = sh, None
    return bool(region.inside(np.array([0]), np.array([cy]), np.array([cx]),
                              np.array([tc]))[0])


def attribute(row, region, identities, lat, reader, probe, face_cache):
    ix, iy, tc, level = (int(row[k]) for k in ("ix", "iy", "code", "level"))
    sh = region.shapes
    x0, x1, y0, y1 = sh.bbox()
    cx, cy = (ix + .5) * qr.RAW, (iy + .5) * qr.RAW
    candidates = np.nonzero((sh.cls == 2) & (sh.lengths() >= 3) & (sh.type == tc))[0]
    demanders = []
    centre = bool(region.inside(np.array([0]), np.array([cy]), np.array([cx]),
                                np.array([tc]))[0])
    for s in candidates:
        xs, ys = sh.x[sh.off[s]:sh.off[s + 1]], sh.y[sh.off[s]:sh.off[s + 1]]
        home_x = np.floor((x0[s] + x1[s]) / 2 / qr.RAW)
        home_y = np.floor((y0[s] + y1[s]) / 2 / qr.RAW)
        one = (x0[s] >= home_x * qr.RAW and x1[s] <= (home_x + 1) * qr.RAW
               and y0[s] >= home_y * qr.RAW and y1[s] <= (home_y + 1) * qr.RAW)
        branches = []
        if one and (home_x, home_y) == (ix, iy):
            rx, ry = np.rint(xs), np.rint(ys)
            if np.add.reduceat(rx * np.roll(ry, -1) - np.roll(rx, -1) * ry, [0])[0] != 0:
                branches.append("a")
        elif not one:
            kx, ky = np.floor(xs / qr.RAW), np.floor(ys / qr.RAW)
            fx, fy = xs - kx * qr.RAW, ys - ky * qr.RAW
            if np.any((kx == ix) & (ky == iy) & (fx >= 1) & (fx <= qr.RAW - 1)
                      & (fy >= 1) & (fy <= qr.RAW - 1)):
                branches.append("b")
        c_hit = y0[s] <= cy < y1[s] and inside_shape(sh.take([s]), cy, cx, tc)
        if c_hit:
            branches.append("c")
        if not branches:
            continue
        hx, hy, ordinal, tid = identities[s]
        ref = f"L{level}:home({hx},{hy}):ordinal={ordinal}"
        if tid is not None:
            ref = f"tall={tid}:" + ref
        slat, slon, mc, src_tc, flags, cls = repair.source_attrs(
            reader, level, [level, hx, hy], ordinal)
        assert cls == 2 and src_tc == tc
        assert np.array_equal(lat.gx(slon), xs) and np.array_equal(lat.gy(slat), ys)
        poly = list(zip(xs.tolist(), ys.tolist()))
        cachekey = (level, hx, hy, ordinal)
        if cachekey not in face_cache:
            face_cache[cachekey] = repair.decompose_eo_faces(poly)
        faces = face_cache[cachekey]
        results = []
        for face in faces:
            clipped = repair.clip_rect(face, ix * qr.RAW, iy * qr.RAW,
                                       (ix + 1) * qr.RAW, (iy + 1) * qr.RAW)
            q, area2, emits = repair.encoder_piece_densified(clipped, mc)
            # Production bg_shape performs the clipping itself, on each EO face.
            fx, fy = np.asarray(face, np.float64).T
            flat = lat.lat0 + fy / qr.RAW * lat.cell_lat
            flon = lat.lon0 + fx / qr.RAW * lat.cell_lon
            rc, nr = probe.run(flat, flon, mc, tc, flags, repair.cell_b4(lat, ix, iy))
            assert rc >= 0, f"C bg_shape error {rc}"
            results.append({"clipped_raw": clipped, "q": q, "area2": area2,
                            "mirror_emits": bool(emits), "c_records": nr})
        records = sum(f["c_records"] for f in results)
        mirror = any(f["mirror_emits"] for f in results)
        rc, original = probe.run(slat, slon, mc, tc, flags, repair.cell_b4(lat, ix, iy))
        assert rc >= 0
        demanders.append({"shape_ref": ref, "region_shape": int(s), "branch": branches[0],
                          "branches": branches, "c_tol_only": bool(c_hit and not
                              repair._point_in_poly_eo(cx, cy, poly)),
                          "mirror_emits": mirror, "c_records": records,
                          "representable": records > 0, "mc": mc, "flags": flags,
                          "ncoord": len(xs), "bbox_raw": [x0[s], x1[s], y0[s], y1[s]],
                          "raw_coords": poly, "faces": results,
                          "c_original_records": original, "home_delta": [hx - ix, hy - iy],
                          "mirror_c_disagree": mirror != (records > 0)})
    assert centre == any("c" in d["branches"] for d in demanders), "Region c union differs"
    return demanders


def publish(universe):
    proofs = [json.loads(p.read_text()) for p in (SCRATCH / "proofs").glob("*.json")]
    proofs = sorted([p for p in proofs if p["disc_sha256"] == SHA], key=lambda p: p["dump_row"])
    rows, branches, all_branches = [], Counter(), Counter()
    exceptions, errors, disagreements, checker_disagreements, unrepresentable = [], [], [], [], 0
    for p in proofs:
        ds = p["demanders"]
        all_zero = bool(ds) and not p.get("error") and all(not d["representable"] for d in ds)
        unrepresentable += all_zero
        if p.get("error"):
            errors.append({"dump_row": p["dump_row"], "error": p["error"]})
        if p.get("checker_disagreement"):
            checker_disagreements.append(p["dump_row"])
        if any(d["representable"] for d in ds):
            exceptions.append(p["dump_row"])
        for d in ds or [{"shape_ref": "ERROR", "branch": "", "c_tol_only": "",
                        "mirror_emits": "", "c_records": "", "representable": ""}]:
            branches.update([d["branch"]] if d["branch"] else [])
            all_branches.update(d.get("branches", []))
            if d.get("mirror_c_disagree"):
                disagreements.append([p["dump_row"], d["shape_ref"]])
            rows.append({**{k: p[k] for k in FIELDS[:6]},
                         **{k: d[k] for k in FIELDS[6:12]},
                         "all_demanders_unrepresentable": int(all_zero)})
    with (TRIAGE / "demand_attribution_3-01.tsv").open("w") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {"keys": len(proofs), "universe": len(universe), "rows": len(rows),
               "branches": dict(branches), "all_matching_branches": dict(all_branches),
               "all_demanders_unrepresentable": unrepresentable, "exceptions": exceptions,
               "errors": errors, "mirror_c_disagreements": disagreements,
               "checker_disagreements": checker_disagreements}
    write_json(SCRATCH / "summary.json", summary)
    lines = ["# Demand attribution — 3-01", "", f"Disc SHA256: `{SHA}`.", "",
             f"Attributed {len(proofs)}/{len(universe)} keys; error rows: {len(errors)}.",
             "One TSV row per distinct shape. Branch is the first matching a/b/c branch;",
             "JSON records all matching branches. Shape ordinals and tall IDs are zero-based.",
             "", f"Per-branch distinct-demander counts: {dict(branches)}.",
             f"All matching branch counts (overlap allowed): {dict(all_branches)}.",
             f"Keys with all demanders unrepresentable (3-03 prediction): {unrepresentable}.",
             "", "## dump_row 335", ""]
    p335 = next((p for p in proofs if p["dump_row"] == 335), None)
    if p335:
        for d in p335["demanders"]:
            lines += [f"- `{d['shape_ref']}`: branch `{d['branch']}`, {d['ncoord']} coordinates,",
                      f"  bbox raw `{d['bbox_raw']}`, home delta `{d['home_delta']}`;",
                      f"  TOL-only centre hit: {d['c_tol_only']}; mirror emits: {d['mirror_emits']};",
                      f"  production C records: {d['c_records']}; representable: {d['representable']}."]
        if any(d["c_tol_only"] for d in p335["demanders"]):
            lines += ["", "The ±32 search missed this shape because it tested strict per-ring EO,",
                      "which excludes the centre. Region.inside accepts it with TOL=0.5 along",
                      "the horizontal scan line. Its home is only five rows away; the radius",
                      "was sufficient. Tall selection supplies the shape to the checking block."]
    lines += ["", "## Representable-demand exceptions", ""]
    lines += [f"- dump_row {n}: build-defect candidate; see `proofs/{n}.json`." for n in exceptions] or ["None."]
    lines += ["", "## Findings and errors", "", json.dumps(errors),
              f"Mirror/C disagreements: {disagreements}.",
              f"C/Python checker disagreements: {checker_disagreements}."]
    (TRIAGE / "demand_attribution_3-01.md").write_text("\n".join(lines) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", default="all", help="Comma-separated dump_row list, or all")
    parser.add_argument("--max-keys", type=int)
    args = parser.parse_args()
    started = time.perf_counter()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "proofs").mkdir(exist_ok=True)
    repair.assert_no_whole_file(SPOOL, DISC)
    assert repair.digest(DISC) == SHA, "wrong disc in force"
    with (TRIAGE / "completeness_evidence.tsv").open() as fh:
        universe = list(csv.DictReader(fh, delimiter="\t"))
    assert len(universe) == 776
    want = None if args.keys == "all" else {int(k) for k in args.keys.split(",")}
    selected = [r for r in universe if want is None or int(r["dump_row"]) in want]
    if want is not None:
        assert len(selected) == len(want), "unknown dump_row"
    if args.max_keys is not None:
        assert args.max_keys > 0
        selected = selected[:args.max_keys]
    container = qr.walk.read_container(str(DISC))
    keys = qr._block_keys(str(DISC))
    reader = SpoolReader(str(SPOOL))
    lats = {lv: qr.Lattice(lv) for lv in {k[0] for k in keys}}
    tasks = qr._block_tasks(reader, container, keys, lats, qr.PLAN_WORKERS)
    resolved = {}
    for row in selected:
        level, ix, iy = (int(row[k]) for k in ("level", "ix", "iy"))
        matches = []
        for key, lo, hi in tasks:
            if key[0] != level or not lo <= iy <= hi:
                continue
            c0, c1, r0, r1 = qr.key_cells(container, key, lats[level])
            if c0 <= ix <= c1:
                matches.append((key, lo, hi))
        assert len(matches) == 1, f"dump_row {row['dump_row']}: {len(matches)} checking blocks"
        resolved[int(row["dump_row"])] = matches[0]
    tall = {lv: tall_set(reader, lv, lats[lv]) for lv in {int(r["level"]) for r in selected}}
    probe = repair.CProbe(SCRATCH / "cprobe")
    disc_map = np.memmap(DISC, dtype=np.uint8, mode="r")
    cspools = {lv: cenc.E1Spool(str(SPOOL), lv) for lv in tall}
    blocks, face_cache, run_errors = {}, {}, []
    for row in selected:
        number, level, ix, iy, tc = (int(row[k]) for k in ("dump_row", "level", "ix", "iy", "code"))
        key, lo, hi = resolved[number]
        c0, c1, r0, r1 = qr.key_cells(container, key, lats[level])
        rect = c0, c1, max(r0, lo), min(r1, hi)
        proof = {"dump_row": number, "level": level, "ix": ix, "iy": iy, "type": tc,
                 "block": json.dumps(list(key[:7]), separators=(",", ":")), "rect": rect,
                 "band": [lo, hi], "disc_sha256": SHA, "demanders": []}
        try:
            if (key, lo, hi) not in blocks:
                lat = lats[level]
                sh, refs = tall[level]
                region = qr.Region(reader, level, lat, sh, sh.bbox(), *rect)
                expected, identities = region_refs(reader, level, lat, sh, refs, rect)
                for attr in ("x", "y", "off", "type", "cls"):
                    assert np.array_equal(getattr(region.shapes, attr), getattr(expected, attr))
                dec = qr.Decoded(qr._iter_leaves(str(DISC), container, key, lat, lo, hi), lat)
                assert not dec.errors, str(dec.errors)
                cells = set(zip(dec.leaf["ix"].tolist(), dec.leaf["iy"].tolist())) | region.spool_cells
                cells = {(x, y) for x, y in cells if rect[0] <= x <= rect[1] and rect[2] <= y <= rect[3]}
                required = qr._required_cells(region, cells, *rect)
                pc = np.nonzero((dec.bg_cls == 2) & (np.diff(dec.bg_off) >= 3))[0]
                leaves = dec.bg_leaf[pc]
                present = set(zip(dec.leaf["ix"][leaves].tolist(), dec.leaf["iy"][leaves].tolist(),
                                  dec.bg_type[pc].tolist()))
                python_missing = required - present
                dump, acc = cenc.K1Dump(), cenc.K1Acc()
                cenc.k1_check_band(disc_map, cenc.d1_block_rows([key], container), lo, hi,
                                   cspools[level], acc, dump=dump)
                ci = cenc._k1_cols["kinds"].index("completeness")
                c_missing = {(int(d["ix"]), int(d["iy"]), int(d["code"]))
                             for d in dump.rows if int(d["kind"]) == ci}
                difference = {"python_only": sorted(python_missing - c_missing),
                              "c_only": sorted(c_missing - python_missing)}
                blocks[key, lo, hi] = region, identities, required, len(cells), difference
            region, identities, required, ncells, difference = blocks[key, lo, hi]
            proof["checker_difference"] = difference
            proof["checker_disagreement"] = bool(difference["python_only"] or difference["c_only"])
            assert (ix, iy, tc) in required, "key absent from oracle _required_cells"
            proof.update(required_self_check=True, required_count=len(required), cells_count=ncells,
                         required_sha256=hashlib.sha256(json.dumps(sorted(required)).encode()).hexdigest())
            proof["demanders"] = attribute(row, region, identities, lats[level], reader, probe, face_cache)
            assert proof["demanders"], "zero demanders"
        except Exception as exc:
            proof["error"] = f"{type(exc).__name__}: {exc}"
            run_errors.append(number)
        write_json(SCRATCH / "proofs" / f"{number}.json", proof)
        print(f"dump_row {number}: demanders={len(proof['demanders'])} error={proof.get('error')}", flush=True)
    summary = publish(universe)
    wall = time.perf_counter() - started
    result = {"selected_keys": len(selected), "wall_s": wall,
              "projected_776_s": wall * 776 / len(selected), "run_errors": run_errors, **summary}
    write_json(SCRATCH / f"run_{args.keys.replace(',', '_')}_{args.max_keys or len(selected)}.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return int(bool(run_errors))


if __name__ == "__main__":
    raise SystemExit(main())
