"""Plan 39 P2 rework (review F1): clause (b) at SHAPE level. The item is the old record (leaf, type, record) that carries
the failing vertex, not the raw vertex itself: a build fix moves or deletes the bad vertex, so a vertex-level key cannot
tell "fixed" from "removed". A record persists on 4ed9cd80 if a class>0 record of the same type in the same leaf
(footprint-equal cells only) carries the old record's NON-failing vertices (traceable identity: same source ring
vertices, same quantisation). Per-row status (u8), written to output/scratch-39/shape/<basis>_<kind>.status.u8:
  3 footprints changed (untested)  4 new leaf missing  5 old mapping mismatch  6 old leaf missing
  10 persists: one same-type new record holds >= 50% of the old record's non-failing vertices
  11 partial: best same-type new record holds 1 .. < 50%
  12 same type present in the new leaf, no shared non-failing vertex
  13 same type present, but the old record has no non-failing vertex (identity undetermined)
  14 no record of that type in the new leaf (removed)
  Identity guard (re-review N1), written to <basis>_<kind>.guard.u8:
  20 identity-proven: a same-type new record that is NOT coordinate-identical to another (unchanged) old same-type
     record of the leaf holds >= 1 identity-bearing vertex of the old record: a non-failing vertex held by no other
     old same-type record of the leaf and not on the leaf's outer vertex bbox edge
  21 weak: shared vertices exist, but all are neighbour-held or leaf-edge (identity undetermined)
  22 none after excluding new records identical to unchanged other old records
  (13, 14 and 3-6 copied from the status above.) Thresholds (50 %, >= 1) are implementer choices, not the design's.
  Only the failing vertices of the kind being processed are excluded from "non-failing" (conservative: lowers shares).
Bases: 87a01b14 all rows (dump_pre311); 013586b5 rows in the 37 3-11 cells (dump_311)."""
import sys, os, json
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(HERE + "/allrows_clause_b.py").read().split('os.makedirs("output/scratch-39/allrows"')[0])
cells37 = {(int(l.split("\t")[0]), int(l.split("\t")[1]), int(l.split("\t")[2])) for l in open("output/scratch-36/diff-3-11-au.cells.tsv").read().splitlines()[1:]}
NEW = "output/scratch-14/G_new/ALLDATA.KWI"
NAMES = {0: "unset", 3: "footprints_changed", 4: "new_leaf_missing", 5: "old_mapping_mismatch", 6: "old_leaf_missing",
         10: "persists_ge50pct", 11: "partial_lt50pct", 12: "type_present_no_shared_vertex", 13: "type_present_old_all_failing",
         14: "type_absent_removed"}
os.makedirs("output/scratch-39/shape", exist_ok=True)
out = {}
fn = open(NEW, "rb"); h2 = volume.parse_volume_header(oc.read_exact(fn, 0, volume.DATAVOL_SIZE)); ss2, ls2 = h2.sector_size, h2.logical_sector_size
for basis, D, OLD, only37 in (("87a01b14", "output/scratch-39/dump_pre311", "output/scratch-36/G_pre311/ALLDATA.KWI", False),
                              ("013586b5_37cells", "output/scratch-39/dump_311", "output/scratch-3-11/G_new/ALLDATA.KWI", True)):
    fo = open(OLD, "rb"); h1 = volume.parse_volume_header(oc.read_exact(fo, 0, volume.DATAVOL_SIZE)); ss, ls = h1.sector_size, h1.logical_sector_size
    for kind in ("background", "background_boundary"):
        m = json.load(open(D + "/dump_manifest.json"))["kinds"][kind]
        dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
        R = np.memmap(f"{D}/{kind}.bin", dtype=dt, mode="r")
        sel = None
        if only37:
            ck = (np.asarray(R["level"]).astype(np.int64) << 40) | (np.asarray(R["ix"]).astype(np.int64) << 20) | np.asarray(R["iy"]).astype(np.int64)
            sel = np.flatnonzero(np.isin(ck, np.array(sorted((l << 40) | (x << 20) | y for l, x, y in cells37), np.int64)))
        cols = {k: (np.asarray(R[k]) if sel is None else np.asarray(R[k][sel])) for k in
                ("level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert", "vx", "vy", "code")}
        n = len(cols["level"]); status = np.zeros(n, np.uint8)
        key = np.stack([cols["level"].astype(np.int64), cols["ix"], cols["iy"], cols["depth"], cols["p0"],
                        np.where(cols["depth"] > 1, cols["p1"], 0), np.where(cols["depth"] > 2, cols["p2"], 0)], 1)
        order = np.lexsort(key.T[::-1]); ks = key[order]
        brk = np.flatnonzero(np.any(ks[1:] != ks[:-1], axis=1)) + 1; starts = np.concatenate(([0], brk)); ends = np.concatenate((brk, [n]))
        cellset = set(map(tuple, np.unique(key[:, :3], axis=0).tolist()))
        old, new = frames(OLD, cellset), frames(NEW, cellset)
        best_share = np.zeros(n, np.float32); guard = np.zeros(n, np.uint8); id_share = np.zeros(n, np.float32)
        print(basis, kind, "rows", n, "leaves", len(starts), flush=True)
        for a, b in zip(starts, ends):
            k0 = ks[a]; idx = order[a:b]; c = (int(k0[0]), int(k0[1]), int(k0[2]))
            lk = c + (tuple(int(v) for v in k0[4:4 + int(k0[3])]),)
            if lk not in old: status[idx] = 6; continue
            S, V, C, X, Y = leaf_vertices(fo, old[lk], ss, ls)
            okey = S * 65536 + V; rkey = cols["shape"][idx].astype(np.int64) * 65536 + cols["vert"][idx]
            if len(okey):
                pos = np.minimum(np.searchsorted(okey, rkey), len(okey) - 1)
                good = (okey[pos] == rkey) & (X[pos] == cols["vx"][idx]) & (Y[pos] == cols["vy"][idx]) & (C[pos] == cols["code"][idx])
            else:
                good = np.zeros(len(idx), bool)
            status[idx[~good]] = 5
            gi = idx[good]
            if not len(gi): continue
            if fe.get(c, "0") != "1": status[gi] = 3; continue
            if lk not in new: status[gi] = 4; continue
            nS, nV, nC, nX, nY = leaf_vertices(fn, new[lk], ss2, ls2)
            nP = pack(nC, nX, nY) if nS.size else np.zeros(0, np.int64)
            ex = (X.min(), X.max(), Y.min(), Y.max()) if X.size else (0, 0, 0, 0)
            tcache = {}
            for s_old in np.unique(cols["shape"][gi]):
                rows_s = gi[cols["shape"][gi] == s_old]
                t = int(cols["code"][rows_s[0]])
                ms = S == s_old
                keep = ~np.isin(V[ms], cols["vert"][rows_s])
                onf = np.unique(pack(C[ms][keep], X[ms][keep], Y[ms][keep])) if keep.any() else np.zeros(0, np.int64)
                same = nC == t
                if not same.any(): status[rows_s] = 14; guard[rows_s] = 14; continue
                if not len(onf): status[rows_s] = 13; guard[rows_s] = 13; continue
                hit = np.isin(nP, onf) & same
                if not hit.any(): status[rows_s] = 12; guard[rows_s] = 22; continue
                pairs = np.unique(np.stack([nS[hit], nP[hit]], 1), axis=0)
                share = np.bincount(np.searchsorted(np.unique(pairs[:, 0]), pairs[:, 0])).max() / len(onf)
                best_share[rows_s] = share
                status[rows_s] = 10 if share >= 0.5 else 11
                # identity guard
                if t not in tcache:
                    oS = np.unique(S[C == t])
                    osets = {o: np.unique(pack(C[S == o], X[S == o], Y[S == o])) for o in oS}
                    nsets = {r: np.unique(nP[nS == r]) for r in np.unique(nS[same])}
                    tcache[t] = (osets, nsets)
                osets, nsets = tcache[t]
                others = [o for o in osets if o != s_old]
                obytes = {osets[o].tobytes() for o in others}
                masq = {r for r in np.unique(pairs[:, 0]).tolist() if nsets[r].tobytes() in obytes}
                othset = np.unique(np.concatenate([osets[o] for o in others])) if others else np.zeros(0, np.int64)
                px = ((onf >> 21) & ((1 << 21) - 1)) - (1 << 20); py = (onf & ((1 << 21) - 1)) - (1 << 20)
                edge = (px == ex[0]) | (px == ex[1]) | (py == ex[2]) | (py == ex[3])
                idset = onf[~np.isin(onf, othset) & ~edge]
                okp = pairs[~np.isin(pairs[:, 0], list(masq))] if masq else pairs
                if not len(okp): guard[rows_s] = 22; continue
                idhit = okp[np.isin(okp[:, 1], idset)]
                if len(idhit):
                    guard[rows_s] = 20
                    rid = idhit[:, 0]
                    best = np.unique(rid)
                    id_share[rows_s] = max(int(np.isin(okp[okp[:, 0] == r, 1], onf).sum()) for r in best) / len(onf)
                else:
                    guard[rows_s] = 21
        for k in (3, 4, 5, 6):
            guard[status == k] = k
        status.tofile(f"output/scratch-39/shape/{basis}_{kind}.status.u8")
        best_share.tofile(f"output/scratch-39/shape/{basis}_{kind}.share.f32")
        guard.tofile(f"output/scratch-39/shape/{basis}_{kind}.guard.u8")
        os.makedirs("output/scratch-39/keep", exist_ok=True)
        np.savez_compressed(f"output/scratch-39/keep/{basis}_{kind}_keyed.npz", status=status, guard=guard, share=best_share, id_share=id_share,
                            **{k: cols[k] for k in ("level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert", "code")})
        res = {NAMES[k]: v for k, v in sorted(Counter(status.tolist()).items())}
        tested = (status >= 10) & (status <= 12)
        res["share_quantiles_where_shared"] = [round(float(q), 3) for q in np.quantile(best_share[(status == 10) | (status == 11)], [0.1, 0.5, 0.9])] if ((status == 10) | (status == 11)).any() else []
        GN = {3: "footprints_changed", 4: "new_leaf_missing", 5: "old_mapping_mismatch", 6: "old_leaf_missing", 13: "type_present_old_all_failing",
              14: "type_absent_removed", 20: "identity_proven", 21: "weak_identity_undetermined", 22: "none_after_neighbour_exclusion"}
        res["guard"] = {GN.get(k, str(k)): v for k, v in sorted(Counter(guard.tolist()).items())}
        res["guard_identity_proven_share_ge50"] = int(((guard == 20) & (id_share >= 0.5)).sum())
        out[f"{basis}:{kind}"] = res
        if kind == "background" and basis == "87a01b14":
            a01 = np.fromfile("output/scratch-39/classifyR01_pre311/assign_background.u16", dtype="<u2")
            out[f"{basis}:background_R01"] = {NAMES[k]: v for k, v in sorted(Counter(status[a01 == 0].tolist()).items())}
            out[f"{basis}:background_R01_guard"] = {GN.get(k, str(k)): v for k, v in sorted(Counter(guard[a01 == 0].tolist()).items())}
            out[f"{basis}:background_R01_guard_identity_proven_share_ge50"] = int(((guard == 20) & (id_share >= 0.5) & (a01 == 0)).sum())
            out[f"{basis}:background_non_R01_guard"] = {GN.get(k, str(k)): v for k, v in sorted(Counter(guard[a01 != 0].tolist()).items())}
            out[f"{basis}:background_non_R01"] = {NAMES[k]: v for k, v in sorted(Counter(status[a01 != 0].tolist()).items())}
        print(basis, kind, json.dumps(res), flush=True)
json.dump(out, open("output/scratch-39/shape/shape_clause_b.json", "w"), indent=1); print("SHAPEDONE")
