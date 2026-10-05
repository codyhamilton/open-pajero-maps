# Phase 1 fingerprint census

The light census measures **341 × code 288 + 1 × code 321**, over all 342 native keys. The type-321 row is dump_row **246**, L0 `(834,886)`. The plan-28 rule join is **O01: 340**, **O05: 2** (246 and 567). Native keys and dump rows are checked against both `phase3_membership.tsv` and `per_rule_phase2_join.tsv`; each proof and requirement witness must match the same key and dump row. Closed triage TSVs are read only.

`fingerprint.tsv` has the full 13-field native key and separate R slot-matching and cell-local polygon counts. R counts, vertex lists and per-polygon bboxes cover every matching polygon in the decoded covering slot, including the closing vertex. Bboxes use `[lat_min,lat_max,lon_min,lon_max]`; `R_bbox_lat_lon` is their union. `R_cell_local_meets` retains the proof's leaf path, vertex count, bbox-cell and branch information, so slot presence is distinguishable from cell-local presence. The type-321 outlier has **11** matching polygons, **one** cell-local meet (branch **a**, 28 vertices), and matching vertex counts `[21,33,37,58,19,23,17,28,10,33,19]`. It receives `not-288`, independently of the template cohort.

All **341/341** type-288 members have one matching, cell-local polygon with **13** decoded coordinates, branch **c**, and spans **1/12° latitude × 1/8° longitude** (5′ × 7.5′). Each span must differ from that exact target by at most **1e-9 degrees**, an absolute tolerance. Every member matches one of the two measured local sequences; **template exceptions: 0**.

The signature is the complete decoded vertex sequence, with each latitude normalised by `(lat-lat_min)/lat_span` and longitude by `(lon-lon_min)/lon_span`, rounded to **nine decimal places** in bbox units. Closure, start vertex and winding are retained; there is no rotation or reversal to force a match. The two most frequent qualifying sequences are labelled T1 and T2 in descending frequency, with lexical ordering to break ties; any further sequence or failure of the 13-vertex/span checks is `other` and its dump row is listed. The summary records both complete sequences and the SHA256 of their compact JSON representation.

| Signature | Members | First normalised (lat,lon) | Sequence SHA256 |
| --- | ---: | --- | --- |
| T1 | 191 | `(1,0)` (north-west) | `a2d6484aa79ffb5c9c9a60c0c27e192ffe58036427570a5f09c6cba3686eb2dd` |
| T2 | 150 | `(0,0)` (south-west) | `6c708c999ac155a01e0e763c9d82b075e61276c9dee5abcf4875c47ce093bd56` |

Both sequences have signed doubled area **+2** with longitude as x and latitude as y, hence the **same counterclockwise winding**, with different start corners. This corrects the design's Ground phrase suggesting opposite winding; the measured counts and two-sequence result agree with Ground.

Geographic labels use the midpoint of the union R bbox, in this order: `west` if longitude <113; `east` if longitude >153.5; `south_offshore` if latitude <−35.5 and 113≤longitude<130; otherwise `other`. The south label is a conservative south-of-WA window, with no coastline intersection test. These are descriptive inputs for Phase 2, with no disposition attached: **west 85, east 86, south_offshore 129, other 42**. The code-321 row is `other`.

Spool demander identity comes directly from the requirement witness: source cell, background ordinal, byte offset/length and source-cell SHA256, with trigger information retained. The existing proof supplies the clip/emit summary. All 342 rows retain `encoder_drops_clipped_source_sliver`, branch **b**, `area2=0`, and `encoder_emits=False`; neither source geometry nor clip science was re-derived. This does not settle whether another OSM source could supply presence.

`fingerprint_summary.json` records SHA256 for all **688** census inputs: the script, three TSVs, 342 coordinate proofs and 342 requirement witnesses. Hashes cover exactly the bytes parsed for TSV/JSON. These are retained scratch-14 R proofs, not a fresh R-disc read or fresh validation of the R pin. No ALLDATA.KWI, R disc or spool was opened by the unit worker.

Historical G counts are **0 for all 342** from the membership TSV, checked against the retained proof JSON. Their status is `retained-proof;pending-disc-control`. Successor G count/hash columns remain empty with status `pending-disc-probe`. These states are intentional: Phase 1's disc verification remains for Execute.

The Execute-only `--disc` command first validates the full SHA256 by streaming 1 MiB chunks, then uses existing volume, frame, parcel and shape decoders with a bounded LeafIndex (64-entry leaf-list LRU). Metadata, management records and individual leaf frames use `os.pread`, each capped at 64 MiB; unbounded, oversized, short or out-of-file reads fail. Management-record parse errors propagate rather than masquerading as absence. Counts follow the historical slot contract: demanded code, class 2, at least three coordinates. Decoded geometry is discarded per leaf; only counts/keys/statuses are retained. The disc must remain unchanged during hashing/probing. Output is restricted to `output/scratch-30/`; loaded repo decoder dependencies and profile JSONs are hashed in the probe output. The heavy wrapper supplies the lock, argv log and memory.peak.

Execute runs these sequentially from the repository root:

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/g_successor.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/fingerprint.py --disc output/scratch-29/G_new/ALLDATA.KWI --pin successor --output output/scratch-30/g_successor.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/g_historical.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/fingerprint.py --disc output/scratch-14/G_new/ALLDATA.KWI --pin historical --output output/scratch-30/g_historical.json
.venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/fingerprint.py merge --successor-json output/scratch-30/g_successor.json --historical-json output/scratch-30/g_historical.json
```

The merge validates both full pins, input membership hashes, exact native-key sets, dump rows, count/status validity and equality of every historical count to `g_cell_type_count`. Validation happens before either census output is changed. It fills both G columns only from the probe JSON, marks their slot statuses as disc-verified and records hashes of its inputs. A different successor count is preserved as measured evidence. Never fill the successor columns by hand.

To reproduce the light census before probing or merging:

```bash
.venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/fingerprint.py census
```

Execute also owns the append-only wording corrections in OVERVIEW, the plan-14 follow-up and the plan-28 reconciliation note. This unit changes none of those surfaces. No disposition verdict, encoder/checker/vocab change, 3-90 run, Phase 3 close claim or plan-29 work is included.

## Measured disc probes (Execute, 2026-10-06 ~06:50 AEST)

`output/scratch-30/run_p1.{sh,log}`, guarded:
- Successor `2ee3456a…` probe: exit 0, 342 rows, demanded-type total **0**. Full pin streamed and verified.
- Historical `4ed9cd80…` probe: exit 0, 342 rows, total **0**. It equals the membership TSV's `g_cell_type_count` in every row (control matched).
- `merge` exit 0: `successor-and-historical-verified;historical-control-matched`. The TSV status columns above now read `disc-verified:<slot_status>`; the "pending" wording earlier in this note describes the pre-probe state.
- `test_parity_fingerprint.py`: 22 passed.

G omits the demanded type in all 342 cells on both discs. Plan 29's (0,541) change touches none of these cells.
