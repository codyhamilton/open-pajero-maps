#!/usr/bin/env python3
"""Plan 64 Phase 1 trace driver (23 empty-clip groups; read-only on discs and spool).

  build    sidecar window builds (plan 63's committed sidecar_33006aa.patch, applied in a throwaway
           33006aa worktree): one single-cell window per group leaf cell, -j4, KW_SIDECAR_DIR set.
  analyze  per group:
     G1        every window frame of the cell byte-equal to a 013586b5 leaf of the cell (and every
               013586b5 leaf matched) -> sidecar output-neutral;
     emitter   the sidecar emitter of the group's 013586b5 shape (W/F+P entries, I/C lines; plan 63
               provenance.py parse) vs the recorded producer -> H1 test (part 1);
     probes    recorded producer ring clipped by the 33006aa clipper (does it reproduce the shape's
               bytes, and how many same-type candidates do: plan-46 unique-byte scan, Moore(8) U
               FarHomes) and by the d35b565 clipper (size; expect 0) -> H1 test (part 2);
     geometry  shape vertices vs the leaf clip rect (on-frame counts per edge), producer ring vs rect
               (vertices inside, exact polygon/rect clip area in raw units^2, signed ring area);
     footprint records of R, 013586b5, 4ed9cd80, 0c22b266 in the leaf's cell (parent-raw units via
               trim_witness.r_parent) whose geometry meets the shape's footprint (raster overlap);
     extract   producer ring -> OSM way, tags, mapped type, ring == way coords (reextract_cell.py
               output) -> H5 test.
Writes trace.json (sorted keys)."""
from __future__ import annotations

import argparse, csv, hashlib, json, os, subprocess, sys, tempfile, time, shutil, atexit
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
HB = HERE.parent
sys.path[:0] = [str(ROOT / p) for p in ("parser", "parser/tools",
                "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive",
                "docs/plans/04-c-core-orchestration/triage/historical_bg/p7_producer_tie",
                "docs/plans/04-c-core-orchestration/triage/trim_r_parity")]
import bg_producer_scan as S  # noqa: E402
import bg_owner_exclusive as O  # noqa: E402
import leaf_io as L  # noqa: E402
import provenance as PV  # noqa: E402
import trim_witness as TW  # noqa: E402
from leaf_io import cell_b4, frames  # noqa: E402
from kiwiw import volume  # noqa: E402

TRANSITIONS = HB / "p9_r01_residual/transitions.json"
R_G5_1_B = {"parent": "R-G5-1-b", "leaf": [0, 1750, 594, "598"], "shape": 171, "rows": 50,
            "old_class": "source-removed(plan46)", "producer": [1751, 594, 16, 288], "clip_size_d35b565": 0}


def groups():
    t = json.loads(TRANSITIONS.read_text())
    gs = [R_G5_1_B] + t["source_removed_groups"]
    out = []
    for g in gs:
        lv, ix, iy, p = g["leaf"]
        path = tuple(int(x) for x in str(p).split("."))
        par = g["parent"]
        row = {"R-G5-4-a": "R-G5-4-a-2", "R-G5-4-b": "R-G5-4-b-1"}.get(par, par)
        out.append({**g, "row": row, "path": list(path), "cell": [lv, ix, iy],
                    "gid": f"{lv}_{ix}_{iy}_{'.'.join(map(str, path))}_{g['shape']}"})
    return out


def cmd_build(a):
    a.out = a.out.resolve(); a.spool = a.spool.resolve()  # builds run with cwd=worktree
    a.out.mkdir(parents=True, exist_ok=True)
    cells = sorted({tuple(g["cell"]) for g in groups()})
    t0 = time.time()
    for lv, ix, iy in cells:
        d = a.out / f"w_{lv}_{ix}_{iy}"
        if (d / "DONE").exists():
            continue
        (d / "sc").mkdir(parents=True, exist_ok=True)
        for p in (d / "sc").iterdir():
            p.unlink()
        env = dict(os.environ, KW_SIDECAR_DIR=str(d / "sc"), PYTHONDONTWRITEBYTECODE="1")
        cmd = [a.python, "-B", "parser/build_alldata.py", "--spool", str(a.spool), "--out", str(d / "ALLDATA.KWI"),
               "-j", str(a.j), "--window", str(lv), str(ix), str(iy), str(ix + 1), str(iy + 1),
               "--frame-dump", str(d / "frames")]
        r = subprocess.run(cmd, cwd=a.worktree, env=env, capture_output=True, text=True)
        (d / "build.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            print(json.dumps({"window": d.name, "rc": r.returncode}), flush=True)
            sys.exit(2)
        (d / "ALLDATA.KWI").unlink(missing_ok=True)
        (d / "DONE").write_text("ok\n")
        print(json.dumps({"window": d.name, "t": round(time.time() - t0, 1)}), flush=True)
    print(json.dumps({"windows": len(cells), "wall_s": round(time.time() - t0, 1)}))


def pip(px, py, P):
    """even-odd point-in-polygon for sample arrays against closed polygon P (k,2)."""
    x = P[:, 0]; y = P[:, 1]; x2 = np.roll(x, -1); y2 = np.roll(y, -1)
    inside = np.zeros(px.shape, bool)
    for i in range(len(P)):
        c = ((y[i] > py) != (y2[i] > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = x[i] + (py - y[i]) * (x2[i] - x[i]) / (y2[i] - y[i])
        inside ^= c & (px < xi)
    return inside


def area(P):
    P = np.asarray(P, float)
    if len(P) < 3:
        return 0.0
    x, y = P[:, 0], P[:, 1]
    return float(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))


def rect_clip_area(P, r):
    """|area| of polygon P (closed or not) intersected with rect r, by exact Sutherland-Hodgman per edge
    (valid for any simple or even-odd polygon whose clipped parts do not overlap)."""
    pts = [tuple(p) for p in np.asarray(P, float)]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    for ax, v, keep in ((0, r[0], 1), (0, r[2], -1), (1, r[1], 1), (1, r[3], -1)):
        out = []
        for i in range(len(pts)):
            A, B = pts[i - 1], pts[i]
            ia, ib = (A[ax] - v) * keep >= 0, (B[ax] - v) * keep >= 0
            if ib:
                if not ia:
                    t = (v - A[ax]) / (B[ax] - A[ax]); out.append(tuple(A[k] + t * (B[k] - A[k]) for k in range(2)))
                out.append(B)
            elif ia:
                t = (v - A[ax]) / (B[ax] - A[ax]); out.append(tuple(A[k] + t * (B[k] - A[k]) for k in range(2)))
        pts = out
        if not pts:
            return 0.0, []
    return abs(area(pts)), pts


def self_intersections(P):
    P = np.asarray(P, float)
    if len(P) > 1 and (P[0] == P[-1]).all():
        P = P[:-1]
    n = len(P); cnt = 0
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue
            c, d = P[j], P[(j + 1) % n]
            def o(p, q, r):
                return np.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
            if o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0:
                cnt += 1
    return cnt


def on_frame(V, r, tol=0.0):
    V = np.asarray(V, float)
    e = {"W": np.abs(V[:, 0] - r[0]) <= tol, "E": np.abs(V[:, 0] - r[2]) <= tol,
         "S": np.abs(V[:, 1] - r[1]) <= tol, "N": np.abs(V[:, 1] - r[3]) <= tol}
    anyf = e["W"] | e["E"] | e["S"] | e["N"]
    return {**{k: int(v.sum()) for k, v in e.items()}, "on_frame": int(anyf.sum()), "off_frame": int((~anyf).sum()),
            "n": len(V)}


def bg_rule(tags, level=0):
    """first level-`level` rule of parser/refdata/vocab/bg_type.json matching tags (vocab.lookup order)."""
    from kiwiw import vocab
    v = json.loads((ROOT / "parser/refdata/vocab/bg_type.json").read_text())
    rng = next(r for r in v["levels"] if r[0] <= level <= r[1])
    for i, r in enumerate(v["rules"]):
        if r["levels"] == rng[0] and vocab._tags_match(r["match"], tags):
            return {"index": i, "match": r["match"], "value": r["value"], "catch_all": not r["match"]}
    return None


def disc_cell(disc, ix, iy, lat, cache):
    """parent-raw decoded records of a cell + wire bytes (leaf_all_records) per leaf."""
    k = (disc, ix, iy)
    if k in cache:
        return cache[k]
    from overlay_test import RReader
    from r_neighbours import LeafIndex
    rr = RReader(disc)
    st, div, leaves = TW.r_parent(rr, LeafIndex(rr, 0), 0, ix, iy, lat)
    out = []
    for lf in leaves:
        rr.fh.seek(lf["file_offset"]); buf = rr.fh.read(lf["length"]); buf = buf[:L.U16(buf, 0) * 2]
        recs = PV.leaf_all_records(buf)
        ok = len(recs) == len(lf["_bgs"])
        for i, (tc, sc, P) in enumerate(lf["_bgs"]):
            out.append({"leaf_path": lf["leaf_path"], "s": i, "type": int(tc), "class": int(sc),
                        "P": np.asarray(P, float), "wire": recs[i][3].hex() if ok else None,
                        "wire_ok": ok})
    cache[k] = (st, div, out)
    return cache[k]


def cmd_analyze(a):
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p64_trace_", dir=a.tmp)); atexit.register(shutil.rmtree, tmp, True)
    fnv = PV.load_fnv(tmp)
    cenc = {}
    for c in ("33006aa", "d35b565"):
        src = tmp / f"cenc_{c}" / "kiwiw"; src.mkdir(parents=True)
        names = subprocess.run(["git", "ls-tree", "--name-only", c, "parser/kiwiw/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
        for f in [Path(n).name for n in names if n.endswith(".h") or Path(n).name.startswith("_") and n.endswith(".c")]:
            (src / f).write_bytes(subprocess.run(["git", "show", f"{c}:parser/kiwiw/{f}"], cwd=ROOT,
                                                 capture_output=True, check=True).stdout)
        cenc[c] = O.load_probe(O.compile_probe(src / "_cenc.c", tmp / f"p_{c}.so"))
    from kiwiw.spool import SpoolReader
    from quantisation_roundtrip import Lattice
    spool = SpoolReader(str(a.spool)); far = S.FarHomes(a.spool, 0)
    lat = Lattice(0)
    rex = json.loads(a.reextract.read_text())
    discs = {"R": a.r_disc, "013586b5": a.old_disc.parent, "4ed9cd80": a.d35_disc.parent, "0c22b266": a.live_disc.parent}
    dcache = {}
    res = []
    gs = groups()
    by_cell = defaultdict(list)
    for g in gs:
        by_cell[tuple(g["cell"])].append(g)
    with open(a.old_disc, "rb") as fo:
        for cell, cgs in sorted(by_cell.items()):
            lv, ix, iy = cell
            d = a.win / f"w_{lv}_{ix}_{iy}"
            rows = list(csv.reader(open(d / "frames.tsv"), delimiter="\t"))
            fb = (d / "frames.bin").read_bytes()
            ptype = {}
            fr = frames(str(a.old_disc), {cell}, ptype_out=ptype)
            disc = {}
            for k, (dsa, size, ss, ls) in fr.items():
                b = os.pread(fo.fileno(), size * ls, volume.getsector(dsa, ss, ls))
                disc[k[3]] = b[:L.U16(b, 0) * 2]
            items, cells, W, P, F = PV.parse_sidecar(d)
            g1 = Counter(); emit_of = {}
            for r in rows:
                lk = (int(r[0]), int(r[1]), int(r[2]))
                if lk != cell:
                    continue
                pt, sxi, syi, o, n = int(r[3]), int(r[4]), int(r[5]), int(r[6]), int(r[7])
                buf = fb[o:o + n]
                match = [p for p, b in disc.items() if b == buf]
                if not match:
                    g1["frame_mismatch"] += 1; continue
                g1["frames_equal"] += 1
                path = match[0]
                if len(match) > 1:
                    nxp = 2 if pt == 1 else 4
                    cand = [p for p in match if len(p) >= 2 and p[-1] == syi * nxp + sxi]
                    path = cand[0] if len(cand) == 1 else min(match)
                h = fnv(buf)
                if pt == 0:
                    wl = W.get(lk); ents = wl[2] if wl and wl[1] == h else None
                else:
                    nxp = 2 if pt == 1 else 4; c = syi * nxp + sxi
                    pl = P.get((*lk, c, h), []); fl = F.get((*lk, c))
                    ents = pl[0] if pl and fl and fl[1] == h and all(e == pl[0] for e in pl) else None
                if ents is None:
                    g1["sidecar_fail"] += 1; continue
                recs = PV.leaf_all_records(buf)
                emit = [(i, c) for i, c, k in ents for _ in range(k)]
                if len(emit) != len(recs) or any(e[1] != rc[1] for e, rc in zip(emit, recs)):
                    g1["sidecar_count_fail"] += 1; continue
                g1["sidecar_frames"] += 1
                emit_of[path] = (recs, [PV.source_of(items, cells, lk, i) for i, _c in emit], [i for i, _ in emit])
            g1["disc_leaves"] = len(disc); g1["disc_leaf_unmatched"] = len(set(disc) - set(emit_of))
            for g in cgs:
                path = tuple(g["path"]); s = g["shape"]
                hx, hy, ri, tc = g["producer"]
                o = {"gid": g["gid"], "row": g["row"], "parent": g["parent"], "rows": g["rows"],
                     "old_class": g["old_class"], "leaf": [*cell, list(path)], "shape": s,
                     "producer": g["producer"], "gate1_cell": dict(sorted(g1.items()))}
                recs, src, merged = emit_of[path]
                code, wire = recs[s][2], recs[s][3]; cls = recs[s][1]
                so = src[s]
                o["shape_record"] = {"class": cls, "type": code, "wire_len": len(wire),
                                     "wire_sha256": hashlib.sha256(wire).hexdigest()}
                o["sidecar_emitter"] = {"kind": so[0], "hx": so[1], "hy": so[2], "ri": so[3], "merged": merged[s]}
                o["sidecar_equals_producer"] = so[0] in ("own", "routed", "cover") and (so[1], so[2], so[3]) == (hx, hy, ri)
                same_bytes = [j for j, rc in enumerate(recs) if rc[1] and rc[2] == code and rc[3] == wire]
                o["same_bytes_in_leaf"] = same_bytes
                # probes
                pt = ptype.get((*cell, path), 0)
                b4, cr, rect = S.leaf_clip_geometry(lv, ix, iy, path, pt, cell_b4)
                b4e = (0.0, cr, 0.0, cr)
                cands = S.fast_spool_candidates(spool, lv, ix, iy, rect, b4, cr, 8, None,
                                                extra_homes=far.query(ix, iy))
                ring = next((rg for cid, rg, _ll in cands if cid[:3] == (hx, hy, ri)), None)
                hits = []
                for cid, rg, _ll in cands:
                    if cid[3] != code:
                        continue
                    sz, _n, blob = O.clip_ring(cenc["33006aa"], rg, rect=rect, tc=cid[3], b4=b4e, cr=cr)
                    if sz > 0 and wire in O.wire_records(blob):
                        hits.append(list(cid[:3]))
                o["scan_unique_byte_hits_33006aa"] = hits
                o["producer_in_candidates"] = ring is not None
                if ring is not None:
                    pr = {}
                    for c in ("33006aa", "d35b565"):
                        sz, nrec, blob = O.clip_ring(cenc[c], ring, rect=rect, tc=code, b4=b4e, cr=cr)
                        ps = O.wire_records(blob) if sz > 0 else []
                        pr[c] = {"size": sz, "nrec": nrec, "shape_bytes_in_pieces": wire in ps,
                                 "pieces_sha256": [hashlib.sha256(p).hexdigest()[:16] for p in ps]}
                    o["probe"] = pr
                    R_ = np.asarray(ring, float)
                    inside = ((R_[:, 0] >= rect[0]) & (R_[:, 0] <= rect[2]) & (R_[:, 1] >= rect[1]) & (R_[:, 1] <= rect[3]))
                    ca, cpts = rect_clip_area(R_, rect)
                    o["producer_ring"] = {"n": len(R_), "verts_in_rect": int(inside.sum()),
                                          "bbox_leaf_raw": [*R_.min(0).round(3).tolist(), *R_.max(0).round(3).tolist()],
                                          "signed_area": round(area(R_), 3), "self_intersections": self_intersections(R_),
                                          "rect_clip_area_raw2": round(ca, 4),
                                          "rect_clip_bbox": ([*np.min(cpts, 0).round(3).tolist(), *np.max(cpts, 0).round(3).tolist()]
                                                             if cpts else None)}
                o["clip_rect"] = list(rect); o["clip_range"] = cr; o["parcel_type"] = pt
                # shape geometry in leaf raw (leaf_records frame) and footprint in parent raw
                verts = next(v for s_, c_, w_, v in L.leaf_records(fo, fr[(*cell, path)]) if s_ == s)
                o["shape_geometry"] = {**on_frame(verts, rect), "area_raw2": round(abs(area(verts)), 1),
                                       "rect_area_raw2": (rect[2] - rect[0]) * (rect[3] - rect[1]),
                                       "bbox": [*np.min(verts, 0).tolist(), *np.max(verts, 0).tolist()]}
                st, dv, recs_old = disc_cell(str(discs["013586b5"]), ix, iy, lat, dcache)
                fp = next(r for r in recs_old if tuple(r["leaf_path"]) == path and r["s"] == s)
                FP = fp["P"]; lo, hi = FP.min(0), FP.max(0)
                gx, gy = np.meshgrid(np.linspace(lo[0], hi[0], 97)[:-1] + (hi[0] - lo[0]) / 192,
                                     np.linspace(lo[1], hi[1], 97)[:-1] + (hi[1] - lo[1]) / 192)
                fin = pip(gx, gy, FP); nfs = int(fin.sum())
                fpo = {"bbox_parent_raw": [*lo.round(3).tolist(), *hi.round(3).tolist()], "samples_in_footprint": nfs, "discs": {}}
                for dn, dp in discs.items():
                    st, dv, rr = disc_cell(str(dp), ix, iy, lat, dcache)
                    meet = []
                    cov288 = np.zeros(fin.shape, bool); covany = np.zeros(fin.shape, bool)
                    for r in rr:
                        Q = r["P"]
                        if not len(Q) or (Q.max(0) < lo).any() or (Q.min(0) > hi).any():
                            continue
                        if r["class"] == 2 and len(Q) >= 3:
                            ins = pip(gx, gy, Q) & fin
                            k = int(ins.sum())
                            if k == 0:
                                continue
                            covany |= ins
                            if r["type"] == code:
                                cov288 |= ins
                            meet.append({"leaf_path": r["leaf_path"], "s": r["s"], "type": r["type"], "class": r["class"],
                                         "n": len(Q), "overlap_frac": round(k / max(nfs, 1), 4),
                                         "bbox": [*Q.min(0).round(1).tolist(), *Q.max(0).round(1).tolist()],
                                         "wire_sha256": hashlib.sha256(bytes.fromhex(r["wire"])).hexdigest() if r["wire"] else None,
                                         "same_as_shape": r["wire"] == wire.hex()})
                        else:
                            pin = pip(Q[:, 0], Q[:, 1], FP) if len(Q) else np.zeros(0, bool)
                            if pin.any():
                                meet.append({"leaf_path": r["leaf_path"], "s": r["s"], "type": r["type"], "class": r["class"],
                                             "n": len(Q), "verts_in_footprint": int(pin.sum())})
                    fpo["discs"][dn] = {"status": st, "divided": dv, "n_records_meeting": len(meet),
                                        "same_type_cover_frac": round(int(cov288.sum()) / max(nfs, 1), 4),
                                        "any_polygon_cover_frac": round(int(covany.sum()) / max(nfs, 1), 4),
                                        "records": meet}
                o["footprint"] = fpo
                h = rex["homes"].get(f"{hx},{hy}")
                if h is not None:
                    rg = h["rings"][ri] if ri < len(h["rings"]) else None
                    mm = [m for m in h["mismatch_rows"] if m["ri"] == ri]
                    o["extract"] = {"home_all_equal": h["all_equal"], "n_spool": h["n_spool"], "n_osm": h["n_osm"],
                                    "ring_equal": rg is not None and not mm, "osm_way": rg["way"] if rg else None,
                                    "tags": rg["tags"] if rg else None, "bg_type": rg["bg_type"] if rg else None,
                                    "n": rg["n"] if rg else None,
                                    "osm_way_closed": rg.get("way_closed") if rg else None,
                                    "n_nodes": rg.get("n_nodes") if rg else None,
                                    "closed_by_extractor": (rg is not None and rg.get("way_closed") is False),
                                    "bg_rule": bg_rule(rg["tags"]) if rg else None}
                res.append(o)
                print(json.dumps({"gid": g["gid"], "emitter_ok": o["sidecar_equals_producer"],
                                  "hits": len(hits), "t": round(time.time() - t0, 1)}), flush=True)
            L.clear_spool_caches()
    out = {"groups": res, "n_groups": len(res), "rows": sum(o["rows"] for o in res),
           "pbf_sha256": a.pbf_sha256, "reextract_stats": rex.get("stats"),
           "inputs": {"transitions_sha256": hashlib.sha256(TRANSITIONS.read_bytes()).hexdigest(),
                      "sidecar_patch": "p7_producer_tie/sidecar/sidecar_33006aa.patch",
                      "sidecar_patch_sha256": hashlib.sha256((HB / "p7_producer_tie/sidecar/sidecar_33006aa.patch").read_bytes()).hexdigest()}}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"groups": len(res), "wall_s": round(time.time() - t0, 1)}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--worktree", type=Path, required=True); b.add_argument("--spool", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True); b.add_argument("--python", default=sys.executable)
    b.add_argument("-j", type=int, default=4)
    z = sub.add_parser("analyze")
    for k in ("win", "old_disc", "d35_disc", "live_disc", "r_disc", "spool", "reextract", "out", "tmp"):
        z.add_argument("--" + k.replace("_", "-"), type=Path, required=True)
    z.add_argument("--pbf-sha256", required=True)
    a = ap.parse_args(argv)
    (cmd_build if a.cmd == "build" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
