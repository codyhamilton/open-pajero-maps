"""Control for r01_clause_b.py: the same presence test applied to EVERY vertex of every class>0 record in a random
sample of 400 R01 leaves (87a01b14), excluding the R01 failing vertices. If the test can detect persistence, a large
share of ordinary vertices must be found on 4ed9cd80 at the same (leaf, type, raw vertex)."""
import random
src = open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/r01_clause_b.py").read()
exec(src.split("res = Counter()")[0].replace('old = frames("output/scratch-36/G_pre311/ALLDATA.KWI"); print("old leaves", len(old), flush=True)', 'pass').replace('new = frames("output/scratch-14/G_new/ALLDATA.KWI"); print("new leaves", len(new), flush=True)', 'pass'))
leaves = sorted({(int(r["level"]), int(r["ix"]), int(r["iy"]), leafkey(r)) for r in rows})
random.seed(39); samp = random.sample(leaves, 400)
cells = {k[:3] for k in samp}
old = frames("output/scratch-36/G_pre311/ALLDATA.KWI"); new = frames("output/scratch-14/G_new/ALLDATA.KWI")
fail = {}
for r in rows:
    k = (int(r["level"]), int(r["ix"]), int(r["iy"]), leafkey(r))
    fail.setdefault(k, set()).add((int(r["code"]), int(r["vx"]), int(r["vy"])))
tot = pres = 0; ftot = fpres = 0
for k in samp:
    if k not in old or k not in new or fe.get(k[:3], ("", "0"))[1] != "1": continue
    bgo = sec.split(old[k])["background"]; bgn = sec.split(new[k])["background"]
    nt = defaultdict(set)
    for p, code, cls in records(bgn):
        if cls: xs, ys = verts(bgn, p); nt[code].update(zip(xs.tolist(), ys.tolist()))
    for p, code, cls in records(bgo):
        if not cls: continue
        xs, ys = verts(bgo, p)
        for x, y in zip(xs.tolist(), ys.tolist()):
            if (code, x, y) in fail.get(k, ()):
                ftot += 1; fpres += (x, y) in nt[code]
            else:
                tot += 1; pres += (x, y) in nt[code]
out = {"sample_leaves": len(samp), "ordinary_vertices": tot, "ordinary_present_on_4ed9cd80": pres, "share": round(pres / max(tot, 1), 4),
       "r01_vertices_in_sample": ftot, "r01_present": fpres}
json.dump(out, open("output/scratch-39/r01_clause_b_control.json", "w"), indent=1); print(out)
