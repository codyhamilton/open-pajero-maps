---
unit: 2-01
phase: 2
group: g-omits-cell-local-dvd-type
---

# Brief: 2-01 — Group `g-omits-cell-local-dvd-type`

Consumer: Maps Execute (lands on master). Assigned instance: OpenCode DeepSeek Flash.

## Outcome (Phase 2 slice)

Close named group **`g-omits-cell-local-dvd-type`**: every Phase 1 row that has cell-local R presence of the demanded type and G absence, with a committed reproducer isolating one mechanism (G omit of a DVD-present type) and an expected completeness count movement or R/G type-count equality. No rule registration. No encoder/checker edit.

## Owned paths

- `docs/plans/14-completeness-root-cause/triage/` — group membership TSV/note + reproducer script(s)
- `docs/plans/14-completeness-root-cause/reports/2-01-g-omits-dvd-type.md`
- Scratch only under `output/scratch-14/` (git-ignored); do not overwrite `scratch-3-11/G_new`

## Non-goals

- No `_k1_cmp.c` / `_cenc.c` / rules JSON edits. No O07. No Phase 3 fix.
- Do not reseat 170 / 3-16 / 3-17. Do not touch plan 15/16/17 paths.
- Do not force-push. Do not open a PR/feature branch. Do not push (Execute pushes).
- Do not claim plan 04 Phase 3 closed. Do not invent `other_mechanism` values.

## Pre-edit checks

1. Disc `output/scratch-14/G_new/ALLDATA.KWI` sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (prefer worktree copy or `/home/codyh/workspace/open-pajero-maps/output/scratch-14/G_new/ALLDATA.KWI`).
2. R readable at `/run/media/codyh/464210-8480/ALLDATA.KWI`; spool `output/extract_timing/spool` (main checkout OK).
3. Phase 1 table `triage/completeness_evidence.tsv` has 776 rows; seed `R_polygon_count > 0` count is **343**.
4. Quote Phase 2 outcome from `DESIGN.md`.

## Steps

1. From `completeness_evidence.tsv`, list all rows with `R_polygon_count > 0` (343). Record dump_row keys.
2. **Cell-local discriminator** (required — Phase 1 R witness is frame-presence and may alias sparse tiles): for each seed, prove whether at least one qualifying R polygon (class-2, ≥3 coords, demanded `code`) geometrically meets the target cell `(level,ix,iy)`, not merely shares a covering leaf/tile. Prefer read-only decode of R frames already named in `R_witness` JSON; heavy under `flock output/.heavy.lock`, K1 ≤ `-j6`.
3. Members of this group = seeds that **pass** cell-local R presence and have `G_polygon_count == 0`. Seeds that fail cell-local go to unit 2-03 open questions (tile-alias residual) — list them explicitly; do not silently drop.
4. **Reproducer** (committed under plan-14 triage or `output/scratch-14/` with a committed driver script in triage): for the group (full enumeration, or stratified sample with an explicit proof that the rest share the same path), show:
   - R cell-local type present; G type absent under the same presence contract;
   - K1/spool requirement witness retained from Phase 1;
   - isolation of one mechanism on the build path (e.g. meeting sources clip/densify/round to empty or wrong type on G while R emits the type) — read-only `_cenc.c` / spool forensics. Do **not** patch C.
5. State expected movement: e.g. “build emits demanded type in these N cells → completeness failing −N” or “R/G type-count equality for each member”.
6. Write group note + membership TSV (native keys + dump_row + cell-local proof path). Write `reports/2-01-g-omits-dvd-type.md`.
7. Commit on master (detached HEAD OK) with a plain summary title. **No** `Workflow-Phase:` trailer. Do not push.

## Done evidence

- Membership TSV + group note committed; every 2-01 member has cell-local R proof path.
- Reproducer script + recorded outputs (scratch OK) isolate one mechanism and state expected movement.
- Rejected seeds listed for 2-03. No rule/encoder/checker edits. Disc sha unchanged; `scratch-3-11/G_new` untouched.
