# Plan 44 revision note — for Execute

## What failed

Phase 1 stopped at `0551ed2` on the control gate. Smoke n=12 rate 0.25; home-with-bg n=60 rate 0.3167; every disagreement was `prod_none` / `disagree_producer_none`. The OE limb was 100% whenever a unique `33006aa` producer existed. Root cause (proven in `triage/historical_bg/p5_owner_exclusive/control_analysis.md`): plan 39 identity-proven R01 shapes are often EO fragments / cover pieces — disc bytes disagree with a full-leaf `33006aa` clip of the geometric source (e.g. 220 B probe vs 140 B disc). Systematic, not sample noise. R-G5-4-a/b unchanged. Phase 2 not started. Plans 45/46 were blocked on 44's identity rule.

Those smoke/home rates are DESIGN-stop evidence under the old byte-equal-only producer. They are not a Phase 1 pass.

## What changed in the contract

Producer against spool candidates whose bbox meets L, using the `33006aa` probe into L's exact integer rectangle, is now two classes:

1. **unique-byte** — exactly one S whose clip bytes equal the old record. Strongest.
2. **unique-fragment** — no unique-byte; exactly one S such that (a) every identity-bearing vertex of the record appears in S's `33006aa` clip into L, and (b) at least one of those vertices is not produced by any other candidate's clip into L. Identity-bearing = not on L's rectangle boundary and not R01-failing on the old disc (use disc record verts; dump may not retain).

Zero matching S → **`producer_none`** (named; was control's dominant class). More than one → **`producer-ambiguous`**. EO cover/fragment pieces on disc are expected to take unique-fragment, not unique-byte.

Proven-fixed (`build:eo_bg_stitch`) is unchanged in substance: (a) K1 failing 0 on `4ed9cd80`; (b) new record byte-equals S's `d35b565` clip into L OR holds ≥1 owner-exclusive vertex of S at `d35b565`; (c) cell in 3-14 changed list class `eo_bg_stitch`. S may be unique-byte or unique-fragment.

Control: stratified sample of plan 39's 825,634 identity-proven rows; under the revised producer, ≥99% must agree (resolve unique-byte or unique-fragment, then pass OE/new-disc). Every disagreement reported. Systematic disagreement still stops the phase. Phase 1 is not closed until this control passes after fragment-producer lands.

Residuals: `producer_none`, `producer-ambiguous`, `no-owner-exclusive-vertex`, `source-removed`, `still-failing`. No waivers. Decision 3 / Assumption 2 revised accordingly; Assumption 3 added for the identity-bearing vertex source.

## What to implement next

1. Grow **fragment-producer** in `parser/tools/bg_owner_exclusive.py` (identity-bearing verts from disc record; exclusive-among-candidates; synthetic tests for fragment vs full-leaf vs ambiguous vs none).
2. Re-run the stratified control under the revised contract. Close Phase 1 only on ≥99% agreement with every disagreement reported.
3. Then Phase 2: decide all R-G5-4-a and joined R-G5-4-b rows.

Designs 45 and 46 now cite unique-byte OR unique-fragment (and `producer_none`) in lockstep; their phase counts and non-goals are unchanged. R-G5-4-a/b remain open until Phase 2. Meanwhile keep draining 47 and DESIGN commits for 48–53 if already doing that.

Full contract: `maps-design-drafts/44-r01-owner-exclusive-identity/DESIGN.md`.
