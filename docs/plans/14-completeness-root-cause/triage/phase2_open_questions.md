# Phase 2 open questions — plan 14 (unit 2-03)

These are the residual rows left after groups `g-omits-cell-local-dvd-type` (2-01,
**342**) and `r-absent-complete-repair-zero` (2-02, **432**). There are **2** of
them. The authoritative union map is `phase2_membership.tsv`: 776 rows,
exhaustive and pairwise disjoint (asserted by `residuals_2-03.py`).

Discriminator outputs: `output/scratch-14/residuals/{335,765}.json`,
`q_2-01_densify_c.json`, `summary.json`. The reproducer is
`triage/residuals_2-03.py`, run via `run_heavy_python.py` at `--window 8` and
`--window 32`.

## Q-source-335 — dump_row 335, key `(0, 1379, 1138, 288)`

- **Phase 1:** `R_polygon_count = 0`. The R tile carries only `289` ×3.
  `G_polygon_count = 0`; the G leaf carries `291` ×1. The Phase 1 requirement
  witness has `source = null`: the (a)/(b) enumeration found no meeting source,
  and the centre branch was not enumerated.
- **Discriminators tried:**
  1. **Windowed centre-branch (c) search with (a)/(b) re-check.** Same demanded
     code, class 2, per-ring even-odd, as in `_required_cells`.
     - ±8 cells: 289 spool cells, 31 rings of code 288.
     - ±32 cells: 4,225 spool cells, 433 rings.
     - Result: **0 centre hits, 0 vertex-in-cell hits, 0 inside-cell rings.**
       Exactly one ring's bbox meets the cell: a 4-coord sliver homed at
       (1379,1143), x-span 1968–2367 raw, which does not hold the centre.
  2. **Representability of that ring.** Densified mirror: 0 emits. Production C
     `bg_shape`: 0 records, on the original ring and on the repaired face.
- **Why unproven:** no spool source reproduces the K1 demand under the checker's
  per-ring a/b/c rule within ±32 L0 cells. The remaining hypotheses are untested:
  - a demanding ring homed more than 32 cells away (more than about 1° of
    latitude);
  - checker region semantics (`region.inside`) that differ from per-ring EO
    across a block halo.
  R and G both lack 288, but without the demanding source the 2-02 mechanism
  cannot be claimed.
- **Next:** in Phase 3 or later, instrument `_k1_cmp.c`/the classify side to
  emit the demanding shape id for this key, read-only.

## Q-tile-alias — dump_row 765, key `(0, 1307, 1756, 291)`, in_historic_188

- **Phase 1:** `R_polygon_count = 1`, but that is frame presence only. 2-01's
  cell-local test rejected it: the only R `291` polygon sits in column 1304, not
  1307. `G_polygon_count = 0`; the G leaf has `288` ×2.
- **Discriminators tried:**
  1. 2-01 cell-local meet (a/b/c): none (2-01 reject TSV).
  2. Complete repair on its Phase 1 source (38 coords, branch `b`, homed at
     (1307,1755), 2 crossings, 3 EO faces):
     - densified mirror: 0 emits;
     - production C: 0 records, original and faces.
- **Why left open rather than moved:** the evidence matches the 2-02 mechanism.
  R has no cell-local `291`, G lacks it, and the source is not representable after
  repair. But DESIGN defines 2-02 membership as `R_polygon_count == 0` and routes
  tile-alias seeds here. Moving it would redefine the group without a Design
  ruling. **Proposal for Phase 3:** treat 765 with the 2-02 disposition once
  Design accepts "cell-local R absence" as equivalent to `R_polygon_count == 0`.

## Q-repair-emits — none

0 rows. The single apparent emitter in an early 2-02 run, dump_row 656, came from
a no-densify mirror. With `emit_piece`'s densify the piece collapses to `q = 2`,
and production C agrees with 0 records. It is a 2-02 member. See
`reports/2-02-r-absent-complete-repair.md`.

## Q-2-01-densify (verification, closed)

2-01 recorded its clip/round result from a mirror without densify. Production C
`bg_shape` was run on each 2-01 member's meeting source (original ring, target
cell): **0 records on 342/342.** The 2-01 claim "G path emits nothing" holds under
the production encoder. No 2-01 artefact was rewritten.

## Other discriminators considered

- **Code splits (288/291/578/290).** Every 2-02 code subset gives the same
  zero-representable outcome, so this does not discriminate.
- **Branch `a` vs `b`.** The one `a` (656) and the 431 `b` give the same outcome.
- **Crossing / set membership** (historic + added self-crossing; neither mostly
  simple). Same outcome, so the set stays one group.
- **Recovering `other_mechanism` (O01/O04/O05).** Not attempted; DESIGN rejects
  it as a gate, and the side tables are gone.
