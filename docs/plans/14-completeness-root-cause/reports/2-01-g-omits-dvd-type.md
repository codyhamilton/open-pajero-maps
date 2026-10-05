# Report 2-01 — group `g-omits-cell-local-dvd-type`

Phase 2, unit **2-01** of plan 14. Status: **closed on master** (detached HEAD OK).
No rule registration, no `_k1_cmp.c` / `_cenc.c` / `rules_*.json` edit, no Phase 3 fix.

## Phase 2 outcome it closes (quoted from `DESIGN.md`)

> **2-01** | `g-omits-cell-local-dvd-type` | Rows with `R_polygon_count > 0` that
> pass a **cell-local** R presence check (geometric meet of a qualifying R polygon
> with the target cell — not sparse-tile alias alone). Seed count before cell-local
> filter: **343**. | Single mechanism: production G path omits a type that R emits
> cell-locally for the same completeness key. Script under plan-14 triage/scratch;
> read-only discs/spool/`_cenc.c` clip contract. | Build fix emitting that type →
> those rows leave the failing set; or committed R/G type-count equality for each
> member cell/type.

## Inputs and disc pins (unchanged)

| Input | Value |
| --- | --- |
| Phase 1 evidence | `triage/completeness_evidence.tsv` — **776** rows, **343** seeds (`R_polygon_count > 0`) |
| G disc | `output/scratch-14/G_new/ALLDATA.KWI` sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` |
| R disc | `/run/media/codyh/464210-8480/ALLDATA.KWI` |
| Spool | `output/extract_timing/spool` |

All 343 seeds are **level 0** with `frame_class = l0_sparse_tile` on R; every one has
`G_polygon_count == 0` in Phase 1. Membership therefore reduces to whether the
Phase 1 R hit is a genuine cell-local meet or only an L0 sparse-tile alias.

## Method — cell-local R discriminator

The reproducer decodes the covering R leaf slot (read-only) and applies the *same*
presence contract the checker uses (`_k1_cmp.c` / `quantisation_roundtrip._required_cells`):
a qualifying R polygon (`shape_class == 2`, `>= 3` coords, demanded `code`) is
**cell-local** for the target cell `(level, ix, iy)` iff it meets that cell by

- **(a)** sitting inside the cell rectangle with a non-zero rounded raw area;
- **(b)** having a vertex at least one raw unit inside the cell; or
- **(c)** holding the cell centre (even-odd point-in-polygon).

A Phase 1 hit whose only polygon meets a *different* cell of the tile fails all
three and is rejected to 2-03. The target cell index is the global raw cell
(`floor(global_raw / 4096)`), identical for the checker key, the decoded leaf cell
and the `CellGrid` lattice.

## Membership

| Decision | Count | Notes |
| --- | ---: | --- |
| Seeds (`R_polygon_count > 0`) | 343 | all level 0, `l0_sparse_tile` |
| **2-01 members** (cell-local R meet, G absent) | **342** | 341 `code 288` + 1 `code 321` |
| **2-03 rejects** (tile alias only) | **1** | `dump_row 765`, key `(0,1307,1756,291)`, `in_historic_188` |
| G absent on all seeds | 343 | `g_cell_type_count == 0` for every member; Phase 1 `G_polygon_count == 0` |

R meet branch histogram: **c 341, a 1**. None of the 342 members is `in_historic_188`
or `in_added_89` (all `neither`).

Plan-14 partition context (other units own their slices): 2-01 **342** + 2-02 **432**
(`R_polygon_count == 0` minus native `dump_row 335`) + 2-03 residual **2**
(this tile-alias reject `765` + the `dump_row 335` source gap) = **776**.

Committed artefacts:

- `triage/2-01_g-omits-cell-local-dvd-type_members.tsv` (342 rows)
- `triage/2-01_g-omits-cell-local-dvd-type_rejects.tsv` (1 row, for 2-03)
- `triage/cell_local_2-01.py` — the committed reproducer
- scratch proofs: `output/scratch-14/cell_local/proofs/<dump_row>.json`
  (per member: R polygons, cell-local meet branches, G cell decode, spool source,
  clip/round drop test) and `output/scratch-14/cell_local/summary.json`

## Reproducer — one isolated mechanism

For each member the meeting source is the spool shape named by the Phase 1
requirement witness. Its footprint in the target cell is clipped to the cell
rectangle and then run through the build's own round/clean/drop decision,
replayed read-only from `_cenc.c:emit_piece`:

- `_cenc.c:562-568` — rasterise with `rint` (half-even) and drop consecutive
  duplicates;
- `_cenc.c:569-586` — close-ring dedup and spike collapse, then
  `if (q < 3) return 0;` — **fewer than three distinct rounded vertices emits nothing**;
- `_cenc.c:587-592` — `area2 != 0` required, then
  `if (area2 == 0) return 0;` — **zero rounded area emits nothing**.

Observed on all 342 members:

| Property | Value |
| --- | ---: |
| Spool source requirement branch | `b` for **342/342** |
| Source shape homed in a different cell than the target | **342/342** |
| Source bbox degenerate (zero height / zero width) | 326 / 14 (340); 2 more are sub-raw slivers (e.g. height `0.4` raw) |
| Clipped ring `q` after round/clean | 3 (321), 4 (14), 2 (7) |
| Clipped ring `area2` | **0 for 342/342** |
| `encoder_emits` | **False for 342/342** |

So the single mechanism is: **the meeting source contributes only a zero/sliver
footprint to the target cell; the production clip → densify → round/clean produces
no representable ring (`q < 3` or `area2 == 0`) and the G frame emits nothing for
that `(cell, type)`. R, the original disc, carries a same-`code` polygon whose
footprint covers the cell (341 by cell-centre containment, branch `c`; 1 by a
polygon wholly inside the cell, branch `a`).** The demanded type is `288`
(catch-all background) for 341 members and `321` (park/wood) for one.

Representative members:

- `dump_row 2`, cell `(851,637)`, code `288`: spool source is a 4-coord zero-width
  vertical line homed at `(851,617)` with a vertex `1363.9` raw inside row `637`;
  clipped+rounded it becomes 3 points with `area2 = 0`; G cell has **no**
  background polygon; R tile polygon covers the cell (branch `c`).
- `dump_row 246`, cell `(834,886)`, code `321`: spool source is a real 2-D polygon
  homed at `(834,885)` poking only `2.39` raw units into `(834,886)`; the clipped
  sliver rounds to zero area; R emits a type-321 polygon lying wholly inside the
  cell (branch `a`).

Expected movement (Phase 3, not applied here): if the production path emitted a
representable piece for these meeting sources, or if the demand itself were removed
for zero-rounded-area meeting sources, **342 completeness rows leave the failing
set** (342 → 0 for this group); equivalently, committed R/G type-count equality per
member cell/type. Count is the movement; per-member byte evidence is in the proofs.
Whether the Phase 3 locus is build (synthesise a piece) or checker (exclude
zero-rounded-area sources from branch `b`) is a Phase 3 decision and is **not**
taken here.

## Rejected seeds for unit 2-03 (tile-alias residual)

| dump_row | key | in_historic_188 | Reason |
| ---: | --- | ---: | --- |
| 765 | `(0, 1307, 1756, 291)` | 1 | The only R polygon of `code 291` in the tile sits in column `1304`; the target cell is column `1307`. No branch `a`/`b`/`c` meet → frame-presence alias only. G also lacks `291` (has `288`). Listed as a 2-03 open question; not dropped silently. |

## Non-goals honoured

- No `_k1_cmp.c` / `_cenc.c` / rules JSON edit; no O07; no Phase 3 fix.
- 3-16 / 3-17 / design-170 files untouched; plan 15/16/17 paths untouched.
- `output/scratch-3-11/G_new` untouched; spool and `.venv-rp` untouched.
- G disc sha unchanged (`4ed9cd80…`); no re-encode.
- `artifact_feedback` MCP unreachable during this unit; no workflow post, no
  invented forbid story.

## Provenance

- Committed reproducer: `triage/cell_local_2-01.py`; run under
  `flock output/.heavy.lock` with `/home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B`.
- Scratch outputs recorded in `docs/provenance.md` (`output/scratch-14/`, Phase 2
  unit 2-01 entry).
