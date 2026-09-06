"""Reference profile: a census of the reference disc (`R`), used by the
`vocab`/`envelope`/`mfde` checks to judge a generated disc against the real
disc's own observed vocabulary, size/count envelopes and mfde/nregion
encoding -- see `docs/design/target-disc.md` ("Evaluation: the offline
oracle": "Same vocabulary", "Profile envelope") and this plan's "Vocabulary"
/ "Name records" contract bullets.

`build_profile()` streams `walk.iter_parcels()` exactly once (plus one cheap
pass over the already-in-memory PDMDH for block counts) -- nothing decoded
is retained past the parcel being folded into the running per-level
histograms, so this scales to the country-scale reference disc the same way
`walk.iter_parcels()` itself does.

Schema note: `profile["mfde"]["absent"]` (top-level, not per-level) is a
pre-existing contract from unit 02's `harness/checks/decode.py`
(`_mfde_absent_value()`), landed before this unit and left untouched here --
`build_profile()` populates it from the single absent-slot value observed
across the whole census (the refinement note recorded exactly one:
`(0xFFFFFFFF, 0)`). The per-level, per-entry-index mfde detail this unit's
own `checks/mfde.py` needs lives under `levels.<level>.mfde` instead.
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk
from kiwiw.bitutils import sws

NO_DATA_DSA = 0xFFFFFFFF

# RoadLink boolean-ish attributes censused per level, keyed by the same
# attribute name `kiwiw.road.decode_road_frame()` sets on `RoadLink`.
_LINK_FLAG_ATTRS = [
    "altitude_flag", "route_type_guidance_flag", "route_planning_tag",
    "link_id_flag", "selected_link_flag", "toll_flag", "route_number_flag",
    "infra_link_flag", "link_id_number_flag", "pseudo3d_updown",
]


def _percentile95(sorted_vals: list) -> float:
    if not sorted_vals:
        return 0.0
    idx = int(round(0.95 * (len(sorted_vals) - 1)))
    return sorted_vals[idx]


def _counter_to_dict(c: Counter) -> dict:
    return {str(k): v for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))}


class _LevelAccumulator:
    def __init__(self) -> None:
        self.parcel_count_by_type: Counter = Counter()
        self.mapframe_sizes: list = []
        self.frame_kind_bytes: Counter = Counter()  # road/background/name/ext_in_buffer/tail
        self.frame_kind_max_bytes: dict = {
            "road": 0, "background": 0, "name": 0, "ext_in_buffer": 0,
        }
        self.road_link_count = 0
        self.road_node_count = 0
        self.road_type_hist: Counter = Counter()
        self.display_class_hist: Counter = Counter()
        self.link_flag_hists: dict = {attr: Counter() for attr in _LINK_FLAG_ATTRS}
        self.node_oneway_hist: Counter = Counter()
        self.bg_shape_count = 0
        self.bg_type_code_hist: Counter = Counter()
        self.bg_shape_class_hist: Counter = Counter()
        self.bg_mult_const_hist: Counter = Counter()
        self.bg_max_n_coords = 0
        self.name_record_count = 0
        self.name_string_type_hist: Counter = Counter()
        self.name_type_code_hist: Counter = Counter()
        self.name_priority_hist: Counter = Counter()
        self.name_max_text_length = 0
        self.mfde_entry_count_hist: Counter = Counter()
        # entry index -> Counter({"absent": n, "in_buffer": n, "out_of_buffer": n})
        self.mfde_index_class_hist: dict = {}
        self.mfde_absent_values: Counter = Counter()  # observed (off, size) absent pairs
        self.nregion_hist: Counter = Counter()
        self.region_list_hex_hist: Counter = Counter()
        self.tail_length_hist: Counter = Counter()

    def add_leaf(self, wp) -> None:
        self.parcel_count_by_type[wp.parcel_type] += 1
        self.mapframe_sizes.append(wp.length)

        parcel = wp.parcel
        if parcel is None or parcel.frame is None:
            return  # decode error on this leaf; block/leaf error checks own this, not the census
        frame = parcel.frame

        # --- mfde table: entry count, absent-slot value, per-index class ---
        self.mfde_entry_count_hist[len(frame.mfde_raw)] += 1
        frame_size = frame.frame_size
        for idx, (raw_off, raw_size) in enumerate(frame.mfde_raw):
            cls_counter = self.mfde_index_class_hist.setdefault(idx, Counter())
            if raw_off == NO_DATA_DSA:
                cls_counter["absent"] += 1
                self.mfde_absent_values[(raw_off, raw_size)] += 1
            else:
                off_v = sws(raw_off)
                if off_v < frame_size:
                    cls_counter["in_buffer"] += 1
                else:
                    cls_counter["out_of_buffer"] += 1

        # --- frame-kind byte totals, from the mfde table's own declared
        # sizes (independent of whether the sub-frame itself decoded) ---
        kind_by_index = {0: "road", 1: "background", 2: "name"}
        for idx, (raw_off, raw_size) in enumerate(frame.mfde_raw):
            if raw_off == NO_DATA_DSA:
                continue
            size_v = sws(raw_size)
            if idx in kind_by_index:
                kind = kind_by_index[idx]
                self.frame_kind_bytes[kind] += size_v
                self.frame_kind_max_bytes[kind] = max(self.frame_kind_max_bytes[kind], size_v)
            elif idx >= 3:
                off_v = sws(raw_off)
                if off_v < frame_size:
                    self.frame_kind_bytes["ext_in_buffer"] += size_v
                    self.frame_kind_max_bytes["ext_in_buffer"] = max(
                        self.frame_kind_max_bytes["ext_in_buffer"], size_v)
        self.frame_kind_bytes["tail"] += len(frame.tail_raw)

        # --- nregion / region-list bytes / tail length ---
        self.nregion_hist[frame.header.nregion] += 1
        self.region_list_hex_hist[frame.region_list_raw.hex()] += 1
        self.tail_length_hist[len(frame.tail_raw)] += 1

        # --- road ---
        if parcel.road is not None:
            for link in parcel.road.links:
                self.road_link_count += 1
                self.road_node_count += len(link.nodes)
                self.road_type_hist[link.road_type] += 1
                self.display_class_hist[link.display_class] += 1
                for attr in _LINK_FLAG_ATTRS:
                    self.link_flag_hists[attr][getattr(link, attr)] += 1
                for node in link.nodes:
                    self.node_oneway_hist[node.oneway] += 1

        # --- background ---
        if parcel.background is not None:
            for shape in parcel.background.shapes:
                self.bg_shape_count += 1
                self.bg_type_code_hist[shape.type_code] += 1
                self.bg_shape_class_hist[shape.shape_class] += 1
                self.bg_mult_const_hist[shape.mult_const] += 1
                self.bg_max_n_coords = max(self.bg_max_n_coords, shape.n_coords)

        # --- name ---
        if parcel.name is not None:
            for rec in parcel.name.records:
                self.name_record_count += 1
                self.name_string_type_hist[rec.string_type] += 1
                self.name_type_code_hist[rec.type_code] += 1
                self.name_priority_hist[rec.priority] += 1
                self.name_max_text_length = max(self.name_max_text_length, len(rec.text))

    def to_dict(self) -> dict:
        sizes = sorted(self.mapframe_sizes)
        n = len(sizes)
        mean = (sum(sizes) / n) if n else 0.0
        link_flag_hist_out = {
            attr: _counter_to_dict(c) for attr, c in self.link_flag_hists.items()
        }
        link_flag_hist_out["oneway"] = _counter_to_dict(self.node_oneway_hist)
        mfde_index_class_out = {
            str(idx): _counter_to_dict(c) for idx, c in sorted(self.mfde_index_class_hist.items())
        }
        return {
            "parcel_count_by_type": _counter_to_dict(self.parcel_count_by_type),
            "block_count": self.block_count,
            "occupied_block_count": self.occupied_block_count,
            "mapframe_size": {
                "min": sizes[0] if n else 0,
                "max": sizes[-1] if n else 0,
                "mean": mean,
                "p95": _percentile95(sizes),
                "byte_total": sum(sizes),
            },
            "frame_kind_bytes": _counter_to_dict(self.frame_kind_bytes),
            "frame_kind_max_bytes": dict(self.frame_kind_max_bytes),
            "road": {
                "link_count": self.road_link_count,
                "node_count": self.road_node_count,
                "road_type_hist": _counter_to_dict(self.road_type_hist),
                "display_class_hist": _counter_to_dict(self.display_class_hist),
                "link_flag_hists": link_flag_hist_out,
            },
            "background": {
                "shape_count": self.bg_shape_count,
                "type_code_hist": _counter_to_dict(self.bg_type_code_hist),
                "shape_class_hist": _counter_to_dict(self.bg_shape_class_hist),
                "mult_const_hist": _counter_to_dict(self.bg_mult_const_hist),
                "max_n_coords": self.bg_max_n_coords,
            },
            "name": {
                "record_count": self.name_record_count,
                "string_type_hist": _counter_to_dict(self.name_string_type_hist),
                "type_code_hist": _counter_to_dict(self.name_type_code_hist),
                "priority_hist": _counter_to_dict(self.name_priority_hist),
                "max_text_length": self.name_max_text_length,
            },
            "mfde": {
                "entry_count_hist": _counter_to_dict(self.mfde_entry_count_hist),
                "per_entry_index_class_hist": mfde_index_class_out,
                "absent_values_observed": _counter_to_dict(
                    Counter({f"{off},{size}": n for (off, size), n in self.mfde_absent_values.items()})
                ),
            },
            "nregion_hist": _counter_to_dict(self.nregion_hist),
            "region_list_hex_hist": _counter_to_dict(self.region_list_hex_hist),
            "tail_length_hist": _counter_to_dict(self.tail_length_hist),
        }


def _profiled_at_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent), timeout=10, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def build_profile(alldata_path: str) -> dict:
    """Census `alldata_path`'s `ALLDATA.KWI` into the reference profile
    dict described in this module's docstring. Streams `walk.iter_parcels()`
    once; per-level accumulators are the only retained state."""
    container = walk.read_container(alldata_path)
    hdr, pdmdh, mht = container.hdr, container.pdmdh, container.mht
    logical_sz = hdr.logical_sector_size

    accs: dict = {}

    def acc(level: int) -> _LevelAccumulator:
        a = accs.get(level)
        if a is None:
            a = _LevelAccumulator()
            accs[level] = a
        return a

    # --- block / occupied-block counts, per level: direct from the
    # already-fully-parsed PDMDH (no need to walk into leaves for this). ---
    block_counts: dict = {}
    occupied_counts: dict = {}
    for lmr in pdmdh.levels:
        level = lmr.level
        block_counts.setdefault(level, 0)
        occupied_counts.setdefault(level, 0)
        for bs_ordinal, bs in enumerate(pdmdh.blocksets):
            if bs.level != level:
                continue
            bmt_table = next(
                (t for t in pdmdh.bmt_tables if t.blockset_ordinal == bs_ordinal), None)
            if bmt_table is None:
                continue
            block_counts[level] += len(bmt_table.entries)
            occupied_counts[level] += sum(
                1 for e in bmt_table.entries if e.dsa != NO_DATA_DSA and e.size)

    blocks_bytes_total = 0
    for table in pdmdh.bmt_tables:
        for entry in table.entries:
            if entry.dsa != NO_DATA_DSA and entry.size:
                blocks_bytes_total += entry.size * logical_sz

    # --- one streaming pass over every leaf Map Frame ---
    mapframes_bytes_total = 0
    for wp in walk.iter_parcels(alldata_path):
        if wp.leaf_path == ():
            continue  # whole-block parse failure; not this census's concern
        acc(wp.level).add_leaf(wp)
        mapframes_bytes_total += wp.length

    levels_out = {}
    global_absent_values: Counter = Counter()
    for level, a in accs.items():
        a.block_count = block_counts.get(level, 0)
        a.occupied_block_count = occupied_counts.get(level, 0)
        levels_out[str(level)] = a.to_dict()
        global_absent_values.update(a.mfde_absent_values)

    # --- whole-file byte total by layer, via the MHT ---
    pdmdh_entry = mht.entries[0]
    pdmdh_blob_bytes = pdmdh_entry.size * logical_sz
    map_layer_bytes = pdmdh_blob_bytes + blocks_bytes_total + mapframes_bytes_total

    other_mht_bytes: dict = {}
    for entry in mht.entries:
        if entry.index == 0:
            continue  # PDMDH -- part of the map layer total above
        if entry.dsa == NO_DATA_DSA:
            continue  # sentinel: this index carries no content on R
        if entry.name:
            other_mht_bytes[str(entry.index)] = {"file_based": True, "name": entry.name}
        else:
            other_mht_bytes[str(entry.index)] = entry.size * logical_sz

    # Global mfde absent-slot value (schema pre-existing per
    # `harness/checks/decode.py`'s `_mfde_absent_value()`): the single most
    # common (offset, size) absent pair observed across the whole census.
    if global_absent_values:
        (absent_off, absent_size), _count = global_absent_values.most_common(1)[0]
        absent_value = [absent_off, absent_size]
    else:
        absent_value = [NO_DATA_DSA, 0]

    return {
        "source": {
            "disk_title": hdr.disk_title,
            "data_version": hdr.data_version,
        },
        "profiled_at_commit": _profiled_at_commit(),
        "mfde": {"absent": absent_value},
        "byte_totals_by_layer": {
            "map": {
                "pdmdh_blob_bytes": pdmdh_blob_bytes,
                "blocks_bytes": blocks_bytes_total,
                "mapframes_bytes": mapframes_bytes_total,
                "total_bytes": map_layer_bytes,
            },
            "other_mht_entries": other_mht_bytes,
        },
        "levels": levels_out,
    }


# ---------------------------------------------------------------------
# Memoised census of the *generated* disc, `G`, for the vocab/envelope/mfde
# checks: they each need the same full per-level census this module already
# knows how to build (same shape as the reference profile), so they reuse
# `build_profile()` on `ctx.generated` rather than reimplementing a second
# walk. Cached per path so vocab+envelope+mfde run together (as the
# kickoff self-check does) only walk `G` once.
# ---------------------------------------------------------------------
_generated_profile_cache: dict = {}


def generated_profile(path: str) -> dict:
    if path not in _generated_profile_cache:
        _generated_profile_cache[path] = build_profile(path)
    return _generated_profile_cache[path]

