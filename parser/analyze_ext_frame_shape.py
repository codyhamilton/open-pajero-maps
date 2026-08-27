#!/usr/bin/env python3
"""Dedicated "shape" analysis of the two functionally-unresolved Ch.10.5
vendor ext-frame Data Identification Codes: ``0xAF100100`` (62.1% of all
ext bytes, present in every region) and ``0xAF100300`` (37.7% of ext bytes,
level-8-only).

This does NOT attempt to resolve their semantic meaning (see
``docs/phases/01-format-analysis.md``'s "Ch.10.5/10.5.1 ext frame content
census" section for why that's judged out of reach from static evidence
alone). Its job is narrower and more mechanical: for each code, across
100% of the disc's 1,864 real regions (not a sample),

  1. find the fixed record/unit size (if any) that most cleanly divides
     every real payload with zero remainder;
  2. decompose one unit into candidate sub-fields and check whether
     sentinel/monotonic/range patterns land at consistent sub-offsets;
  3. correlate payload length (in bytes and in candidate-unit counts)
     against every already-decoded per-region quantity (node count, link
     count, boundary-node count, road-reference-table record count,
     region level, child-region count) and report exact fit percentages;
  4. for 0xAF100300 specifically, check whether its unit count lines up
     with any cross-region/boundary-link quantity relevant to the
     "escape link" contraction work in ``kiwiw/contraction.py`` /
     ``kiwiw/route_planning_writer.py``.

Kept (not scratch) per this project's convention for rerunnable analysis
scripts; does not modify the parser package or any other agent's files.

Usage:
    python3 parser/analyze_ext_frame_shape.py --alldata /path/to/ALLDATA.KWI
"""
from __future__ import annotations

import argparse
import collections
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from kiwiw.disc import AllData
from kiwiw.misc import DISC_STAMP_12B
from kiwiw.route_planning import (
    NO_DATA_DSA,
    parse_node_table,
    parse_region_frame,
    parse_road_reference_table,
    parse_rp_frame,
)
from kiwiw.volume import getsector

TARGET_CODES = {0xAF100100: "0xAF100100", 0xAF100300: "0xAF100300"}
CANDIDATE_UNITS = [2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32]


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "big")


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "big")


def load_regions(alldata_path: str):
    """Yield one dict per real region with every already-decoded
    per-region quantity we might correlate against, plus the raw bytes of
    any 0xAF100100 / 0xAF100300 ext payload found."""
    disc = AllData(alldata_path)
    rf = parse_region_frame(disc)
    real_regions = [r for r in rf.regions if not r.is_dummy]

    rows = []
    for rec in real_regions:
        lmr = next(l for l in rf.levels if l.level == rec.level)
        if rec.rp_dsa == NO_DATA_DSA or rec.rp_size_ls == 0:
            continue
        disc._fh.seek(getsector(rec.rp_dsa, disc.sector_sz, disc.logical_sz))
        buf = disc._fh.read(rec.rp_size_ls * disc.logical_sz)
        f = parse_rp_frame(buf, lmr.n_basic_rp_frames, lmr.n_ext_rp_frames)

        n_nodes = f.node_header.n_nodes if f.node_header else 0
        n_links = f.node_header.n_links if f.node_header else 0
        n_boundary_nodes = (
            sum(r.n_boundary_nodes for r in f.node_header.ranks)
            if f.node_header else 0
        )
        n_ranks = f.node_header.n_ranks if f.node_header else 0

        # Actual boundary-node count cross-checked against the Node Table
        # itself (is_boundary flag), not just the rank-header sum, and the
        # link records belonging to boundary nodes carry a region_number
        # field (Ch.10.7.1.1 item 8) -- i.e. count of distinct
        # (adjacent region) escape-link endpoints, the closest analogue
        # to "cross-region link structure" already decoded in this repo.
        n_boundary_nodes_actual = 0
        n_escape_links = 0
        road_ref_records = 0
        node_sub = f.sub("node")
        link_sub = f.sub("link")
        if node_sub and node_sub.offset != 0xFFFFFFFF and f.node_header:
            try:
                nodes = parse_node_table(buf, node_sub, f.node_header)
                n_boundary_nodes_actual = sum(1 for n in nodes if n.is_boundary)
                if link_sub and link_sub.offset != 0xFFFFFFFF:
                    from kiwiw.route_planning import parse_node_links
                    for n in nodes:
                        if n.is_boundary and n.n_link_records < 15:
                            n_escape_links += len(parse_node_links(buf, link_sub, n))
            except Exception:
                pass
        road_ref_sub = f.sub("road_ref")
        if road_ref_sub and road_ref_sub.offset != 0xFFFFFFFF and road_ref_sub.size:
            try:
                road_ref_records = len(parse_road_reference_table(buf, road_ref_sub))
            except Exception:
                pass

        ext_payloads = {}
        for s in f.ext:
            if s.size <= 0 or s.offset == 0xFFFFFFFF or s.offset + 16 > len(buf):
                continue
            dataid = u32(buf, s.offset + 12)
            if dataid in TARGET_CODES:
                payload = buf[s.offset + 16: s.offset + s.size]
                ext_payloads.setdefault(dataid, []).append(payload)

        rows.append(dict(
            level=rec.level, region_no=rec.region_no,
            n_nodes=n_nodes, n_links=n_links,
            n_boundary_nodes=n_boundary_nodes,
            n_boundary_nodes_actual=n_boundary_nodes_actual,
            n_escape_links=n_escape_links,
            n_ranks=n_ranks,
            n_child_regions=rec.n_child_regions,
            road_ref_records=road_ref_records,
            ext_payloads=ext_payloads,
        ))
    disc.close()
    return rows


def unit_fit_report(payloads: list[bytes], label: str) -> dict:
    """For a list of raw payloads (one per region occurrence of this data
    id), test every candidate unit size and report the % of occurrences
    that divide evenly. Returns the per-unit-size fit-percentage table
    plus the winning size."""
    n = len(payloads)
    fits = {}
    for u in CANDIDATE_UNITS:
        exact = sum(1 for p in payloads if len(p) % u == 0)
        fits[u] = exact / n if n else 0.0
    print(f"\n[{label}] Divisibility of raw payload length by candidate unit size "
          f"(n={n} occurrences, 100% of population):")
    for u in CANDIDATE_UNITS:
        print(f"  unit={u:3d} B: {100*fits[u]:6.2f}% exact")
    return fits


def preamble_adjusted_fit(payloads: list[bytes], preamble_bytes: int, label: str) -> dict:
    """Same as unit_fit_report but first strips a fixed preamble (e.g. the
    8-word / 16-byte constant header noted in the prior pass for
    0xAF100100) before testing divisibility of the remainder."""
    n = len(payloads)
    fits = {}
    usable = [p for p in payloads if len(p) >= preamble_bytes]
    for u in CANDIDATE_UNITS:
        exact = sum(1 for p in usable if (len(p) - preamble_bytes) % u == 0)
        fits[u] = exact / len(usable) if usable else 0.0
    print(f"\n[{label}] After stripping a {preamble_bytes}-byte preamble, divisibility "
          f"of the remainder by candidate unit size (n={len(usable)}/{n} payloads "
          f">= preamble size):")
    for u in CANDIDATE_UNITS:
        print(f"  unit={u:3d} B: {100*fits[u]:6.2f}% exact")
    return fits


def correlate(rows, ycol_fn, ycol_name, candidates: dict):
    """Report exact-match percentage and Pearson r for each named candidate
    x-quantity (a fn(row)->number) against ycol_fn(row), across all rows
    for which ycol_fn is not None."""
    pairs = []
    for r in rows:
        y = ycol_fn(r)
        if y is None:
            continue
        pairs.append((r, y))
    n = len(pairs)
    print(f"\nCorrelation of {ycol_name} against candidate quantities (n={n} regions):")
    for name, fn in candidates.items():
        xs, ys = [], []
        exact = 0
        for r, y in pairs:
            x = fn(r)
            if x is None:
                continue
            xs.append(x)
            ys.append(y)
            if x == y:
                exact += 1
        if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
            corr = float("nan")
        else:
            try:
                corr = statistics.correlation(xs, ys)
            except statistics.StatisticsError:
                corr = float("nan")
        pct_exact = 100 * exact / len(xs) if xs else 0.0
        print(f"  {name:28s}: n={len(xs):5d}  exact-match={pct_exact:6.2f}%  Pearson r={corr:6.3f}")


def analyze_af100100(rows):
    print("\n" + "=" * 78)
    print("0xAF100100 shape analysis")
    print("=" * 78)
    payloads = []
    per_region = []
    for r in rows:
        for p in r["ext_payloads"].get(0xAF100100, []):
            payloads.append(p)
            per_region.append((r, p))
    print(f"Total occurrences: {len(payloads)} (should be 1,864 -- one per real region)")

    unit_fit_report(payloads, "0xAF100100 raw")
    # Prior pass's structural read: constant-looking 8-word (16 B) preamble
    # before the sentinel-filled body.
    preamble_adjusted_fit(payloads, 16, "0xAF100100 minus 16B preamble")

    # Sentinel-offset check: does 0x7FFF land at consistent offsets mod
    # candidate unit sizes, or is it scattered uniformly (i.e. not
    # structured into fixed fields at all)?
    print("\n0x7FFF sentinel word-offset-mod-unit distribution (raw payload, "
          "16-bit-word-aligned scan; unit sizes tested in words):")
    for unit_words in [1, 2, 3, 4, 6, 8]:
        hist = collections.Counter()
        total = 0
        for p in payloads:
            nwords = len(p) // 2
            for wi in range(nwords):
                if u16(p, wi * 2) == 0x7FFF:
                    hist[wi % unit_words] += 1
                    total += 1
        if total == 0:
            continue
        dist = ", ".join(f"{k}:{100*v/total:.1f}%" for k, v in sorted(hist.items()))
        # A perfectly uniform/unstructured scatter would show ~1/unit_words
        # at each offset; a spiked distribution suggests real field
        # structure at that unit size.
        expected = 100 / unit_words
        maxdev = max(abs(100*v/total - expected) for v in hist.values())
        print(f"  unit={unit_words} words ({unit_words*2:2d} B): offsets={dist}  "
              f"(uniform-would-be {expected:.1f}% each; max deviation {maxdev:.1f} pts)")

    # First non-preamble, non-sentinel real 16-bit values: are they small
    # (index-like) or large/near-random (cost/distance-like)?
    real_vals = []
    for p in payloads:
        for wi in range(8, len(p) // 2):
            v = u16(p, wi * 2)
            if v not in (0x7FFF, 0x0000):
                real_vals.append(v)
    if real_vals:
        print(f"\nNon-sentinel, non-zero 16-bit words after the 16B preamble: "
              f"n={len(real_vals)}")
        print(f"  min={min(real_vals)} max={max(real_vals)} "
              f"median={statistics.median(real_vals)} mean={statistics.mean(real_vals):.1f}")
        small = sum(1 for v in real_vals if v < 256)
        midr = sum(1 for v in real_vals if 256 <= v < 4096)
        large = sum(1 for v in real_vals if v >= 4096)
        print(f"  <256: {100*small/len(real_vals):.1f}%  256-4095: {100*midr/len(real_vals):.1f}%  "
              f">=4096: {100*large/len(real_vals):.1f}%")

    # Byte-length / unit-count correlations against known per-region
    # quantities (both raw byte length and unit-count under the winning
    # candidate unit size, tried at 2B and 4B since those are the cleanest
    # 16-bit-word-aligned candidates per the divisibility scan above).
    for unit in (2, 4):
        def unitcount(row, u=unit):
            ps = row["ext_payloads"].get(0xAF100100)
            if not ps:
                return None
            return len(ps[0]) // u
        correlate(
            rows,
            unitcount, f"0xAF100100 payload-length / {unit}B-unit-count",
            {
                "n_nodes": lambda r: r["n_nodes"],
                "n_links": lambda r: r["n_links"],
                "n_boundary_nodes(rank hdr)": lambda r: r["n_boundary_nodes"],
                "n_boundary_nodes(actual)": lambda r: r["n_boundary_nodes_actual"],
                "n_nodes^2": lambda r: r["n_nodes"] ** 2,
                "n_boundary_nodes^2": lambda r: r["n_boundary_nodes_actual"] ** 2,
                "n_nodes * n_boundary_nodes": lambda r: r["n_nodes"] * r["n_boundary_nodes_actual"],
                "road_ref_records": lambda r: r["road_ref_records"],
                "n_child_regions": lambda r: r["n_child_regions"],
                "n_escape_links": lambda r: r["n_escape_links"],
            },
        )


def analyze_af100300(rows):
    print("\n" + "=" * 78)
    print("0xAF100300 shape analysis (level-8 only)")
    print("=" * 78)
    lvl8 = [r for r in rows if r["level"] == 8]
    print(f"Level-8 regions: {len(lvl8)}")
    payloads = []
    payload_region_pairs = []  # (region_no, payload) for cross-region ID sharing checks
    for r in lvl8:
        for p in r["ext_payloads"].get(0xAF100300, []):
            payloads.append(p)
            payload_region_pairs.append((r["region_no"], p))
    print(f"0xAF100300 occurrences: {len(payloads)} "
          f"({100*len(payloads)/len(lvl8):.1f}% of level-8 regions)")

    # Boundary-node correlation: does 0xAF100300 presence line up with
    # ABSENCE of boundary nodes (the cross-region escape-link structure
    # already implemented in kiwiw/contraction.py), rather than presence?
    has300 = [r for r in lvl8 if 0xAF100300 in r["ext_payloads"]]
    no300 = [r for r in lvl8 if 0xAF100300 not in r["ext_payloads"]]
    bn_has300_zero = sum(1 for r in has300 if r["n_boundary_nodes_actual"] == 0)
    bn_no300_nonzero = sum(1 for r in no300 if r["n_boundary_nodes_actual"] > 0)
    print(f"\nBoundary-node / 0xAF100300-presence cross-check (level 8, n={len(lvl8)}):")
    print(f"  regions WITH 0xAF100300 that have zero boundary nodes: "
          f"{bn_has300_zero}/{len(has300)} ({100*bn_has300_zero/len(has300):.2f}%)" if has300 else "")
    print(f"  regions WITHOUT 0xAF100300 that have >0 boundary nodes: "
          f"{bn_no300_nonzero}/{len(no300)} ({100*bn_no300_nonzero/len(no300):.2f}%)" if no300 else "  (none)")

    # Prior pass's structural read: 2B "0002" tag + 2B count header, then
    # repeating ~12B records.
    header_ok = sum(1 for p in payloads if len(p) >= 4 and u16(p, 0) == 2)
    print(f"\nPayloads starting with 16-bit tag == 0x0002: {header_ok}/{len(payloads)} "
          f"({100*header_ok/len(payloads):.2f}%)" if payloads else "")

    unit_fit_report(payloads, "0xAF100300 raw")
    preamble_adjusted_fit(payloads, 4, "0xAF100300 minus 4B header (tag+count)")

    # Exact model check: does header_count * 12 + 4 == payload_len hold?
    exact_12 = 0
    exact_any_unit = collections.Counter()
    counts, lens = [], []
    for p in payloads:
        if len(p) < 4:
            continue
        cnt = u16(p, 2)
        counts.append(cnt)
        lens.append(len(p))
        if cnt * 12 + 4 == len(p):
            exact_12 += 1
        for u in CANDIDATE_UNITS:
            if cnt * u + 4 == len(p):
                exact_any_unit[u] += 1
    n = len(counts)
    print(f"\nModel check: declared_count*12 + 4-byte-header == payload_len: "
          f"{exact_12}/{n} ({100*exact_12/n:.2f}%)" if n else "no usable payloads")
    print("Model check for other candidate unit sizes (declared_count*U + 4 == payload_len):")
    for u in CANDIDATE_UNITS:
        print(f"  U={u:3d}: {exact_any_unit[u]}/{n} ({100*exact_any_unit[u]/n:.2f}%)" if n else "")

    # Sub-field decomposition of the 12-byte record, using only payloads
    # that fit the declared_count*12+4 model exactly (so record boundaries
    # are trustworthy).
    ids_monotonic = 0
    ids_ties = 0
    id_transitions = 0
    field_v2_eq_v3 = 0   # offset 6-7 vs offset 8-9 -- the actual "value repeated" pair
    field_total = 0
    tail_zero = 0
    tail_total = 0
    id_values = []
    smallfield_values = []  # offset 4-5
    bigfield_values = []    # offset 6-7 (== offset 8-9 almost always)
    id_to_regions: dict[int, set] = collections.defaultdict(set)
    n_exact_model_payloads = 0

    for region_no, p in payload_region_pairs:
        if len(p) < 4:
            continue
        cnt = u16(p, 2)
        if cnt * 12 + 4 != len(p):
            continue
        n_exact_model_payloads += 1
        prev_id = None
        for i in range(cnt):
            o = 4 + i * 12
            rec_id = u32(p, o)
            v1 = u16(p, o + 4)
            v2 = u16(p, o + 6)
            v3 = u16(p, o + 8)
            v4 = u16(p, o + 10)
            id_values.append(rec_id)
            smallfield_values.append(v1)
            bigfield_values.append(v2)
            id_to_regions[rec_id].add(region_no)
            if prev_id is not None:
                id_transitions += 1
                if rec_id > prev_id:
                    ids_monotonic += 1
                elif rec_id == prev_id:
                    ids_ties += 1
            prev_id = rec_id
            field_total += 1
            if v2 == v3:
                field_v2_eq_v3 += 1
            tail_total += 1
            if v4 == 0:
                tail_zero += 1

    if id_values:
        n_shared = sum(1 for v in id_to_regions.values() if len(v) > 1)
        max_share = max(len(v) for v in id_to_regions.values())
        print(f"\n12-byte record sub-field check (n={len(id_values)} records from "
              f"{n_exact_model_payloads} exact-model payloads):")
        print(f"  offset 0-3 (u32 'ID') strictly increasing record-to-record: "
              f"{ids_monotonic}/{id_transitions} transitions ({100*ids_monotonic/id_transitions:.2f}%); "
              f"exact ties: {ids_ties} ({100*ids_ties/id_transitions:.2f}%)")
        print(f"  offset 6-7 (u16) == offset 8-9 (u16) [\"value repeated\"]: "
              f"{field_v2_eq_v3}/{field_total} ({100*field_v2_eq_v3/field_total:.2f}%)")
        print(f"  offset 10-11 (u16, hypothesized trailing 0x0000): "
              f"{tail_zero}/{tail_total} ({100*tail_zero/tail_total:.2f}%)")
        print(f"  ID field range: min={min(id_values)} max={max(id_values)}, "
              f"{len(id_to_regions)} DISTINCT ID values across {len(id_values)} instances "
              f"(mean reuse {len(id_values)/len(id_to_regions):.1f}x per distinct ID)")
        print(f"  IDs appearing in >1 distinct region: {n_shared}/{len(id_to_regions)} "
              f"({100*n_shared/len(id_to_regions):.2f}%); max regions sharing one ID: {max_share}")
        print(f"  offset 4-5 'small' field range: min={min(smallfield_values)} "
              f"max={max(smallfield_values)} median={statistics.median(smallfield_values)}")
        print(f"  offset 6-7 'big' field range: min={min(bigfield_values)} "
              f"max={max(bigfield_values)} median={statistics.median(bigfield_values)}")

    # Correlate record count against per-region quantities, restricted to
    # level-8 rows and using the exact model where it applies (falling
    # back to raw payload_len // 12 elsewhere).
    def reccount(row):
        ps = row["ext_payloads"].get(0xAF100300)
        if not ps:
            return None
        p = ps[0]
        if len(p) >= 4:
            return u16(p, 2)
        return None

    correlate(
        lvl8,
        reccount, "0xAF100300 declared record count",
        {
            "n_nodes": lambda r: r["n_nodes"],
            "n_links": lambda r: r["n_links"],
            "n_boundary_nodes(rank hdr)": lambda r: r["n_boundary_nodes"],
            "n_boundary_nodes(actual)": lambda r: r["n_boundary_nodes_actual"],
            "n_escape_links": lambda r: r["n_escape_links"],
            "road_ref_records": lambda r: r["road_ref_records"],
            "n_child_regions": lambda r: r["n_child_regions"],
            "n_links - n_boundary_nodes": lambda r: r["n_links"] - r["n_boundary_nodes_actual"],
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alldata", required=True)
    args = ap.parse_args()

    rows = load_regions(args.alldata)
    n_with_100 = sum(1 for r in rows if 0xAF100100 in r["ext_payloads"])
    n_with_300 = sum(1 for r in rows if 0xAF100300 in r["ext_payloads"])
    print(f"Loaded {len(rows)} real regions with a Route Planning Data Frame.")
    print(f"  0xAF100100 present: {n_with_100} ({100*n_with_100/len(rows):.1f}%)")
    print(f"  0xAF100300 present: {n_with_300} ({100*n_with_300/len(rows):.1f}%)")

    analyze_af100100(rows)
    analyze_af100300(rows)


if __name__ == "__main__":
    main()
