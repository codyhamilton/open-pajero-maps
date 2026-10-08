# Tracked background producer scan: 8,876 identities + per-row cause (R-G5-1, R-G5-2, R-G8-4-c)

Plan 46 rebuilt the row identities of the classify remainder (137 background + 8,739 background_boundary) on the
3C-04 / `013586b5` basis with a tracked producer scan. It discharged **R-G8-4-c** and the proven part of
**R-G5-1 / R-G5-2** (4,214 rows `build:eo_bg_stitch`). The rest is carried by exact children
**R-G5-1-a** (4,594 producer_ambiguous), **R-G5-1-b** (50 source-removed) and **R-G5-2-a** (18 producer_ambiguous),
all still `blocks-phase3`.

There was no encoder or oracle change: live AU `0c22b266…` / Perth `5b86d33e…` are unchanged. Not done here:
Phase 3 product close, waivers, F6 / kind-order / L8 changes.

## Intent
Cody ruling 1 (2026-10-06): design a new tracked producer scan that rebuilds row identities against the committed
3C-04 basis. Each row then gets a proven cause or is named as a residual. Design ruling (2026-10-08 09:24, option b)
re-baselined the S02-dependent gate figures.

## Why This Existed
The side columns behind the historical remainder came from 3-07/3-11/3-12 scratch producers that were deleted
(`pin_producers_attempt3.py` was never committed; `output/scratch-3-07` is gone). Row identities were therefore not
reproducible and R-G5-1 / R-G5-2 / R-G8-4-c could not be decided.

## What Was Built

**Tooling:**
- `parser/tools/bg_producer_scan.py` + `_bg_producer_scan.c`: a streaming, sharded scan with an RssAnon watchdog. The
  producer clipper is the disc's own encoder (33006aa).
- Opt-in helpers in `bg_owner_exclusive.py` and `leaf_io.py` (piecewise match, divided-leaf frames).
- `dump_join.py` now refuses an undeclared appended field.
- `run_heavy_python.py` gained the cgroup memory cap.
- `p6_producer/`: `gate_repro.py` (default `--s02-scope full`), `phase23.py` (identity/decide; deterministic gz),
  `s02_list.py`, `tie_probe.py`.

**Root causes fixed in the scan** (each one moved a gate figure; none absorbed):
- RC0: producer encoder pin;
- RC0b: explicit-closure artefact;
- RC1: byte-145 layout;
- RC2: per-piece byte match;
- RC3: far producers (K1 tall bbox-meet);
- RC4: divided-leaf clip rect;
- RC5: same-type producer;
- RC6: edge length in raw units.

### Phase 1 gate (Design ruling b)
| Figure | Retired 3-07 | Baseline (full S02 predicate) | Status |
| --- | --- | --- | --- |
| remainder fill / bnd | 137 / 8,739 | 137 (11 g) / 8,739 (169 g) | exact |
| cls2 R01 | 920,786 | 920,786 | exact |
| S03 rows / bg st1 groups / bg rings | 517,648 / 30,547 / 24,731 | same (rings from v5) | exact |
| res fill groups | 30,558 | 30,558 | exact |
| S02+S04 spool rows | 16,541,304 | 11,127,333 + 5,413,971 | exact |
| S02 scope | 145,960 / 11,127,845 | same | exact |
| S02 = S | 1,939,053 / 25,772 | **11,127,333 / 145,954** | new baseline |
| res entries | 425,416 | **305,231** (+3 cover) | = 451,185 − \|S\| + 3 |
| res bnd groups / S04 groups | 216,488 / 216,319 | **204,123 / 203,954** | = 219,201 / 219,032 − a(S), a = 15,078 |
| res rings | 70,999 | **70,861** | inside feasible range |

**Root cause for every S-dependent delta.** The historical figure is a proven function of S, and the 3-07
attempt-3 pin-stop S was never recorded. The identities are validated on v4, v5 and the full predicate. The
historical a(S) = 2,713 is implied independently by both res-bnd and S04, and the historical rings lie inside the
feasible range.

Out-of-order (parallel) block completion of the pin-stop walk is recorded **only as an unproven hypothesis**.
`gate_result_full.json` `cover_bound` compares against the retired 3-07 figures; its `false` is not a gate.

**S committed:** `p6_producer/s02_full_predicate_groups.tsv.gz`, TSV sha `ae2ce385…`, gz `7ab5a029…`, with
generator `s02_list.py`. **Double run** (scan v5 + gate A, versus an independent scan B + gate B): all data artefacts
byte-identical, as are the gate JSON, S and the identity table. The only differing file is the work-dir path string
inside `dump_manifest.json`.

**Scope vs predicate delta (6 groups / 512 rows):** all `producer_ambiguous`, meaning two same-type candidates
byte-hit the record (`p6_producer/ties.json`, which includes per-piece evidence).

| Group (shapes) | Candidates | Whole clip blob | Outcome |
| --- | --- | --- | --- |
| (1753,1158,p217) 1, 2 | (1755,1157,1), (1755,1157,2) | identical | **proven-producer-tied**; tie-break (1755,1157,1) |
| (1481,1288,p265) 0, 2 | (1485,1280,0), (1486,1280,0) | differ | **open, RC owed** |
| (1754,1158,p218) 1, 3 | (1755,1157,1), (1755,1157,2) | differ | **open, RC owed** |

RC evidence for Design: in the open leaves the two shapes are byte-identical duplicate records. Each candidate emits
one copy plus a distinct second piece that is also on disc. This fits "one copy per producer" but is not proven.

### Phase 2: identities (R-G8-4-c discharged)
`p6_producer/identity_remainder.tsv.gz`: 8,876 rows, sha `96093444…`, content `28cb90fb…`. Double run identical.

### Phase 3: per-row decisions
`p6_producer/verdicts.tsv.gz` (sha `ca4a555a…`; decide run twice, identical). Old disc 013586b5, new disc 4ed9cd80,
exclusivity clipper d35b565, R=8 plus far bbox-meet.

| Kind | Verdict | Rows / groups | Row |
| --- | --- | --- | --- |
| background | build:eo_bg_stitch | 119 / 9 | R-G5-2 (discharged part) |
| background | producer_ambiguous | 18 / 2 | R-G5-2-a |
| background_boundary | build:eo_bg_stitch | 4,095 / 72 | R-G5-1 (discharged part) |
| background_boundary | producer_ambiguous | 4,594 / 96 | R-G5-1-a |
| background_boundary | source-removed (producer (1751,594,16) clips empty on d35b565) | 50 / 1 | R-G5-1-b |

### Memory
| Run | Max shard RssAnon | Max RSS | cgroup peak |
| --- | --- | --- | --- |
| Scan v5 | **928.6 MiB** (cap 3072) | 4.39 GiB | 4.69 GB |
| Re-baseline double run | – | 7.55 GiB | 7.85 GB |
| phase23 | – | 3.7 GiB | 6.10 GB |

All runs were under `run_heavy_python --memory-max 12G` + flock. Recorded in the plan-56 ledger
(`ledger/bg_producer_scan_plan46.json`, SUMMARY row).

Tests:
- 41 passed: `test_bg_producer_scan`, `test_bg_owner_exclusive`, `test_dump_join_memory`, `test_perf_inventory`;
- 114 passed: the dump_join / leaf_io / s02 / memory-guard / k1_triage modules.

## Review
Flash (`deepseek/deepseek-flash`): **LAND**, claims A–G pass. Non-blocking hygiene items, resolved in this close-out:
- IMPLEMENTATION status lines: the folder is collapsed into this record.
- The record path is now present.
- The per-piece tie evidence is committed as `p6_producer/ties.json`.
- The test counts are stated per file set above.
- The `cover_bound` false is explained above.

## Residual Risks
- R-G5-1-a / R-G5-2-a (98 groups) need a Design tie rule beyond whole-blob identity. There must be no nearest-ring
  choice.
- R-G5-1-b: the d35b565 clip of the unique producer is empty. Whether the record is removed or re-produced by
  another source is not established.
- The 4 open scope-delta groups owe an RC (they are outside S and do not move any gate figure).
- The 3-07 S-dependent figures are retired, not reproduced. The pin-stop S is unrecoverable.

## Follow-ups
Design: a tie/duplicate-record rule for producer_ambiguous (the duplicate-copy evidence in `ties.json`), and
R-G5-1-b. Plan 62 is not started.

Scratch: `output/scratch-46/` (scans, gate work dirs, probes, run logs, Flash review; regenerable).
