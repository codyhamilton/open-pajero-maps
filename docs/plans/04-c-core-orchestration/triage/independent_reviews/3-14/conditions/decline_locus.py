"""Plan 43 review F2: instrumented decline locus for the five seeded EO declines.

Compiles a throwaway probe against a copy of _cenc.c with every `return -1`
tagged by line number, then probes the five rings that stress_20k.json records
as size==-1. Prints the last tag before each decline. Evidence only; not a
runtime check. Run: .venv-rp/bin/python -B <this>  (no heavy lock needed)."""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tests")]
import test_bg_eo_stress as t
RINGS = ["r359", "r8475", "r11892", "r14503", "r19650"]
SEED_N = 20000

def main():
    t.N_RINGS = SEED_N
    rings = {f"r{i}": r for i, r in enumerate(t.seeded_rings())}
    assert set(RINGS) <= set(rings)
    with tempfile.TemporaryDirectory(prefix="eo_decl_") as tmp:
        tmp = Path(tmp)
        (tmp / "kiwiw").mkdir(); (tmp / "tests/fixtures/bg_eo").mkdir(parents=True)
        src = (ROOT / "parser/kiwiw/_cenc.c").read_text()
        # Tag every return -1 with its 1-based line number (stderr).
        lines = src.splitlines(True)
        # Tag return -1 only inside eo_clip (static int eo_clip ... through the next top-level static/int64).
        start = next(i for i, L in enumerate(lines) if L.startswith("static int eo_clip"))
        end = next(i for i, L in enumerate(lines[start+1:], start+1) if L.startswith("static ") or L.startswith("int64_t "))
        out = ["#include <stdio.h>\n"]
        for i, L in enumerate(lines, 1):
            if start < i-1 < end and "return -1;" in L and "fprintf" not in L:
                L = L.replace("return -1;", f'{{fprintf(stderr,"L%d\\n",{i}); return -1;}}', 1)
            out.append(L)
        (tmp / "kiwiw/_cenc.c").write_text("".join(out))
        for h in (ROOT / "parser/kiwiw").glob("*.h"):
            (tmp / "kiwiw" / h.name).write_bytes(h.read_bytes())
        probe = (ROOT / "parser/tests/fixtures/bg_eo/probe.c").read_text()
        # Redirect the #include to the instrumented copy.
        probe = probe.replace('#include "../../../kiwiw/_cenc.c"',
                              f'#include "{tmp}/kiwiw/_cenc.c"')
        (tmp / "tests/fixtures/bg_eo/probe.c").write_text(probe)
        from kiwiw import cbuild
        so = tmp / "p.so"
        subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, "-shared",
                        str(tmp / "tests/fixtures/bg_eo/probe.c"), "-lm", "-o", str(so)],
                       check=True, cwd=str(ROOT))
        import ctypes, numpy as np
        fn = ctypes.CDLL(str(so)).probe_bg
        fn.restype = ctypes.c_int64
        fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
                       ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
        results = {}
        for name in RINGS:
            ring = rings[name]
            lat = np.array([y for x, y in ring], "f8"); lon = np.array([x for x, y in ring], "f8")
            R = np.array([0, 0, 4096, 4096], "f8"); o = np.zeros(1 << 20, "u1"); nr = ctypes.c_int64()
            err = subprocess.run(
                [sys.executable, "-B", "-c",
                 "import ctypes,numpy as np,sys\n"
                 f"fn=ctypes.CDLL({str(so)!r}).probe_bg; fn.restype=ctypes.c_int64\n"
                 f"lat=np.array({lat.tolist()},'f8'); lon=np.array({lon.tolist()},'f8')\n"
                 "R=np.array([0,0,4096,4096],'f8'); o=np.zeros(1<<20,'u1'); nr=ctypes.c_int64()\n"
                 "print(fn(lat.ctypes.data,lon.ctypes.data,len(lat),R.ctypes.data,o.ctypes.data,1<<20,ctypes.byref(nr)))\n"],
                capture_output=True, text=True, cwd=str(ROOT))
            tags = [int(x[1:]) for x in err.stderr.split() if x.startswith("L") and x[1:].isdigit()]
            # Drop the ring coordinates from the committed artefact (large); keep size/tags only.
            try:
                size = int(err.stdout.strip().split()[-1]) if err.stdout.strip() else None
            except ValueError:
                size = None
            results[name] = {"size": size, "tags": tags, "face_walk_guard_hit": 885 in tags,
                             "propagates_via_951": 951 in tags, "rc": err.returncode,
                             "stderr_tail": err.stderr[-200:] if err.returncode else ""}
            print(name, results[name]["size"], results[name]["face_walk_guard_hit"], results[name]["tags"][-4:], err.returncode)
        ok = [r for r in results.values() if r["size"] == -1]
        assert ok and all(r["face_walk_guard_hit"] for r in ok), results
        assert sum(1 for r in results.values() if r["size"] == -1) >= 3
        outp = {"seed": t.SEED, "n_rings": SEED_N, "declines": {k: {kk: vv for kk, vv in v.items() if kk != "stderr_tail"} for k, v in results.items()},
                "locus": "_cenc.c:885 (eo_clip face-walk guard: g_eh[h].used || np >= ne; arms not split)",
                "propagates_via": "_cenc.c:951 (eo_clip return -1 -> kw__bg_shape)",
                "build_error_cites": ["_cenc.c:1070 (enc_bg decline)", "_e2.c:48 (declined row is a build error)"],
                "note": "Why the walk meets a used half-edge is not established (plan 48)."}
        json.dump(outp, open(HERE / "decline_locus.json", "w"), indent=1)
        print("DECLINEDONE")

if __name__ == "__main__":
    main()
