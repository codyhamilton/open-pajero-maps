#!/usr/bin/env python3
"""Plan 63: duplicate-emission census of one disc.

Every leaf frame of every level (frame addresses deduplicated: a sparse alias slot is read once,
reported under its first leaf key). A leaf "holds duplicates" when two or more class>0 background
records have the same type code and identical bytes. Output: <out>.json summary (per level: leaves,
leaves_with_dup, dup classes, extra copies; by type code) and <out>.tsv.gz rows
(level ix iy path code copies record_sha256), gz mtime 0. Streams block by block."""
from __future__ import annotations

import argparse, gzip, hashlib, io, json, os, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p7_producer_tie")]
import leaf_io as L  # noqa: E402
from kiwiw import volume  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402
from provenance import leaf_all_records  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="prefix")
    a = ap.parse_args(argv)
    t0 = time.time()
    oc = L.oc
    lv_stats = defaultdict(Counter); by_code = Counter(); rows = []; seen = set()
    with open(a.disc, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if entry.dsa in seen:
                        lv_stats[lm.level]["alias_slots"] += 1
                        continue
                    seen.add(entry.dsa)
                    b = os.pread(f.fileno(), entry.size * ls, volume.getsector(entry.dsa, ss, ls))
                    buf = b[:L.U16(b, 0) * 2]
                    st = lv_stats[lm.level]; st["leaves"] += 1
                    c = Counter((code, w) for _s, cls, code, w in leaf_all_records(buf) if cls)
                    d = {k: n for k, n in c.items() if n >= 2}
                    if d:
                        st["leaves_with_dup"] += 1
                        for (code, w), n in sorted(d.items()):
                            st["dup_classes"] += 1; st["extra_copies"] += n - 1
                            by_code[f"{lm.level}/{code}"] += 1
                            rows.append((lm.level, bx + x, by + y, ",".join(map(str, leaf)), code, n,
                                         hashlib.sha256(w).hexdigest()))
    rows.sort()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(b"level\tix\tiy\tpath\tcode\tcopies\trecord_sha256\n")
        for r in rows:
            g.write(("\t".join(map(str, r)) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    summ = {"disc_sha256_16": None, "levels": {str(k): dict(sorted(v.items())) for k, v in sorted(lv_stats.items())},
            "by_level_code": dict(sorted(by_code.items())),
            "total": dict(sorted(sum(lv_stats.values(), Counter()).items()))}
    h = hashlib.sha256()
    with open(a.disc, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    summ["disc_sha256_16"] = h.hexdigest()[:16]
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ["total"]), json.dumps({"wall_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
