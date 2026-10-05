#!/usr/bin/env python3
"""Plan 32 census and empty assignments; never read a disc or spool.

Run from the repository root under run_heavy_python.py. The disc pin is
inherited from Execute's K1 run and plan 29, not rehashed by this tool.
Nonempty dumps are identified by exact native dump-row intervals; producer
recovery and classification belong to a subsequent work unit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

PLAN = Path("docs/plans/32-other-kind-classify-joins")
TRIAGE = Path("docs/plans/04-c-core-orchestration/triage")
KINDS = ("interior_cover", "name_anchor", "background", "background_boundary")
POINT_KINDS = ("range", "step", "road_node", "road_point")
DISC_PIN = "2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae"
ASSIGNMENT_COLUMNS = (
    "level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
    "shape", "vert", "dump_row", "rule_id", "cause",
)
TSV_COLUMNS = (
    "kind", "failing_rows", "k1_failing", "dump_path", "dump_bytes", "row_size",
    "dump_sha256", "manifest_sha256", "workers", "memory_peak_bytes", "disc_pin",
    "control_failing", "control_match",
)


def integer(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label}: expected integer >= {minimum}")
    return value


def safe_path(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.suffix.lower() == ".kwi" or "spool" in resolved.parts:
        raise ValueError(f"disc/spool access forbidden: {path}")
    if path.is_symlink():
        raise ValueError(f"input/output file symlink forbidden: {path}")
    if path.exists() and path.stat().st_nlink != 1:
        raise ValueError(f"input/output file hardlink forbidden: {path}")
    return resolved


def load(path: Path) -> dict:
    safe_path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def sha256(path: Path) -> str:
    safe_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def option(argv: list[str], flag: str) -> str:
    if argv.count(flag) != 1:
        raise ValueError(f"guard argv: expected one {flag}")
    index = argv.index(flag) + 1
    if index == len(argv):
        raise ValueError(f"guard argv: missing value for {flag}")
    return argv[index]


def build_census(dump_dir: Path, report_path: Path, guard_path: Path,
                 control_path: Path) -> dict:
    manifest_path = dump_dir / "dump_manifest.json"
    manifest = load(manifest_path)
    report, guard, control = load(report_path), load(guard_path), load(control_path)
    if manifest["tool"] != "quantisation_roundtrip" or manifest["engine"] != "c":
        raise ValueError("expected C K1 dump manifest")
    if set(manifest["kinds"]) != set(KINDS):
        raise ValueError("manifest must contain exactly the four in-scope kinds")
    workers = integer(report["timing"]["workers"], "workers", 1)
    if workers > 6:
        raise ValueError("workers exceed -j6")
    if guard["exit"] != 0 or guard.get("cgroup_error") is not None:
        raise ValueError("K1 guard run did not succeed")
    peak = integer(guard["memory_peak"], "memory_peak", 1)
    argv = guard["argv"]
    if not isinstance(argv, list) or not all(isinstance(v, str) for v in argv):
        raise ValueError("guard argv must be a string list")
    if "parser/tools/quantisation_roundtrip.py" not in argv:
        raise ValueError("guard does not record the K1 entry point")
    if option(argv, "-j") != str(workers) or option(argv, "--engine") != "c":
        raise ValueError("guard engine/workers disagree with report")
    if set(option(argv, "--dump-kinds").split(",")) != set(KINDS):
        raise ValueError("guard dump kinds disagree")
    # Inspect argv strings only; do not resolve/open the disc or spool arguments.
    if option(argv, "--disc") != "output/scratch-29/G_new/ALLDATA.KWI":
        raise ValueError("guard disc is not the declared plan-29 successor")
    for flag, expected in (("--out", report_path), ("--dump-failures", dump_dir)):
        recorded = Path(option(argv, flag))
        if not recorded.is_absolute():
            recorded = Path(guard["cwd"]) / recorded
        if recorded.resolve() != expected.resolve():
            raise ValueError(f"guard {flag} disagrees with census input")
    manifest_hash = sha256(manifest_path)
    rows = []
    for kind in KINDS:
        info = manifest["kinds"][kind]
        if info["file"] != f"{kind}.bin":
            raise ValueError(f"{kind}: unexpected dump filename")
        path = dump_dir / info["file"]
        safe_path(path)
        row_size = integer(info["row_size"], f"{kind} row_size", 1)
        if row_size != manifest["row_size"]:
            raise ValueError(f"{kind}: row_size differs from manifest")
        size = path.stat().st_size
        count, remainder = divmod(size, row_size)
        if remainder:
            raise ValueError(f"{kind}: dump bytes are not an integer number of rows")
        k1_count = integer(report["totals"][kind]["failing"], f"{kind} K1 failing")
        if count != integer(info["rows"], f"{kind} manifest rows") or count != k1_count:
            raise ValueError(f"{kind}: dump/manifest/K1 counts disagree")
        if integer(report["dump"][kind], f"{kind} reported dump rows") != count:
            raise ValueError(f"{kind}: report dump count disagrees")
        control_count = integer(control["comparisons"]["totals"][kind]["new"]["failing"],
                                f"{kind} control failing")
        rows.append(dict(
            kind=kind, failing_rows=count, k1_failing=k1_count, dump_path=str(path),
            dump_bytes=size, row_size=row_size, dump_sha256=sha256(path),
            manifest_sha256=manifest_hash, workers=workers, memory_peak_bytes=peak,
            disc_pin=DISC_PIN, control_failing=control_count, control_match=count == control_count,
            # Every row id is represented without allocating a whole-file key list.
            dump_row_ids=dict(start=0, stop=count, step=1),
            native_key_set=[] if count == 0 else None,
        ))
    nonempty = [r["kind"] for r in rows if r["failing_rows"]]
    return dict(
        schema=1, disc_pin=DISC_PIN,
        disc_pin_basis="Execute K1 argv and plan-29 successor_sha.json; disc not opened",
        inputs=dict(dump_dir=str(dump_dir), report=str(report_path), guard=str(guard_path),
                    control=str(control_path)),
        provenance=dict(manifest_sha256=manifest_hash, report_sha256=sha256(report_path),
                        guard_sha256=sha256(guard_path), control_sha256=sha256(control_path),
                        argv=argv, workers=workers, memory_peak_bytes=peak,
                        pss_peak_kb=integer(report["timing"]["pss_peak_kb"], "pss_peak_kb")),
        kinds=rows, branch_flag=f"nonempty_kinds={json.dumps(nonempty)}" if nonempty else "all_live_empty",
        nonempty_kinds=nonempty,
        control=dict(pass_failing_counts=all(r["control_match"] for r in rows),
                     plan29_pass=control.get("pass") is True),
        excluded=dict(completeness=dict(status="excluded", plan="docs/plans/28-phase1-per-rule-classify-recovery.md")),
        point_kinds=[dict(kind=k, status="out_of_scope",
                          k1_failing=integer(report["totals"][k]["failing"], f"{k} failing"))
                     for k in POINT_KINDS],
        carried_point_kinds=[k for k in POINT_KINDS if report["totals"][k]["failing"]],
    )


def check_outputs(paths: list[Path], inputs: list[Path]) -> None:
    protected = {safe_path(path) for path in inputs}
    for path in paths:
        if safe_path(path) in protected:
            raise ValueError(f"output aliases input: {path}")


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def census(args: argparse.Namespace) -> dict:
    result = build_census(args.dump_dir, args.report, args.guard, args.control)
    targets = [args.out_dir / "census.json", args.out_dir / "census.tsv"]
    inputs = [args.report, args.guard, args.control, args.dump_dir / "dump_manifest.json"]
    inputs.extend(args.dump_dir / f"{kind}.bin" for kind in KINDS)
    check_outputs(targets, inputs)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(targets[0], result)
    with targets[1].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, TSV_COLUMNS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["kinds"])
    return result


def publish(args: argparse.Namespace) -> dict:
    recorded = load(args.census)
    inputs = recorded["inputs"]
    fresh = build_census(Path(inputs["dump_dir"]), Path(inputs["report"]),
                         Path(inputs["guard"]), Path(inputs["control"]))
    if recorded != fresh:
        raise ValueError("census is stale or edited; rerun census")
    if fresh["branch_flag"] != "all_live_empty":
        raise ValueError(f"nonempty kinds require recovery: {fresh['nonempty_kinds']}")
    if not all(fresh["control"].values()):
        raise ValueError("plan-29 control failed; empty discharge refused")
    safe_path(args.assignment_header)
    with args.assignment_header.open(encoding="utf-8") as stream:
        header = stream.readline().rstrip("\r\n")
    if header.split("\t") != list(ASSIGNMENT_COLUMNS):
        raise ValueError("plan-28 assignment header changed")
    targets = [args.out_dir / "assignments" / f"{k}_assignment.tsv" for k in KINDS]
    evidence = [args.census, args.assignment_header, Path(inputs["report"]),
                Path(inputs["guard"]), Path(inputs["control"]),
                Path(inputs["dump_dir"]) / "dump_manifest.json"]
    evidence.extend(Path(inputs["dump_dir"]) / f"{k}.bin" for k in KINDS)
    check_outputs(targets, evidence)
    targets[0].parent.mkdir(parents=True, exist_ok=True)
    for target in targets:
        target.write_text(header + "\n", encoding="utf-8")
    return dict(branch_flag="all_live_empty", native_key_sets={k: [] for k in KINDS},
                assignment_rows={k: 0 for k in KINDS})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("census")
    scan.add_argument("--dump-dir", type=Path, default=Path("output/scratch-32/dump"))
    scan.add_argument("--report", type=Path, default=Path("output/scratch-32/k1_dump_report.json"))
    scan.add_argument("--guard", type=Path, default=Path("output/scratch-32/runs/k1_dump.json"))
    scan.add_argument("--control", type=Path, default=TRIAGE / "name_anchor/witnesses/successor_k1_compare.json")
    scan.add_argument("--out-dir", type=Path, default=PLAN)
    pub = commands.add_parser("publish")
    pub.add_argument("--census", type=Path, default=PLAN / "census.json")
    pub.add_argument("--assignment-header", type=Path, default=TRIAGE / "per_rule_classify_assignment.tsv")
    pub.add_argument("--out-dir", type=Path, default=PLAN)
    args = parser.parse_args(argv)
    try:
        result = census(args) if args.command == "census" else publish(args)
        print(json.dumps(result, sort_keys=True))
        return 1 if args.command == "census" and not all(result["control"].values()) else 0
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"census.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
