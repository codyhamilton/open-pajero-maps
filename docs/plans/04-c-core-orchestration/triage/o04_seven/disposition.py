#!/usr/bin/env python3
"""Close seven O04 rows from retained JSON/TSV evidence; never open discs/spool.

Execute runs publish through run_heavy_python.py. A failed prerequisite writes
conflict-open, with reasons, and exits 2. No fix-landed verdict is available.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys

PLAN = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("o04_disposition_presence", PLAN / "presence_witness.py")
presence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presence)
ROOT = presence.ROOT
PRESENCE_SHA256 = "0f03858f350f6fcc3e14dc6bea83e1a1d641fb8644640d8c920dcd2a9ea62458"
K1 = presence.TRIAGE / "name_anchor/witnesses/successor_k1_compare.json"
K1_SHA256 = "d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b"
PREFIXES = {"g_successor": "G_successor", "g_historical": "G_historical", "r": "R"}
ERRORS = (ValueError, KeyError, TypeError, IndexError, OSError, csv.Error)


def light(path, suffix):
    path = Path(path)
    resolved = path.resolve()
    presence.require(path.suffix == resolved.suffix == suffix
                     and "spool" not in resolved.parts
                     and not str(resolved).startswith("/run/media/"),
                     f"expected light {suffix} input: {path}")
    return path.read_bytes()


def tsv_records(raw):
    # Retained frame/index hex can exceed Python's 128 KiB CSV field default.
    previous = csv.field_size_limit(presence.CAP * 2)
    try:
        return list(csv.DictReader(io.StringIO(raw.decode()), delimiter="\t"))
    finally:
        csv.field_size_limit(previous)


def keyed(rows, label):
    result = {}
    for row in rows:
        dump = row["dump_row"]
        presence.require(type(dump) is int and dump in presence.TARGETS,
                         f"unknown dump_row in {label}")
        presence.require(dump not in result, f"duplicate dump_row in {label}: {dump}")
        result[dump] = row
    return result


def verify_k1(raw):
    result = json.loads(raw)
    presence.require(result["pass"] is True and result["errors"] == []
                     and result["expected_k1_exit"] == 0, "K1 comparison not passing")
    checked = failing = 0
    for level, kinds in result["comparisons"].items():
        for comparison in kinds.values():
            presence.require(comparison["equal"] is True
                             and comparison["new"] == comparison["expected"],
                             "K1 kind differs from expected successor result")
        counts = kinds["completeness"]["new"]
        presence.require(all(type(counts[n]) is int and counts[n] >= 0
                             for n in ("checked", "failing")), "invalid K1 counts")
        if level != "totals":
            checked += counts["checked"]
            failing += counts["failing"]
    totals = result["comparisons"]["totals"]["completeness"]["new"]
    presence.require((totals["checked"], totals["failing"]) == (checked, failing),
                     "K1 totals disagree with per-level completeness")
    presence.require((checked, failing) == (1800514, 0), "K1 completeness citation differs")
    return {"checked": checked, "failing": failing,
            "disc_sha256": presence.PINS["g_successor"],
            "verification": "retained successor comparison citation; K1 not rerun"}


def classify(member, witness, probes, common_issues):
    """Each row earns its verdict through its own index/frame-byte replay."""
    issues = list(common_issues)
    if witness is None:
        issues.append("missing Phase 1 row witness")
        return "conflict-open", issues
    for name in (*presence.NATIVE, "dump_row", "rule_id", "cause", "stratum"):
        if witness.get(name) != member[name] or type(witness.get(name)) is not type(member[name]):
            issues.append(f"Phase 1 identity differs: {name}")
    if witness.get("presence_witness_status") != "absence-proven":
        issues.append("Phase 1 row is not absence-proven")
    if witness.get("exceptions") != []:
        issues.append(f"Phase 1 row exceptions: {witness.get('exceptions')}")
    for label, prefix in PREFIXES.items():
        count = witness.get(f"{prefix}_type_count")
        if type(count) is not int or count != 0:
            issues.append(f"{label}: demanded type count is not integer zero ({count})")
        status = witness.get(f"{prefix}_slot_status")
        if status not in {"resolved", "empty_slot"}:
            issues.append(f"{label}: unresolved slot ({status})")
        if witness.get(f"{prefix}_sha256") != presence.PINS[label]:
            issues.append(f"{label}: Phase 1 disc pin differs")
        evidence = witness.get(f"{prefix}_evidence")
        probe_row = probes.get(label, {}).get(member["dump_row"])
        if evidence is None or probe_row is None:
            issues.append(f"{label}: missing retained byte/decode witness or probe row")
            continue
        if evidence != probe_row:
            issues.append(f"{label}: Phase 1 evidence differs from hashed probe")
        if evidence.get("status") != status or type(evidence.get("type_count")) is not int \
                or evidence.get("type_count") != count:
            issues.append(f"{label}: summary differs from byte/decode evidence")
        error = presence.validate_row(evidence, member)
        if error:
            issues.append(f"{label}: byte/decode replay failed: {error}")
    return ("conflict-open" if issues else "proven-non-deviation"), issues


def publish(args):
    members, sources = presence.source_rows()
    common, inputs, witness_rows, probes, probe_hashes = [], {}, {}, {}, {}
    witness = {}
    try:
        raw = light(args.presence_json, ".json")
        inputs[presence.rel(args.presence_json)] = presence.sha(raw)
        presence.require(presence.sha(raw) == args.presence_sha256, "Phase 1 JSON hash mismatch")
        witness = json.loads(raw)
        presence.require(witness["schema"] == "plan33-presence-witness-v1", "wrong Phase 1 schema")
        presence.require(witness["source_sha256"] == sources, "Phase 1 O04 source hashes differ")
        witness_rows = keyed(witness["rows"], "Phase 1 JSON")
    except ERRORS as exc:
        common.append(f"invalid/missing Phase 1 JSON: {exc}")
    tsv_rows = {}
    try:
        raw = light(args.presence_tsv, ".tsv")
        inputs[presence.rel(args.presence_tsv)] = presence.sha(raw)
        for row in tsv_records(raw):
            dump = int(row["dump_row"])
            presence.require(dump in presence.TARGETS and dump not in tsv_rows,
                             "unknown/duplicate Phase 1 TSV row")
            tsv_rows[dump] = row
    except ERRORS as exc:
        common.append(f"invalid/missing Phase 1 TSV: {exc}")
    reader_hashes = None
    for label in PREFIXES:
        path = getattr(args, label)
        try:
            raw = light(path, ".json")
            ref = presence.rel(path)
            inputs[ref] = probe_hashes[ref] = presence.sha(raw)
            presence.require(probe_hashes[ref] == witness["probe_sha256"][ref],
                             f"{label}: probe hash mismatch")
            probe = json.loads(raw)
            presence.require(probe["schema"] == presence.SCHEMA and probe["disc"] == label
                             and probe["disc_sha256"] == presence.PINS[label], "probe schema/disc/pin differs")
            presence.require(probe["source_sha256"] == sources, "probe O04 source hashes differ")
            expected = "historical-citation" if label == "r" else "streamed-full-sha256"
            presence.require(probe["pin_verification"] == expected, "probe pin verification differs")
            # These are historical probe-producer hashes. Live replay below is
            # authoritative; an import-path-only close-out edit is not a reason
            # to reopen discs to regenerate identical retained bytes.
            recorded = probe["reader_sha256"]
            presence.require(recorded and all(isinstance(h, str) and len(h) == 64
                                              for h in recorded.values()), "missing reader hashes")
            if reader_hashes is None:
                reader_hashes = recorded
            presence.require(recorded == reader_hashes, "probe reader provenance differs")
            probes[label] = keyed(probe["rows"], f"{label} probe")
        except ERRORS as exc:
            common.append(f"invalid/missing {label} probe: {exc}")
    k1 = {"checked": None, "failing": None, "disc_sha256": presence.PINS["g_successor"],
          "verification": "missing or invalid retained comparison; K1 not rerun"}
    try:
        raw = light(args.k1, ".json")
        inputs[presence.rel(args.k1)] = presence.sha(raw)
        presence.require(presence.sha(raw) == args.k1_sha256, "K1 comparison hash mismatch")
        k1 = verify_k1(raw)
    except ERRORS as exc:
        common.append(f"invalid/missing K1 citation: {exc}")
    rows = []
    for member in members:
        dump = member["dump_row"]
        row_witness = witness_rows.get(dump)
        local = list(common)
        tsv_row = tsv_rows.get(dump)
        if tsv_row is None:
            local.append("missing Phase 1 TSV row")
        elif row_witness is not None:
            for name, value in row_witness.items():
                expected = presence.packed(value) if isinstance(value, (dict, list)) \
                    else ("" if value is None else str(value))
                if tsv_row.get(name) != expected:
                    local.append(f"Phase 1 TSV/JSON differs: {name}")
        verdict, issues = classify(member, row_witness, probes, local)
        rationale = (
            "Per-row retained index/frame bytes replay G successor, G historical and R "
            "demanded-type absence in this cell. Historical completeness was checker-over-demand "
            "on unrepresentable crossing-closing geometry (plans 14/28). O04 remains spool; "
            "the source defect is a spool hygiene residual, with no live G!=R presence deviation."
            if not issues else "; ".join(issues))
        counterfactual = (
            "Penultimate deletion emits 1 piece; counterfactual stays evidence only. "
            "Applying it would invent R-absent presence."
            if member["stratum"] == "emit-piece" else
            "Penultimate deletion removes demand and emits 0 pieces; optional hygiene fix not applied.")
        rows.append({**member, "verdict": verdict, "rationale": rationale,
                     "exceptions": issues, "penultimate_counterfactual": counterfactual,
                     "spool_hygiene_residual": "O04 crossing-closing ring; source unchanged",
                     "presence_witness_ref": presence.rel(args.presence_tsv) + f"#dump_row={dump}",
                     "presence_json_ref": presence.rel(args.presence_json) + f"#dump_row={dump}",
                     "presence_json_sha256": inputs.get(presence.rel(args.presence_json)),
                     "presence_tsv_sha256": inputs.get(presence.rel(args.presence_tsv)),
                     "probe_sha256": probe_hashes,
                     "fix_artifact_paths": [], "fix_disc_sha256": None,
                     "disc_in_force_sha256": presence.PINS["g_successor"],
                     "K1_ref": presence.rel(args.k1), "K1_sha256": inputs.get(presence.rel(args.k1)),
                     "K1_completeness_checked": k1["checked"], "K1_completeness_failing": k1["failing"],
                     **{f"{prefix}_{field}": (row_witness or {}).get(f"{prefix}_{field}")
                        for prefix in PREFIXES.values() for field in ("type_count", "slot_status")}})
    counts = {v: Counter(r["verdict"] for r in rows)[v]
              for v in ("proven-non-deviation", "fix-landed", "conflict-open")}
    result = {"schema": "plan33-disposition-v1", "rows": rows, "verdict_counts": counts,
              "phase2_verified": counts["conflict-open"] == 0,
              "input_sha256": inputs, "probe_reader_sha256": reader_hashes,
              "K1": k1, "spool_edited": False, "encode_run": False, "K1_rerun": False,
              "plan04_phase3_closed": False,
              "spool_hygiene_residual_rows": list(presence.TARGETS)}
    presence.write_json(args.json, result)
    columns = list(rows[0])
    Path(args.tsv).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.tsv).open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: presence.packed(value) if isinstance(value, (dict, list))
                             else ("" if value is None else value) for name, value in row.items()})
    return 2 if counts["conflict-open"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pub = sub.add_parser("publish")
    pub.add_argument("--presence-json", type=Path, default=PLAN / "presence_witness.json")
    pub.add_argument("--presence-tsv", type=Path, default=PLAN / "presence_witness.tsv")
    pub.add_argument("--presence-sha256", default=PRESENCE_SHA256)
    for label in PREFIXES:
        pub.add_argument("--" + label.replace("_", "-"), type=Path,
                         default=ROOT / "output/scratch-33" / f"{label}.json")
    pub.add_argument("--k1", type=Path, default=K1)
    pub.add_argument("--k1-sha256", default=K1_SHA256)
    pub.add_argument("--tsv", type=Path, default=PLAN / "disposition.tsv")
    pub.add_argument("--json", type=Path, default=PLAN / "disposition.json")
    args = parser.parse_args(argv)
    try:
        return publish(args)
    except ERRORS as exc:
        print(f"disposition: refusing publication: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
