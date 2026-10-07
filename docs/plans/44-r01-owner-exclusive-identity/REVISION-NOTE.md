# Plan 44 revision note (second) — for Execute

Hand this note verbatim. Box draft only; no ubuntu edits, no commits, no agent messages from this revision.

## What failed (second stop)

Phase 1 stopped again at `8ee2559`. Stratified control n=200 seed=44: rate **0.7576 (150/198)**; agree 91 unique-fragment + 59 unique-byte; all **48 disagrees** `producer_none` / no-cover under neighbourhood=1.

Critical: `leaf_io` neighbourhood=1 **already is** the Assump-1 3×3 window. That fallback is exhausted — do **NOT** revise to "just enable 3×3."

Post-commit `diag_nbhd` on the same 48 (recovery includes unique-byte as routing signal):

| Moore radius | recovered of 48 | projected agree/198 |
| ---: | ---: | ---: |
| 1 (3×3) | 0 | 0.7576 |
| 2 (5×5) | 16 | 0.8384 |
| 3 (7×7) | 25 | 0.8838 |
| 5 (11×11) | 37 | 0.9444 |

Still 11 `producer_none` at nb=5 → still short of ≥0.99 under the old full-set gate. Bucket of 48 at nb=1: ~18 zero spool; ~20 few clips incomplete IB cover; ~10 many clips incomplete IB cover. Mostly full uncover (41/48). Plan 39 identity-proven never consults spool — definitional routing gap (search-window understatement, not OE failure). OE limb remains 100% whenever a unique producer is found.

Cody HARD: no waivers; every deviation needs proven RC. Loosening cover (partial/Jaccard) = not justified. Carving control to ignore no-cover without RC = not justified.

(First stop at `0551ed2` was byte-equal-only → unique-fragment; that limb is done and stays.)

## What changed in the contract (second revision)

### 1. Assump-1 chosen answer is WRONG

Evidence: Assump-1 window understates true producer homes for a large fraction of identity-proven R01 fragments (`diag_nbhd` recovery including unique-byte at nb≥2).

**New candidate set:** union of (a) every spool source whose bbox meets L, and (b) every spool source whose home cell lies in a Moore neighbourhood of radius **R** around the leaf home cell.

- R is **not** preset to 1.
- Phase 1 must run an **offset census** on control disagrees (distribution of recovering `(dx,dy)` / min radius / class) before locking R for the Phase 2 tool default.
- Interim Phase 1 control re-runs use **expanding search**: for each row, grow Moore radius from 1 upward until unique-byte or unique-fragment, or hit Design cap **R_cap=8** (17×17), logging the recovering radius. Cap bounds the census; it does **not** claim 8 suffices for ≥99% agreement-rate.

### 2. Control gate retargeted (the key fix)

The prior ≥99% agreement-rate against all plan-39 identity-proven rows **conflated** spool producer attribution under a narrow window with OE/new-disc correctness. Plan 39 never used spool producers. **Retired.** Both gates required to close Phase 1:

**Gate A — OE limb:** Among stratified-sample rows that resolve unique-byte or unique-fragment under expanding search (≤R_cap), ≥99% must pass the OE/new-disc check. Every disagreement reported. Systematic OE disagreement still stops.

**Gate B — producer census:** Every evaluable stratified-sample row must receive exactly one of: unique-byte, unique-fragment, or a **named producer residual with proven RC** in `control_analysis.md`. Allowed census residual classes:
- `producer_home_outside_R_cap` — expanding search to R_cap still no-cover; record max radius tried, spool/clip counts, IB/uncovered counts
- `producer_ambiguous` — >1 cover at the recovering radius

Tool-level `producer_none` stays only as the pre-census label; Gate B forbids closing on bare `producer_none` without a named RC class. Gate B passes at **100% class coverage with RC**, not at 99% unique-* rate. Unexplained `producer_none` still blocks — this is not a waiver.

### 3. Cover definition unchanged

Cover = all identity-bearing verts of the disc record appear in one candidate's `33006aa` clip into L; exclusive-among-candidates for unique-fragment. Do not loosen.

### 4. Proven-fixed / Phase 2

Unchanged in substance. S from unique-byte|unique-fragment under the locked R (Decision after census). Rows that remain `producer_home_outside_R_cap` after census become named Phase 2 residuals (or residual children of R-G5-4), never silent.

### 5. Decisions / R lock

- Control gates are A+B; full-set ≥99% agreement-rate retired.
- R for Phase 2 defaults locked only after offset census lands in `control_analysis.md`. For this revision: Execute reports the census and uses expanding search ≤R_cap=8 for Gate A/B; if Gate A+B pass, Phase 1 closes and Execute proposes R = max recovering radius among unique-* in the sample (or percentile with proof) in IMPLEMENTATION for Design to confirm before Phase 2 mass run.
- Phase 1 outcomes now: fragment-producer (done), offset census + expanding search, Gate A, Gate B, 925 inventory (done).
- `8ee2559` rates + `diag_nbhd` table are DESIGN-stop evidence under Assump-1 window.
- Cascade 45/46: identity/producer citations must mention expanding Moore search / post-census R, not Assump-1-only bbox-meet.

## What to implement next

1. **Offset census** on the 48 (and any new disagrees under expanding search): recovering `(dx,dy)` / min radius / class; write into `control_analysis.md`.
2. **Expanding search** in the control path: Moore radius 1→R_cap=8 per row until unique-byte or unique-fragment (or residual); log recovering radius. Do not hardcode R=1 or "enable 3×3."
3. Close Phase 1 only when **Gate A and Gate B** both pass. Propose R in IMPLEMENTATION for Design confirm before Phase 2.
4. Then Phase 2: decide all R-G5-4-a and joined R-G5-4-b rows under locked R; name `producer_home_outside_R_cap` residuals explicitly.

Designs 45 and 46 cite expanding Moore / post-census R in lockstep. R-G5-4-a/b remain open until Phase 2.

Full contract: `maps-design-drafts/44-r01-owner-exclusive-identity/DESIGN.md`.
