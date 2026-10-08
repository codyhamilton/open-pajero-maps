"""Plan 46 (Design ruling b): commit S = the full-predicate S02 group set.

Reads <work>/side/s02_background_boundary.npy (gate_repro --s02-scope full), keeps status==1 groups with
rows>0, sorts by the full group key and writes a deterministic TSV.gz (gzip mtime=0, no name).
Prints counts and sha256 of the uncompressed TSV (the identity of S) and of the .gz file.
"""
import gzip, hashlib, io, json, sys
from pathlib import Path
import numpy as np
GROUP = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape")

def main(work, out):
    s = np.load(Path(work) / "side/s02_background_boundary.npy")
    q = s[(s["status"] == 1) & (s["rows"] > 0)]
    kd = np.dtype([(f, "<i8") for f in GROUP])
    k = np.empty(len(q), kd)
    for f in GROUP:
        k[f] = q[f]
    o = np.argsort(k, kind="stable")
    buf = io.StringIO()
    buf.write("\t".join(GROUP + ("rows",)) + "\n")
    for i in o:
        buf.write("\t".join(str(int(q[i][f])) for f in GROUP) + f"\t{int(q[i]['rows'])}\n")
    raw = buf.getvalue().encode()
    bio = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=bio, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    Path(out).write_bytes(bio.getvalue())
    res = {"groups": int(len(q)), "rows": int(q["rows"].sum()),
           "tsv_sha256": hashlib.sha256(raw).hexdigest(), "gz_sha256": hashlib.sha256(bio.getvalue()).hexdigest(),
           "gz_bytes": len(bio.getvalue())}
    print(json.dumps(res))
    return res

if __name__ == "__main__":
    main(*sys.argv[1:3])
