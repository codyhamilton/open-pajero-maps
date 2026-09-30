"""Whole-`ALLDATA.KWI`-file assembler: the layout/allocation layer that
decides *where* every structure lives in a freshly-built file, composing
the already-proven structural writers (`volume_writer.py`,
`parcel_writer.py`) rather than re-implementing any byte encoding.

Everything up to this module answers "given where a structure already
lives in the real file, what are its exact bytes" (see
`volume_writer.write_pdmdh()` and `parcel_writer.write_map_frame()`,
both of which place content at offsets read out of the parsed IR). This
module answers the complementary question this phase still owed:
"given only the parsed IR, where should each structure go in a
from-scratch buffer, and how do the cross-references get rewritten so
everything still finds everything else."

Two allocation modes are supported, both walking a full mesh region (one
or more whole block sets -- every block, every parcel, every subparcel
reachable from them, not just a hand-picked coordinate):

- `assemble_inplace()`: reproduce the *original* disc's own layout
  decisions exactly (same file offsets the source disc used for every
  block and Map Frame). A byte-identical match against the real disc at
  each of those offsets proves the allocation *rule* is understood, not
  just "a plausible one" -- this is the "replicate the original's exact
  choices" check the phase doc asks for.
- `assemble_denovo()`: pack the same content into a brand-new, freshly
  chosen contiguous layout (blocks, then Map Frames, back-to-back,
  32-byte aligned per the disc's own KIWI-W sector-address granularity --
  see `encode_sector_addr()`), rewriting every pointer (Block Management
  Table entries, Parcel Management Record leaf entries, the Management
  Header Table's own PDMDH pointer) to match. This is the genuinely new
  problem: existing writers only ever wrote a structure back to the same
  place it was read from.

Both modes reuse the exact same `write_pdmdh()` / `write_parcel_mgmt_record()`
/ `write_map_frame()` (+ sub-frame writers) that are already proven
byte-identical "in place" -- only the *pointer values fed into them*
differ between modes, never the encoding logic itself.

Out of scope (see this module's
callers for the full reasoning, not repeated here): the two vendor ext-
frame types (0xAF100100/0xAF100300) are not synthesized -- when a Map
Frame's mfde table has an in-buffer "Extended Data Frame" entry, its raw
bytes are carried through unchanged (already true of `MapFrame.ext_frame_raw`,
untouched by this module); anything living in the separate management
frame at file offset 4096..6144 is never
referenced here at all -- the de novo layout places the PDMDH blob
directly after the Management Header Table instead, since reproducing
that gap's content is out of scope and not needed for the layout question
this module answers.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

import numpy as np

from . import volume, volume_writer, parcel_writer
from . import mesh
from .model import BoundingBox, MeshLocation, Parcel, ParcelMapInfoEntry, ParcelMgmtRecord
from .parcel import decode_parcel
from .parcel_mgmt import parse_parcel_mgmt_record

POISON = parcel_writer.POISON
NO_DATA_DSA = 0xFFFFFFFF


# ---------------------------------------------------------------------
# Sector-address / alignment helpers
# ---------------------------------------------------------------------

def encode_sector_addr(byte_offset: int, sector_sz: int, logical_sz: int) -> int:
    """Inverse of `volume.getsector()`: pack an absolute byte offset back
    into a KIWI-W "sector address" (top 24 bits = a `sector_sz`-sized
    sector index, low 6 bits = a sub-offset within that sector in units of
    `logical_sz`).

    Raises if `byte_offset` isn't `logical_sz`-aligned, or if the
    sub-offset can't fit in 6 bits -- the latter can't actually happen for
    this disc's real `sector_sz=2048`/`logical_sz=32` (max sub-offset is
    `2048/32 - 1 = 63`, which is exactly the 6-bit range), but is checked
    explicitly rather than silently truncated.
    """
    if byte_offset % logical_sz != 0:
        raise ValueError(
            f"byte offset {byte_offset} is not a multiple of logical_sz={logical_sz}")
    sector_index, rem = divmod(byte_offset, sector_sz)
    sub = rem // logical_sz
    if sub > 0x3F:
        raise ValueError(
            f"sub-sector offset {sub} (from byte {byte_offset}) does not fit in 6 bits "
            f"-- sector_sz={sector_sz} is not an exact multiple of 64*logical_sz={64*logical_sz}")
    if sector_index > 0xFFFFFF:
        raise ValueError(f"sector index {sector_index} does not fit in 24 bits")
    return (sector_index << 8) | sub


def align_up(n: int, granularity: int) -> int:
    rem = n % granularity
    return n if rem == 0 else n + (granularity - rem)


# ---------------------------------------------------------------------
# Bounds bookkeeping for a *full enumeration* of a block's parcel tree
# (mesh.locate_parcel() only ever narrows bounds along the single path to
# one queried coordinate; here every entry needs its own bounds, purely
# from grid arithmetic -- no query point is involved at all).
# ---------------------------------------------------------------------

def _lon_span(lo: float, hi: float) -> float:
    span = hi - lo
    return span + 360.0 if span < 0 else span


def _block_base_bounds(pdmdh, lmr, bsx: int, bsy: int, blx: int, bly: int) -> BoundingBox:
    """The full bounding box covering every top-level parcel of one block
    (blockset coords `bsx,bsy`, block coords `blx,bly`), computed the same
    way `mesh.locate_parcel()` derives a single top-level parcel's cell
    (same `mx`/`my` grid-cell size, same row-major lat-outer/lon-inner
    indexing confirmed in docs/01-format-analysis.md), just without a
    query coordinate to select one cell -- this returns the box spanning
    *all* of them."""
    lon_span = _lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    mx = lon_span / lmr.grid_nx
    my = lat_span / lmr.grid_ny
    npc_lng = 1 + lmr.n_parcels_lng[0]
    npc_lat = 1 + lmr.n_parcels_lat[0]
    nbl_lng = 1 + lmr.n_blocks_lng
    nbl_lat = 1 + lmr.n_blocks_lat
    base_ix = (bsx * nbl_lng + blx) * npc_lng
    base_iy = (bsy * nbl_lat + bly) * npc_lat
    base_lon = pdmdh.coverage.lon_lo + base_ix * mx
    base_lat = pdmdh.coverage.lat_lo + base_iy * my
    return BoundingBox(lat_lo=base_lat, lat_hi=base_lat + npc_lat * my,
                        lon_lo=base_lon, lon_hi=base_lon + npc_lng * mx)


def _narrow_bounds(bounds: BoundingBox, gn_lat: int, gn_lng: int, idx: int) -> BoundingBox:
    """Narrow `bounds` to the sub-cell at flat grid index `idx` of a
    `gn_lat` x `gn_lng` grid -- the same row-major (lat outer, lon inner)
    narrowing `mesh.locate_parcel()` performs for one recursion step, but
    driven by the mapinfo array's own index rather than a query point's
    fractional position (mesh.py needs the latter only because it's
    walking towards one specific coordinate; a full-tree enumeration
    already knows every entry's index directly)."""
    lpy, lpx = divmod(idx, gn_lng)
    lon_step = (bounds.lon_hi - bounds.lon_lo) / gn_lng
    lat_step = (bounds.lat_hi - bounds.lat_lo) / gn_lat
    lon_lo = bounds.lon_lo + lpx * lon_step
    lat_lo = bounds.lat_lo + lpy * lat_step
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_lo + lat_step,
                        lon_lo=lon_lo, lon_hi=lon_lo + lon_step)


# ---------------------------------------------------------------------
# Loading a whole block set's content from the real disc
# ---------------------------------------------------------------------

@dataclass
class LoadedLeaf:
    """One leaf Map Frame reachable from a block's Parcel Management
    Record tree: the `ParcelMapInfoEntry` object itself (kept by
    reference -- mutating its `.dsa` in place is how `assemble_denovo()`
    repoints it at a new location), the fully-decoded `Parcel`, and its
    original absolute file offset/length (for the in-place check and for
    diffing content-equality after a de novo re-parse)."""
    entry: ParcelMapInfoEntry
    parcel: Parcel
    original_offset: int
    length: int
    bounds: BoundingBox


@dataclass
class LoadedBlock:
    """One block reachable from a target block set's Block Management
    Table: the raw parsed `ParcelMgmtRecord` tree, every leaf it
    reaches (`leaves`), and enough of the owning `BmtEntry`'s identity to
    repoint it (`bmt_table`/`entry_index` index into
    `pdmdh.bmt_tables`/`.entries`)."""
    bmt_table_ordinal: int   # index into pdmdh.bmt_tables
    entry_index: int         # index into that table's .entries
    original_offset: int
    length: int
    root: ParcelMgmtRecord
    leaves: list[LoadedLeaf] = field(default_factory=list)


@dataclass
class LoadedRegion:
    hdr: volume.VolumeHeader
    extras: volume.VolumeHeaderExtras
    mht: volume.ManagementHeaderTable
    pdmdh: volume.Pdmdh
    prdm_offset: int
    level: int = 0
    blocks: list[LoadedBlock] = field(default_factory=list)


def _walk_tree(rec: ParcelMgmtRecord, bounds: BoundingBox, lmr, leaves: list[tuple],
               path: tuple = ()) -> None:
    """Append (entry, leaf_bounds, leaf_path, parcel_type) for every leaf;
    parcel_type is the enclosing record's (0 = normal, 1..3 = pardiv)."""
    gn_lat = 1 + lmr.n_parcels_lat[rec.parcel_type]
    gn_lng = 1 + lmr.n_parcels_lng[rec.parcel_type]
    for idx, entry in enumerate(rec.entries):
        if entry.dsa == NO_DATA_DSA:
            continue
        child_bounds = _narrow_bounds(bounds, gn_lat, gn_lng, idx)
        if entry.subrecord is not None:
            _walk_tree(entry.subrecord, child_bounds, lmr, leaves, path + (idx,))
        elif entry.size:
            leaves.append((entry, child_bounds, path + (idx,), rec.parcel_type))


def load_region(path: str, level: int, blockset_indices: list[int]) -> LoadedRegion:
    """Read the real disc's container/mesh layer plus the *full* content
    (every block, every parcel, every subparcel, every road/background/
    name sub-frame) reachable from the given block sets at `level`.

    This is deliberately not limited to hand-picked coordinates: every
    real, non-empty Block Management Table entry in each requested block
    set is loaded, and every leaf its Parcel Management Record tree
    reaches is decoded, exactly like `roundtrip_parcel_content.py` does
    for one coordinate at a time -- just exhaustively.
    """
    with open(path, "rb") as fh:
        raw_header = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_header)
        extras = volume.parse_volume_header_extras(raw_header)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        if prdm.name:
            raise NotImplementedError("file-based PDMDH not supported")
        prdm_off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        prdm_size = prdm.size * hdr.logical_sector_size
        fh.seek(prdm_off)
        raw_prdm = fh.read(prdm_size)
        pdmdh = volume.parse_pdmdh_full(raw_prdm)

        lmr = next((l for l in pdmdh.levels if l.level == level), None)
        if lmr is None:
            raise ValueError(f"no LMR for level {level}")
        nbl_lng = 1 + lmr.n_blocks_lng
        nbs_lng = 1 + lmr.n_blocksets_lng

        region = LoadedRegion(hdr=hdr, extras=extras, mht=mht, pdmdh=pdmdh,
                               prdm_offset=prdm_off, level=level)

        for bsidx in blockset_indices:
            bs = next((b for b in pdmdh.blocksets
                       if b.level == level and b.blockset_index == bsidx), None)
            if bs is None:
                raise ValueError(f"no blockset {bsidx} at level {level}")
            bsy, bsx = divmod(bsidx, nbs_lng)
            table_ordinal = next(
                i for i, t in enumerate(pdmdh.bmt_tables)
                if pdmdh.blocksets[t.blockset_ordinal] is bs)
            table = pdmdh.bmt_tables[table_ordinal]

            for entry_index, bmt_entry in enumerate(table.entries):
                if bmt_entry.dsa == NO_DATA_DSA or not bmt_entry.size:
                    continue
                bly, blx = divmod(entry_index, nbl_lng)
                boff = volume.getsector(bmt_entry.dsa, hdr.sector_size, hdr.logical_sector_size)
                blen = bmt_entry.size * hdr.logical_sector_size
                fh.seek(boff)
                bbuf = fh.read(blen)
                root = parse_parcel_mgmt_record(bbuf, lmr)

                block = LoadedBlock(bmt_table_ordinal=table_ordinal, entry_index=entry_index,
                                     original_offset=boff, length=blen, root=root)
                block_bounds = _block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
                raw_leaves: list[tuple] = []
                _walk_tree(root, block_bounds, lmr, raw_leaves)

                sparse = mesh.sparse_memo(root.entries, 1 + lmr.n_parcels_lng[0])
                for entry, leaf_bounds, leaf_path, ptype in raw_leaves:
                    # Decode against the leaf's real frame and range
                    # (`mesh.leaf_frame`, as `harness.walk` does); the leaf
                    # keeps those bounds, so any re-encode uses the same range.
                    bounds, _ = mesh.leaf_frame(level, ptype, leaf_path, leaf_bounds,
                                                block_bounds, lmr, sparse)
                    moff = volume.getsector(entry.dsa, hdr.sector_size, hdr.logical_sector_size)
                    mlen = entry.size * hdr.logical_sector_size
                    fh.seek(moff)
                    mapdata = fh.read(mlen)
                    loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=bsidx,
                                        block_index=entry_index, parcel_index=leaf_path[-1],
                                        bounds=bounds,
                                        sector_addr=entry.dsa, size_logical_sectors=entry.size)
                    parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                            n_ext_map=lmr.n_ext_map)
                    block.leaves.append(LoadedLeaf(entry=entry, parcel=parcel,
                                                    original_offset=moff, length=mlen,
                                                    bounds=bounds))
                region.blocks.append(block)

    return region


# ---------------------------------------------------------------------
# Serializing one block / one parcel's Map Frame (thin wrappers around
# parcel_writer, isolated so both allocation modes share one code path)
# ---------------------------------------------------------------------

def _write_block_buffer(block: LoadedBlock) -> bytes:
    buf = bytearray([POISON]) * block.length
    parcel_writer.write_parcel_mgmt_record(block.root, buf)
    return bytes(buf)


def _write_leaf_frame(leaf: LoadedLeaf) -> bytes:
    p = leaf.parcel
    road_bytes = parcel_writer.write_road_frame(p.road) if p.road is not None else None
    bg_bytes = (parcel_writer.write_background_frame(p.background)
                if p.background is not None else None)
    name_bytes = parcel_writer.write_name_frame(p.name) if p.name is not None else None
    return parcel_writer.write_map_frame(p.frame, road_bytes, bg_bytes, name_bytes)


# ---------------------------------------------------------------------
# Mode A: reproduce the original disc's own layout decisions exactly
# ---------------------------------------------------------------------

@dataclass
class RegionCheck:
    name: str
    offset: int
    rebuilt: bytes


def assemble_inplace(region: LoadedRegion) -> list[RegionCheck]:
    """Re-serialize the header layer + every loaded block + every loaded
    leaf Map Frame at the *exact* file offsets the real disc used. Each
    returned `RegionCheck` should byte-diff as identical against the real
    file at `.offset`, proving the allocation rule (not just the byte
    encoding) is understood -- this is the "replicate the original's
    exact choices" half of the task."""
    checks = [
        RegionCheck("Data Volume", 0,
                    volume_writer.write_volume_header(region.hdr, region.extras)),
        RegionCheck("Management Header Table", volume.DATAVOL_SIZE,
                    volume_writer.write_management_header_table(region.mht)),
        RegionCheck("PDMDH+LMR+BSMR+BMT", region.prdm_offset,
                    volume_writer.write_pdmdh(region.pdmdh)),
    ]
    for block in region.blocks:
        checks.append(RegionCheck(
            f"block (bmt_table={block.bmt_table_ordinal}, entry={block.entry_index})",
            block.original_offset, _write_block_buffer(block)))
        for leaf in block.leaves:
            checks.append(RegionCheck(
                f"parcel @ sector {leaf.entry.dsa}", leaf.original_offset,
                _write_leaf_frame(leaf)))
    return checks


# ---------------------------------------------------------------------
# Mode B: allocate a brand-new, freshly chosen contiguous layout
# ---------------------------------------------------------------------

@dataclass
class DenovoResult:
    buf: bytes
    pdmdh_offset: int
    block_offsets: dict[int, int]   # id(block) -> new file offset
    leaf_offsets: dict[int, int]    # id(leaf.entry) -> new file offset


def assemble_denovo(region: LoadedRegion) -> DenovoResult:
    """Pack the loaded region's blocks and Map Frames into a brand-new
    contiguous layout (PDMDH blob right after the Management Header
    Table; every block back-to-back after that in the order loaded;
    every leaf Map Frame back-to-back after all the blocks), rewriting
    every pointer that addresses a relocated structure:

    - the Management Header Table's own entry 0 (`mht.entries[0].dsa`),
      which addresses the PDMDH blob;
    - each relocated block's own `BmtEntry.dsa` inside the PDMDH's Block
      Management Table;
    - each relocated leaf's own `ParcelMapInfoEntry.dsa` inside its
      owning block's Parcel Management Record tree.

    Every block and every Map Frame's own *internal* structure (in-buffer
    `[D]`-encoded subparcel offsets, in-buffer mfde road/background/name
    offsets) is untouched -- relocating a whole buffer doesn't change
    offsets relative to its own start, only the absolute pointer that
    finds that buffer in the first place. `bmt_size`/leaf `size` fields
    are likewise untouched (content length doesn't change, only where it
    sits), which is exactly why only `.dsa` is ever mutated below.

    Deep-copies `region.mht`/`region.pdmdh` before mutating so the
    original parsed IR (used by `assemble_inplace()`) is never disturbed.
    """
    import copy

    hdr, extras = region.hdr, region.extras
    mht = copy.deepcopy(region.mht)
    pdmdh = copy.deepcopy(region.pdmdh)
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size

    pdmdh_offset = align_up(volume.DATAVOL_SIZE + volume.MHT_SIZE, logical_sz)
    offset = pdmdh_offset + pdmdh.total_size
    if offset % logical_sz != 0:
        raise ValueError(
            f"PDMDH total_size ({pdmdh.total_size}) is not logical_sz-aligned -- "
            "cannot place blocks contiguously after it")

    block_offsets: dict[int, int] = {}
    for block in region.blocks:
        block_offsets[id(block)] = offset
        if offset % logical_sz != 0:
            raise ValueError(f"block length not {logical_sz}-aligned so far: offset {offset}")
        offset += block.length

    leaf_offsets: dict[int, int] = {}
    for block in region.blocks:
        for leaf in block.leaves:
            leaf_offsets[id(leaf.entry)] = offset
            offset += leaf.length

    total_len = offset

    # --- rewrite pointers on the deep-copied IR -------------------------
    mht.entries[0].dsa = encode_sector_addr(pdmdh_offset, sector_sz, logical_sz)

    for block in region.blocks:
        table = pdmdh.bmt_tables[block.bmt_table_ordinal]
        bmt_entry = table.entries[block.entry_index]
        bmt_entry.dsa = encode_sector_addr(block_offsets[id(block)], sector_sz, logical_sz)
        # size is unchanged: block.length == bmt_entry.size * logical_sz still holds.

        for leaf in block.leaves:
            leaf.entry.dsa = encode_sector_addr(leaf_offsets[id(leaf.entry)], sector_sz, logical_sz)

    # --- write everything into one contiguous buffer --------------------
    buf = bytearray([POISON]) * total_len

    def _put(off: int, data: bytes) -> None:
        buf[off:off + len(data)] = data

    _put(0, volume_writer.write_volume_header(hdr, extras))
    _put(volume.DATAVOL_SIZE, volume_writer.write_management_header_table(mht))
    _put(pdmdh_offset, volume_writer.write_pdmdh(pdmdh))
    for block in region.blocks:
        _put(block_offsets[id(block)], _write_block_buffer(block))
        for leaf in block.leaves:
            _put(leaf_offsets[id(leaf.entry)], _write_leaf_frame(leaf))

    return DenovoResult(buf=bytes(buf), pdmdh_offset=pdmdh_offset,
                         block_offsets=block_offsets, leaf_offsets=leaf_offsets)


# ---------------------------------------------------------------------
# Whole-Australia, all-seven-level synthetic ALLDATA.KWI builder (unit 12)
# ---------------------------------------------------------------------
#
# An assembler driven by `kiwiw.grid.ReferenceGrid`: one LMR per level (grid
# contract), the reference's own 601-entry BSMR array with real blocksets
# only where `grid.json` says `R` has them, and a Block Management Table
# for every one of those. See docs/design/target-disc.md ("Grid contract",
# "Copy-through management data", "Unknown bytes policy") and
# docs/schema/map-frame.md.


from .grid import ReferenceGrid

# --- Empty-blockset BSMR convention -----------------------------------
# Observed directly on `R` (parser/kiwiw/volume.py's `parse_pdmdh_full()`
# already documents this: "'no block management table' -- the sentinel
# offset (0xFFFFFFFF, doubled by the shared SWS decode) with size 0"). A
# `BlockSetMgmtRecord` for a blockset `grid.json` marks `has_bmt: false`
# gets this bmt_offset/bmt_size pair instead of a real `BmtTable`; then
# `volume_writer.write_bsmr()`'s `unsws()` on write halves it back to the
# literal on-disk 0xFFFFFFFF/0x00000000 R itself uses.
EMPTY_BMT_OFFSET = 0xFFFFFFFF * 2
EMPTY_BMT_SIZE = 0

# --- "No data" convention for an individual empty block/parcel slot ----
# Same NO_DATA_DSA sentinel (0xFFFFFFFF, un-doubled -- these are already
# full 32-bit dsa fields, not [SWS]-halved) already used throughout this
# module and `parcel_mgmt.py` for an empty ParcelMapInfoEntry; the same
# convention is reused here for an empty BmtEntry within an otherwise
# non-empty Block Management Table (a block with real neighbours but no
# parcels of its own -- e.g. open ocean).

# --- MHT entries for other top-level files on the disc ------------------
# Ch. 5.2 Management Header Records can address content two ways: a local
# `dsa` (this file, what unit 12 populates for entries 0/29), or a `name`
# referencing a *different* top-level file on the disc (INDEXDAT.KWI,
# HWMAP.KWI, ...) -- those other files' own work packages, not WP1's.
# `container`'s check compares the whole 2048-byte MHT verbatim except an
# allowlisted dsa/size (any per-entry value is allowed -- see
# `parser/refdata/harness.json`'s `container_allowlist`), but *not* the
# `name` field, so `R`'s own name-addressed entries must be reproduced
# here too or that check fails on content this unit doesn't otherwise
# touch. Observed once directly from the mounted reference disc's MHT
# (read-only inspection, not a build-time disc read -- same "checked-in,
# derived once from R" status as `grid.json`/`mht29_frame.bin`, just not
# routed through unit 01's refdata files since this module's owned paths
# don't include refdata generation; see this unit's report).
MHT_OTHER_FILE_NAMES: dict[int, str] = {
    2: "INDEXDAT.KWI",
    18: "HWMAP.KWI",
    25: "DICVCE56.KWI",
    26: "KGRPDAT.KWI",
    30: "PCT2MNG.KWI",
    34: "COUNTRY.KWI",
}
# Entries 0-47 default-absent as (0xFFFFFFFF, 0); entries 48-112 as
# (0, 0) -- both conventions observed on `R` (dsa/size differences are
# allowlisted regardless, but replicating this costs nothing).
MHT_LOW_ABSENT_LIMIT = 48


@dataclass
class LevelBuild:
    """One level's already-encoded content, ready for `build_alldata_kwi()` to
    place into the reference's blockset/block structure for that level.

    ``table`` is a `kiwiw.frame_table.FrameTable` holding the level's type-0
    *and* divided frames as numpy rows over the encode workers' spill files
    (E2's output, in canonical stream order). ``None`` (the default) is a
    level with no content: it still gets its LMR and empty BSMR entries.
    """
    level: int
    table: object = None


def _level_dims(grid: ReferenceGrid, level: int) -> dict:
    lvl = grid._level_dict(level)
    return dict(
        nbs_lat=1 + lvl["n_blocksets_lat"], nbs_lng=1 + lvl["n_blocksets_lng"],
        nbl_lat=1 + lvl["n_blocks_lat"], nbl_lng=1 + lvl["n_blocks_lng"],
        npc_lat=1 + lvl["n_parcels_lat"][0], npc_lng=1 + lvl["n_parcels_lng"][0],
    )


def _locate(ix: int, iy: int, d: dict) -> tuple[int, int, int, int]:
    """Global cell (ix, iy) -> (blockset_index, block_index, local_ix,
    local_iy), using the same row-major (lat outer, lon inner) indexing
    `_block_base_bounds()`/`_walk_tree()` already establish for the
    read side (`load_region()`)."""
    bsx, rx = divmod(ix, d["nbl_lng"] * d["npc_lng"])
    blx, local_ix = divmod(rx, d["npc_lng"])
    bsy, ry = divmod(iy, d["nbl_lat"] * d["npc_lat"])
    bly, local_iy = divmod(ry, d["npc_lat"])
    blockset_index = bsy * d["nbs_lng"] + bsx
    block_index = bly * d["nbl_lng"] + blx
    return blockset_index, block_index, local_ix, local_iy


@dataclass
class AssembledFile:
    """Result of an assembly: file size and sha256."""
    size: int
    sha256: str


def _write_indexed(lay, fixed_regions, simple_blocks, out_path: str, total: int,
                   logical_sz: int) -> "AssembledFile":
    """Indexed path writer: C frame copy across threads into a sparse file, then
    fixed regions / block records, then the sha256."""
    from . import cenc as _cenc
    lib = _cenc.lib()
    if lib is None:
        raise RuntimeError("indexed assembly needs the C helpers (the C extension failed to load)")
    threads = max(1, min(os.cpu_count() or 1, 16))
    fd = os.open(out_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.ftruncate(fd, total)
        lay.write_frames(lib, fd, threads)
        for off, data in fixed_regions:
            mv, p = memoryview(data), 0
            while p < len(mv):
                p += os.pwrite(fd, mv[p:], off + p)
        for offs, arr in simple_blocks:
            r = lib.kw_write_rows(fd, len(offs), offs.ctypes.data, arr.ctypes.data,
                                  arr.shape[1], arr.shape[1])
            if r:
                raise OSError("block record write failed")
    finally:
        os.close(fd)
    digest = hashlib.sha256()
    with open(out_path, "rb", buffering=0) as fh:
        buf = bytearray(1 << 24)
        while n := fh.readinto(buf):
            digest.update(memoryview(buf)[:n])
    return AssembledFile(size=total, sha256=digest.hexdigest())


def build_alldata_kwi(
    levels: dict[int, "LevelBuild"],
    grid: ReferenceGrid,
    *,
    disk_title: str,
    out_path: str | None = None,
    sector_sz: int = 2048,
    logical_sz: int = 32,
) -> "AssembledFile":
    """Assemble a whole-of-coverage ALLDATA.KWI: the reference's own
    per-level LMR/BSMR/BMT shape (`grid`), the record-29 copy-through
    frame at its reference location, and `levels`' encoded parcel content
    placed into that structure.

    `levels` need not cover every reference level (tests build a 2-level
    file); whichever levels are given get one LMR each and only the
    `grid.json` blocksets belonging to those levels are emitted (so BSMR
    entries never dangle a reference to a level with no LMR). The real
    7-level build (`build_alldata.py`) passes all seven, which reproduces
    the reference's full 601-entry BSMR array.

    Each level's `LevelBuild.table` (a `kiwiw.frame_table.FrameTable`) carries
    both its type-0 frames and its divided-parcel (type 1/2) frames from E2
    (`_e2.c`). A divided parent's own ``ParcelMapInfoEntry`` gets ``size=0``
    and a [D]-encoded (halved) in-buffer offset to a nested
    ``ParcelMgmtRecord`` (Ch.6 divided/integrated-parcel subrecord) written
    into the *same* block buffer, right after that block's own root record;
    every sub-frame becomes its own leaf, sector-addressed exactly like a
    type-0 parcel's frame. Frames are copied by C from the workers' spill
    files straight into `out_path` (required); an `AssembledFile` (size,
    sha256) is returned.
    """
    from . import volume as _vol
    from . import volume_writer as _vw
    from .model import (
        BlockSetMgmtRecord as _BSMR,
        VolumeHeader as _VH,
    )

    ref = grid.data
    cov = ref["coverage"]
    coverage = BoundingBox(lat_lo=cov["lat_lo"], lat_hi=cov["lat_hi"],
                            lon_lo=cov["lon_lo"], lon_hi=cov["lon_hi"])

    lmr_size = ref["pdmdh"]["lmr_size"]          # 170 -- base 40 + 2 + 3*(16+32+16)
    bsmr_size_bytes = _vol.BSMR_SIZE             # 10
    bmt_entry_size = _vol.BMT_SIZE               # 6
    bmr_sz = bmt_entry_size // 2                 # 3 (stored halved)

    dims = {lvl: _level_dims(grid, lvl) for lvl in levels}
    lmrs = [grid.to_level_mgmt_record(lvl) for lvl in levels]

    blockset_specs = [b for b in ref["blocksets"] if b["level"] in levels]

    # Each LMR's own `bsmr_offset` is not a shared constant -- it is the
    # byte offset (from the PDMDH's own start) of *that level's* first
    # slice within the one shared, level-ordered BSMR array (confirmed
    # directly against `grid.json`: level 12's bsmr_offset is
    # `30 + 7*170 = 1220` -- the array's start -- and each subsequent
    # level's offset is the previous level's plus its own blockset count
    # times `bsmr_size`). Reproduce that here from *this build's* own
    # `blockset_specs` ordering/subset rather than trusting the raw
    # 7-level value `to_level_mgmt_record()` returns, which is only
    # correct when `levels` is the full 7-level set built in `grid.json`
    # order (true for the real build, not for a subset test).
    import dataclasses as _dc
    bsmr_table_offset = 30 + lmr_size * len(lmrs)
    level_bsmr_start: dict[int, int] = {}
    running = bsmr_table_offset
    for spec in blockset_specs:
        if spec["level"] not in level_bsmr_start:
            level_bsmr_start[spec["level"]] = running
        running += bsmr_size_bytes
    lmrs = [_dc.replace(lmr, bsmr_offset=level_bsmr_start[lmr.level]) for lmr in lmrs]
    for lmr in lmrs:
        got = len(_vw.write_lmr(lmr, lmr_size))
        if got != lmr_size:
            raise ValueError(
                f"level {lmr.level}: to_level_mgmt_record() produced a "
                f"{got}-byte LMR, pdmdh declares lmr_size={lmr_size}")
    lmr_by_level = {lmr.level: lmr for lmr in lmrs}

    if not any(lb.table is not None for lb in levels.values()):
        raise ValueError("no frames to assemble (every level's FrameTable is absent)")
    if out_path is None:
        raise ValueError("build_alldata_kwi needs out_path (frames are copied by C into the file)")
    from .frame_table import IndexedLayout, locate_np
    lay = IndexedLayout(levels, dims, lmr_by_level, sector_sz, logical_sz, locate_np,
                        lambda slots: 4 + bmt_entry_size * slots)
    # has_bmt is content-driven, not copied from grid.json's own boolean:
    # the contract is "BMTs for every non-empty block" / "empty ones point at
    # empty BMTs" -- i.e. *this build's* emptiness, not R's. `grid.json`'s
    # per-blockset markers reflect R's own Australia-wide OSM coverage, which a
    # partial build (e.g. --fixture perth) will not reproduce; the bmt_offset/
    # bmt_size fields this changes are exactly the ones `container_allowlist`
    # marks as build-specific (`bsmr_bmt_offset`, `bsmr_bmt_size`), so a
    # full-coverage build naturally converges to R's own has_bmt pattern.
    has_bmt = lay.present_blocksets

    # ---- fixed-size regions ---------------------------------------------
    datavol_offset = 0
    mht_offset = _vol.DATAVOL_SIZE                       # 2048
    record29_offset = _vol.DATAVOL_SIZE + _vol.MHT_SIZE   # 4096, matches R
    record29_frame = grid.mht29_frame_bytes()
    if len(record29_frame) != 2048:
        raise ValueError(f"mht29_frame_bytes() is {len(record29_frame)} bytes, expected 2048")
    pdmdh_offset = record29_offset + len(record29_frame)  # 6144, matches R

    # ---- PDMDH header + LMR table + BSMR table sizes ---------------------
    # (bsmr_table_offset computed above, alongside the per-level bsmr_offset fixup)
    bmt_cursor = bsmr_table_offset + bsmr_size_bytes * len(blockset_specs)

    blocksets: list[_BSMR] = []
    bmt_tables: list["_vol.BmtTable"] = []
    bmt_for_ordinal: dict[tuple[int, int], int] = {}   # (level, blockset_index) -> ordinal
    for ordinal, spec in enumerate(blockset_specs):
        level, bsidx = spec["level"], spec["blockset_index"]
        if (level, bsidx) in has_bmt:
            d = dims[level]
            n_blocks = d["nbl_lat"] * d["nbl_lng"]
            table = _vol.BmtTable(blockset_ordinal=ordinal, offset=bmt_cursor,
                                   entries=[_vol.BmtEntry(dsa=NO_DATA_DSA, size=0)
                                            for _ in range(n_blocks)])
            bmt_tables.append(table)
            bmt_for_ordinal[(level, bsidx)] = len(bmt_tables) - 1
            bmt_cursor += n_blocks * bmt_entry_size
            blocksets.append(_BSMR(level=level, blockset_index=bsidx,
                                    bmt_offset=table.offset, bmt_size=n_blocks * bmt_entry_size))
        else:
            blocksets.append(_BSMR(level=level, blockset_index=bsidx,
                                    bmt_offset=EMPTY_BMT_OFFSET, bmt_size=EMPTY_BMT_SIZE))

    pdmdh_record_size = bmt_cursor
    pdmdh_total_size = align_up(pdmdh_record_size, logical_sz)

    # ---- place block buffers, then map frames ----------------------------
    cursor = pdmdh_offset + pdmdh_total_size
    idx_simple: list = []
    lay.place(cursor)
    cursor = lay.total_size
    nb_bl = {lvl: dims[lvl]["nbl_lat"] * dims[lvl]["nbl_lng"] for lvl in dims}
    for b in range(lay.n_blocks):
        level = int(lay.blk_lvl[b])
        bsidx, blidx = divmod(int(lay.blk_key[b]), nb_bl[level])
        ordinal = bmt_for_ordinal[(level, bsidx)]
        bmt_tables[ordinal].entries[blidx] = _vol.BmtEntry(
            dsa=int(lay.block_dsa[b]), size=int(lay.block_size[b]))
    for lvl in sorted({int(v) for v in lay.blk_lvl}):
        n_slots = dims[lvl]["npc_lat"] * dims[lvl]["npc_lng"]
        t_simple = align_up(4 + bmt_entry_size * n_slots, logical_sz)
        sel, arr = lay.simple_block_rows(lvl, 4 + bmt_entry_size * n_slots, t_simple)
        if len(sel):
            idx_simple.append((np.ascontiguousarray(lay.block_off[sel].astype(np.uint64)), arr))
    idx_simple.extend(lay.divided_block_rows())

    total_file_size = cursor

    pdmdh = _vol.Pdmdh(
        coverage=coverage,
        lmr_size=lmr_size,
        bsmr_size=bsmr_size_bytes // 2,   # raw on-disk field, not sws()'d (see parse_pdmdh)
        bmr_size=bmr_sz,
        n_lmr=len(lmrs),
        n_bsmr=len(blocksets),
        levels=lmrs,
        blocksets=blocksets,
        bsmr_table_offset=bsmr_table_offset,
        bmt_table_base=0,
        record_size=pdmdh_record_size,
        total_size=pdmdh_total_size,
        header_gap_hex="00" * 6,
        bmt_tables=bmt_tables,
        trailing_padding_hex="00" * (pdmdh_total_size - pdmdh_record_size),
    )

    # ---- Volume Header ----------------------------------------------------
    # Mids / maker-defined fields / contents flags / background flags are
    # non-zero, content-independent hardware/edition metadata on `R` (not
    # derived from map content, so treating them as copy-through is
    # consistent with target-disc.md Decision 3) -- observed once directly
    # from the mounted reference disc (see this unit's report). Only the
    # four container_allowlist-covered strings vary per build.
    _r_mid = _vol.Mid(lat=34.997638888888886, lon=137.00878472222223,
                       lat_exponent=0, lon_exponent=0, floor=0, reserved=0, date=1826)
    extras = _vol.VolumeHeaderExtras(
        mids=[_r_mid, _r_mid, _r_mid],
        maker_defined_hex=[
            "414641553a322e36342c414741553a322e36340a0000000000000000000000"
            "000000000000000000000000000000000000000000",
            "0f613c003c357d00000000520000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000",
            "0000000000000000000000000000000000000000",
        ],
        contents_word0_low=0,
        contents_words_1_3=[0, 0, 0],
        coverage_exponents=[0, 0, 0, 0],
        background_low=0,
        reserved_478_hex="00" * 14,
        level_mgmt_info_hex="00" * 256,
        reserved_748_hex="00" * 1300,
    )
    hdr = _VH(
        format_version="KIWI-W SYNTHETIC 001",
        data_version="SYNTHETIC",
        disk_title=disk_title,
        media_version="001",
        system_specific_id="AFAU:2.64,AGAU:2.64\n",
        data_author_id="\x0fa<",
        system_id="",
        contents_main_map=True,
        contents_route_planning=True,
        contents_index_data=True,
        coverage=coverage,
        logical_sector_size=logical_sz,
        sector_size=sector_sz,
        background_in_map_is_sea=False,
        background_out_of_map_is_sea=True,
    )

    # ---- Management Header Table --------------------------------------
    mht_entries = []
    for i in range(_vol.MHT_RECORD_COUNT):
        if i < MHT_LOW_ABSENT_LIMIT:
            dsa, size = NO_DATA_DSA, 0
        else:
            dsa, size = 0, 0
        mht_entries.append(_vol.MhrEntry(index=i, dsa=dsa, size=size,
                                          name=MHT_OTHER_FILE_NAMES.get(i, "")))
    mht_entries[0].dsa = encode_sector_addr(pdmdh_offset, sector_sz, logical_sz)
    mht_entries[0].size = pdmdh_total_size // logical_sz
    mht_entries[29].dsa = encode_sector_addr(record29_offset, sector_sz, logical_sz)
    mht_entries[29].size = len(record29_frame) // logical_sz
    mht = _vol.ManagementHeaderTable(
        entries=mht_entries,
        tail_hex="00" * (_vol.MHT_SIZE - _vol.MHT_RECORD_COUNT * _vol.MHR_SIZE),
    )

    # ---- write everything ---------------------------------------------
    # Small fixed regions are in memory; the frames and block records are
    # copied / written by C (`_write_indexed`).
    fixed_regions: list[tuple[int, bytes]] = [
        (datavol_offset, _vw.write_volume_header(hdr, extras)),
        (mht_offset, _vw.write_management_header_table(mht)),
        (record29_offset, record29_frame),
        (pdmdh_offset, _vw.write_pdmdh(pdmdh)),
    ]
    return _write_indexed(lay, fixed_regions, idx_simple, out_path, total_file_size,
                          logical_sz)
