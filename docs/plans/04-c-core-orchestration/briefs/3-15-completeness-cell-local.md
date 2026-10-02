# Brief: 3-15 — Completeness remainder: cell-local representability (+37 post-3-14 honesty)

Consumer: the orchestrator (records Science/classify outcomes; seats Sonnet only if a C-build fix is proposed) and Cody (phase-close honesty on completeness).
Owned paths: triage notes under `docs/plans/04-c-core-orchestration/triage/` (completeness cause/notes only — **do not** edit S02–S05 predicates), scripts + evidence under `output/scratch-3-15/` (git-ignored), optional minimal classify/rule additions in `rules_other.json` **only** when a new named mechanism is witnessed. **Never overwrite** `output/scratch-3-11/G*` / `G_new/` or `output/scratch-3-14/` oracles.
Commits: Science packet + unit record + `docs/provenance.md` for scratch-3-15; rules/cause table only if attribution lands. Never stage discs/dumps.
Depends on: 3-14 landed (`414c5fe`); 3-08/3-12 completeness residual notes (`causes_residual.md` “188 completeness… cell-local representability”); O01/O04/O05 in `rules_other.json`; Design carry of completeness **776** / name_anchor **1**.
Runs alongside: nothing serial on `parser/kiwiw/` unless a later build-fix amendment is Design-approved. Heavy under `flock output/.heavy.lock`; cbuild/make ≤ `-j4`; K1 ≤ `-j6`; no cache drops.
Tier: **Codex / DeepSeek** (prefer). Mandatory Sonnet 5.5 review **only if** proposing a C encoder/checker fix (RE-risky). Pure Science/attribute → no mandatory Sonnet.
Budget: Science ≤ 80 tool turns; each heavy step one flock command. Prefer windowed / key-enumerated work over a second full-AU encode unless classify requires a fresh dump against the 3-14 disc.

## Cited facts (do not re-derive)

- **3-14 new disc** K1: background / background_boundary / interior_cover **0**; **completeness 739 → 776 (+37, all L0)**; **name_anchor 1** (carry). S02–S05 → **0**. IMPLEMENTATION §3-14; Design ruled completeness carry unless pinned to EO stitch (**not pinned**).
- **Pre-3-13 / 3-12 ledger:** completeness total **739** on G_new `013586b5…` = checker **495** (O01 363 + O05 132) + spool **56** (O04) + unattributed **188** (182 L0/type288 + 6 L0/type291). `causes_rootcause.md` / `causes_residual.md`: next step = **cell-local representability / required-type** after complete topology repair over every meeting source; one-coordinate repair left deep-vertex requirement with no C piece for 187/188.
- **O06** (13 build count-wrap) → 0 after 3-11; not in scope.
- **L8 TRIM** road 308/14,012 (2.198%) known budget identical pre/post 3-14 — **out of scope**.
- **9,064** unattributed + PARTITION FAIL is a **pre-3-14** classify ledger; re-baseline on 3-14 disc is a side deliverable here only if cheap (empty-dump tooling), else defer to backlog.

## Goal (measurement story)

1. **Historic 188:** For each unattributed completeness group key, measure whether any meeting spool source is **cell-locally representable** as the required type under the same clip/densify/round contract the build uses (full topology repair of all meeting sources in that cell — not one-coordinate deletion). Classify each group: **checker** (requirement over-demands; absent piece valid), **spool** (source topology still defective after repair), **build** (representable source + independent clip emits a piece the disc lacks / wrong type), or remain **unattributed** with named failed predicate.
2. **+37 post-3-14:** Census the 37 new L0 completeness failures vs pre-edit 739 set (set-diff of full keys). For each: pin to EO stitch side-effect (build), to newly representable requirements after bg faces changed (checker/build), or **unexplained**. If unexplained after bounded Science → `done with concerns`; **do not** force EO attribution.
3. **Recount:** Quote completeness failing total and O01/O04/O05 (± any new rule) hits on the **3-14 disc**; arithmetic must sum without silent remainder absorption.

**Non-goals:** reopen S02–S05; expand L8 TRIM to zero; fix name_anchor; change K1 tolerances; encode R01 exclusivity; Phase 4+; catch-all PARTITION rules; full-AU rebuild unless dump-invalid vs 3-14 tip.

## Science-first gate (more-evidence vs build-fix)

- Default path = **Science / attribute**. A **build-fix** (C or checker) is in-scope **only if** ≥1 group has: (a) independent cell-local representability witness, (b) original-spool window CF or byte gate showing the missing piece appears when the named defect is corrected, (c) Design amendment naming owned paths. Otherwise stop at honesty packet.

## Pre-edit checks (any fail → `blocked`)

C1. Tip contains 3-14 (`414c5fe` or descendant); record AU/Perth shas in force (`4ed9cd80…` / `04be2f6e…` per IMPLEMENTATION, or tip equivalents).
C2. Locate pre-3-14 completeness key list (scratch-3-08/3-12 `small_hypotheses.jsonl` / remaining completeness keys) and post-3-14 `k1_full` / completeness dump samples; confirm **776** and **+37** arithmetic.
C3. Confirm O01/O04/O05 still load; dry-run classify on available dump or document empty-dump mmap caveat.
C4. Baseline quote: completeness 776; name_anchor 1; S02–S05 = 0; do not claim 9,064 live without re-classify.

## Steps (in order)

1. **Inventory (no heavy):** set-diff 739 vs 776 keys; table of +37 (level, ix, iy, type, reason). Separate “historic 188 still failing” vs “cleared” vs “new”.
2. **Cell-local representability Science:** for historic unattributed (and +37), enumerate meeting sources of the required type; apply complete topology repair (region-preserving / crossing faces as in 3-13 spirit — **completeness-scoped**, not a bg residual reopen); run independent clip; record whether a piece of the required type is representable inside the cell. Witness files under `output/scratch-3-15/`.
3. **Attribute or honesty:** write per-group cause; add `rules_other.json` entries only for strict witnessed mechanisms; leave remainder unattributed.
4. **Optional classify gate:** if dump valid against 3-14 disc (or new dump under lock), run classify; quote completeness cause totals; PARTITION may still FAIL — disclose.
5. **Build-fix branch (Design gate):** only if Science-first gate passes; otherwise skip.
6. **Record** in `IMPLEMENTATION.md` (3-15 heading): C1–C4, key tables, before/after counts, +37 disposition, deviations.

## Done evidence

- +37 census table with disposition (EO-pinned / other named / unattributed).
- Historic 188 (or surviving subset) each have a tested cell-local predicate outcome.
- Completeness arithmetic quoted; no silent absorption into O01/O04/O05.
- No S02–S05 predicate edits; no L8 TRIM expand; no tolerance loosen.
- If build-fix proposed: Sonnet review of diff + affected completeness cells before treat-as-landed.

## Report back

Under 600 tokens: status (`done` | `done with concerns` | `blocked` | `over budget`), completeness before→after by cause, +37 disposition, whether build-fix is justified, deviations. Never resolve a contradiction silently. Do not start Phase 4; no `Workflow-Phase` trailer.
