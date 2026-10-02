"""Frozen pre-Phase-2 finalizer; preserve the original algorithm verbatim."""
from pathlib import Path
import json
import numpy as np

DUMP_ORDER = ("level", "iy", "ix", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "depth",
              "vx", "vy", "reason", "code", "lat", "lon", "err", "shape", "vert")

def finalize_dump_baseline(dump_dir, kinds, ntasks, log):
    """Concatenate the per-task parts per kind, order them canonically (independent of
    the band split), write `DIR/<kind>.bin`, delete the parts and write the manifest;
    return `{kind: rows}` for the report."""
    from kiwiw import cenc
    dump_dir = Path(dump_dir)
    fields = [{"name": n, "type": t} for n, t in cenc.K1_DUMP_FIELDS]
    row_size = cenc.K1_DUMP_DTYPE.itemsize
    counts = {}
    for name in kinds:
        parts = []
        for i in range(ntasks):
            p = dump_dir / f"part_{i:05d}_{name}.bin"
            if p.exists():
                parts.append(np.fromfile(p, dtype=cenc.K1_DUMP_DTYPE))
                p.unlink()
        arr = np.concatenate(parts) if parts else np.zeros(0, cenc.K1_DUMP_DTYPE)
        if len(arr) > 1:
            arr = arr[np.argsort(arr, order=DUMP_ORDER, kind="stable")]
        (dump_dir / f"{name}.bin").write_bytes(arr.tobytes())
        counts[name] = int(len(arr))
    manifest = {"tool": "quantisation_roundtrip", "engine": "c", "row_size": row_size,
                "fields": fields,
                "kinds": {n: {"rows": counts[n], "row_size": row_size,
                              "file": f"{n}.bin", "fields": fields} for n in kinds}}
    (dump_dir / "dump_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log("dump: " + ", ".join(f"{n} {counts[n]:,}" for n in kinds))
    return counts

