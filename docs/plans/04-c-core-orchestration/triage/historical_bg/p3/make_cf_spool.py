"""Plan 39 P3: counterfactual spool = pinned spool minus source (L0,1689,508,rec0). That cell holds only this source
(n_bgs 1, no roads/names), so the CF drops the cell from level_0.idx; every data file is a read-only symlink to the
pinned spool (offsets of all other cells unchanged). Pinned spool is never opened for writing."""
import struct, numpy as np, os, sys
SRC = os.path.realpath("output/extract_timing/spool"); DST = sys.argv[1]
for f in sorted(os.listdir(SRC)):
    if f != "level_0.idx" and not os.path.exists(f"{DST}/{f}"): os.symlink(f"{SRC}/{f}", f"{DST}/{f}")
raw = open(f"{SRC}/level_0.idx", "rb").read()
assert raw[:8] == b"KWSPIDX1"; n, parcels, roads, bgs, names = struct.unpack_from("<5Q", raw, 8)
p = 48; ix = np.frombuffer(raw, "<i4", n, p); p += 4 * n; iy = np.frombuffer(raw, "<i4", n, p); p += 4 * n
off = np.frombuffer(raw, "<u8", n, p); p += 8 * n; ln = np.frombuffer(raw, "<u8", n, p); p += 8 * n; assert p == len(raw)
keep = ~((ix == 1689) & (iy == 508)); assert (~keep).sum() == 1
with open(f"{DST}/level_0.idx", "wb") as fh:
    fh.write(b"KWSPIDX1" + struct.pack("<5Q", n - 1, parcels - 1, roads, bgs - 1, names))
    for a in (ix, iy, off, ln): fh.write(np.ascontiguousarray(a[keep]).tobytes())
print("cf spool written", n - 1, "cells")
