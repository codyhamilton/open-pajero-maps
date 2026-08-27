#!/usr/bin/env python3
"""Empirical survey: is the Ch.10.13 Road Reference Table (aggregated-
intersection clustering) actually populated on the real disc, and if so,
what does it structurally contain?

Motivation: the first route-planning writer prototype
(``route_planning_writer.write_road_reference_table``) always wrote this
table empty, treating "aggregated-intersection clustering" as a deferred
design decision. Per project direction, that is only a legitimate
simplification if the real disc's own road reference tables are
themselves empty or negligible -- otherwise it's a real gap that needs
implementing, not punting. This script measures that directly by
decoding the table (``kiwiw.route_planning.parse_road_reference_table``)
across every real region on the mounted disc.

Usage:
    python3 survey_road_reference_table.py [--alldata PATH] [--json-out FILE]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.disc import AllData
from kiwiw.route_planning import (
    NO_DATA_DSA,
    parse_node_table,
    parse_region_frame,
    parse_road_reference_table,
    parse_rp_frame,
)

DEFAULT_ALLDATA = "/run/media/codyh/464210-8480/ALLDATA.KWI"


def survey(alldata_path: str) -> dict:
    disc = AllData(alldata_path)
    rf = parse_region_frame(disc)

    n_regions_total = 0
    n_regions_with_data = 0
    n_regions_with_aggregation = 0
    n_regions_decode_error = 0
    total_aggregated_nodes = 0
    ncl_values: list[int] = []
    nri_values: list[int] = []
    nsni_values: list[int] = []
    size_values: list[int] = []
    sample_records: list[dict] = []
    by_level: dict[int, dict] = {}

    for rec in rf.regions:
        if rec.is_dummy or rec.rp_dsa == NO_DATA_DSA or rec.rp_size_ls == 0:
            continue
        n_regions_total += 1
        lvl = by_level.setdefault(rec.level, {
            "n_regions": 0, "n_with_agg": 0, "total_agg_nodes": 0,
        })
        lvl["n_regions"] += 1

        lmr = next(l for l in rf.levels if l.level == rec.level)
        disc._fh.seek(disc._fh.tell())  # no-op; keep style consistent
        from kiwiw.volume import getsector
        disc._fh.seek(getsector(rec.rp_dsa, disc.sector_sz, disc.logical_sz))
        buf = disc._fh.read(rec.rp_size_ls * disc.logical_sz)
        try:
            f = parse_rp_frame(buf, lmr.n_basic_rp_frames, lmr.n_ext_rp_frames)
        except Exception:
            n_regions_decode_error += 1
            continue
        n_regions_with_data += 1

        road_ref = f.sub("road_ref")
        if road_ref is None or road_ref.size < 2:
            continue

        node_sub = f.sub("node")
        node_records = None
        if node_sub is not None and f.node_header is not None:
            try:
                node_records = parse_node_table(buf, node_sub, f.node_header)
            except Exception:
                node_records = None

        try:
            aggs = parse_road_reference_table(buf, road_ref, node_records)
        except Exception:
            n_regions_decode_error += 1
            continue

        if aggs:
            n_regions_with_aggregation += 1
            lvl["n_with_agg"] += 1
            lvl["total_agg_nodes"] += len(aggs)
            total_aggregated_nodes += len(aggs)
            for a in aggs:
                ncl_values.append(a.n_composition_links)
                nri_values.append(a.n_route_info)
                nsni_values.append(a.n_subordinate_nodes)
                size_values.append(a.size)
            if len(sample_records) < 15:
                sample_records.append({
                    "level": rec.level, "region_no": rec.region_no,
                    "n_nodes": f.node_header.n_nodes if f.node_header else None,
                    "n_aggregated": len(aggs),
                    "first": {
                        "node_number": aggs[0].node_number,
                        "size": aggs[0].size,
                        "n_composition_links": aggs[0].n_composition_links,
                        "n_route_info": aggs[0].n_route_info,
                        "n_subordinate_nodes": aggs[0].n_subordinate_nodes,
                        "n_connected_links": aggs[0].n_connected_links,
                        "subordinate_node_offsets": aggs[0].subordinate_node_offsets,
                        "composition_link_cost_numbers": aggs[0].composition_link_cost_numbers,
                    },
                })

    def dist(xs):
        if not xs:
            return None
        return {
            "n": len(xs), "min": min(xs), "max": max(xs),
            "mean": round(statistics.mean(xs), 3),
            "median": statistics.median(xs),
        }

    return {
        "n_regions_total": n_regions_total,
        "n_regions_with_data": n_regions_with_data,
        "n_regions_decode_error": n_regions_decode_error,
        "n_regions_with_aggregation": n_regions_with_aggregation,
        "pct_regions_with_aggregation": round(
            100 * n_regions_with_aggregation / n_regions_with_data, 2
        ) if n_regions_with_data else None,
        "total_aggregated_nodes": total_aggregated_nodes,
        "n_composition_links_dist": dist(ncl_values),
        "n_route_info_dist": dist(nri_values),
        "n_subordinate_nodes_dist": dist(nsni_values),
        "record_size_bytes_dist": dist(size_values),
        "by_level": by_level,
        "sample_records": sample_records,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alldata", default=DEFAULT_ALLDATA)
    ap.add_argument("--json-out")
    args = ap.parse_args()

    result = survey(args.alldata)
    print(json.dumps(result, indent=1, default=str))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=1, default=str))


if __name__ == "__main__":
    main()
