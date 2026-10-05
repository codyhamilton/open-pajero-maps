"""Plan 22: map-only harness honesty + WP2–WP5 NA negative controls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from harness import registry, report
from harness.context import CheckResult, Context


WP_IDS = ("wp2_route", "wp3_address", "wp4_index")
WP_LAYERS = ("route", "address", "index")
META_CHECK_ID = "copy_through_graphics"  # plan 23 subsumed wp5_meta
META_LAYER = "meta"


def test_wp_na_checks_discovered():
    ids = {c.id for c in registry.discover()}
    for cid in WP_IDS:
        assert cid in ids


def test_wp_na_under_map_only_layers():
    cfg = {"layers_present": ["map"]}
    ctx = Context(reference=None, generated="/dev/null", config=cfg)
    by_id = {c.id: c for c in registry.discover()}
    for cid, layer in zip(WP_IDS, WP_LAYERS):
        check = by_id[cid]
        assert check.layer == layer
        assert not ctx.layer_present(check.layer)
        # CLI short-circuit path
        assert check.layer not in cfg["layers_present"]


def test_report_json_map_only_scope(tmp_path):
    results = [
        {"id": "decode", "layer": "map", "status": "PASS", "message": "ok", "details": {}},
        {"id": "wp2_route", "layer": "route", "status": "NA",
         "message": "layer 'route' not present per config", "details": {}},
        {"id": "wp3_address", "layer": "address", "status": "NA",
         "message": "layer 'address' not present per config", "details": {}},
        {"id": "wp4_index", "layer": "index", "status": "NA",
         "message": "layer 'index' not present per config", "details": {}},
        {"id": "copy_through_graphics", "layer": "meta", "status": "NA",
         "message": "layer 'meta' not present per config", "details": {}},
    ]
    path = tmp_path / "report.json"
    report.write_report(str(path), None, "/tmp/G/ALLDATA.KWI", results,
                        binding={"manifest_bound": False},
                        layers_present=["map"])
    data = json.loads(path.read_text())
    assert data["layers_present"] == ["map"]
    assert data["scope"] == "map-only"
    assert data["full_disc_parity"] is False
    assert {c["id"] for c in data["checks"]} >= set(WP_IDS) | {META_CHECK_ID}
    assert all(c["status"] != "FAIL" for c in data["checks"])
    # exit policy: no FAIL → 0
    assert all(c["status"] in ("PASS", "NA") for c in data["checks"])


def test_wp_run_body_na_not_started():
    by_id = {c.id: c for c in registry.discover()}
    # Even if layer were present, WP2–WP4 sentinels stay NA / not started
    ctx = Context(reference=None, generated="/dev/null",
                  config={"layers_present": ["map", "route", "address", "index", "meta"]})
    for cid in WP_IDS:
        result = by_id[cid].run(ctx)
        assert isinstance(result, CheckResult)
        assert result.status == "NA"
        assert "not started" in result.message.lower()
    # plan 23: meta layer check is real cmp (NA without disc roots), not wp5_meta
    assert META_CHECK_ID in by_id
    assert by_id[META_CHECK_ID].layer == META_LAYER
    assert "wp5_meta" not in by_id
