"""Reviewer-2 probe (light): sample R01 rows by shape status (11 partial, 10 persists) on 87a01b14, re-derive the
shared non-failing vertices with the best same-type new record, and test whether those shared coordinates are
(i) also held by ANOTHER same-type old record in the leaf (ambiguous identity) and (ii) on the leaf's outer bbox edge."""
import os, sys, json, random
import numpy as np
from collections import Counter
H = "docs/plans/04-c-core-orchestration/triage/historical_bg/p2"
src = open(H + "/allrows_clause_b.py").read().replace("__file__", repr(H + "/allrows_clause_b.py"))
exec(src.split('os.makedirs("output/scratch-39/allrows"')[0])
D = "output/scratch-39/dump_pre311"
m = json.load(open(D + "/dump_manifest.json"))["kinds"]["background"]
dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
R = np.memmap(f"{D}/background.bin", dtype=dt, mode="r")
st = np.fromfile("output/scratch-39/shape/87a01b14_background.status.u8", np.uint8)
sh = np.fromfile("output/scratch-39/shape/87a01b14_background.share.f32", np.float32)
a01 = np.fromfile("output/scratch-39/classifyR01_pre311/assign_background.u16", dtype="<u2")
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
want = int(sys.argv[1])
fo, fn = open("output/scratch-36/G_pre311/ALLDATA.KWI", "rb"), open("output/scratch-14/G_new/ALLDATA.KWI", "rb")
h1 = volume.parse_volume_header(oc.read_exact(fo, 0, volume.DATAVOL_SIZE)); h2 = volume.parse_volume_header(oc.read_exact(fn, 0, volume.DATAVOL_SIZE))
res = {}
for status in (11, 10):
    pool = np.flatnonzero((a01 == 0) & (st == status))
    samp = np.array(sorted(random.sample(pool.tolist(), 300)))
    rows = R[samp]
    cellset = set(zip(rows["level"].tolist(), rows["ix"].tolist(), rows["iy"].tolist()))
    old, new = frames("output/scratch-36/G_pre311/ALLDATA.KWI", cellset), frames("output/scratch-14/G_new/ALLDATA.KWI", cellset)
    rec = []
    for j, r in zip(samp, rows):
        c = (int(r["level"]), int(r["ix"]), int(r["iy"])); d = int(r["depth"])
        lk = c + (tuple(int(r[f"p{i}"]) for i in range(d)),)
        S, V, C, X, Y = leaf_vertices(fo, old[lk], h1.sector_size, h1.logical_sector_size)
        nS, nV, nC, nX, nY = leaf_vertices(fn, new[lk], h2.sector_size, h2.logical_sector_size)
        t = int(r["code"]); s_old = int(r["shape"])
        # failing verts of this record in this kind (same as script)
        rr = np.flatnonzero((R["level"][max(0,j-5000):j+5000] == r["level"]))  # cheap neighbourhood not needed; use all rows of record via status arrays below
        ms = S == s_old
        fail = set()
        lo, hi = max(0, j - 20000), j + 20000
        W = R[lo:hi]
        sel = (W["ix"] == r["ix"]) & (W["iy"] == r["iy"]) & (W["level"] == r["level"]) & (W["shape"] == s_old) & (W["depth"] == r["depth"]) & (W["p0"] == r["p0"]) & (W["p1"] == r["p1"]) & (W["p2"] == r["p2"])
        fail = set(W["vert"][sel].tolist())
        keep = ~np.isin(V[ms], list(fail))
        onf = np.unique(pack(C[ms][keep], X[ms][keep], Y[ms][keep]))
        same = nC == t
        hit = np.isin(pack(nC, nX, nY), onf) & same
        pairs = np.unique(np.stack([nS[hit], pack(nC, nX, nY)[hit]], 1), axis=0)
        ids, cnt = np.unique(pairs[:, 0], return_counts=True)
        best = ids[cnt.argmax()]; bcoords = pairs[pairs[:, 0] == best, 1]
        # other old same-type records' coords
        oth = (C == t) & (S != s_old)
        othset = np.unique(pack(C[oth], X[oth], Y[oth]))
        ambig = np.isin(bcoords, othset)
        bset = np.unique(pack(nC[nS == best], nX[nS == best], nY[nS == best]))
        masq = any(np.array_equal(bset, np.unique(pack(C[S == o], X[S == o], Y[S == o]))) for o in np.unique(S[oth]))
        oldsets = [np.unique(pack(C[S == o], X[S == o], Y[S == o])) for o in np.unique(S[oth])]
        alt = 0.0
        for nid, nc in zip(ids, cnt):
            ns = np.unique(pack(nC[nS == nid], nX[nS == nid], nY[nS == nid]))
            if not any(np.array_equal(ns, o) for o in oldsets): alt = max(alt, nc / len(onf))
        oldself = np.array_equal(bset, np.unique(pack(C[ms], X[ms], Y[ms])))
        allx, ally = X[C >= 0], Y[C >= 0]
        bx = (bcoords >> 21) & ((1 << 21) - 1); by = bcoords & ((1 << 21) - 1)
        bx = (bx ^ 0) - (1 << 20); by = by - (1 << 20)
        edge = np.isin(bx, [X.min(), X.max()]) | np.isin(by, [Y.min(), Y.max()])
        rec.append(dict(share=float(sh[j]), nonfail=int(len(onf)), shared=int(len(bcoords)), shared_unique=int((~ambig).sum()),
                        shared_edge=int(edge.sum()), shared_unique_nonedge=int((~ambig & ~edge).sum()), n_new_recs_hit=int(len(ids)),
                        share_recheck=float(len(bcoords) / len(onf)), union_share=float(len(np.unique(pairs[:, 1])) / len(onf)), masq=int(masq), alt=float(alt), oldself=int(oldself)))
    a = {k: np.array([x[k] for x in rec]) for k in rec[0]}
    def q(v): return [int(np.quantile(v, p)) for p in (0, .1, .5, .9, 1)] if v.dtype != np.float64 else [round(float(np.quantile(v, p)), 3) for p in (0, .1, .5, .9, 1)]
    res[f"R01_status{status}"] = dict(n=len(rec), cells=len(cellset),
        share_recheck_matches=int((np.abs(a["share"] - a["share_recheck"]) < 1e-4).sum()),
        shared_q0_10_50_90_100=q(a["shared"]), nonfail_q=q(a["nonfail"]),
        shared_hist={str(k): int(v) for k, v in sorted(Counter(np.minimum(a["shared"], 10).tolist()).items())},
        union_share_q=[round(float(np.quantile(a['union_share'], p)), 3) for p in (0, .1, .5, .9, 1)], rows_union_ge50=int((a['union_share'] >= .5).sum()),
        best_is_unchanged_other_old_record=int(a['masq'].sum()), best_equals_old_record=int(a['oldself'].sum()),
        masq_rows_alt_share=[round(float(x), 3) for x in a['alt'][a['masq'] == 1]],
        rows_excl_unchanged_neighbours={'ge50': int((a['alt'] >= .5).sum()), 'partial': int(((a['alt'] > 0) & (a['alt'] < .5)).sum()), 'none': int((a['alt'] == 0).sum())},
        rows_shared_le2=int((a["shared"] <= 2).sum()),
        rows_all_shared_ambiguous=int((a["shared_unique"] == 0).sum()),
        rows_all_shared_on_leaf_edge=int((a["shared_edge"] == a["shared"]).sum()),
        rows_no_unique_nonedge_shared=int((a["shared_unique_nonedge"] == 0).sum()),
        shared_unique_q=q(a["shared_unique"]), n_new_recs_hit_q=q(a["n_new_recs_hit"]))
print(json.dumps(res, indent=1))
