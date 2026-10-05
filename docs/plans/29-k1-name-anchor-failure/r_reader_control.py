"""Positive control for witness_p1 R reader: a populated cell resolves, and the census of the
block holding (0,541) on R vs G. Bounded preads only."""
import sys, json, importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("w", "docs/plans/29-k1-name-anchor-failure/witness_p1.py")
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
R = "/run/media/codyh/464210-8480/ALLDATA.KWI"; G = "output/scratch-14/G_new/ALLDATA.KWI"
out = {}
for tag, disc in (("R", R), ("G", G)):
    perth = [(r["status"], len(r["frames"]), sum(len(f["names"]) for f in r["frames"])) for r in w.disc_cells(disc, [(827, 866)])]
    block = [(tuple(r["cell"]), len(r["frames"]), sum(len(f["names"]) for f in r["frames"]))
             for r in w.disc_cells(disc, [(x, y) for y in range(512, 576) for x in range(0, 32)])]
    out[tag] = {"perth_827_866": perth,
                "block0_cells_with_frames": sum(1 for _, n, _ in block if n),
                "block0_names": sum(k for *_, k in block),
                "block0_nonempty": [c for c, n, _ in block if n][:20]}
print(json.dumps(out))
Path("docs/plans/29-k1-name-anchor-failure/witnesses/r_reader_control.json").write_text(json.dumps(out, indent=1))
