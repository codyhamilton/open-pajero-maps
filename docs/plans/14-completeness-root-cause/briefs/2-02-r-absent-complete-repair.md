---
unit: 2-02
phase: 2
group: r-absent-complete-repair-zero
---

# Brief: 2-02 — Group `r-absent-complete-repair-zero`

Consumer: Maps Execute (lands on master). Assigned instance: OpenCode DeepSeek Flash.

## Outcome (Phase 2 slice)

Close named group **`r-absent-complete-repair-zero`**: Phase 1 rows where R lacks the demanded type (`R_polygon_count == 0`), G lacks it, and a **new** committed complete-repair reproducer shows meeting sources remain non-representable under the builder clip/densify/round contract. Expected count movement (checker) or proven non-deviation stated. Label-only `checker:repaired-not-representable` without this reproducer is rejected. 3-16 may be cited only to exclude EO-stitch bypass for the added_89 subset — it does not close the group. No rule registration. No encoder/checker edit.

## Owned paths

- `docs/plans/04-c-core-orchestration/triage/` — membership TSV/note + complete-repair reproducer script(s)
- `docs/plans/14-completeness-root-cause/reports/2-02-r-absent-complete-repair.md`
- Scratch under `output/scratch-14/` only

## Non-goals

- No rules JSON / `_k1_cmp.c` / `_cenc.c` edits. No O07 registration.
- Do not reseat 3-15/3-16/3-17 packets; may **cite** and re-implement their harness ideas under plan-14 paths.
- Do not treat 3-16's 0/89 EO-stitch fail as a positive group close.
- No Phase 3 fix. No PR/feature branch. Do not push.

## Pre-edit checks

1. G disc sha `4ed9cd80…` as in 2-01. Spool available. Phase 1 TSV present.
2. Seed: `R_polygon_count == 0` and dump_row ≠ **335** → **432** rows (433 R=0 minus row 335). Confirm with a count script.
3. Prefer existing venv `/home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B`.
4. Quote Phase 2 outcome + Assumption 5 from `DESIGN.md` (3-15 science may be cited; group closes only with this plan's reproducer).

## Steps

1. Build membership list from Phase 1 TSV: all `R_polygon_count == 0` except dump_row 335. Cross-tab historic_188 / added_89 / neither; keep one group unless a discriminator **proves** a different mechanism (then split and document).
2. Implement a **new** complete-repair reproducer under plan-14 triage (Python OK):
   - For each member (or full set under flock; encode/cbuild ≤ `-j4`; prefer windowed/key-enumerated work — no full-AU re-encode unless unavoidable):
     - Load meeting class-2 source ring(s) from spool using Phase 1 requirement witness / K1 source fields;
     - Decompose to even-odd simple faces (3-13-style exact rational / equivalent documented algorithm — copy or reimplement under plan-14; do not edit historical scratch-only trees as authoritative without copying into plan-14);
     - Run builder clip/densify/round contract (C `bg_shape` via existing bindings if available, and/or independent Python mirror); record quantised area2 and whether any C record of the demanded type would emit.
   - Control: at least one positive control that a known representable ring still emits (document).
3. Group members = rows where repair yields **0** representable demanded-type pieces. Rows where repair **emits** → list for 2-03 (different mechanism).
4. For added_89 members: cite 3-16 outcomes TSV only as **exclusion** of EO-stitch face-bypass recovery; still require the complete-repair (or other positive) reproducer for close.
5. State expected movement: checker ceases demanding these N identities → failing −N; **or** proven non-deviation (R and G both lack type; demand inapplicable under named contract) with byte/decode evidence already in Phase 1 witnesses.
6. Write group note + membership TSV + `reports/2-02-r-absent-complete-repair.md`.
7. Commit on master; no `Workflow-Phase:` trailer; do not push.

## Done evidence

- New reproducer committed (not a prose restatement of 3-15).
- Membership TSV covers every R=0 row except those deferred to 2-03; each member has repair outcome recorded.
- Expected movement stated. No rule/encoder/checker edits. Protected discs untouched.
