# Brief: 3-16 — Window counterfactual for the 89 stitch-absent completeness keys

Consumer: the orchestrator (records the counterfactual; does **not** seat a C fix from this unit) and Design (amends only if gate (b) passes).
Owned paths: notes under `docs/plans/04-c-core-orchestration/triage/` (3-16 outcome only — **do not** edit S02–S05 or add `rules_other.json` entries), evidence under `output/scratch-3-16/` (git-ignored). **Never overwrite** `output/scratch-3-11/`, `output/scratch-3-14/`, or `output/scratch-3-15/` oracles.
Commits: Science packet + unit record + `docs/provenance.md` for scratch-3-16. No encoder, checker, or rule edits. Never stage discs/dumps.
Depends on: 3-15 landed (master merge `6b8a68a`, science `7a12618`). Use that packet's key list. Do not re-census 776 from scratch.
Runs alongside: nothing on `parser/kiwiw/`. Heavy under `flock output/.heavy.lock`; cbuild/make ≤ `-j4`; K1 ≤ `-j6`; no cache drops. **No full-AU encode.**
Tier: **Codex / DeepSeek**. No Sonnet. A C fix is out of scope even if the counterfactual passes — stop and return to Design.
Budget: ≤ 60 tool turns. Windowed / key-enumerated only.

## Cited facts (do not re-derive)

From the 3-15 science packet (stitch contract on the 3-14 disc):

- Completeness **776 = O01 363 + O05 132 + O04 7 + unattributed 274**.
- Key churn vs pre-3-14 **739**: **687 shared + 89 added + 52 cleared** (net +37). Not a 37-key superset.
- The **89** were present under the legacy encoder and absent under stitch: contract-level EO side-effect / build regression. **Not byte-pinned** (no window counterfactual).
- Historic **188**: complete topology repair → **0 representable** → label `checker:repaired-not-representable` (sub-unit slivers). **O07 was not registered.** Leave it that way.
- Science-first gate from 3-15: a build-fix needs (a) a representability witness, (b) an original-spool window counterfactual or byte gate showing the missing piece appears when the named defect is corrected, (c) a Design amendment. **(b) and (c) are unmet.** This unit exists only to test (b).

## Goal (measurement story)

For each of the **89** keys, run an original-spool **window** counterfactual under the same clip/densify/round contract the build uses:

Does the completeness piece that the legacy encoder emitted, and stitch omitted, **reappear** when the named stitch/EO defect is corrected inside that window?

Per key, one of:

- **(b) pass** — the missing piece appears when that named defect is corrected. Cite the window, the defect, and the byte or geometry witness.
- **(b) fail** — the piece does not reappear. The contract-level "stitch regression" claim does not survive the counterfactual for that key.
- **untested** — say why (window too wide, sources missing). Do not fill the gap with a full-AU run.

No third outcome called "probably EO."

## Non-goals

- Any C, checker, or `rules_other.json` edit. Do not register O07.
- Re-open historic 188, S02–S05, O01/O05, R01 exclusivity, name_anchor, L8 TRIM, or the +60 B container residual.
- Re-classify the 9,064 ledger.
- Full-AU rebuild. If a key cannot be windowed, mark it untested.

## Pre-edit checks (any fail → `blocked`)

C1. Tip contains 3-15 (`6b8a68a` or descendant). Science packet `7a12618` is the key-list source.
C2. The 89-key list is recoverable from that packet or `output/scratch-3-15/`. If it is not, **blocked** — do not reconstruct by diffing discs.
C3. Quote the 3-15 arithmetic once (776 = 363+132+7+274; 687/89/52) and do not recompute it.

## Steps

1. Load the 89 keys and the named defect the 3-15 packet claims (legacy-present, stitch-absent).
2. For each key, window counterfactual only. Record pass / fail / untested with the witness path under `output/scratch-3-16/`.
3. Write the tally. No code changes.
4. Record in `IMPLEMENTATION.md` under a 3-16 heading: C1–C3, tally, deviations.

## Done evidence

- Every one of the 89 is pass, fail, or untested. Untested keys are listed, not folded into fail.
- No encoder/checker/rule diff.
- If any key passes: status `done`, and **stop**. Design will amend before any build unit. Do not open a fix branch.
- If every tested key fails: status `done`. Disposition for those keys is accept-with-honesty (contract comparison does not survive the counterfactual). Untested keys stay open.

## Report back

Under 400 tokens: status (`done` | `blocked` | `over budget`); pass/fail/untested counts; whether any pass is strong enough to justify a later C amendment; deviations. Never resolve a contradiction silently. Do not start another unit.
