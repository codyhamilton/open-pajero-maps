#!/usr/bin/env python3
"""Plan 46 Phases 2-3: identity table of the classify remainder, then per-row cause.

identity: rows with assign==NO_RULE in <work>/cls2 (R01,S02,S03,S04 on the tracked-scan
          extended 013586b5 dump) joined to the shard scan TSVs by row_index.
decide:   per remainder shape, design-44 OE limb mirrored from p5_owner_exclusive/mass_decide.py:
          producer (scan, 33006aa encoder, Moore R=8 U bbox-meet) -> d35b565 clip into the leaf
          -> byte-equal to a 4ed9cd80 same-type record or an owner-exclusive vertex present in a
          4ed9cd80 same-type record => build:eo_bg_stitch. Clause "vertex not failing on
          4ed9cd80" is the committed K1 (3-14 conditions k1head_314/k1old_314: background and
          background_boundary failing 0 on 4ed9cd80), cited per row.
          Otherwise a named residual: producer_home_outside_R_cap | producer_ambiguous |
          removed | source-removed | no-owner-exclusive-vertex.
"""
from __future__ import annotations

import argparse, csv, gzip, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive")]
NO_RULE = 0xFFFF
HERE = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def det_gz_text(path):
    """gzip text writer with no filename and mtime=0 so equal content gives byte-identical files."""
    import io
    raw = open(path, "wb")
    gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
    t = io.TextIOWrapper(gz, encoding="utf-8", newline="")
    t._raw_keep = raw
    return t


def close_det(t):
    t.close(); t._raw_keep.close()


def relp(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def content_sha(path):
    h = hashlib.sha256()
    with gzip.open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def cmd_identity(a):
    out = a.out
    fields = None
    n = Counter()
    fo = det_gz_text(out)
    if True:
        w = None
        for kind, short in (("background", "bg"), ("background_boundary", "bb")):
            asg = np.fromfile(a.work / f"cls2/assign_{kind}.u16", "<u2")
            want = set(np.nonzero(asg == NO_RULE)[0].tolist())
            for part in sorted(a.gate.glob(f"{short}.s*/scan.tsv.gz")):
                with gzip.open(part, "rt") as fi:
                    r = csv.DictReader(fi, delimiter="\t")
                    if w is None:
                        fields = ["kind"] + r.fieldnames
                        w = csv.DictWriter(fo, fieldnames=fields, delimiter="\t", lineterminator="\n")
                        w.writeheader()
                    for d in r:
                        if int(d["row_index"]) in want:
                            d["kind"] = kind
                            w.writerow(d)
                            n[kind] += 1
            if n[kind] != len(want):
                raise SystemExit(f"{kind}: joined {n[kind]} != remainder {len(want)}")
    close_det(fo)
    summ = {"rows": dict(n), "total": sum(n.values()), "file": relp(out),
            "sha256": sha(out), "content_sha256": content_sha(out)}
    out.with_suffix(".json").write_text(json.dumps(summ, indent=2) + "\n")
    print(json.dumps(summ))
    return 0


def cmd_decide(a):
    from kiwiw.spool import SpoolReader
    from bg_owner_exclusive import compile_probe, load_probe, clip_ring, wire_vertices, \
        owner_exclusive_vertices, wire_records
    from leaf_io import cell_b4, frames, leaf_records
    import bg_producer_scan as ps
    rows = []
    with gzip.open(a.identity, "rt") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    by_leaf = defaultdict(list)
    for r in rows:
        d = int(r["depth"])
        lk = (int(r["level"]), int(r["ix"]), int(r["iy"]), tuple(int(r[f"p{j}"]) for j in range(d)))
        by_leaf[lk].append(r)
    cells = {lk[:3] for lk in by_leaf}
    old_pt: dict = {}
    old_fr = frames(str(a.old_disc), cells, ptype_out=old_pt)
    new_fr = frames(str(a.new_disc), cells)
    far: dict = {}
    probe_excl = load_probe(compile_probe(a.cenc_excl.resolve(), (Path(__import__("tempfile").mkdtemp(prefix="p46_decide_")) / "probe_excl_d35b565.so").resolve()))
    spool = SpoolReader(str(a.spool))
    cnt = Counter(); out_rows = []
    with open(a.old_disc, "rb") as fo, open(a.new_disc, "rb") as fn:
        for lk, rs in sorted(by_leaf.items()):
            level, ix, iy, path = lk
            # same E2 geometry as the scan (divided sub-rects; plan 46 root cause 3)
            b4, cr, rect = ps.leaf_clip_geometry(level, ix, iy, path, old_pt.get(lk, 0), cell_b4)
            b4e = (0.0, float(cr), 0.0, float(cr))
            by_shape = defaultdict(list)
            for r in rs:
                by_shape[(int(r["shape"]), int(r["code"]))].append(r)
            new_recs = list(leaf_records(fn, new_fr[lk])) if lk in new_fr else None
            new_wires = defaultdict(set); new_verts = defaultdict(set)
            for _s, code, wire, verts in (new_recs or []):
                new_wires[code].add(wire)
                new_verts[code].update((int(x), int(y)) for x, y in verts)
            cands = None
            for (shape, code), srs in by_shape.items():
                pc = srs[0]["producer_raw"]
                ex = {"depth": len(path), "producer_raw": pc}
                if pc not in ("unique-byte", "unique-fragment"):
                    dec = srs[0]["producer_class"]
                elif new_recs is None:
                    dec = "removed"
                else:
                    if cands is None:
                        if level not in far:
                            far[level] = ps.FarHomes(a.spool, level)
                        cands = ps.fast_spool_candidates(spool, level, ix, iy, rect, b4, cr, a.r, None,
                                                         extra_homes=far[level].query(ix, iy))
                    pid = (int(srs[0]["producer_hx"]), int(srs[0]["producer_hy"]), int(srs[0]["producer_ri"]))
                    ring = next((rg for cid, rg, _ll in cands if cid[:3] == pid), None)
                    ex["producer"] = list(pid)
                    if ring is None:
                        dec = "source-removed"; ex["why"] = "producer not in candidate set at decide"
                    else:
                        sz, _n, blob = clip_ring(probe_excl, ring, rect=rect, tc=code, b4=b4e, cr=float(cr))
                        if sz <= 0:
                            dec = "source-removed"; ex["sz"] = sz
                        else:
                            src_v = [(int(x), int(y)) for x, y in wire_vertices(blob)]
                            other = []
                            for cid, org, _ll in cands:
                                if cid[:3] == pid:
                                    continue
                                s2, _, b2 = clip_ring(probe_excl, org, rect=rect, tc=code, b4=b4e, cr=float(cr))
                                if s2 > 0:
                                    other.append([(int(x), int(y)) for x, y in wire_vertices(b2)])
                            fail = {(int(r["vx"]), int(r["vy"])) for r in srs}
                            excl = owner_exclusive_vertices(src_v, other, rect, failing=fail)
                            # per piece: a clip may emit several records (plan 46 root cause 2)
                            bh = any(pc_ in new_wires.get(code, ()) for pc_ in wire_records(blob))
                            vh = any(v in new_verts.get(code, ()) for v in excl)
                            ex.update({"byte": int(bh), "vert": int(vh), "n_excl": len(excl)})
                            dec = "build:eo_bg_stitch" if (bh or vh) else "no-owner-exclusive-vertex"
                for r in srs:
                    cnt[(r["kind"], dec)] += 1
                    out_rows.append({**{k: r[k] for k in ("kind", "row_index", "level", "ix", "iy", "depth",
                                    "p0", "p1", "p2", "shape", "vert", "code", "vx", "vy",
                                    "producer_class", "producer_raw", "producer_hx", "producer_hy",
                                    "producer_ri", "mechanism")},
                                     "verdict": dec,
                                     "not_failing_4ed9cd80": "k1head_314+k1old_314:bg_family_failing_0",
                                     "extra": json.dumps(ex, separators=(",", ":"))})
    f = det_gz_text(a.out)
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()), delimiter="\t", lineterminator="\n")
    w.writeheader(); w.writerows(out_rows)
    close_det(f)
    summ = {"rows": len(out_rows), "by_kind_verdict": {f"{k}|{v}": n for (k, v), n in sorted(cnt.items())},
            "old_disc_sha": sha(a.old_disc)[:16], "new_disc_sha": sha(a.new_disc)[:16],
            "cenc_excl_sha": sha(a.cenc_excl)[:16], "R": a.r,
            "file": relp(a.out), "sha256": sha(a.out),
            "content_sha256": content_sha(a.out)}
    a.out.with_suffix(".json").write_text(json.dumps(summ, indent=2) + "\n")
    print(json.dumps(summ, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("identity")
    i.add_argument("--work", type=Path, required=True)
    i.add_argument("--gate", type=Path, required=True)
    i.add_argument("--out", type=Path, default=HERE / "identity_remainder.tsv.gz")
    d = sub.add_parser("decide")
    d.add_argument("--identity", type=Path, default=HERE / "identity_remainder.tsv.gz")
    d.add_argument("--old-disc", type=Path, required=True)
    d.add_argument("--new-disc", type=Path, required=True)
    d.add_argument("--cenc-excl", type=Path, required=True)
    d.add_argument("--spool", type=Path, required=True)
    d.add_argument("--r", type=int, default=8)
    d.add_argument("--out", type=Path, default=HERE / "verdicts.tsv.gz")
    a = ap.parse_args()
    return {"identity": cmd_identity, "decide": cmd_decide}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
