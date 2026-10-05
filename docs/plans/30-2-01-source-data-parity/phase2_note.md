# Phase 2 disposition and Execute handoff

The implementation is ready for guarded source probes. The worker-built `disposition.tsv` has **342** joined native keys and verdict counts **0 supply-path / 0 unfixable-proven / 342 conflict-open**. Every row names the measured retained demander and lattice discriminator, and the two pending source discriminators. This is a reproducible pending baseline, not a negative supply finding or a completed Phase 2 outcome.

The light inventory reproduced the Phase 1 **341 × 288 + 1 × 321 (246)** census and the **341** aligned template members. Row 246 is separate. Both G pins and all demanded-type counts are required to have Phase 1's measured `disc-verified` state. The generated summary enumerates every member of the 288 stratum, every open row with tried discriminators, and row 246's full record.

Candidate scores and the selected **(a)+(b)+(c)** combination are in `phase2_candidates.md`. Actual source availability is unmeasured. Neither the lattice nor the retained demander proves that another OSM polygon cannot supply presence. A wrong-code emitter is an alternate-type observation, never a demanded-code supply.

## Commands for Execute

Run sequentially from `/home/codyh/workspace/open-pajero-maps-14-completeness`. The wrapper takes `output/.heavy.lock`, records argv and cgroup `memory.peak`, and fails if accounting is absent. Probe outputs, exhaustive event logs, compile artifacts and the PBF cache are under `output/scratch-30/`.

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2_inventory.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py inventory --output output/scratch-30/disposition_inventory.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2_spool.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py spool --spool output/extract_timing/spool --output output/scratch-30/disposition_spool.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2_pbf.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py pbf --pbf /home/codyh/workspace/open-pajero-maps/australia-260824.osm.pbf --cache output/scratch-30/p2_pbf_cache_01 --output output/scratch-30/disposition_pbf.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2_publish.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py publish --inventory output/scratch-30/disposition_inventory.json --spool-json output/scratch-30/disposition_spool.json --spool-run output/scratch-30/runs/p2_spool.json --pbf-json output/scratch-30/disposition_pbf.json --pbf-run output/scratch-30/runs/p2_pbf.json
```

The PBF command requires a **fresh cache directory**. On a retry, use a new suffix such as `p2_pbf_cache_02`; it refuses to reuse a partially populated database. Disk use scales with the node catalogue and relation member geometry. Resident geometry is bounded by the per-source caps and fixed SQLite cache. No AU spool/disc is generated.

If the spool probe already has positives but the PBF query is still pending, Execute can publish that measured partial result by omitting both `--pbf-json` and `--pbf-run`. Supply witnesses publish; all remaining negatives stay `conflict-open`. A failed probe or failed memory-accounting wrapper must not be supplied to publish.

`publish` validates exact native-key and dump-row sets, Phase 1 pins and zero counts, fingerprint/summary/member/script hashes, search windows, successful wrapper outputs and peaks, all light/runtime dependency hashes, and the full streamed proof-event SHA256. It reconstructs candidate/emitter counters and the chosen witness from the event log, rejecting disagreement with the probe summary. Heavy input hashes are carried from the probes; publish never reopens spool or PBF. Probe hashing uses 1 MiB chunks and requires file identity/size/time stamps to remain unchanged through the scan. All validation precedes changes to either publication file.

## Evidence shape after the probes

For every member, `discriminator_records` contains retained demander evidence, aligned-grid identity, per-code candidate/emitter counts and grid-coincidence counts for each completed probe, row-specific gap state, and unresolved discriminators. `proof_paths` names the Phase 1 and inventory evidence and the exhaustive probe event logs. Each event identifies the source, source-coordinate SHA256, independent clip/densify/round result, and production-C byte/record counts for the three variants.

An emitting demanded-code source records `production_C_counterfactual` and `successor_implement_path`; publication selects a spool witness first when both probes supply one. A template negative can settle only with both source scans and no gap affecting that member. Alternate-code emitters are named in the unfixable proof. The summary lists a uniform 288 disposition or exhaustive split groups by verdict/cause. Row 246 is never incorporated into the lattice disposition. A non-degenerate correct-code source with only negative probes keeps its representability question open.

Unknown/missing geometry, nested relations, invalid relation topology and explicit resource limits affect negative verdicts conservatively. Their full source IDs and affected member lists are in the event logs; each affected row names the failing discriminator and its gap classes. A positive C witness still supplies presence despite unrelated gaps. Further bounded discriminators are required for any residual `conflict-open`; do not weaken the negative gate to obtain zero.

Execute owns the OVERVIEW narrowing and phase record. `disposition_summary.json` provides a count-based `overview_handoff` sentence. Seven O04 spool rows remain outside this set. Nothing here closes plan 04 Phase 3, changes vocabulary/extraction/encoding, reruns 3-90, or reseats 170/3-16/3-17.

## Worker verification

```bash
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_parity_disposition.py --basetemp output/scratch-30/tests/p2
```

**36 passed in 5.38s.** Tests use invented TSV/JSON, freshly created tiny spool/PBF inputs and a compiled production-C probe. They cover aligned-grid identity and exceptions, required Phase 1 pin state, square/line/mult probes, reverse relation members and inherited tags, holes, missing/open/branched/nested relations, bounded index reads and malformed cells, a distant spool source cell, demander pins, wrong-code emitters, positive evidence despite gaps, the separate row-246 ceiling, stale/partial/forged joins and wrapper evidence, unchanged publication on rejection, native-C vertex limits, rejection of fully bounded remote relations before topology work, and the prohibition on heavy reads during publication.

The real-data inventory and baseline publish exited 0 using only Phase 1 TSV/JSON and checked-in grid data. **No retained spool, production PBF, ALLDATA.KWI or R disc was opened.** Only the new synthetic test file was run. The concurrent plan-29 close-out surfaces were neither touched nor run. Changes remain uncommitted.

## Execute measured result (2026-10-06, guarded)

Run chain `output/scratch-30/run_p2.{sh,log}`; all four steps exit 0 under `run_heavy_python.py` (lock held, one heavy job).

| Step | wall s | cgroup memory.peak |
|---|---|---|
| inventory | 0.1 | 31 MB |
| spool (432,295 cells, 7,546,320 backgrounds, scan complete, 0 gaps) | 283.7 | 575 MB |
| pbf (`australia-260824.osm.pbf`, cache `p2_pbf_cache_01`) | 2,382.5 | 6.05 GB (page cache incl.; max RSS 258 MiB) |
| publish | 0.7 | 41 MB |

Published counts: **243 supply-path / 0 unfixable-proven / 99 conflict-open** (status `incomplete`; `disposition.tsv` sha256 `67c0f285…`, summary `0051c538…`).

- Spool: 0 supply witnesses; every row has demanded-code candidates but no production-C emitter.
- PBF: 243 supply witnesses, all **OSM boundary relations** (`type=boundary`; marine parks / habitat zones; e.g. relation 8601872 Coral Sea Habitat Protection Zone ×94, 8602576/8602574 South-west Corner AMP ×44/×34, 8602315 Gascoyne AMP ×28, 8602594 Abrolhos AMP ×23). Successor path: assemble the relation from member nodes, inherit tags, even-odd holes, retile; a separate implement unit, then re-oracle.
- 99 conflict-open (98 type-288, 85 of them south_offshore; plus row 246 type 321): `supply discriminator incomplete`. The PBF scan has coverage gaps that touch their windows (7,922 missing/nested relation members, plus small vertex/edge/member-limit counts). Each row names the discriminators tried.
