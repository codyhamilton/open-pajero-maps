#!/usr/bin/env python3
"""Plan 63 Phase 3: per-row producer + decide verdict for the 4,612 producer_ambiguous rows.

Per row (p6_producer/verdicts.tsv.gz, verdict producer_ambiguous) the group's copy (the row's shape)
gets its proven producer from the Phase 2 sidecar (provenance.tsv.gz, copy_shape == group_shape),
cross-checked against the accepted rule (rules.json; contiguous per-producer block emission,
re-evaluated here from dup_cases.tsv.gz with provenance.rule_keys). The decide verdict is the
unchanged phase-23 limb result for that candidate from ties_all.json (Phase 1). Output
verdicts_ambiguous.tsv.gz (gz mtime 0) + .json summary; every input sha recorded."""
from __future__ import annotations

import argparse, csv, gzip, hashlib, io, json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from provenance import rule_keys  # noqa: E402

SCOPE_DELTA = {(1481, 1288, 0), (1481, 1288, 2), (1753, 1158, 1), (1753, 1158, 2),
               (1754, 1158, 1), (1754, 1158, 3)}


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="prefix (.tsv.gz/.json)")
    a = ap.parse_args(argv)
    rules = json.loads((HERE / "rules.json").read_text())
    acc = [n for n, r in rules["rules"].items() if r["accepted"] and n == "contiguous_block_emission"]
    assert acc == ["contiguous_block_emission"], acc
    ties = json.loads((HERE / "ties_all.json").read_text())
    groups = {(g["leaf"][1], g["leaf"][2], tuple(g["leaf"][3]), g["shape"]): g for g in ties["groups"]}
    prov = {}
    with gzip.open(HERE / "provenance.tsv.gz", "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["group_shape"] == r["copy_shape"]:
                prov[(int(r["ix"]), int(r["iy"]), tuple(int(x) for x in r["path"].split(",")),
                      int(r["group_shape"]))] = r
    cases = defaultdict(list)
    with gzip.open(HERE / "dup_cases.tsv.gz", "rt") as f:
        next(f)
        for line in f:
            c = json.loads(line)
            cases[(c["leaf"][1], c["leaf"][2], tuple(c["leaf"][3]))].append(c)
    # per group: sidecar producer, rule prediction, candidate decide
    gres = {}
    for k, g in sorted(groups.items()):
        ix, iy, path, shape = k
        p = prov[k]
        side = (int(p["emitter_hx"]), int(p["emitter_hy"]), int(p["emitter_ri"]))
        case = [c for c in cases[(ix, iy, path)] if shape in c["copies"]]
        assert len(case) == 1, k
        c = case[0]
        pred = sorted((tuple(h) for h in c["hits"]), key=rule_keys(c)["contiguous_block_emission"])
        rule_p = pred[sorted(c["copies"]).index(shape)]
        hit = [h for h in g["hits"] if tuple(h["cid"][:3]) == side]
        assert len(hit) == 1, k
        gres[k] = {"producer": side, "rule": rule_p, "decide": hit[0]["decide"],
                   "decide_extra": hit[0]["decide_extra"], "class": g["class"],
                   "emitter_kind": p["emitter_kind"]}
    out_rows, cnt = [], Counter()
    hdr = None
    with gzip.open(a.verdicts, "rt") as f:
        rd = csv.DictReader(f, delimiter="\t")
        hdr = rd.fieldnames
        for r in rd:
            if r["verdict"] != "producer_ambiguous":
                continue
            d = int(r["depth"])
            k = (int(r["ix"]), int(r["iy"]), tuple(int(r[f"p{j}"]) for j in range(d)), int(r["shape"]))
            g = gres[k]
            agree = g["producer"] == g["rule"]
            cnt["rows"] += 1; cnt[f"rows_{r['kind']}"] += 1; cnt[f"rows_{g['class']}"] += 1
            cnt[f"verdict_{g['decide']}"] += 1; cnt["rule_agrees_sidecar"] += agree
            sd = (k[0], k[1], k[3]) in SCOPE_DELTA
            cnt["scope_delta_rows"] += sd
            out_rows.append([r["kind"], r["row_index"], r["level"], r["ix"], r["iy"], r["depth"],
                             r["p0"], r["p1"], r["p2"], r["shape"], r["vert"], r["code"], r["vx"], r["vy"],
                             g["class"], *g["producer"], g["emitter_kind"],
                             "sidecar" + ("+rule:contiguous_block_emission" if agree else ""),
                             g["decide"], json.dumps(g["decide_extra"], sort_keys=True), r["not_failing_4ed9cd80"]])
    out_rows.sort(key=lambda x: (x[0], int(x[1])))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(("\t".join(["kind", "row_index", "level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert",
                            "code", "vx", "vy", "tie_class", "producer_hx", "producer_hy", "producer_ri",
                            "emitter_kind", "producer_proof", "verdict", "decide_extra",
                            "not_failing_4ed9cd80"]) + "\n").encode())
        for r in out_rows:
            g.write(("\t".join(map(str, r)) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    cnt["groups"] = len(gres)
    cnt["groups_rule_agrees"] = sum(v["producer"] == v["rule"] for v in gres.values())
    summ = {"counts": dict(sorted(cnt.items())),
            "inputs": {"verdicts": fsha(a.verdicts), "ties_all": fsha(HERE / "ties_all.json"),
                       "provenance": fsha(HERE / "provenance.tsv.gz"), "rules": fsha(HERE / "rules.json"),
                       "dup_cases": fsha(HERE / "dup_cases.tsv.gz")},
            "output_sha256": hashlib.sha256(buf.getvalue()).hexdigest()}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
