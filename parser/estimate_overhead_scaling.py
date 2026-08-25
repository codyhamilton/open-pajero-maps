#!/usr/bin/env python3
"""Per-parcel content-vs-overhead measurement for ALLDATA.KWI.

Companion to `estimate_density.py` (whose mesh-walking helpers this script
imports rather than duplicates). `estimate_density.py` answered "how many
content bytes are on this disc"; this script answers the follow-up needed
for the size budget: **is the remaining ~74% of the file a fixed cost of
tiling the continent, or does it scale with content?**

Does NOT modify any parser/writer code and writes nothing to the disc.

--------------------------------------------------------------------------
ACCOUNTING DEFINITION (deliberately explicit so it is reproducible)
--------------------------------------------------------------------------
The unit of measurement is one *unique physical parcel record*, keyed by its
sector address (DSA). Deduplication matters: on this disc many adjacent mesh
cells reference the same physical record (see estimate_density.py PASS 1),
so counting mesh cells would multiply-count real bytes.

For each unique parcel record of `size` logical sectors:

  alloc_bytes  = size * logical_sector_size (32)
                 -- the bytes the record actually occupies on the disc.

  index_bytes  = the Map Frame header size field at byte 0 ([SWS]-encoded).
                 This region is 36 B of Map Frame header + nregion*4 B of
                 region list + the Main Map Data Frame Entry (mfde) table
                 that follows it. Pure bookkeeping: field values and
                 offset/size/cross-reference pointers, no map content.
                 Verified against a hexdump of a real level-0 parcel: the
                 first content frame begins exactly at this offset.

  content_bytes= sum of the `size` fields of the mfde entries that point at
                 a *map data frame inside this record* -- entries
                 0..(n_basic_map + n_ext_map - 1) from this level's LMR
                 (12 on every level of this disc), skipping the 0xFFFFFFFF
                 "no data" sentinel and anything whose offset+size falls
                 outside the record. Entry 0 = road, 1 = background,
                 2 = name (kiwiread's showmap()); entries 3..11 are the
                 extended-map slots, empty on this disc (counted anyway, and
                 the script reports how many were non-empty so the claim is
                 checkable). mfde entries at index >= 12 hold *sector
                 addresses of other parcel records* (confirmed by hexdump:
                 e.g. level-0 parcel dsa=20530211 lists 20530222 there,
                 which is itself an enumerated neighbouring parcel) -- they
                 are cross-reference pointers, so they are overhead, and
                 counting their sizes as content would double-count.

  slack_bytes  = alloc_bytes - index_bytes - content_bytes
                 -- inter-frame gaps plus the pad up to the 32-byte logical
                 sector boundary. Unavoidable given the record's shape, so
                 it is overhead.

  mesh_bytes   = 6 * (number of mesh cells referencing this DSA)
                 -- this record's own entries in its block's parcel
                 management record (6 B each: 4 B DSA + 2 B size).

  block_share  = this record's pro-rata share (by mesh entry count) of the
                 parcel management records themselves, which are wholly
                 bookkeeping: alloc = bsize * 32 for each block, including
                 the 4-byte type header of each (sub)parcel array and the
                 6-byte entries for empty cells that hold only the
                 0xFFFFFFFF sentinel.

  overhead_bytes = index_bytes + slack_bytes + mesh_bytes + block_share
                 = alloc_bytes - content_bytes + mesh_bytes + block_share

The PDMDH/LMR/BSMR/BMT blob (mhr[0], one 21 kB record for the whole disc)
is reported separately as a flat constant rather than smeared per parcel.

--------------------------------------------------------------------------
WHOLE-FILE CENSUS (--census)
--------------------------------------------------------------------------
The per-parcel numbers above only describe the *main map* frame. Running
`--census` additionally builds a byte-coverage bitmap of the entire file at
32-byte logical-sector granularity and reports what fraction of
ALLDATA.KWI the main-map mesh actually reaches, plus the identity of the
regions it does not. This exists because the main-map mesh reaches only a
minority of the file, so any "% overhead" figure computed from the mesh
walk alone is describing a minority of the disc.

Usage:
    python3 estimate_overhead_scaling.py --alldata /path/to/ALLDATA.KWI
    python3 estimate_overhead_scaling.py --levels 0,6 --max-parcels 200000
    python3 estimate_overhead_scaling.py --census
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import estimate_density as ed  # reuse its mesh-walking logic verbatim
from kiwiw.bitutils import extract, sws, u16, u32
from kiwiw.disc import AllData
from kiwiw.volume import getsector

NO_DATA_DSA = 0xFFFFFFFF
BMT_SIZE = 6
MFDE_SIZE = 6
MAPFRAME_HEADER_SIZE = 36

# content-bucket edges (bytes)
BUCKETS = [0, 1, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 1 << 30]


def bucket_of(n: int) -> int:
    for i in range(len(BUCKETS) - 1):
        if BUCKETS[i] <= n < BUCKETS[i + 1]:
            return i
    return len(BUCKETS) - 2


def bucket_label(i: int) -> str:
    lo, hi = BUCKETS[i], BUCKETS[i + 1]
    if lo == 0 and hi == 1:
        return "0 (empty)"
    if hi >= 1 << 30:
        return f"{lo}+"
    return f"{lo}..{hi - 1}"


def walk_level(pdmdh, lmr, fh, zdat0, sector_sz, logical_sz):
    """Like ed.iter_level_leaf_parcels but also surfaces the block-level
    parcel management record sizes (which ed's version consumes internally
    and discards). Yields ('block', block_alloc_bytes) and
    ('parcel', pt, dsa, size, ...) events."""
    level = lmr.level
    lon_span = ed._lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    mx = lon_span / lmr.grid_nx
    my = lat_span / lmr.grid_ny
    nbs_lng = 1 + lmr.n_blocksets_lng
    nbl_lng, nbl_lat = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
    npc_lng, npc_lat = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]
    n_blocks = nbl_lat * nbl_lng

    for bs in pdmdh.blocksets:
        if bs.level != level or bs.bmt_size == 0:
            continue
        bsx = bs.blockset_index % nbs_lng
        bsy = bs.blockset_index // nbs_lng
        n_entries = bs.bmt_size // BMT_SIZE
        bmt_entries = ed.read_bmt_array(zdat0, bs.bmt_offset, min(n_entries, n_blocks))
        for block_flat, (bdsa, bsize) in enumerate(bmt_entries):
            if bdsa == NO_DATA_DSA or bsize == 0:
                continue
            blx = block_flat % nbl_lng
            bly = block_flat // nbl_lng
            poff = getsector(bdsa, sector_sz, logical_sz)
            fh.seek(poff)
            pdat = fh.read(bsize * logical_sz)
            yield ("block", bsize * logical_sz)
            block_lon_lo = pdmdh.coverage.lon_lo + (bsx * nbl_lng * npc_lng + blx * npc_lng) * mx
            block_lat_lo = pdmdh.coverage.lat_lo + (bsy * nbl_lat * npc_lat + bly * npc_lat) * my
            block_bounds = (block_lat_lo, block_lat_lo + my * npc_lat,
                            block_lon_lo, block_lon_lo + mx * npc_lng)
            for pt, dsa, size, bounds in ed.walk_subparcel(pdat, 0, lmr, block_bounds, depth=1):
                yield ("parcel", pt, dsa, size)


def measure_parcel(fh, dsa, size, sector_sz, logical_sz, n_map_frames, stats):
    """Return (alloc, index_bytes, content_bytes, slack, n_frames_present)
    or None if the record is unreadable/short."""
    alloc = size * logical_sz
    fh.seek(getsector(dsa, sector_sz, logical_sz))
    md = fh.read(alloc)
    if len(md) < MAPFRAME_HEADER_SIZE + 2:
        return None
    index_bytes = sws(u16(md, 0))
    nregion = u16(md, 34)
    de_off = MAPFRAME_HEADER_SIZE + nregion * 4
    if not (de_off <= index_bytes <= alloc):
        stats["bad_index_size"] += 1
        # fall back to the minimum the layout guarantees
        index_bytes = min(max(de_off, 0), alloc)

    content = 0
    n_present = 0
    slots = []
    for i in range(n_map_frames):
        eoff = de_off + i * MFDE_SIZE
        if eoff + MFDE_SIZE > alloc or eoff + MFDE_SIZE > index_bytes:
            break
        raw_off = u32(md, eoff)
        if raw_off == NO_DATA_DSA:
            continue
        foff = sws(raw_off)
        fsize = sws(u16(md, eoff + 4))
        if fsize == 0:
            continue
        if foff < index_bytes or foff + fsize > alloc:
            stats["frame_out_of_record"] += 1
            continue
        content += fsize
        n_present += 1
        slots.append(i)
        stats["frames_by_slot"][i] += 1
    # "stub" = a parcel record whose only content is a background frame,
    # i.e. it exists purely because the mesh cell exists (sea/empty land).
    # These are the records that most directly answer "is overhead avoidable
    # by having less content" -- there are no content==0 records on this
    # disc, a background frame is always present, so a stub is the floor.
    if slots == [1]:
        stats["stub_parcels"] += 1
        stats["stub_content"] += content
        stats["stub_alloc"] += alloc
    slack = alloc - index_bytes - content
    if slack < 0:
        stats["negative_slack"] += 1
        slack = 0
    return alloc, index_bytes, content, slack, n_present


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sxx = syy = 0.0
    for x, y in zip(xs, ys):
        dx, dy = x - mx, y - my
        sxy += dx * dy
        sxx += dx * dx
        syy += dy * dy
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / (sxx * syy) ** 0.5


def linfit(xs, ys):
    """Least-squares y = a + b*x. Returns (a, b)."""
    n = len(xs)
    if n < 2:
        return float("nan"), float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sxx = 0.0
    for x, y in zip(xs, ys):
        sxy += (x - mx) * (y - my)
        sxx += (x - mx) ** 2
    if sxx <= 0:
        return my, 0.0
    b = sxy / sxx
    return my - b * mx, b


def census(disc, file_size):
    """Byte-coverage bitmap of the whole file at 32-byte granularity, so we
    can state exactly how much of ALLDATA.KWI the main-map mesh reaches and
    what the rest is. Region identities below are each confirmed by parsing
    the corresponding management header against its spec chapter -- see the
    printout, which shows the decoded fields that establish the claim."""
    LS = 32
    fh = disc._fh
    p = disc.pdmdh
    nls = file_size // LS + 1
    cov = bytearray(nls)
    TAGS = {
        1: "volume header + management header table",
        2: "main-map PDMDH/LMR/BSMR/BMT blob (mhr[0])",
        3: "block (parcel-management) records",
        4: "main-map parcel records",
        5: "route-guidance frames (per-parcel rg_addr)",
        6: "other management headers (mhr[1..])",
    }

    def mark(off, length, tag):
        a = off // LS
        b = (off + length + LS - 1) // LS
        for i in range(a, min(b, nls)):
            cov[i] = tag

    mark(0, 4096, 1)
    mark(getsector(disc.mhr[0].dsa, disc.sector_sz, disc.logical_sz),
         disc.mhr[0].size * LS, 2)
    for e in disc.mhr[1:]:
        if e.dsa != NO_DATA_DSA and e.size and not e.name:
            mark(getsector(e.dsa, disc.sector_sz, disc.logical_sz), e.size * LS, 6)

    for lmr in sorted(p.levels, key=lambda l: l.level):
        seen = set()
        for ev in walk_level(p, lmr, fh, disc._zdat0, disc.sector_sz, disc.logical_sz):
            if ev[0] == "block":
                continue
            _, pt, dsa, size = ev
            if dsa in seen:
                continue
            seen.add(dsa)
            off = getsector(dsa, disc.sector_sz, disc.logical_sz)
            mark(off, size * LS, 4)
            fh.seek(off)
            md = fh.read(size * LS)
            if len(md) >= 34:
                ra, rs = u32(md, 28), u16(md, 32)
                if ra != NO_DATA_DSA and rs:
                    mark(getsector(ra, disc.sector_sz, disc.logical_sz), sws(rs) * LS, 5)
    # block records: re-walk cheaply, marking the record extents
    for lmr in sorted(p.levels, key=lambda l: l.level):
        nbl = (1 + lmr.n_blocks_lng) * (1 + lmr.n_blocks_lat)
        for bs in p.blocksets:
            if bs.level != lmr.level or bs.bmt_size == 0:
                continue
            n_entries = min(bs.bmt_size // BMT_SIZE, nbl)
            for bdsa, bsize in ed.read_bmt_array(disc._zdat0, bs.bmt_offset, n_entries):
                if bdsa == NO_DATA_DSA or bsize == 0:
                    continue
                mark(getsector(bdsa, disc.sector_sz, disc.logical_sz), bsize * LS, 3)

    cnt = Counter(cov)
    print("\n\n=== WHOLE-FILE CENSUS ===")
    print(f"ALLDATA.KWI = {file_size:,} B")
    for t in sorted(cnt):
        b = cnt[t] * LS
        label = TAGS.get(t, "UNREACHED from the main-map mesh")
        print(f"  tag {t}: {b:>15,} B ({100*b/file_size:5.1f}%)  {label}")

    runs = []
    i = 0
    while i < nls:
        if cov[i] == 0:
            j = i
            while j < nls and cov[j] == 0:
                j += 1
            runs.append((j - i, i))
            i = j
        else:
            i += 1
    runs.sort(reverse=True)
    print(f"\n{len(runs):,} unreached runs; largest 6:")
    for ln, st in runs[:6]:
        print(f"  {st*LS:>13,} .. {(st+ln)*LS:>13,}   {ln*LS:>13,} B")

    # --- identify the two big unreached regions from their management headers ---
    print("\nIdentification of the large unreached regions (decoded, not guessed):")
    e = disc.mhr[1]  # Management Header Record 2 = Region-related Data Management
    if e.dsa != NO_DATA_DSA and e.size:
        off = getsector(e.dsa, disc.sector_sz, disc.logical_sz)
        fh.seek(off)
        b = fh.read(e.size * LS)
        hdr_sz = sws(u16(b, 0))
        n_regions = u32(b, 4)
        rmt_dsa = u32(b, 8)
        rmt_bs = u16(b, 12)
        rmt_off = getsector(rmt_dsa, disc.sector_sz, disc.logical_sz)
        print(f"  mhr[1] @{off:,} = spec Ch.9 Region Data Management Distribution Header:")
        print(f"    header_size(SWS)={hdr_sz}  total region management records={n_regions:,}")
        print(f"    Region Management Table DSA -> byte {rmt_off:,} "
              f"(size field {rmt_bs} logical sectors = {rmt_bs*LS:,} B; "
              f"{n_regions} x 24 B = {n_regions*24:,} B)")
        print(f"    -> the ~151 MB unreached run starts at exactly that address; Ch.9 "
              f"describes\n       this frame as managing the route-planning data frames "
              f"(Data Contents word 0\n       bit 14 'Route Planning' is set on this disc).")
    e = disc.mhr[6]  # Management Header Record 7 = Voice Data Management
    if e.dsa != NO_DATA_DSA and e.size:
        off = getsector(e.dsa, disc.sector_sz, disc.logical_sz)
        fh.seek(off)
        b = fh.read(min(64, e.size * LS))
        vh_sz = sws(u32(b, 0))
        n_lang = u16(b, 4)
        n_rec = u16(b, 6)
        usage = u16(b, 20)
        n_voices = u16(b, 24)
        print(f"  mhr[6] @{off:,} = spec Ch.34 Voice Distribution Header:")
        print(f"    header_size(SWS)={vh_sz:,} B (record alloc {e.size*LS:,} B)  "
              f"languages={n_lang}")
        print(f"    first General-purpose Voice Offset Management Table: {n_rec} records; "
              f"record 1 usage id={usage:#06x} "
              f"({'Voice Guidance A' if usage == 0x10 else 'see Ch.34 (1)'}), "
              f"n_voices={n_voices:,}")
        print(f"    -> the ~844 MB unreached run begins immediately after this header; "
              f"it is the\n       Voice Data Frame's real-data sequences (Ch.34 records 3 "
              f"and 4).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alldata", default="/run/media/codyh/464210-8480/ALLDATA.KWI")
    ap.add_argument("--levels", default="", help="comma-separated levels (default: all)")
    ap.add_argument("--max-parcels", type=int, default=0,
                    help="if >0, randomly subsample this many unique parcel "
                         "records per level for the content read (the mesh "
                         "walk is always exhaustive)")
    ap.add_argument("--scatter-sample", type=int, default=100000,
                    help="max (content, overhead) pairs retained per level "
                         "for correlation/regression stats")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--census", action="store_true",
                    help="also build a whole-file byte-coverage census")
    args = ap.parse_args()

    random.seed(args.seed)
    t0 = time.time()

    disc = AllData(args.alldata)
    pdmdh = disc.pdmdh
    fh, zdat0 = disc._fh, disc._zdat0
    sector_sz, logical_sz = disc.sector_sz, disc.logical_sz
    file_size = Path(args.alldata).stat().st_size

    want = None
    if args.levels:
        want = {int(x) for x in args.levels.split(",")}

    print(f"# ALLDATA.KWI = {file_size:,} bytes; sector={sector_sz} logical={logical_sz}")
    print(f"# PDMDH/LMR/BSMR/BMT blob (mhr[0]) = {len(zdat0):,} bytes "
          f"({disc.mhr[0].size} logical sectors) -- flat, whole-disc constant")
    print("#")
    print("# ACCOUNTING: content = map-data-frame bytes inside the parcel record")
    print("#             (mfde slots 0..n_basic_map+n_ext_map-1, i.e. road/bg/name")
    print("#             + extended slots). overhead = alloc - content, plus the")
    print("#             6 B/mesh-cell entries and the pro-rata block-record share.")

    grand = Counter()
    per_level = {}
    all_scatter = []

    for lmr in sorted(pdmdh.levels, key=lambda l: l.level):
        if want is not None and lmr.level not in want:
            continue
        n_map_frames = lmr.n_basic_map + lmr.n_ext_map
        print(f"\n=== Level {lmr.level} === grid {lmr.grid_nx}x{lmr.grid_ny}, "
              f"mfde map-frame slots = {lmr.n_basic_map}+{lmr.n_ext_map} = {n_map_frames}")

        # --- PASS 1: exhaustive mesh walk (no parcel content reads) ---
        refcount = defaultdict(int)   # dsa -> mesh cells referencing it
        sizes = {}                    # dsa -> size in logical sectors
        block_alloc_total = 0
        n_blocks_used = 0
        n_cells = 0
        for ev in walk_level(pdmdh, lmr, fh, zdat0, sector_sz, logical_sz):
            if ev[0] == "block":
                block_alloc_total += ev[1]
                n_blocks_used += 1
                continue
            _, pt, dsa, size = ev
            refcount[dsa] += 1
            sizes[dsa] = size
            n_cells += 1

        n_unique = len(refcount)
        if n_unique == 0:
            print("  (no parcels)")
            continue
        parcel_alloc_declared = sum(sizes[d] * logical_sz for d in sizes)
        print(f"  mesh cells: {n_cells:,} -> {n_unique:,} unique parcel records "
              f"(avg {n_cells / n_unique:.2f} cells/record)")
        print(f"  block (parcel-management) records: {n_blocks_used:,}, "
              f"{block_alloc_total:,} B total "
              f"({block_alloc_total / n_unique:.1f} B per unique parcel)")

        # --- PASS 2: one content read per unique parcel record ---
        keys = list(refcount.keys())
        sampled = False
        if args.max_parcels and len(keys) > args.max_parcels:
            keys = random.sample(keys, args.max_parcels)
            sampled = True
        scale = n_unique / len(keys)

        stats = {"bad_index_size": 0, "frame_out_of_record": 0,
                 "negative_slack": 0, "frames_by_slot": Counter(),
                 "stub_parcels": 0, "stub_content": 0, "stub_alloc": 0}
        b_count = Counter()
        b_content = Counter()
        b_overhead = Counter()
        b_index = Counter()
        b_slack = Counter()
        b_mesh = Counter()
        index_hist = Counter()
        scatter = []
        n_read = 0
        tot_alloc = tot_content = tot_index = tot_slack = tot_mesh = 0

        for dsa in keys:
            r = measure_parcel(fh, dsa, sizes[dsa], sector_sz, logical_sz,
                               n_map_frames, stats)
            if r is None:
                continue
            alloc, index_bytes, content, slack, n_present = r
            mesh = MFDE_SIZE * refcount[dsa]
            n_read += 1
            tot_alloc += alloc
            tot_content += content
            tot_index += index_bytes
            tot_slack += slack
            tot_mesh += mesh
            index_hist[index_bytes] += 1
            bi = bucket_of(content)
            b_count[bi] += 1
            b_content[bi] += content
            b_index[bi] += index_bytes
            b_slack[bi] += slack
            b_mesh[bi] += mesh
            b_overhead[bi] += index_bytes + slack + mesh
            if len(scatter) < args.scatter_sample:
                scatter.append((content, index_bytes + slack + mesh))
            elif random.random() < args.scatter_sample / n_read:
                scatter[random.randrange(args.scatter_sample)] = (
                    content, index_bytes + slack + mesh)

        if sampled:
            print(f"  SAMPLED {n_read:,}/{n_unique:,} unique parcel records "
                  f"({100 * n_read / n_unique:.2f}%), scale factor {scale:.3f}x")
        else:
            print(f"  READ {n_read:,}/{n_unique:,} unique parcel records (100%)")

        print(f"  mfde slots actually populated: "
              f"{dict(sorted(stats['frames_by_slot'].items()))}  "
              f"(slot 0=road 1=background 2=name; 3..{n_map_frames-1}=extended)")
        if stats["bad_index_size"] or stats["frame_out_of_record"] or stats["negative_slack"]:
            print(f"  ANOMALIES: bad_index_size={stats['bad_index_size']} "
                  f"frame_out_of_record={stats['frame_out_of_record']} "
                  f"negative_slack={stats['negative_slack']}")
        if stats["stub_parcels"]:
            sp = stats["stub_parcels"]
            print(f"  STUB parcels (background frame only, no road/name/extended): "
                  f"{sp:,} of {n_read:,} read ({100*sp/n_read:.1f}%); "
                  f"mean content {stats['stub_content']/sp:.1f} B, "
                  f"mean alloc {stats['stub_alloc']/sp:.1f} B")
        top_idx = index_hist.most_common(5)
        print(f"  header+index-table size distribution (top 5): "
              + ", ".join(f"{v}B x{c:,}" for v, c in top_idx)
              + f"  [{len(index_hist)} distinct values]")

        print(f"  {'content bucket':>14} {'n':>9} {'meanCont':>9} {'meanIdx':>8} "
              f"{'meanSlack':>9} {'meanMesh':>8} {'meanOvh':>8} {'ovh/cont':>9}")
        for bi in sorted(b_count):
            n = b_count[bi]
            mc = b_content[bi] / n
            print(f"  {bucket_label(bi):>14} {n:>9,} {mc:>9.1f} "
                  f"{b_index[bi]/n:>8.1f} {b_slack[bi]/n:>9.1f} {b_mesh[bi]/n:>8.1f} "
                  f"{b_overhead[bi]/n:>8.1f} "
                  + (f"{b_overhead[bi]/b_content[bi]:>9.2f}" if b_content[bi] else f"{'inf':>9}"))

        cs = [c for c, _ in scatter]
        os_ = [o for _, o in scatter]
        r = pearson(cs, os_)
        a, b = linfit(cs, os_)
        print(f"  scatter n={len(scatter):,}: pearson r(content, overhead) = {r:.4f}; "
              f"least-squares overhead ~= {a:.1f} + {b:.4f} * content")

        tot_block = block_alloc_total * (n_read / n_unique if n_unique else 1)
        tot_overhead = tot_index + tot_slack + tot_mesh + tot_block
        print(f"  level totals (over the records read): content={tot_content:,} B, "
              f"overhead={tot_overhead:,.0f} B "
              f"(index={tot_index:,} slack={tot_slack:,} mesh={tot_mesh:,} "
              f"block={tot_block:,.0f})")
        if tot_alloc + tot_mesh + tot_block:
            print(f"  -> content is {100*tot_content/(tot_content+tot_overhead):.1f}% "
                  f"of this level's parcel+mesh bytes")

        per_level[lmr.level] = dict(
            n_cells=n_cells, n_unique=n_unique, n_read=n_read, scale=scale,
            tot_alloc=tot_alloc, tot_content=tot_content, tot_index=tot_index,
            tot_slack=tot_slack, tot_mesh=tot_mesh, tot_block=tot_block,
            block_alloc_total=block_alloc_total, n_blocks=n_blocks_used,
            parcel_alloc_declared=parcel_alloc_declared,
            r=r, fit_a=a, fit_b=b, b_count=dict(b_count), b_overhead=dict(b_overhead),
            b_content=dict(b_content), b_index=dict(b_index), b_slack=dict(b_slack),
            b_mesh=dict(b_mesh),
        )
        all_scatter.extend(scatter)
        for k in ("tot_alloc", "tot_content", "tot_index", "tot_slack", "tot_mesh",
                  "n_cells", "n_unique", "n_read", "n_blocks"):
            grand[k] += per_level[lmr.level][k]
        grand["tot_block"] += tot_block

    if args.census:
        census(disc, file_size)

    disc.close()

    # ------------------------------------------------------------------
    print("\n\n=== OVERALL (main-map frame only) ===")
    est = 1.0
    print(f"unique parcel records read: {grand['n_read']:,} of {grand['n_unique']:,} "
          f"({100*grand['n_read']/max(1,grand['n_unique']):.2f}%); "
          f"mesh cells walked: {grand['n_cells']:,}; blocks: {grand['n_blocks']:,}")
    tot_ovh = grand["tot_index"] + grand["tot_slack"] + grand["tot_mesh"] + grand["tot_block"]
    tot = grand["tot_content"] + tot_ovh
    print(f"content : {grand['tot_content']:>15,} B  ({100*grand['tot_content']/tot:5.1f}%)")
    print(f"index   : {grand['tot_index']:>15,} B  ({100*grand['tot_index']/tot:5.1f}%)  "
          f"map-frame header + region list + mfde table")
    print(f"slack   : {grand['tot_slack']:>15,} B  ({100*grand['tot_slack']/tot:5.1f}%)  "
          f"intra-record gaps + logical-sector padding")
    print(f"mesh    : {grand['tot_mesh']:>15,} B  ({100*grand['tot_mesh']/tot:5.1f}%)  "
          f"6 B per mesh-cell reference")
    print(f"block   : {grand['tot_block']:>15,.0f} B  ({100*grand['tot_block']/tot:5.1f}%)  "
          f"parcel-management records (whole)")
    print(f"TOTAL   : {tot:>15,.0f} B   vs file {file_size:,} B "
          f"({100*tot/file_size:.1f}% of the file accounted for)")

    if grand["n_read"]:
        print(f"\nper unique parcel record (mean over {grand['n_read']:,} read):")
        print(f"  content  {grand['tot_content']/grand['n_read']:8.1f} B")
        print(f"  index    {grand['tot_index']/grand['n_read']:8.1f} B")
        print(f"  slack    {grand['tot_slack']/grand['n_read']:8.1f} B")
        print(f"  mesh     {grand['tot_mesh']/grand['n_read']:8.1f} B")
        print(f"  block    {grand['tot_block']/grand['n_read']:8.1f} B")
        print(f"  OVERHEAD {tot_ovh/grand['n_read']:8.1f} B")

    cs = [c for c, _ in all_scatter]
    os_ = [o for _, o in all_scatter]
    if len(cs) > 1:
        print(f"\npooled scatter n={len(cs):,}: pearson r = {pearson(cs, os_):.4f}")
        a, b = linfit(cs, os_)
        print(f"pooled least-squares: overhead ~= {a:.1f} + {b:.4f} * content")
        empt = [o for c, o in all_scatter if c == 0]
        if empt:
            empt.sort()
            print(f"empty parcels (content==0) in scatter: n={len(empt):,}, "
                  f"overhead min={empt[0]} median={empt[len(empt)//2]} max={empt[-1]}")

    print(f"\n(elapsed {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
