#!/usr/bin/env python3
"""Plan 62 Phase 2 summary: transitions.json (old->new with RC attribution) and audit.json
(same-type audit of the 87,743 proven rows) from redecide.tsv.gz; cross-check against the
phase23 decide run (verdicts_census.tsv.gz); 'joint' attributions resolved from u4f_probe.json."""
import csv, gzip, json, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p6_producer")]
from phase23 import sha, relp  # noqa: E402
H = Path(__file__).resolve().parent
RED, VER, U4F = H / "redecide.tsv.gz", H / "verdicts_census.tsv.gz", H / "u4f_probe.json"
VMAP = {"build:eo_bg_stitch": "build", "source-removed": "source-removed", "producer_ambiguous": "ambiguous",
        "no-owner-exclusive-vertex": "no_oe", "removed": "removed",
        "producer_home_outside_R_cap": "outside"}


def main():
    u4f = json.loads(U4F.read_text())
    u4f_leaf = tuple(str(v) for v in u4f["leaf"][:3]) + (".".join(map(str, u4f["leaf"][3])),)
    ver = Counter()
    with gzip.open(VER, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            d = int(r["depth"])
            ver[(r["level"], r["ix"], r["iy"], ".".join(r[f"p{j}"] for j in range(d)), r["shape"],
                 VMAP[r["verdict"]])] += 1
    trans, attr, audit, xchk = Counter(), Counter(), Counter(), Counter()
    ties, sr = [], []
    with gzip.open(RED, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            n = int(r["n_rows"]); par = r["parent"]; oc, nc = r["old_class"], r["full_class"]
            trans[f"{par}|{oc}|{nc}"] += n
            at = r.get("attribution") or ""
            if at == "joint" and (r["level"], r["ix"], r["iy"], r["path"]) == u4f_leaf \
                    and int(r["shape"]) == int(u4f["shape"]):
                at = "U4F_RING"
            if r["mode"] != "audit":
                attr[f"{par}|{oc}|{nc}|{at}"] += n
            else:
                audit[f'{r["audit"]}|{nc}'] += n
            k = (r["level"], r["ix"], r["iy"], r["path"], r["shape"])
            cf = json.loads(r["configs"])
            if r["mode"] != "ceiling":
                xchk[int(ver.get(k + (nc,), 0) == n)] += n
            if nc == "ambiguous":
                ties.append({"leaf": [int(r["level"]), int(r["ix"]), int(r["iy"]), r["path"]],
                             "shape": int(r["shape"]), "rows": n, "tie_decide": cf["FULL"].get("tie_decide")})
            if nc == "source-removed":
                sr.append({"parent": par, "leaf": [int(r["level"]), int(r["ix"]), int(r["iy"]), r["path"]],
                           "shape": int(r["shape"]), "rows": n, "old_class": oc,
                           "producer": cf["FULL"]["pid"], "clip_size_d35b565": cf["FULL"].get("sz")})
    tj = {"transitions": dict(sorted(trans.items())), "attribution": dict(sorted(attr.items())),
          "attribution_method": "single-fix ablation over ALL residual groups (exhaustive, not a sample): a "
                                "transition is attributed to each RC whose single removal from FULL reverts the "
                                "row to its plan-44 class; skip->X is RC4 by construction; U4F_RING = plan 44 "
                                "Unit 4f picked the first ring in the producer home (u4f_probe.json); RC6 moves "
                                "no class (mechanism bit only)",
          "phase23_crosscheck_rows": {"agree": xchk[1], "disagree": xchk[0]},
          "ambiguous_groups": ties, "source_removed_groups": sr,
          "inputs": {"redecide": [relp(RED), sha(RED)], "verdicts_census": [relp(VER), sha(VER)],
                     "u4f_probe": [relp(U4F), sha(U4F)]}}
    (H / "transitions.json").write_text(json.dumps(tj, indent=1) + "\n")
    aj = {"proven_rows": sum(audit.values()), "by_tag_fullclass": dict(sorted(audit.items())),
          "definition": "PLAN44 matcher config (no type filter, whole-blob, Moore(recover_r), full-frame rect) "
                        "re-run on every plan-44 build group: producer type (cid tc) == record code => same_type; "
                        "FULL (plan-46) class recorded alongside",
          "inputs": {"redecide": [relp(RED), sha(RED)]}}
    (H / "audit.json").write_text(json.dumps(aj, indent=1) + "\n")
    print(json.dumps({k: tj[k] for k in ("transitions", "attribution", "phase23_crosscheck_rows")}, indent=1))
    print(json.dumps(aj["by_tag_fullclass"]), len(ties), len(sr))


if __name__ == "__main__":
    main()
