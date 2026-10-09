#!/usr/bin/env python3
"""Plan 63 Phase 2: sidecar window builds at 33006aa.

Window list (deterministic): one single-cell window per affected cell of ties_all.json (46 cells),
plus SAMPLE_N 6x6 L0 sample windows anchored at the spool L0 cells with the lowest
sha256("p63-sample:{ix},{iy}") (proven-set sampler; cells already covered are skipped at analysis).
Each window: `build_alldata.py --window 0 ix0 iy0 ix1 iy1 --frame-dump` run from a throwaway
worktree at 33006aa with sidecar/sidecar_33006aa.patch applied and KW_SIDECAR_DIR set.
Run under the heavy wrapper (flock + --memory-max 12G); builds are serial at -j4."""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
SAMPLE_N = 40
SAMPLE_W = 6


def window_list(spool: Path) -> list[dict]:
    sys.path[:0] = [str(ROOT / "parser")]
    from kiwiw.spool import SpoolReader
    ties = json.loads((HERE / "ties_all.json").read_text())
    cells = sorted({(g["leaf"][0], g["leaf"][1], g["leaf"][2]) for g in ties["groups"]})
    out = [{"name": f"t_{lv}_{ix}_{iy}", "set": "tie", "window": [lv, ix, iy, ix + 1, iy + 1]}
           for lv, ix, iy in cells]
    idx = SpoolReader(str(spool))._load_idx(0)
    keys = sorted((hashlib.sha256(f"p63-sample:{x},{y}".encode()).hexdigest(), int(x), int(y))
                  for x, y in zip(idx.ix, idx.iy))
    for _h, x, y in keys[:SAMPLE_N]:
        out.append({"name": f"s_0_{x}_{y}", "set": "sample",
                    "window": [0, x, y, x + SAMPLE_W, y + SAMPLE_W]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", type=Path, required=True)
    ap.add_argument("--spool", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("-j", type=int, default=4)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    wins = window_list(a.spool)
    (a.out / "windows.json").write_text(json.dumps(wins, indent=1) + "\n")
    t0 = time.time()
    for w in wins:
        d = a.out / w["name"]
        if (d / "DONE").exists():
            continue
        (d / "sc").mkdir(parents=True, exist_ok=True)
        for p in (d / "sc").iterdir():
            p.unlink()
        env = dict(os.environ, KW_SIDECAR_DIR=str(d / "sc"), PYTHONDONTWRITEBYTECODE="1")
        cmd = [a.python, "-B", "parser/build_alldata.py", "--spool", str(a.spool),
               "--out", str(d / "ALLDATA.KWI"), "-j", str(a.j), "--window",
               *map(str, w["window"]), "--frame-dump", str(d / "frames")]
        for f in ("frames.bin", "frames.tsv"):
            (d / f).unlink(missing_ok=True)
        r = subprocess.run(cmd, cwd=a.worktree, env=env, capture_output=True, text=True)
        (d / "build.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            print(json.dumps({"window": w["name"], "rc": r.returncode}), flush=True)
            sys.exit(2)
        (d / "ALLDATA.KWI").unlink(missing_ok=True)  # frames.bin carries the frame bytes
        (d / "DONE").write_text("ok\n")
        print(json.dumps({"window": w["name"], "t": round(time.time() - t0, 1)}), flush=True)
    print(json.dumps({"windows": len(wins), "wall_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
