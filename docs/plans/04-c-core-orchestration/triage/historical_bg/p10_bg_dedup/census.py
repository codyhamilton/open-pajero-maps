#!/usr/bin/env python3
"""Plan 68 Phase 1: national duplicate census with per-copy emitters (live sidecar).

Inputs: a disc (byte-equal to the sidecar build that wrote --sc; the caller gates the sha) and the
plan-63 sidecar directory written by a full build at tip with sidecar_33006aa.patch applied
(the patch applies unchanged at tip c5d329c; output-neutral gate = full-disc sha equality).

A leaf "holds duplicates" when two or more class>0 background records have the same type code and
identical bytes (plan 63 definition, dup_census.py). Per duplicate class and per copy: record index s,
emitting enc_bg entry (merged background ordinal i, class c) and its source (own / routed / cover,
source cell, shape k) from the sidecar. Rule check (plan 63 accepted rule): copies in leaf order have
strictly increasing (class, own-first, source iy, ix, k) == strictly increasing merged ordinal.

Outputs <out>.tsv.gz (one row per class; copies as JSON) and <out>.json (summary, gates).
Streams block by block; sidecar lines kept only for cells holding duplicates."""
from __future__ import annotations

import argparse, atexit, gzip, hashlib, io, json, os, shutil, sys, tempfile, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p7_producer_tie")]
import leaf_io as L  # noqa: E402
from kiwiw import volume  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402
from provenance import leaf_all_records, load_fnv, source_of  # noqa: E402


def iter_leaves(path):
    """Yield (level, ix, iy, path_tuple, dsa, frame_bytes) for every distinct leaf frame."""
    oc = L.oc; seen = set()
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            nbx = 1 + lm.n_blocks_lng
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * (1 + lm.n_blocks_lat) + bi // nbx) * ny
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if entry.dsa in seen:
                        yield lm.level, bx + x, by + y, tuple(leaf), entry.dsa, None
                        continue
                    seen.add(entry.dsa)
                    b = os.pread(f.fileno(), entry.size * ls, volume.getsector(entry.dsa, ss, ls))
                    yield lm.level, bx + x, by + y, tuple(leaf), entry.dsa, b[:L.U16(b, 0) * 2]


def dup_classes(recs):
    by = defaultdict(list)
    for s, cls, code, w in recs:
        if cls:
            by[(code, w)].append(s)
    return {k: v for k, v in by.items() if len(v) >= 2}


def parse_sidecar_filtered(scdir, cells):
    items, own, W, P, F = {}, {}, {}, defaultdict(list), {}
    for fp in sorted(Path(scdir).iterdir()):
        with open(fp) as fh:
            for line in fh:
                t = line.rstrip("\n").split("\t")
                lk = (int(t[1]), int(t[2]), int(t[3]))
                if lk not in cells:
                    continue
                if t[0] == "I":
                    _lv, _ix, _iy, j, sx, sy, kc = map(int, t[1:8])
                    items[(*lk, j)] = (sx, sy, kc >> 1, kc & 1)
                elif t[0] == "C":
                    own[lk] = (int(t[4]), int(t[5]), int(t[6]))
                else:
                    cell, fl = int(t[4]), int(t[5]); h = t[6]
                    ents = [tuple(map(int, e.split(":"))) for e in t[7].split(",")] if len(t) > 7 and t[7] else []
                    if t[0] == "W":
                        W[lk] = (fl, h, ents)
                    elif t[0] == "P":
                        P[(*lk, cell, h)].append(ents)
                    else:
                        F[(*lk, cell)] = (fl, h)
    return items, own, W, P, F


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=Path, required=True)
    ap.add_argument("--sc", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="prefix")
    a = ap.parse_args(argv)
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p68_census_")); atexit.register(shutil.rmtree, tmp, True)
    fnv = load_fnv(tmp)
    # pass 1: duplicate leaves (frames kept only as fnv + dup positions + record classes)
    lv = defaultdict(Counter); dl = {}
    for level, ix, iy, path, dsa, buf in iter_leaves(a.disc):
        if buf is None:
            lv[level]["alias_slots"] += 1; continue
        lv[level]["leaves"] += 1
        recs = leaf_all_records(buf)
        d = dup_classes(recs)
        if d:
            lv[level]["leaves_with_dup"] += 1
            dl[(level, ix, iy, path)] = (fnv(buf), len(recs), [r[1] for r in recs],
                                        {k: v for k, v in d.items()})
    print(json.dumps({"pass1_dup_leaves": len(dl), "t": round(time.time() - t0, 1)}), flush=True)
    cells = {k[:3] for k in dl}
    items, own, W, P, F = parse_sidecar_filtered(a.sc, cells)
    print(json.dumps({"sidecar_cells": len(own), "t": round(time.time() - t0, 1)}), flush=True)
    g = Counter(); fails = []; rows = []; by_code = Counter(); rule_fail = []
    for key in sorted(dl):
        level, ix, iy, path = key; lk = key[:3]
        h, nrec, rcls, d = dl[key]
        ents = None
        wl = W.get(lk)
        if wl and wl[1] == h:
            ents = wl[2]; g["frame_W"] += 1
        elif len(path) >= 2:
            fl = F.get((*lk, path[-1]))
            pl = P.get((*lk, path[-1], h), [])
            if fl and fl[1] == h and pl and all(e == pl[0] for e in pl):
                ents = pl[0]; g["frame_F"] += 1
        if ents is None:
            g["sidecar_unmatched"] += 1; fails.append([*lk, list(path), "hash"]); continue
        emit = [(i, c) for i, c, k in ents for _ in range(k)]
        if len(emit) != nrec or any(e[1] != c for e, c in zip(emit, rcls)):
            g["sidecar_count_fail"] += 1; fails.append([*lk, list(path), f"count {len(emit)}/{nrec}"]); continue
        for (code, w), ss in sorted(d.items(), key=lambda kv: kv[1][0]):
            cp = []
            for s in ss:
                i, c = emit[s]
                so = source_of(items, own, lk, i)
                cp.append([s, c, i, so[0], so[1], so[2], so[3]])
            ords = [x[2] for x in cp]
            keys = [(x[1], 0 if (x[3] == "own") else 1, x[5], x[4], x[6]) for x in cp]
            ident = [tuple(x[3:]) if x[3] != "cover" else ("routed", *x[4:]) for x in cp]
            ok_ord = all(o1 < o2 for o1, o2 in zip(ords, ords[1:]))
            ok_key = all(k1 < k2 for k1, k2 in zip(keys, keys[1:]))
            shared = len(set(ident)) != len(ident)
            g["classes"] += 1; g["extra_copies"] += len(ss) - 1
            g["rule63_ok" if (ok_ord and ok_key) else "rule63_fail"] += 1
            g["shared_emitter"] += shared
            g["cover_form_copies"] += sum(x[3] == "cover" for x in cp)
            by_code[f"{level}/{code}"] += 1
            if not (ok_ord and ok_key) and len(rule_fail) < 50:
                rule_fail.append({"leaf": [*lk, list(path)], "code": code, "copies": cp})
            rows.append((level, ix, iy, ",".join(map(str, path)), code, len(ss),
                         hashlib.sha256(w).hexdigest(), json.dumps(cp, separators=(",", ":"))))
    rows.sort()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(b"level\tix\tiy\tpath\tcode\tcopies\trecord_sha256\temitters\n")
        for r in rows:
            gz.write(("\t".join(map(str, r)) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    hd = hashlib.sha256()
    with open(a.disc, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            hd.update(ch)
    summ = {"disc_sha256": hd.hexdigest(), "levels": {str(k): dict(sorted(v.items())) for k, v in sorted(lv.items())},
            "by_level_code": dict(sorted(by_code.items())), "gate": dict(sorted(g.items())),
            "sidecar_fail": fails[:200], "rule63_fail_examples": rule_fail,
            "emitter_columns": ["s", "class", "merged_ordinal", "kind", "src_ix", "src_iy", "k"],
            "rule63": "copies in leaf order strictly increasing in merged ordinal and in (class, own-first, src_iy, src_ix, k)"}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"gate": summ["gate"], "wall_s": round(time.time() - t0, 1)}))
    if fails:
        sys.exit(3)


if __name__ == "__main__":
    main()
