#!/usr/bin/env python3
"""Plan 68 Phase 1: duplicate census of R (the DVD) without the frame-length truncation.

Plan 63's dup_census.py cuts every frame to U16(frame, 0) * 2 bytes. On G discs that word is the
frame length; on R it is not (an R L0 frame (0,1834,340,(650,)) truncates to 140 bytes and loses
its road / background / name sections), so plan 63's R census may have read no records at all.
This census reads each distinct R frame whole (all sectors of the leaf entry; section offsets bound
every read) and applies plan 63's duplicate definition (class>0, same type, byte-identical).
Also counts records per frame read both ways, so the truncation effect is measured, not assumed."""
from __future__ import annotations

import argparse, gzip, hashlib, io, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from census import iter_leaves, dup_classes, L  # noqa: E402
from provenance import leaf_all_records  # noqa: E402
import census as CZ  # noqa: E402
import os  # noqa: E402
from kiwiw import volume  # noqa: E402


def iter_full(path):
    """as census.iter_leaves, but yields (level, ix, iy, path, full_buf, trunc_buf)."""
    oc = L.oc; seen = set()
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
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
                        continue
                    seen.add(entry.dsa)
                    b = os.pread(f.fileno(), entry.size * ls, volume.getsector(entry.dsa, ss, ls))
                    yield lm.level, bx + x, by + y, tuple(leaf), b, b[:L.U16(b, 0) * 2]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    st = defaultdict(Counter); by_code = Counter(); rows = []
    for level, ix, iy, path, full, tr in iter_full(a.disc):
        s = st[level]; s["leaves"] += 1
        rf = leaf_all_records(full); rt = leaf_all_records(tr)
        s["records_full"] += len(rf); s["records_trunc"] += len(rt)
        s["records_full_cls>0"] += sum(1 for r in rf if r[1])
        s["frames_trunc_lost_records"] += len(rt) < len(rf)
        d = dup_classes(rf)
        if d:
            s["leaves_with_dup"] += 1
            for (code, w), ss in sorted(d.items(), key=lambda kv: kv[1][0]):
                s["dup_classes"] += 1; s["extra_copies"] += len(ss) - 1
                by_code[f"{level}/{code}"] += 1
                rows.append((level, ix, iy, ",".join(map(str, path)), code, len(ss), hashlib.sha256(w).hexdigest(),
                             ",".join(map(str, ss))))
    rows.sort()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(b"level\tix\tiy\tpath\tcode\tcopies\trecord_sha256\tpositions\n")
        for r in rows:
            g.write(("\t".join(map(str, r)) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    summ = {"levels": {str(k): dict(sorted(v.items())) for k, v in sorted(st.items())},
            "by_level_code": dict(sorted(by_code.items())),
            "total": dict(sorted(sum(st.values(), Counter()).items())), "wall_s": round(time.time() - t0, 1)}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ["total"]))


if __name__ == "__main__":
    main()
