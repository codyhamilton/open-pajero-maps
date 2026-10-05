#!/usr/bin/env python3
"""Prove R cell-local zero contribution; run via run_heavy_python.py.

--keys 765 writes its geometry proof; --keys 2-02 re-decodes the 432
members and writes Phase 3 accounting only after both proof sets pass.
R is read by indexed byte ranges. No Phase 1/2 or production files are written.
"""
import argparse
import csv
import gc
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np

TRIAGE = Path(__file__).resolve().parent
ROOT = TRIAGE.parents[3]
spec = importlib.util.spec_from_file_location("repair", TRIAGE / "complete_repair_2-02.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
cl = repair._cl
decompose_eo_faces = repair.decompose_eo_faces
encoder_piece_densified = repair.encoder_piece_densified
CProbe = repair.CProbe
cell_b4 = repair.cell_b4
RAW = cl.RAW
SCRATCH = ROOT / "output/scratch-14/r_contribution"
PINS = {
    "output/scratch-3-11/G_new/ALLDATA.KWI":
        "013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04",
    "output/scratch-14/G_new/ALLDATA.KWI": repair.G_SHA,
}


def read_tsv(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(path, rows, fields):
    with path.open("w") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def protected_shas():
    got = {name: cl.digest(ROOT / name) for name in PINS}
    assert got == PINS, got
    return got


def polygons(reader, index, ix, iy, code):
    # Use the existing slot decoder for selection; augment matching polygons
    # with wire multiplier/flags and range hashes via the same indexed decode.
    decoded = cl.decode_slot_shapes(reader, index, 0, ix, iy, code)
    assert decoded["status"] == "resolved", (ix, iy, decoded["status"])
    if not decoded["polys"]:
        return [], []
    out, frames = [], []
    for lmr, blk, row in index.get(ix, iy).handles:
        lpath, le, lb, ptype, _, (fb, fc) = row
        bounds = cl.walk.with_range(fb, cl.walk.leaf_frame_range(0, ptype, lpath, fc))
        offset = reader.volume.getsector(le.dsa, reader.ss, reader.ls)
        length = le.size * reader.ls
        reader.fh.seek(offset)
        buf = reader.fh.read(length)
        assert len(buf) == length
        frames.append({"offset": offset, "length": length,
                       "sha256": repair.hashlib.sha256(buf).hexdigest()})
        loc = cl.MeshLocation(level=0, parcel_type=ptype, blockset_index=blk[1],
                              block_index=blk[2], parcel_index=lpath[-1], bounds=bounds,
                              sector_addr=le.dsa, size_logical_sectors=le.size)
        parcel = cl.decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map,
                                  n_ext_map=lmr.n_ext_map)
        for s in parcel.background.shapes if parcel.background else []:
            if s.shape_class == 2 and len(s.coords) >= 3 and s.type_code == code:
                out.append({"leaf_path": list(lpath), "coords": [list(c) for c in s.coords],
                            "mult": int(s.mult_const),
                            "flags": int(s.underground) | (int(s.pen_up) << 1)})
    assert [(p["leaf_path"], p["coords"]) for p in out] == [
        (p["leaf_path"], p["coords"]) for p in decoded["polys"]]
    return out, frames


def c_run(probe, lat, poly, mc, code, flags, b4):
    # bg_shape rejects a zero-vertex input. An empty clip supplies no shape;
    # the uncut face is also passed to C below to prove its target-cell output.
    if not poly:
        return {"bytes": 0, "records": 0, "skipped": "empty clip; no shape to encode"}
    a = np.asarray(poly, dtype=float).reshape(-1, 2)
    nb, nr = probe.run(lat.lat0 + a[:, 1] / RAW * lat.cell_lat,
                       lat.lon0 + a[:, 0] / RAW * lat.cell_lon, mc, code, flags, b4)
    assert nb >= 0 and nr >= 0, (nb, nr)
    return {"bytes": nb, "records": nr}


def proof(row, reader, index, lat, probe):
    level, ix, iy, code = [int(row[k]) for k in ("level", "ix", "iy", "code")]
    assert level == 0
    rect = [ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW]
    x0, y0, x1, y1 = rect
    b4 = cell_b4(lat, ix, iy)
    polys, frames = polygons(reader, index, ix, iy, code)
    results = []
    for ordinal, p in enumerate(polys):
        raw = [(float(lat.gx(c[1])), float(lat.gy(c[0]))) for c in p["coords"]]
        xs, ys = zip(*raw)
        bbox = [min(xs), min(ys), max(xs), max(ys)]
        outside = bbox[2] <= x0 or bbox[0] >= x1 or bbox[3] <= y0 or bbox[1] >= y1
        faces = decompose_eo_faces(raw)
        repaired = []
        for face in faces:
            clipped = cl.clip_rect(face, *rect)
            q, area2, emits = encoder_piece_densified(clipped, p["mult"])
            c_clipped = c_run(probe, lat, clipped, p["mult"], code, p["flags"], b4)
            c_face = c_run(probe, lat, face, p["mult"], code, p["flags"], b4)
            repaired.append({"face_global_raw": face, "clipped_global_raw": clipped,
                             "q": q, "area2": area2, "mirror_emits": bool(emits),
                             "c_clipped": c_clipped, "c_face_target_cell": c_face})
        # R pieces are already emitted output. Check their clipped, rounded
        # footprint directly, independently of EO repair / encoder simulation.
        emitted_clip = cl.clip_rect(raw, *rect)
        rounded = np.rint(np.asarray(emitted_clip, dtype=float).reshape(-1, 2)
                          - [x0, y0])
        area = int(np.sum(rounded[:, 0] * np.roll(rounded[:, 1], -1)
                          - np.roll(rounded[:, 0], -1) * rounded[:, 1]))
        present = len(rounded) >= 3 and area != 0
        c_original = c_run(probe, lat, raw, p["mult"], code, p["flags"], b4)
        c_records = sum(f["c_clipped"]["records"] for f in repaired)
        # Either encoder route finding a record defeats a zero proof.
        zero = (c_records == 0 and c_original["records"] == 0
                and all(f["c_face_target_cell"]["records"] == 0 for f in repaired)
                and not present and not any(f["mirror_emits"] for f in repaired))
        mechanism = ("outside the cell" if outside else
                     "clips to nothing" if not any(f["clipped_global_raw"] for f in repaired)
                     else "filters to nothing") if zero else "cell-local contribution found"
        results.append({"polygon_ordinal": ordinal, "leaf_path": p["leaf_path"],
                        "mult": p["mult"], "flags": p["flags"], "n_coords": len(raw),
                        "decoded_latlon": p["coords"], "decoded_global_raw": raw,
                        "bbox_global_raw": bbox,
                        "bbox_relative_to_cell": [bbox[0]-x0, bbox[1]-y0,
                                                  bbox[2]-x0, bbox[3]-y0],
                        "faces": repaired, "c_original_target_cell": c_original,
                        "mirror_emits": sum(f["mirror_emits"] for f in repaired),
                        "c_records": c_records, "emitted_output": {
                            "clipped_global_raw": emitted_clip,
                            "rounded_cell_raw": rounded.tolist(),
                            "vertices": len(rounded), "rounded_area2": area,
                            "present": bool(present)}, "zero_contribution": zero,
                        "mechanism": mechanism})
    if int(row["dump_row"]) == 765:
        witness = json.loads((ROOT / "output/scratch-14/witnesses/0765_R.json").read_text())
        assert len(results) == 1 and frames == [
            {k: f[k] for k in ("offset", "length", "sha256")} for f in witness["frames"]]
    return {"dump_row": int(row["dump_row"]), "key": [level, ix, iy, code],
            "cell_rect_global_raw_half_open": rect, "cell_b4_degrees": b4,
            "R_polygon_count": len(results), "R_frames": frames, "polygons": results,
            "mirror_emits": sum(p["mirror_emits"] for p in results),
            "c_records": sum(p["c_records"] for p in results),
            "emitted_output_present": any(p["emitted_output"]["present"] for p in results),
            "verdict": "proven" if all(p["zero_contribution"] for p in results) else "not proven",
            "mechanism": "; ".join(p["mechanism"] for p in results) or "no R polygon of the type",
            "cenc_sha256": probe.cenc_sha}


def records(proofs):
    return [{k: p[k] for k in ("dump_row", "R_polygon_count", "mirror_emits", "c_records",
                              "emitted_output_present", "verdict", "mechanism")}
            | {"key": json.dumps(p["key"]),
               "proof_path": f"output/scratch-14/r_contribution/{p['dump_row']}.json"}
            for p in sorted(proofs, key=lambda p: p["dump_row"])]


def phase3(rows, proofs, absent_ok):
    folded = absent_ok and proofs[765]["verdict"] == "proven"
    for r in rows:
        r["phase3_group"] = ("r-absent-complete-repair-zero" if folded else
                              "r-765-cell-local-contribution") if int(r["dump_row"]) == 765 else r["phase2_group"]
    ids = [int(r["dump_row"]) for r in rows]
    keys = [tuple(r[k] for k in cl.NATIVE) for r in rows]
    assert len(rows) == len(set(ids)) == len(set(keys)) == 776
    assert set(ids) == set(range(776)), "not exhaustive"
    assert next(r for r in rows if int(r["dump_row"]) == 335)["phase3_group"] == "open-question:Q-source-335"
    counts = dict(Counter(r["phase3_group"] for r in rows))
    expected = {"g-omits-cell-local-dvd-type": 342, "r-absent-complete-repair-zero": 433 if folded else 432,
                "open-question:Q-source-335": 1}
    if not folded:
        expected["r-765-cell-local-contribution"] = 1
    assert counts == expected, counts
    write_tsv(TRIAGE / "phase3_membership.tsv", rows, list(rows[0]))
    definition = ('Amended 2-02 definition: **"R polygons contributing 0 cell-local records"**.\n'
                  'dump_row 765 folds into 2-02; the Phase 2 ledger is unchanged.\n') if folded else (
                  '765 remains its own group: `r-765-cell-local-contribution`.\n'
                  'Its polygon/record/cell mechanism is recorded in the proof JSON.\n')
    accounting = "776 = 342 (2-01) + 433 (2-02 amended) + 1 (Q-source-335)" if folded else "776 = 342 + 432 + 1 + 1"
    p = proofs[765]
    (TRIAGE / "phase3_groups.md").write_text(
        '# Phase 3 membership — unit 3-02\n\n' + definition + '\n'
        'Binding authority: plan 14 DESIGN Phase 3 refine, Design ruling on 765 (now the record `docs/plans/14-completeness-root-cause.md`).\n\n'
        'Evidence: `output/scratch-14/r_contribution/765.json` and dump_row 765 in '
        '`r_contribution_3-02.tsv`; full decode, multiplier, bbox, EO faces, mirror, '
        'production C, and emitted-output footprint. Verdict: ' + p['verdict'] + '. '
        'Mechanism: ' + p['mechanism'] + '.\n\n'
        f'Re-check: {sum(proofs[i]["R_polygon_count"] == 0 and proofs[i]["verdict"] == "proven" for i in proofs if i != 765)}/432 '
        'from actual covering-slot decodes; zero polygons and zero contribution. '
        'Per-row evidence: `r_contribution_3-02.tsv` and its proof paths.\n\n'
        + accounting + '. Membership: 776 rows, unique native keys and dump_row IDs, '
        'exact ID coverage 0–775; exhaustive and disjoint assertions pass.\n\n'
        '335 stays `open-question:Q-source-335`; 3-01 disposition is outside this unit. '
        'This records membership only; checker changes belong to 3-03. '
        'Plan 04 Phase 3 remains open.\n\n'
        'Carried Design observation: R emits 288 in the 342 2-01 cells while the spool '
        'has no representable 288 source: a source-data parity difference outside this unit.\n')
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keys", required=True, choices=("765", "2-02"))
    args = ap.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    before = protected_shas()
    rows = read_tsv(TRIAGE / "phase2_membership.tsv")
    seeds = [r for r in rows if int(r["dump_row"]) == 765] if args.keys == "765" else read_tsv(
        TRIAGE / "2-02_r-absent-complete-repair-zero_members.tsv")
    assert len(seeds) == (1 if args.keys == "765" else 432)
    if args.keys == "2-02":
        ids = [int(r["dump_row"]) for r in seeds]
        assert len(set(ids)) == 432
        assert set(ids) == {int(r["dump_row"]) for r in rows
                            if r["phase2_group"] == "r-absent-complete-repair-zero"}
    reader = cl.RReader(str(cl.R_DISC))
    index, lat, probe = cl.LeafIndex(reader, 0), cl.Lattice(0), CProbe(SCRATCH / "cprobe")
    ctrl_poly = [(1307*RAW+x, 1756*RAW+y) for x, y in [(512,512),(3584,512),(3584,3584),(512,3584)]]
    ctrl = c_run(probe, lat, ctrl_poly, 1, 291, 0, cell_b4(lat, 1307, 1756))
    assert ctrl["records"] > 0 and encoder_piece_densified(ctrl_poly)[2], ctrl
    proofs, failures = {}, []
    for n, row in enumerate(seeds):
        p = proof(row, reader, index, lat, probe)
        proofs[p["dump_row"]] = p
        write_json(SCRATCH / f'{p["dump_row"]}.json', p)
        if args.keys == "2-02" and (p["R_polygon_count"] != 0 or p["verdict"] != "proven"):
            failures.append(p["dump_row"])
        if n % 32 == 0:
            gc.collect()
    if args.keys == "2-02":
        proofs[765] = json.loads((SCRATCH / "765.json").read_text())
    output = records(list(proofs.values()))
    write_tsv(TRIAGE / "r_contribution_3-02.tsv", output, list(output[0]))
    counts = phase3(rows, proofs, not failures) if args.keys == "2-02" else None
    after = protected_shas()
    assert before == after
    summary = {"keys": args.keys, "rows": len(seeds), "failures": failures,
               "verdict_765": proofs[765]["verdict"], "groups": counts,
               "positive_control": ctrl, "protected_sha_before": before,
               "protected_sha_after": after}
    write_json(SCRATCH / f"summary_{args.keys}.json", summary)
    print(json.dumps(summary, sort_keys=True))
    assert not failures, f"432 re-check failed: {failures}"


if __name__ == "__main__":
    main()
