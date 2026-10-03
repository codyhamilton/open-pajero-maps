# Completeness remainder 3-15 — cell-local representability (+37 post-3-14 honesty)

Unit 3-15 (Science; Codex/DeepSeek seat). Brief: [briefs/3-15-completeness-cell-local.md](../briefs/3-15-completeness-cell-local.md).
Base `adfbdbd` (descends from 3-14 `414c5fe`). Scratch evidence: `output/scratch-3-15/` (git-ignored).
Updates only the completeness cause/notes; no S02–S05 predicate edited; no rule registered.

## C1–C4 (pre-edit checks)

- **C1 PASS.** Tip `adfbdbd` contains 3-14 `414c5fe`. AU disc in force `4ed9cd80…`; Perth `04be2f6e…`.
- **C2 PASS with correction.** 188-key list at `scratch-3-12/small_hypotheses.jsonl`; pre-3-14 dump `scratch-3-11/dump_new_ext/completeness.bin` (739 rows); post-3-14 `scratch-3-14/dump_ext/completeness.bin` (776 rows). Total 776 and net +37 confirmed, **but the key-level set-diff is 687 shared + 89 added + 52 cleared (739 − 52 + 89 = 776), not a 37-key superset.** All 188 historic keys are present in both dumps.
- **C3 PASS (partial).** O01/O04/O05/O06 load from `rules_other.json`. Classify CLI still aborts on the empty residual dump (`k1_triage._memmap`, zero-row mmap); the completeness dump is non-empty. Causes were recomputed spool-side, not via a full classify CLI run.
- **C4 PASS (caveat).** Baseline from `scratch-3-14/k1_full.json`: completeness **776**, name_anchor **1**, background / background_boundary / interior_cover / road_node / range / step **0**. The 9,064 unattributed + PARTITION FAIL is not claimed live without re-classify.

## Measurements

### Historic 188 — complete topology repair = checker

`representability_188.py`: for each of the 188 keys, every class-2 meeting source ring was decomposed into its even-odd simple faces with the 3-13 exact rational arrangement (`scratch-3-13/split.py` `decompose`), then each face was run through the builder clip/densify/round contract (C `bg_shape` and an independent Python reimplementation). Result: **885 repaired faces across 189 meets; 205 faces clip into the target cell; 0 yield non-zero quantised area2; 0 emit C records — original or repaired.** The sources are sub-unit-width slivers (in-cell face widths 0.01–0.05 raw lattice units over a 4096-unit span) that `rint` annihilates. Named outcome: **`checker:repaired-not-representable` ×188**. Harness control reproduces the stored 3-08 clip bytes (725/781; 16/16 positive controls). Supersedes the 3-08 one-coordinate-repair stop for this set.

### +37 (89 added / 52 cleared) — EO-stitch side-effect

Contract comparison (`contract_comparison.json`), original meeting rings, legacy pre-3-14 probe vs 3-14 stitch probe:

| set | n | legacy records>0 | stitch records>0 | disposition |
| --- | ---: | ---: | ---: | --- |
| added (post-only) | 89 | **89** | **0** | EO-stitch side-effect (build regression): all 89 satisfied by the pre-3-14 encoder, dropped by the stitch |
| cleared (pre-only) | 52 | 5* | **52** | EO-stitch side-effect: now satisfied by the stitch |
| historic | 188 | 0 | 0 | checker (unchanged) |

\* the 5 legacy positives are a frame artifact (nominal L0 vs builder spool-degrees frame); in the builder frame all 52 were legacy O04 with `clip_bytes==0`. Not byte-pinned per cell: no window CF was run; the attribution is contract-level.

## Recount on the 3-14 disc (no silent remainder)

Post 776, 3-14 stitch contract (recomputed spool-side; the 3-14 dump's `other_mechanism` bytes are inherited/forced-zero artifacts — 30 O05 and 1 O04 on `AU.differing_cells.tsv` cells were zeroed):

- **776 = O01 363 + O05 132 + O04 7 + unattributed 274**, remainder 0.
- Derivation: shared 687 `{O01 363, O05 132, O04 4, unattributed 188}` + added 89 `{O04 3, unattributed 86}`.
- Movement: pre 739 = 687 shared + 52 cleared; post 776 = 687 shared + 89 added.
- Legacy-contract recomputation (3-08 probe) reproduces pre 739 exactly: O01 363 / O05 132 / O04 56 / unattributed 188.
- The 274 unattributed are all `checker:repaired-not-representable` under the complete-repair test (188 historic + 86 added; the 3 added O04 are likewise not representable after repair). No count is absorbed into O01/O04/O05.

## Candidate rule (not registered)

The 188 (+86 added) are a checker over-demand witnessed only by the complete-topology-repair test; the existing side-table mechanism codes O01/O04/O05 do not express it. A future **O07 "checker: complete-repair still not representable"** is recorded as a candidate. It is **not** added to `rules_other.json` here: the mechanism code has no producer in the current side-table pipeline, and the brief's Science-first gate (b byte-gate window CF, c Design amendment) is unmet. No checker/encoder fix is proposed.
