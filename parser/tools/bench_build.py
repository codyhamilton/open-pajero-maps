#!/usr/bin/env python3
"""Run a command and record wall time and peak RSS summed over its process tree.

Usage: bench_build.py [--out bench.json] -- <command...>
e.g.   bench_build.py -- .venv-rp/bin/python parser/build_alldata.py --fixture perth

Peak RSS is sampled from /proc every 0.2 s (parent + all descendants), so it also
covers multiprocessing workers. Timings go to a separate JSON record (never the
build manifest, which must stay run-invariant).
"""
import argparse
import json
import os
import subprocess
import sys
import time


def _children_map():
    kids: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    page = os.sysconf("SC_PAGE_SIZE")
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as fh:
                st = fh.read()
            rest = st[st.rindex(")") + 2:].split()
            ppid = int(rest[1])
            rss[int(d)] = int(rest[21]) * page
            kids.setdefault(ppid, []).append(int(d))
        except (OSError, ValueError):
            continue
    return kids, rss


def tree_rss(root: int) -> int:
    kids, rss = _children_map()
    total, stack = 0, [root]
    while stack:
        p = stack.pop()
        total += rss.get(p, 0)
        stack.extend(kids.get(p, []))
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd)
    peak = 0
    while proc.poll() is None:
        peak = max(peak, tree_rss(proc.pid))
        time.sleep(0.2)
    rec = {"cmd": cmd, "exit": proc.returncode,
           "wall_s": round(time.monotonic() - t0, 2),
           "peak_rss_tree_mb": round(peak / 1e6, 1)}
    print(json.dumps(rec))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(rec, fh, indent=2)
    # 3C-01: if the wrapped command wrote its own Contract H bench record
    # (`--bench PATH` among its args), merge this process tree's wall time
    # and peak RSS into that same file rather than only into --out, so a
    # bench record is self-contained for anyone reading it without --out.
    if "--bench" in cmd:
        bpath = cmd[cmd.index("--bench") + 1]
        try:
            with open(bpath) as fh:
                bench = json.load(fh)
        except (OSError, ValueError):
            bench = None
        if bench is not None:
            bench["wall_s_tree"] = rec["wall_s"]
            bench["peak_rss_tree_mb"] = rec["peak_rss_tree_mb"]
            with open(bpath, "w") as fh:
                json.dump(bench, fh, indent=2)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
