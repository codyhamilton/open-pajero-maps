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

Out of scope (see docs/00-overview.md's decision log and this module's
callers for the full reasoning, not repeated here): the two vendor ext-
frame types (0xAF100100/0xAF100300) are not synthesized -- when a Map
Frame's mfde table has an in-buffer "Extended Data Frame" entry, its raw
bytes are carried through unchanged (already true of `MapFrame.ext_frame_raw`,
untouched by this module); anything living in the separate management
frame at file offset 4096..6144 (a different, out-of-scope chapter's
layer -- likely route planning, see docs/phases/02-roundtrip.md) is never
referenced here at all -- the de novo layout places the PDMDH blob
directly after the Management Header Table instead, since reproducing
that gap's content is out of scope and not needed for the layout question
this module answers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import volume, volume_writer, parcel_writer
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


def _walk_tree(rec: ParcelMgmtRecord, bounds: BoundingBox, lmr, leaves: list[tuple]) -> None:
    gn_lat = 1 + lmr.n_parcels_lat[rec.parcel_type]
    gn_lng = 1 + lmr.n_parcels_lng[rec.parcel_type]
    for idx, entry in enumerate(rec.entries):
        if entry.dsa == NO_DATA_DSA:
            continue
        child_bounds = _narrow_bounds(bounds, gn_lat, gn_lng, idx)
        if entry.subrecord is not None:
            _walk_tree(entry.subrecord, child_bounds, lmr, leaves)
        elif entry.size:
            leaves.append((entry, child_bounds))


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

                for entry, bounds in raw_leaves:
                    moff = volume.getsector(entry.dsa, hdr.sector_size, hdr.logical_sector_size)
                    mlen = entry.size * hdr.logical_sector_size
                    fh.seek(moff)
                    mapdata = fh.read(mlen)
                    loc = MeshLocation(level=level, parcel_type=0, blockset_index=bsidx,
                                        block_index=entry_index, parcel_index=0, bounds=bounds,
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
# Synthetic ALLDATA.KWI builder
# ---------------------------------------------------------------------

from dataclasses import dataclass as _dataclass


@_dataclass
class SynthParcel:
    """One synthetic parcel ready for assembly into an ALLDATA.KWI file.

    ``ix`` / ``iy`` are the column / row indices within the parcel grid
    (0-based, matching the TileGrid used when the map frame bytes were
    encoded).  ``bounds`` must be the same BoundingBox used during encoding
    so that pixel coordinates decode back to the correct lat/lon values.
    ``map_frame_bytes`` is the output of ``synth.build_map_frame_bytes()``.
    """
    ix: int
    iy: int
    bounds: BoundingBox
    map_frame_bytes: bytes


def build_alldata_kwi(
    parcels: list[SynthParcel],
    coverage: BoundingBox,
    level: int,
    grid_nx: int,
    grid_ny: int,
    sector_sz: int = 2048,
    logical_sz: int = 32,
) -> bytes:
    """Assemble a minimal but parseable ALLDATA.KWI from synthetic parcels.

    Produces a file with:
    - a synthetic Data Volume header (2048 bytes)
    - a synthetic Management Header Table (2048 bytes)
    - a synthetic PDMDH with one LMR / one BSMR / one BMT (one block)
    - one block buffer (a flat Parcel Management Record)
    - map frame bytes for each provided parcel

    The file is readable by ``alldata_writer.load_region()`` for
    verification.

    Parameters
    ----------
    parcels:
        List of encoded parcels.  Parcels outside (grid_nx, grid_ny) raise.
    coverage:
        Geographic bounding box stored in the PDMDH and volume header.
    level:
        Map level number (0, 2, 4, 6, 8 on the real disc).
    grid_nx, grid_ny:
        Total parcel grid dimensions; determines the Parcel Management
        Record grid and the LMR n_parcels_* fields.
    sector_sz, logical_sz:
        Sector / logical-sector sizes (default: real disc values 2048/32).
    """
    import copy as _copy

    from . import volume as _vol
    from . import volume_writer as _vw
    from .model import (
        BlockSetMgmtRecord as _BSMR,
        LevelMgmtRecord as _LMR,
        ParcelMapInfoEntry as _PMI,
        ParcelMgmtRecord as _PMR,
    )

    _POISON = POISON

    # ---- helpers --------------------------------------------------------
    def _u16b(v: int) -> bytes:
        return bytes((v >> 8, v & 0xFF))

    def _u32b(v: int) -> bytes:
        return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))

    def _pad(data: bytes, granularity: int) -> bytes:
        """Pad ``data`` to a multiple of ``granularity`` bytes with zeros."""
        rem = len(data) % granularity
        return data + bytes(granularity - rem) if rem else data

    # ---- layout constants -----------------------------------------------
    datavol_offset = 0
    mht_offset     = _vol.DATAVOL_SIZE          # 2048
    pdmdh_offset   = _vol.DATAVOL_SIZE + _vol.MHT_SIZE  # 4096

    lmr_size = _vol.LMR_BASE_SIZE               # 40 bytes (no extended frame info)
    bsmr_size_bytes = _vol.BSMR_SIZE            # 10 bytes
    bmt_entry_size = _vol.BMT_SIZE              # 6 bytes (= 2 * bmr_sz where bmr_sz=3)
    bmr_sz = bmt_entry_size // 2               # 3 (stored halved)

    # PDMDH layout within its own buffer:
    #   [0..29]  : 30-byte PDMDH header
    #   [30..69] : 1 LMR (40 bytes)
    #   [70..79] : 1 BSMR (10 bytes)  -- bsmr_table_offset = 70
    #   [80..85] : 1 BMT entry (6 bytes)  -- bmt_offset_within_pdmdh = 80
    bsmr_table_offset = 30 + lmr_size          # = 70
    bmt_in_pdmdh      = bsmr_table_offset + bsmr_size_bytes  # = 80

    pdmdh_record_size = bmt_in_pdmdh + bmt_entry_size   # = 86
    pdmdh_total_size  = align_up(pdmdh_record_size, logical_sz)   # = 96
    pdmdh_logical     = pdmdh_total_size // logical_sz    # = 3

    # ---- block buffer ---------------------------------------------------
    n_entries = grid_nx * grid_ny
    block_data_size = 4 + n_entries * bmt_entry_size   # 4 + n*6
    block_total_size = align_up(block_data_size, logical_sz)
    block_logical    = block_total_size // logical_sz

    block_offset = pdmdh_offset + pdmdh_total_size     # byte offset in file

    # ---- map frame layout -----------------------------------------------
    # Each map frame is padded to logical_sz; allocate slots for all entries.
    # Entries with no parcel data get NO_DATA_DSA.
    frame_slot_bytes: dict[int, bytes] = {}  # flat_index -> padded frame bytes
    for sp in parcels:
        if not (0 <= sp.ix < grid_nx and 0 <= sp.iy < grid_ny):
            raise ValueError(
                f"SynthParcel ({sp.ix}, {sp.iy}) outside grid "
                f"{grid_nx}×{grid_ny}")
        flat = sp.iy * grid_nx + sp.ix
        frame_slot_bytes[flat] = _pad(sp.map_frame_bytes, logical_sz)

    # Assign file offsets to each occupied slot.
    frame_offsets: dict[int, int] = {}   # flat_index -> byte offset in file
    cursor = block_offset + block_total_size
    for idx in sorted(frame_slot_bytes):
        frame_offsets[idx] = cursor
        cursor += len(frame_slot_bytes[idx])

    total_file_size = cursor

    # ---- build Parcel Management Record entries -------------------------
    entries: list[_PMI] = []
    for flat in range(n_entries):
        if flat in frame_offsets:
            foff = frame_offsets[flat]
            fsz  = len(frame_slot_bytes[flat])
            dsa  = encode_sector_addr(foff, sector_sz, logical_sz)
            sz   = fsz // logical_sz
            entries.append(_PMI(dsa=dsa, size=sz))
        else:
            entries.append(_PMI(dsa=NO_DATA_DSA, size=0))

    # Tail = padding bytes beyond the record footprint inside the block buf.
    record_footprint = 4 + n_entries * bmt_entry_size   # = block_data_size
    tail_len = block_total_size - record_footprint
    root_pmr = _PMR(
        parcel_type=0,
        list_type=0,
        offset=0,
        entries=entries,
        header_gap_raw=b"\x00\x00",
        tail_raw=bytes(tail_len),
    )

    # ---- Pdmdh IR -------------------------------------------------------
    # BMT entry for the one block.
    block_dsa  = encode_sector_addr(block_offset, sector_sz, logical_sz)
    bmt_entry  = _vol.BmtEntry(dsa=block_dsa, size=block_logical)

    bmt_table = _vol.BmtTable(
        blockset_ordinal=0,
        offset=bmt_in_pdmdh,
        entries=[bmt_entry],
    )

    # BlockSetMgmtRecord.
    blockset = _BSMR(
        level=level,
        blockset_index=0,
        bmt_offset=bmt_in_pdmdh,   # sws-decoded: stored as bmt_in_pdmdh // 2
        bmt_size=bmt_entry_size,    # sws-decoded: 6 (stored as 3)
    )

    # LevelMgmtRecord (minimal, no extended frame-index tables).
    lmr = _LMR(
        level=level,
        upper_level=level,
        lower_level=level,
        n_basic_map=3,
        n_ext_map=0,
        n_basic_route=0,
        n_ext_route=0,
        display_flags=[0] * 5,
        n_blocksets_lat=0,
        n_blocksets_lng=0,
        n_blocks_lat=0,
        n_blocks_lng=0,
        n_parcels_lat=[grid_ny - 1, 0, 0, 0],
        n_parcels_lng=[grid_nx - 1, 0, 0, 0],
        bsmr_offset=bsmr_table_offset,   # = 70; stored as 35 in LMR
        node_record_size=6,              # = sws(3); arbitrary typical value
        grid_nx=grid_nx,
        grid_ny=grid_ny,
        n_road_frames=None,
        raw_tail_hex="",
    )

    lat_span = coverage.lat_hi - coverage.lat_lo
    lon_span = coverage.lon_hi - coverage.lon_lo   # assumes no anti-meridian wrap

    pdmdh = _vol.Pdmdh(
        coverage=coverage,
        lmr_size=lmr_size,
        bsmr_size=bsmr_size_bytes,
        bmr_size=bmr_sz,
        n_lmr=1,
        n_bsmr=1,
        levels=[lmr],
        blocksets=[blockset],
        bsmr_table_offset=bsmr_table_offset,
        bmt_table_base=0,
        record_size=pdmdh_record_size,
        total_size=pdmdh_total_size,
        header_gap_hex="00" * 6,
        bmt_tables=[bmt_table],
        trailing_padding_hex="00" * (pdmdh_total_size - pdmdh_record_size),
    )

    # ---- Volume Header --------------------------------------------------
    mid_zero = _vol.Mid(lat=0.0, lon=0.0, lat_exponent=0, lon_exponent=0,
                        floor=0, reserved=0, date=0)
    extras = _vol.VolumeHeaderExtras(
        mids=[mid_zero, mid_zero, mid_zero],
        maker_defined_hex=["00" * 52, "00" * 52, "00" * 20],
        contents_word0_low=0,
        contents_words_1_3=[0, 0, 0],
        coverage_exponents=[0, 0, 0, 0],
        background_low=0,
        reserved_478_hex="00" * 14,
        level_mgmt_info_hex="00" * 256,
        reserved_748_hex="00" * 1300,
    )
    from .model import VolumeHeader as _VH
    hdr = _VH(
        format_version="KIWI-W SYNTHETIC 001",
        data_version="SYNTHETIC",
        disk_title="OSM SYNTHETIC BUILD",
        media_version="001",
        system_specific_id="",
        data_author_id="",
        system_id="",
        contents_main_map=True,
        contents_route_planning=False,
        contents_index_data=False,
        coverage=coverage,
        logical_sector_size=logical_sz,
        sector_size=sector_sz,
        background_in_map_is_sea=False,
        background_out_of_map_is_sea=False,
    )

    # ---- Management Header Table ----------------------------------------
    mht_entries = [
        _vol.MhrEntry(index=i, dsa=0, size=0, name="")
        for i in range(_vol.MHT_RECORD_COUNT)
    ]
    mht_entries[0].dsa  = encode_sector_addr(pdmdh_offset, sector_sz, logical_sz)
    mht_entries[0].size = pdmdh_logical
    mht = _vol.ManagementHeaderTable(
        entries=mht_entries,
        tail_hex="00" * (_vol.MHT_SIZE - _vol.MHT_RECORD_COUNT * _vol.MHR_SIZE),
    )

    # ---- Assemble block buffer ------------------------------------------
    block_buf = bytearray([_POISON]) * block_total_size
    parcel_writer.write_parcel_mgmt_record(root_pmr, block_buf)

    # ---- Write everything into one buffer --------------------------------
    buf = bytearray(total_file_size)

    def _put_at(off: int, data: bytes) -> None:
        buf[off:off + len(data)] = data

    _put_at(datavol_offset, _vw.write_volume_header(hdr, extras))
    _put_at(mht_offset,     _vw.write_management_header_table(mht))
    _put_at(pdmdh_offset,   _vw.write_pdmdh(pdmdh))
    _put_at(block_offset,   bytes(block_buf))

    for idx, frame_bytes in frame_slot_bytes.items():
        _put_at(frame_offsets[idx], frame_bytes)

    return bytes(buf)
