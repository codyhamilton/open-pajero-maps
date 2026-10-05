#!/usr/bin/env python3
"""Flash/OpenCode heavy-Python wrapper: flock + MemoryAccounting + argv/peak log.

Plan 25 Phase 2b. Every heavy Maps Python invocation under
``output/.heavy.lock`` should go through this helper so the next OOM has a
recoverable cmdline and cgroup ``memory.peak``.

Recipe (from repository root)::

    .venv-rp/bin/python -B parser/tools/run_heavy_python.py \\
      --log output/scratch-25/runs/cell_local.json -- \\
      docs/plans/14-completeness-root-cause/triage/cell_local_2-01.py --max-seeds 8

The wrapper itself takes the lock (unless ``--no-flock``) and runs the child
inside ``systemd-run --user --scope -p MemoryAccounting=yes``. The log JSON
records full argv, wall time, ``/usr/bin/time -v`` max RSS, and cgroup
``memory.peak`` / anon / file. Missing peak → exit 2 (fail closed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_LOCK = REPO / "output" / ".heavy.lock"


def _cgroup_snapshot() -> dict:
    snap: dict = {}
    try:
        line = [l for l in Path("/proc/self/cgroup").read_text().splitlines()
                if l.startswith("0::")][0]
        cg = Path("/sys/fs/cgroup") / line[3:].lstrip("/")
        snap["cgroup"] = str(cg)
        snap["memory_peak"] = int((cg / "memory.peak").read_text())
        snap["memory_current"] = int((cg / "memory.current").read_text())
        st = dict(l.split() for l in (cg / "memory.stat").read_text().splitlines())
        for k in ("anon", "file", "file_dirty", "file_writeback", "file_mapped"):
            if k in st:
                snap[k] = int(st[k])
    except Exception as e:  # noqa: BLE001 — recorded; caller fail-closes
        snap["error"] = repr(e)
    return snap


def _parse_time(text: str) -> dict:
    out: dict = {}
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if m:
        out["max_rss_kib"] = int(m.group(1))
    m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", text)
    if m:
        secs = 0.0
        for part in m.group(1).split(":"):
            secs = secs * 60 + float(part)
        out["time_v_elapsed_s"] = secs
    return out


def _inner(argv: list[str], log_path: Path, cwd: Path) -> int:
    """Run inside the accounting scope: execute argv, write peak log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    time_path = log_path.with_suffix(log_path.suffix + ".time.txt")
    t0 = time.perf_counter()
    cmd = ["/usr/bin/time", "-v", "-o", str(time_path), *argv]
    proc = subprocess.run(cmd, cwd=str(cwd))
    wall = time.perf_counter() - t0
    snap = _cgroup_snapshot()
    time_meta = {}
    if time_path.exists():
        time_meta = _parse_time(time_path.read_text())
    record = {
        "argv": argv,
        "cwd": str(cwd),
        "exit": proc.returncode,
        "wall_s": wall,
        "max_rss_kib": time_meta.get("max_rss_kib"),
        "time_v_elapsed_s": time_meta.get("time_v_elapsed_s"),
        "memory_peak": snap.get("memory_peak"),
        "anon": snap.get("anon"),
        "file": snap.get("file"),
        "file_dirty": snap.get("file_dirty"),
        "cgroup": snap.get("cgroup"),
        "cgroup_error": snap.get("error"),
        "pid": os.getpid(),
        "ppid": os.getppid(),
    }
    log_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if record["memory_peak"] is None:
        print(f"run_heavy_python: missing memory.peak (log {log_path})", file=sys.stderr)
        return 2
    print(json.dumps({
        "log": str(log_path),
        "exit": record["exit"],
        "max_rss_kib": record["max_rss_kib"],
        "memory_peak": record["memory_peak"],
        "wall_s": round(wall, 3),
        "argv0": argv[0] if argv else None,
    }, sort_keys=True))
    return 2 if record["memory_peak"] is None else int(proc.returncode)


def _outer(args: argparse.Namespace, child_argv: list[str]) -> int:
    log_path = Path(args.log).resolve()
    cwd = Path(args.cwd).resolve() if args.cwd else REPO
    lock = Path(args.lock).resolve()
    unit = f"maps-heavy-{os.getpid()}"
    # Re-enter this script as --inner inside scope (+ optional flock).
    inner_cmd = [
        sys.executable, "-B", str(Path(__file__).resolve()),
        "--inner", "--log", str(log_path), "--cwd", str(cwd),
        "--", *child_argv,
    ]
    scoped = [
        "systemd-run", "--user", "--scope", "--quiet",
        "-p", "MemoryAccounting=yes", f"--unit={unit}", "--",
    ]
    if args.no_flock:
        cmd = scoped + inner_cmd
    else:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch(exist_ok=True)
        cmd = scoped + ["flock", str(lock), *inner_cmd]
    print(f"run_heavy_python: unit={unit} lock={'none' if args.no_flock else lock}",
          flush=True)
    print(f"run_heavy_python: argv={child_argv!r}", flush=True)
    return subprocess.call(cmd, cwd=str(cwd))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", required=True, help="JSON log path (argv + peaks)")
    p.add_argument("--cwd", default=None, help="Child working directory (default: repo root)")
    p.add_argument("--lock", default=str(DEFAULT_LOCK), help="flock path")
    p.add_argument("--no-flock", action="store_true", help="Skip flock (tests only)")
    p.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = p.parse_args(argv)
    child = list(args.command)
    if child and child[0] == "--":
        child = child[1:]
    if not child:
        p.error("missing command after --")
    if args.inner:
        cwd = Path(args.cwd).resolve() if args.cwd else REPO
        return _inner(child, Path(args.log).resolve(), cwd)
    return _outer(args, child)


if __name__ == "__main__":
    raise SystemExit(main())
