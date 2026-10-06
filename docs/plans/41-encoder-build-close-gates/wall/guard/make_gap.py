"""Plan 41: account the post-fix wall gap above the pre-regression 33006aa wall, from measured runs only.
Inputs: 33006aa uninstrumented median (bench_table.json + build.log), guard-fix uninstrumented r1-r3 (bench.json),
instrumented profiles at 33006aa (prof/pre) and at the guard fix (guard/prof): per-stage C CPU summed over -j4 workers,
per-process name-guard time. Wall-equivalent = CPU delta x (uninstrumented C-CPU delta / instrumented C-CPU delta) / workers."""
import glob, json, statistics, collections
S = "/home/codyh/workspace/open-pajero-maps-14-completeness/output/scratch-41"
def prof(d):
    s = collections.defaultdict(float)
    for f in glob.glob(d + "/prof.*.tsv"):
        for l in open(f):
            a = l.split("\t")
            if a[0].isdigit(): s[int(a[0])] += float(a[1])
    return s
def lv(b, key): return sum(v[key] for v in b["levels"].values())
bt = {r["commit"]: r for r in json.load(open(S + "/bench/bench_table.json"))}
pre_wall = bt["33006aa"]["median"]
runs = {r: json.load(open(f"{S}/guard/runs/{r}.json"))["wall_s"] for r in ("r1", "r2", "r3")}
med_run = sorted(runs, key=runs.get)[1]; post_wall = runs[med_run]
bp = json.load(open(f"{S}/guard/{med_run}/bench.json"))
ppre, ppost = json.load(open(S + "/prof/pre/bench.json")), json.load(open(S + "/guard/prof/bench.json"))
cpre, cpost = prof(S + "/prof/pre/pf"), prof(S + "/guard/prof/pf")
names = {1: "eo_clip stage 1: segment sweep (pair intersections)", 2: "eo_clip stage 2: eo_left per-chain side checks (residual after a95501c prefilter)",
         3: "eo_clip stage 3: whole-ring duplicate-vertex check", 4: "eo_clip stage 4: successor tie check", 5: "eo_clip stage 5: complex EO face path",
         6: "chains()"}
d_stage = {names[k]: cpost[k] - cpre[k] for k in names}
d_stage["bg_shape rest (outside eo_clip and chains)"] = (cpost[0] - sum(cpost[k] for k in names)) - (cpre[0] - sum(cpre[k] for k in names))
c_unins_post = lv(bp, "c_s"); c_ins_post = lv(ppost, "c_s"); c_ins_pre = lv(ppre, "c_s")
# 33006aa had no uninstrumented bench.json; its instrumented C CPU (no eo_clip; 1 timer pair per bg_shape) is the baseline.
d_c_unins = c_unins_post - c_ins_pre; d_c_ins = c_ins_post - c_ins_pre; scale = d_c_unins / d_c_ins
W = bp["levels"]["0"]["workers"]
guard = collections.defaultdict(list)
for f in glob.glob(S + "/guard/prof/pf/guard.*.tsv"):
    for l in open(f):
        a = l.split("\t"); guard[int(a[0])].append(float(a[1]))
pre_levels = bt["33006aa"]["level_median_s"]; post_levels = {k: v["wall_s"] for k, v in bp["levels"].items()}
out = {"pre_commit": "33006aa", "pre_wall_median_s": pre_wall, "post_commit": "c82f92e (guard fix on 87f78fe, contains a95501c)",
       "post_wall_median_s": post_wall, "post_runs_s": runs, "gap_s": post_wall - pre_wall,
       "by_level_wall_s": {k: {"pre": pre_levels.get(k), "post": round(post_levels[k], 2)} for k in sorted(post_levels, key=int)},
       "outside_encode_s": {"pre_assemble_median": bt["33006aa"]["assemble_median"], "post": round(bp["outside_encode_s"], 2)},
       "c_cpu_s": {"pre_instrumented": round(c_ins_pre, 2), "post_instrumented": round(c_ins_post, 2), "post_uninstrumented": round(c_unins_post, 2),
                   "instrumentation_scale": round(scale, 3)},
       "c_cpu_delta_by_stage_instrumented_s": {k: round(v, 2) for k, v in d_stage.items()},
       "c_wall_equiv_delta_by_stage_s": {k: round(v * scale / W, 2) for k, v in d_stage.items()},
       "python_cpu_s": {"pre_L0_py": round(ppre["levels"]["0"]["py_s"], 2), "post_L0_py": round(bp["levels"]["0"]["py_s"], 2),
                        "pre_L0_prepass": round(ppre["levels"]["0"]["prepass_s"], 2), "post_L0_prepass": round(bp["levels"]["0"]["prepass_s"], 2)},
       "name_guard_s_per_process": {str(k): [round(x, 3) for x in sorted(v)] for k, v in sorted(guard.items())},
       "note": "Stage CPU from CLOCK_MONOTONIC timers in an instrumented copy (bytes unchanged, sha 4e6b0de7); counts lose <=4095 calls per worker (flush cadence). Wall-equivalent assumes the -j4 pool's C time parallelises evenly; level walls and outside_encode are measured directly."}
# Additive accounting. The level wall is E1 stage wall (`prepass_s`: the E1 pool run plus the parent's sort/split) +
# E2 stage wall. The plan 29 name guard runs inside the E1 workers (E1Spool(guard_names=True), once per process per
# level on its first E1 job), so its wall share is inside the E1-stage delta and its CPU is inside E1 `py_s`; it is
# NOT added again (an earlier draft added py_s/W as well and double-counted ~1.1 s). The E2-stage growth is the
# bg_shape C time, apportioned by stage.
ws = sum(out["c_wall_equiv_delta_by_stage_s"].values())
e1d = bp["levels"]["0"]["prepass_s"] - ppre["levels"]["0"]["prepass_s"]
out["accounting_s"] = {"C bg_shape stages (wall-equiv, E2 stage, all levels)": round(ws, 2),
                       "L0 E1 stage delta (contains the worker name guard)": round(e1d, 2),
                       "outside_encode delta": round(bp["outside_encode_s"] - bt["33006aa"]["assemble_median"], 2)}
out["accounting_s"]["sum"] = round(sum(out["accounting_s"].values()), 2)
out["accounting_s"]["residual_vs_gap"] = round(out["gap_s"] - out["accounting_s"]["sum"], 2)
gl0 = guard[0]
out["name_guard_in_E1"] = {"L0_per_process_s": [round(x, 3) for x in sorted(gl0)], "L0_mean_s": round(sum(gl0) / len(gl0), 3),
                           "note": "the 4 workers run it concurrently on their first L0 E1 job, so its wall share is ~ the per-process time, bounded by the measured E1-stage delta",
                           "L0_py_cpu_delta_s": round(bp["levels"]["0"]["py_s"] - ppre["levels"]["0"]["py_s"], 2),
                           "L0_guard_cpu_s": round(sum(gl0), 2)}
# Reconciled partition: the directly measured parts (E1 stage, outside encode) stay as measured; the C stage parts are
# scaled by one common factor so the partition sums to the measured gap (the factor is the even-parallelism error).
pool = {k: v * scale / W for k, v in d_stage.items()}
direct = {"L0 E1 stage: plan 29 name guard": round(e1d, 2), "outside encode": out["accounting_s"]["outside_encode delta"]}
f = (out["gap_s"] - sum(direct.values())) / sum(pool.values())
rec = {k: round(v * f, 2) for k, v in pool.items()}; rec.update(direct)
out["reconciled_partition_s"] = {"pool_scale": round(f, 4), "parts": rec, "sum": round(sum(rec.values()), 2)}
lvd = {k: round(post_levels[k] - pre_levels[k], 2) for k in post_levels if pre_levels.get(k) is not None}
out["by_level_delta_check_s"] = {"levels": lvd, "levels_plus_outside": round(sum(lvd.values()) + out["accounting_s"]["outside_encode delta"], 2), "gap": round(out["gap_s"], 2)}
json.dump(out, open(S + "/guard/gap_table.json", "w"), indent=1)
print(json.dumps(out, indent=1))
