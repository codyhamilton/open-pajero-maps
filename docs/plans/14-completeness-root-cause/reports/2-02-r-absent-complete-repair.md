# Report 2-02 — group `r-absent-complete-repair-zero`

Phase 2, unit **2-02** of plan 14. Status: **closed on master**.
No rule registration. No `_k1_cmp.c` / `_cenc.c` / `rules_*.json` edit. No Phase 3 fix.

## Phase 2 outcome it closes (quoted from `DESIGN.md`)

> **2-02** | `r-absent-complete-repair-zero` | Rows with `R_polygon_count == 0` and a
> concrete spool source witness (exclude native dump_row **335**). Seed count: **432**. …
> | **New** committed complete-repair harness (3-13-style EO face decompose + builder
> clip/densify/round): each member yields 0 quantised area2 / 0 C records for the
> demanded type. Citing `checker:repaired-not-representable` without this re-run/package
> is rejected. 3-16 may exclude EO-stitch bypass for the 89; it does not close the
> group. | Checker stop over-demanding these → −N failing; or proven non-deviation if R
> and G both lack the type under the named contract and the demand is shown inapplicable.

Assumption 5 (quoted): *"That science may be **cited** as prior measurement. A group
closes only when this plan's worker re-runs or packages a reproducer that predicts a
live count movement (or a concrete R/G byte equality) under one mechanism."*

## Pre-edit checks

| Check | Result |
| --- | --- |
| G disc `output/scratch-14/G_new/ALLDATA.KWI` | sha256 `4ed9cd80…` (asserted by the script) |
| Spool | `output/extract_timing/spool`, the restored spool of record (see *Spool incident*). 775/775 Phase 1 `source_cell_sha256` pins match. The script fails closed on any mismatch. |
| Phase 1 TSV | 776 rows. `R_polygon_count == 0` → 433. Minus dump_row 335 → **432** (asserted). |
| Python | `.venv-rp/bin/python -B`, via `parser/tools/run_heavy_python.py` (flock + memory.peak) |

## Reproducer (`triage/complete_repair_2-02.py`)

For each seed:

1. **Source.** Load the meeting class-2 ring from the spool, using the Phase 1
   requirement witness (`source_cell`, `background_ordinal`). The cell sha is
   pinned against the witness.
2. **Even-odd repair.** Exact `fractions.Fraction` arrangement, a plan-14
   reimplementation of the 3-13 `split.decompose` idea. The 3-13 scratch tree no
   longer exists on disk, so nothing was copied.
   - Find the proper edge–edge crossings.
   - Split edges at the crossings and cancel coincident segments mod 2.
   - Walk CCW faces by leftmost-turn half-edge succession.
   - Keep the faces whose left-nudged mid-edge sample is even-odd interior to the
     original ring.
   - A ring with no crossings is one face.
3. **Builder contract, Python mirror.** Sutherland–Hodgman clip of each face to the
   target cell, then `encoder_piece_densified`. This replays `_cenc.c:emit_piece`
   (534–603):
   - densify each edge longer than `lim = 127·mc − 1`;
   - `rint` and drop consecutive duplicates;
   - closing dedup and spike collapse;
   - drop if `q < 3`; drop if `area2 == 0`.
4. **Builder contract, production C.** `output/scratch-14/complete_repair/cprobe/probe_bg.c`
   `#include`s `parser/kiwiw/_cenc.c` (sha `5c43e00d…`, unchanged from the Phase 1
   encoder `f385ef5`) and calls the hidden `kw__bg_shape`. It runs on the **original**
   ring, which is the production path including the 3-14 EO stitch, and on **every
   repaired face**, using the spool record's own `mult/type/flags` and the cell bounds
   on the same lattice.
5. **Member** iff the Python-mirror emits = 0 **and** the C records = 0, for the
   original ring and for every face.

**Controls.**

- Python: an in-cell square emits (`q=4`, `area2=18,874,368`). A bowtie repairs to
  2 faces, and both emit.
- C: an in-cell square on AU cell (1706,1512) emits 1 record.
- Either control failing aborts the run.

## Result

| Quantity | Value |
| --- | ---: |
| Seeds | 432 |
| **2-02 members** | **432** |
| Rejects → 2-03 (repair emits / spool gap) | **0** |
| Seed sets | historic 187 · added 89 · neither 156 |
| Codes | 288 ×393 · 291 ×25 · 578 ×13 · 290 ×1 |
| Source branch | `b` 431 · `a` 1 (dump_row 656) |
| Sources with proper self-crossings | 280 (historic 187, added 89, neither 4) |
| EO faces total / clipping into target cell | 1,664 / 495 |
| Faces emitting (Python, densified) | **0**; max \|area2\| = 0 |
| C records, original ring / repaired faces | **0 / 0** on all 432 |

Clipped faces collapse in one of two ways. 152 collapse to `q = 2`. The rest keep up
to 67 rounded vertices, but every vertex rounds onto one lattice line, so
`area2 = 0`. These are the sub-raw-width slivers that `rint` annihilates.

Cross-check with prior science: historic gives 881 faces / 203 in-cell. This agrees
with 3-15's 885 / 205 over 188 keys; the missing key is 765, which is in 2-01's
reject set. That result is cited, not inherited.

### Densify matters (mirror defect found)

The 2-01 helper `encoder_piece` omits the densify step.

- Without densify, dump_row **656** would emit. Its source is a 3-vertex
  near-collinear ring wholly inside the cell (branch `a`), and the undensified
  mirror gives `q = 3`, `area2 = 106`.
- With densify, the 223-raw closing edge gains a midpoint `(4042.26, 3958.37)`. It
  rounds onto vertex 2 `(4042, 3958)`, spike collapse leaves `q = 2`, and nothing
  emits.
- Production C agrees: 0 records.

656 is therefore a member, not a "repair emits" residual. **Caveat for 2-01:** its
recorded `clipped_ring_q/area2` came from the no-densify mirror. Densify can only add
collinear points before rounding. It is not known whether that can turn a 2-01 zero
into non-zero; it was not re-tested here, and 2-01's artefacts were not rewritten.
Carried to 2-03 as an open check.

### One group, not split

The crossing discriminator splits the set as follows:

- historic + added: all self-crossing;
- neither: 152 of 156 simple.

The outcome mechanism is the same in every case: after complete even-odd repair and
builder clip/densify/round, the meeting source has a zero-area footprint in the
target cell. The discriminator therefore does **not** prove a different mechanism, so
the set stays one group, as the brief requires.

### added_89 and 3-16

All 89 added members are `fail` in `completeness_3-16_outcomes.tsv`. That result is
cited only to exclude EO-stitch face-bypass recovery. The close rests on the
reproducer above: 0 Python emits and 0 C records, for both original and repaired
rings.

## Expected movement (Phase 3; not applied here)

R lacks the demanded type in every member's cell (Phase 1 `R_polygon_count == 0`). G
lacks it too (`G_polygon_count == 0`). The production builder provably cannot
represent the meeting source's in-cell footprint. Under the named contract,
"builder clip/densify/round of the even-odd source region", G already matches R for
these 432 (cell, type) pairs.

Phase 3 options:

1. **Proven non-deviation.** Byte/decode witnesses already exist in Phase 1
   (`witnesses/NNNN_{R,G}.json`).
2. **Checker fix.** Stop demanding a type when the meeting source's quantised in-cell
   footprint is zero. This would take **failing −432** (776 → 344 before other
   groups), with build sha unchanged.

Which one to take is a Phase 3 decision.

## Spool incident (honesty)

During resume setup, a symlink step resolved through the worktree's `output → main
output` link. It replaced the live spool with a self-symlink, and the contents were
lost.

**Recovery:**

1. A first re-extract at tip was rejected: 138/775 witness cells differed because of
   later extractor commits.
2. Re-extracted with tree `34a04cc`, the extractor of record.
3. L0 counts match `run.log`, and 775/775 witness pins match.
4. A full-AU `-j4` re-encode at `f385ef5` produced sha `4ed9cd80…`, byte-identical
   to `G_new`.
5. The restored spool was renamed into place.

The full record is in `output/scratch-14/spool_recovery/INCIDENT.md` and
`docs/provenance.md`. Protected `scratch-3-11/G_new` (`013586b5…`) and `G_new`
(`4ed9cd80…`) were untouched.

## Runs (plan 25 wrapper logs, `output/scratch-14/runs/`)

| Run | exit | memory.peak |
| --- | ---: | ---: |
| `complete_repair_all.json` (`--all-seeds`, 432) | 0 | 78.9 MB |
| `complete_repair_w8.json` / `w8c.json` (windowed probes) | 0 | 55 / 109 MB |
| `spool_rebuild_34a04cc.json` (spool of record) | 0 | 14.5 GB |
| `G_verify_encode.json` (`-j4` byte proof) | 0 | 7.0 GB |
| `spool_rebuild.json` (tip extract, rejected) | 0 | 13.8 GB |

## Non-goals honoured

- No rules / `_k1_cmp.c` / `_cenc.c` edit. The C probe is a scratch `#include`.
- No O07. No Phase 3.
- 3-16 / 3-17 / 170 untouched. 2-01 artefacts untouched.
- No PR or feature branch.
