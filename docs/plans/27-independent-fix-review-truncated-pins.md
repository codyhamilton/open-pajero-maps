# 3-90 independent fix-review + truncated-pins

Independent review of the plan-16 / 3-90 check-3 strip (**PASS**, all four
clauses) and truncated-pin ledger (in-scope digests expanded; `pinned_candidates.tsv`
unverifiable from git). Offline / artifact-only. Phase 3 not closed.

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end
generation matches the original DVD in every aspect that can be verified, every
claim, assumption, and implementation aspect is verified and proven, and there
are no unexplained deviations — each has a root cause.

3-90 independent fix-review + truncated-pins (Quality) — independently review
the 3-90 / plan-16 strip fix against its stated outcome; expand truncated pins
to full provable digests or mark unverifiable with root cause. Land on master.
No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not
draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Delivered

### Phase 1 — Independent REVIEW

- Artifact (archived below): fresh `REVIEW.md`, not a copy of plan 16's Review.
- Verdict: **PASS** on all four clauses (equal after `COMPARE_EXCLUDES` strip;
  non-excluded diffs unequal; timing-only leaves `wall_s` mismatch; brief check 3
  requires `strip_compare_excludes`).
- Pytest: 4 passed / 96 deselected (strip fixture tests); light helper recompute
  corroborated. No disc / 3-90 / encode / heavy.lock.

### Phase 2 — Truncated-pin ledger

- Ledger (archived below): `pins.md`.
- Expanded live surfaces: brief Contract + check 6 (`87a01b14…`, `da13a775…`),
  OVERVIEW `5c5823e` → full object, plan 04 DESIGN hard-gate truncations of those
  oracles. Adjacent proven forms ledgered: `4ed9cd80…`, `013586b5…`, `04be2f6e…`.
- Unverifiable: `pinned_candidates.tsv` (`TRUNCATED=yes`; sha256
  `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`) — exhaustive
  group identity not in git (scratch enumerate dumps). No fabricated pin list.
- OVERVIEW updated per Assumption 6: in-scope truncated-digest defect and plan-16
  strip independent-review gap cleared; other blockers retained; Phase 3 open.

## Explicit non-claims

No 3-90 re-run, no disc mount, no full-AU encode, no Phase 3 / mega-close 3-90,
no WP3 / plan 06, no 170 / 3-16 / 3-17 reseat, no steal of `output/.heavy.lock`,
`output/scratch-3-11/G_new` untouched, `.venv-rp` left untracked, plan-14
completeness worktree not edited.

## Close SHAs

| Step | SHA |
| --- | --- |
| Design land | `a03c9bc2ec66399cd5634bdbb748e79a7f36a55f` |
| Phase 1 | `aaba108e8ab9de5f673158a201c22528142e0f40` |
| Phase 2 | `279e654031d2554a3ab020dc4082ebb66f59e6fb` |

---

## Design (archived)

---
design_id:
---

# 3-90 independent fix-review + truncated-pins

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

3-90 independent fix-review + truncated-pins (Quality) — the 3-90 determinism/verification brief and its fix lack an independent review proving the fix is correct, and some pins (hashes/SHAs/expected values) recorded in docs/briefs/tests are truncated, so they cannot be verified exactly. Independently review the 3-90 fix against its stated outcome using existing artifacts and code; replace truncated pins with full values where the full value is provable from tracked artifacts or a light recompute, or mark them explicitly as unverifiable with root cause. Offline / artifact-only. Do not re-run 3-90 or any full-AU encode. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

Plan **16** closed the 3-90 check-3 strip defect (timing-only strip → `COMPARE_EXCLUDES` = `timing` + `wall_s`) and amended `briefs/3-90-fresh-verify.md` check 3. Plan **19** stopped framing `wall_s` as a live OVERVIEW blocker. Two honesty gaps remain open on tip and are named by OVERVIEW / plan 19 as live Phase 3 blockers:

| Surface | What it does today | Honesty / verification gap |
| --- | --- | --- |
| `docs/plans/16-k1-determinism-wall-s.md` Review | Explicitly: "No `REVIEW.md` was written… This is not an independent review." | The strip fix has author/close-out evidence only; no second agent reviewed code + brief + fixture contract against the signed outcome |
| `parser/tools/quantisation_roundtrip.py` | `COMPARE_EXCLUDES = ["timing", "wall_s"]`; `strip_compare_excludes` / `normalise_k1_report_for_compare` | Implementation exists; independent proof that it meets plan-16 / brief check 3 is missing from the record |
| `parser/tests/test_quantisation_roundtrip.py` | Four fixture-JSON strip tests landed with plan 16 | Tests are evidence of intent, not a signed independent review |
| `briefs/3-90-fresh-verify.md` check 3 | Requires strip via `strip_compare_excludes` (timing **and** `wall_s`) | Live brief is amended; still no independent attestation that the amend matches code and Phase 2 |
| `briefs/3-90-fresh-verify.md` checks 1/6 + Contract cite | Oracle pins written as `87a01b14…`, `da13a775…` | Truncated digests cannot be `sha256sum`-compared exactly from the brief alone |
| `docs/OVERVIEW.md` L50 | "latest 3-90 record at `5c5823e`" | Short git SHA; full object id not written next to the citation |
| `docs/plans/04-c-core-orchestration/DESIGN.md` gates | Mix of full `87a01b14b612…7862` and truncated `87a01b14…` / `da13a775…` | Same oracle, inconsistent pin length — truncated forms remain unverifiable in isolation |
| `triage/pinned_candidates.tsv` | 100 shown groups; footer `TRUNCATED=yes`; file sha256 full | Content truncation is intentional candidate view, not a full-digest pin — still listed under OVERVIEW "truncated pins" without an explicit unverifiable/root-cause ledger row |
| OVERVIEW remaining blockers | Lists "truncated pins" and "incomplete independent-review chain" | Ticket not discharged |

**Ground (artifact-only, tip `df1f071`)** — light recompute of the strip helpers (synthetic j1/j12 dicts differing only in `timing`/`wall_s`) shows they compare equal after `COMPARE_EXCLUDES` and unequal under a timing-only strip; source contains the shared exclude list and helpers; brief check 3 cites `strip_compare_excludes`. That is Ground for the design, not a signed independent review. Full digest forms for the live oracle pins are already present elsewhere on tip (e.g. plan 03 DESIGN / provenance / 3-90 IMPLEMENTATION rows) and are therefore expandable without encode.

Verified on `origin/master` at `df1f071` from committed plan 16 record, 3-90 brief, OVERVIEW, driver/tests, and provenance — **no** disc mount, **no** 3-90 re-run, **no** full-AU encode. Ticket is **not** already satisfied: plan 16 Review admits no independent review; OVERVIEW still lists truncated pins + incomplete independent-review chain. Plans **01–05** and **07–23**, **25** occupy those numbers on master; `/workspace/maps-design-drafts/` has **24** (pickle) and **26** (seven-state search fixtures). **06** is not a work unit. This plan is **27**.

## Solution shape

One bounded honesty package: (1) land an **independent review** of the plan-16 / 3-90 check-3 fix against its stated outcome, using tracked code, brief, tests, and light fixture recompute only; (2) land a **truncated-pin ledger** that expands every in-scope truncated hash/SHA/expected value to a full provable digest, or marks it unverifiable with a named root cause. Do not re-run 3-90. Do not close Phase 3. Do not reseat science packets. Do not clear other open blockers (PSS contract, native classify joins, 3-11 vs 3-14 oracle cell identities, completeness via plan 14).

### Domain: independent review of the 3-90 check-3 / plan-16 fix

- Owns: a committed review artifact that a reader who did not author plan 16 can use to accept or reject the strip fix against its stated outcome.
- Contract: (1) Review cites the stated outcome from plan 16 / brief check 3: reports that differ only in keys in `COMPARE_EXCLUDES` (`timing`, `wall_s`) compare equal after `strip_compare_excludes` / `normalise_k1_report_for_compare`; non-excluded diffs remain unequal; a timing-only strip leaves a `wall_s` mismatch; brief check 3 requires the shared helper, not timing alone. (2) Review walks tip code (`COMPARE_EXCLUDES`, helpers), the four fixture tests, and the live brief check-3 wording, and records PASS/FAIL per clause with file evidence. (3) Review may include one light fixture-JSON recompute (synthetic dicts or the existing unit tests under pytest); it must **not** re-run full-disc K1, mount a disc, or treat historical 3-90 FAIL rows as current strip defects. (4) If any clause fails, the review names the residual defect and does **not** relabel it fine without proof (standing rule). (5) Review is independent of the plan-16 author/close-out narrative: new `REVIEW.md` (or equivalent named section under this plan folder) signed by the Execute worker as a fresh verification pass, not a copy of plan 16's Review section. (6) Closing this domain does **not** claim other 3-90 blockers cleared and does **not** close plan 04 Phase 3.
- Non-goals: no rewrite of plan 16 science; no PSS / classify-join / completeness work; no 3-90 fresh-verify execution; no claiming Phase 3 closed.

### Domain: truncated-pin expansion / unverifiable ledger

- Owns: every in-scope truncated pin (short hex / `…`-ellipsised digest / short git object id used as a verification expected value) in the live 3-90 brief, OVERVIEW 3-90 status paragraph, plan 04 DESIGN hard gates that still truncate the same oracles, and the pinned-candidates truncation named by OVERVIEW — expanded to full value or marked unverifiable with root cause.
- Contract: (1) A committed ledger (table in this plan's record and/or a small `pins.md` under the plan folder — Execute picks one home) lists each truncated occurrence as `path:line`, truncated form, disposition (`expanded` | `unverifiable`), full value when expanded, source of proof (tracked file path + line, or `git rev-parse` of an ancestor object), and root cause when unverifiable. (2) Minimum expansions when full forms are already on tip: `87a01b14…` → `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`; `da13a775…` / `da13a775064…` → `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc`; `4ed9cd80…` → `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`; `013586b5…` → `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`; `04be2f6e…` → `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`; OVERVIEW `5c5823e` → `5c5823e4c267dd64bc986038caddb3ed4b745f60` (git object). (3) Live brief check 6 and Contract cite are amended to carry the full digests (or an explicit "full form: …" adjacent pin), so a future 3-90 run can compare without hunting other docs. (4) `pinned_candidates.tsv` content truncation is **not** silently called fine: ledger row states it is a brief-required 100-row candidate view (`TRUNCATED=yes`; file sha256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`); exhaustive group identity is **unverifiable from git alone** because full native enumerations live under non-committed scratch (`enumerate_*.tsv`) — root cause named; do not invent a full pin list without those artifacts. (5) Historical IMPLEMENTATION / provenance rows that keep truncated forms as accurate quotes of past blocked runs may stay as history **if** the ledger maps each live verification pin; Execute must not mass-rewrite every historical ellipsis outside the in-scope surfaces without proof need. (6) OVERVIEW "truncated pins" wording is updated only to the extent this plan's ledger discharges or reclassifies that blocker for the pins it covers — other open blockers stay listed; Phase 3 stays open.
- Non-goals: no re-hash of multi-GB discs; no commit of scratch enumerate dumps; no new oracle; no claiming the 3-11 vs 3-14 exact-cell-identity gate is closed (that remains a separate blocker).

## Decisions

1. Plan number is **27**. Standalone Quality honesty plan for independent review of the plan-16 / 3-90 check-3 fix plus truncated-pin ledger. It does not absorb plan 20 PSS reconcile, plan 14 completeness, draft 24 pickle quarantine, or a mega 3-90 Phase-3-close.
2. Land on master directly. No feature branch. No pull request.
3. Two phases. Refine skipped (approach known — review artifact + pin ledger/brief/OVERVIEW touch from tracked full forms).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Do not re-run 3-90, full-AU encode, or disc `4ed9cd80…` as acceptance. Light fixture recompute and `git rev-parse` / tracked full-digest cites only.
6. Reject relabeling any truncated or missing pin as "fine" without expansion or an explicit unverifiable + root-cause row (standing rule).
7. Reject treating plan 16's self-Review or close-out as the independent review this ticket requires.
8. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must the independent review re-run full-disc 3-90 K1 (checks 1–6) to accept the plan-16 strip?
- Answer chosen: **no**. Review the strip fix against its stated offline outcome (helpers + fixture tests + brief check 3) with light fixture recompute only.
- Rationale: ticket and hard constraints forbid re-running 3-90 / full-AU encode; the strip defect was defined as verification-normalisation, already closed under plan 16's own gate without encode.
- If wrong: Cody orders a later fresh 3-90 under plan 04 after other blockers have designs — still not absorbed here; this plan's review still stands for the strip.

### Assumption 2

- Question: which truncated pins are in scope — every ellipsis in the repo, or the live 3-90 / OVERVIEW / plan-04 gate surfaces?
- Answer chosen: **live verification surfaces** named above (3-90 brief Contract + check 6, OVERVIEW 3-90 paragraph short SHA, plan 04 DESIGN hard-gate truncations of the same oracles, pinned_candidates truncation called out by OVERVIEW). Historical blocked-run quotes may remain if ledgered; optional best-effort expansion of adjacent same-oracle truncations in plan 04 IMPLEMENTATION is allowed but not required for phase close.
- Rationale: ticket centers 3-90 fix-review + pins that block exact verification; mass-rewriting plan 03 history is out of bounding altitude.
- If wrong: Cody widens to a repo-wide ellipsis sweep in a follow-up — still no encode.

### Assumption 3

- Question: may expanding pins or landing the review claim Phase 3 / 3-90 complete?
- Answer chosen: **no**. Other blockers remain (PSS contract per plan 20, native classify joins, 3-11 vs 3-14 exact cell identities, completeness via plan 14, OOM/CHM hold). OVERVIEW must keep Phase 3 open.
- Rationale: standing rule; plan 19 / OVERVIEW already separate these blockers.
- If wrong: none — still must not mega-close.

### Assumption 4

- Question: is `pinned_candidates.tsv`'s 100-row truncation expandable from git?
- Answer chosen: **no** — mark **unverifiable from git** with root cause (brief-required candidate view; full enumerations are non-committed scratch). Do not fabricate a full pinned list.
- Rationale: cause_table.md and provenance already state this; inventing pins would violate the standing rule.
- If wrong: Cody supplies or authorises committing enumerate artifacts in a separate design — out of scope here.

### Assumption 5

- Question: must Execute re-run the four fixture pytest tests as the review gate, or is reading + light recompute enough?
- Answer chosen: **prefer running the four strip tests** if `.venv-rp` (or equivalent) is available without heavy lock / compile storm; otherwise light in-process recompute of the helpers + static citation of the test bodies is acceptable and must be disclosed.
- Rationale: offline proof; OOM/CHM hold forbids heavy jobs; strip tests are pure fixture-JSON.
- If wrong: Cody requires pytest evidence line in the review — still no disc/K1.

### Assumption 6

- Question: does discharging "truncated pins" for the in-scope ledger remove the OVERVIEW bullet entirely?
- Answer chosen: update OVERVIEW so in-scope pins are no longer described as an open truncated-digest defect; keep an honest residual if pinned_candidates content truncation (or any unverifiable row) remains material to 3-90 check 4 set-equality. Independent-review chain bullet is cleared only for the plan-16 strip review this plan lands — not for every historical unreviewed fix unit.
- Rationale: standing rule; do not over-claim.
- If wrong: Cody keeps both bullets until a later 3-90 fresh-verify — still no Phase 3 close from this plan.

## Open questions

1. Exact review artifact path (`docs/plans/27-…/REVIEW.md` vs a section in the collapsed close-out record) — **Execute chooses**; greppable and committed.
2. Whether to expand truncated same-oracle forms inside historical `IMPLEMENTATION.md` 3-90 FAIL tables in the same phase — **optional**; live brief + OVERVIEW + DESIGN gates are the gate.
3. When a future 3-90 fresh-verify runs, whether check 4's pinned-set equality requires committing full enumerate TSVs — **out of scope** (owned by a later pin/classify design).

## Phases

### Phase 1 — Independent review of the plan-16 / 3-90 check-3 fix exists

- Outcome: A committed independent review artifact records PASS/FAIL against the plan-16 / brief check-3 stated outcome using tip code, the four fixture strip tests (or disclosed light helper recompute), and the live brief wording. It does not treat historical timing-only 3-90 FAIL rows as current strip defects. It does not claim other 3-90 blockers cleared. It does not close plan 04 Phase 3. No disc mount, no 3-90 re-run, no full-AU encode. 170 / 3-16 / 3-17 not reseated. No plan 04 P4–6 / plan 06.
- Surfaces: new review artifact under `docs/plans/27-independent-fix-review-truncated-pins/` (indicative `REVIEW.md`); read-only cite of `parser/tools/quantisation_roundtrip.py`, `parser/tests/test_quantisation_roundtrip.py`, `briefs/3-90-fresh-verify.md` check 3, `docs/plans/16-k1-determinism-wall-s.md`. Product encode/K1/PSS/triage code is **read-only**.
- Approach: known
- Depends on: master tip with plan 16 closed (`d15a46f` / `2a9f3a7` ancestry) and amended brief check 3 (present at `df1f071`).
- Refine: skipped.

### Phase 2 — Truncated pins expanded or marked unverifiable with root cause

- Outcome: (1) A committed pin ledger lists each in-scope truncated occurrence (`path:line`), truncated form, disposition, full value or unverifiable+root-cause. (2) Live `briefs/3-90-fresh-verify.md` check 6 / Contract cites carry full digests for `87a01b14…` and `da13a775…` (or adjacent full-form pins). (3) OVERVIEW 3-90 paragraph cites full `5c5823e4c267dd64bc986038caddb3ed4b745f60` (or equivalent full form) and updates the truncated-pins / independent-review-chain wording per Assumption 6 without claiming Phase 3 closed. (4) Plan 04 DESIGN hard-gate truncations of those same oracles are expanded or ledger-mapped. (5) `pinned_candidates.tsv` truncation has an explicit unverifiable/root-cause ledger row (no fabricated full pin list). (6) No disc re-hash; no encode; no 3-90 re-run; no Phase 3 close; no plan 04 P4–6 / plan 06; 170 / 3-16 / 3-17 not reseated. Plan folder `docs/plans/27-independent-fix-review-truncated-pins/` lands with this design when Execute commits.
- Surfaces: pin ledger under the plan folder; `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md`; `docs/OVERVIEW.md`; optional touch of `docs/plans/04-c-core-orchestration/DESIGN.md` hard-gate lines; read-only cite of provenance / plan 03 full forms / `triage/pinned_candidates.tsv`. Parser runtime code unchanged unless a greppable constant table of oracle digests is added (Execute may skip code change — docs/ledger sufficient).
- Approach: known
- Depends on: Phase 1 review landed (so OVERVIEW can honestly clear the strip-review half of the independent-review-chain bullet without lying). Does **not** depend on draft 24 or OOM hold clearance.
- Refine: skipped. One worker may carry both phases sequentially.

## Provenance

- Ground tip read: `origin/master` `df1f0714c7fb69bce2962aa662c14bfb0d2b304d` (“Close plan 25: OOM memory RCA + Flash peak wrapper + cell_local bounds”). Shallow clone was unshallowed to resolve short git pins.
- Candidate: Maps Quality Assessor offline ticket (Quality tip `f01ed41` wave) — **3-90 independent fix-review + truncated-pins**. Exact Assessor agent transcript text was not required beyond the Design-lane task brief; substance matches OVERVIEW / plan 16 Review / plan 19 residual-blocker wording.
- Evidence cited (committed): plan 16 closed record (Review: not independent); `COMPARE_EXCLUDES` + `strip_compare_excludes` / `normalise_k1_report_for_compare` at tip; four fixture strip tests; amended `3-90-fresh-verify.md` check 3; OVERVIEW open blockers including truncated pins + incomplete independent-review chain; full digest forms in plan 03 DESIGN / provenance / 3-90 IMPLEMENTATION; `pinned_candidates.tsv` `TRUNCATED=yes` + sha256 `7dfe6ed7…`; git object `5c5823e4c267dd64bc986038caddb3ed4b745f60`.
- Light recompute (Design Ground only): synthetic j1/j12 reports differing only in `timing`/`wall_s` compare equal after strip helpers and unequal under timing-only strip; brief cites `strip_compare_excludes`. Not a substitute for Phase 1's signed independent review.
- Rejected for this design: re-running 3-90; full-AU encode; disc remount as gate; fabricating full pinned enumerate lists; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; mega Phase-3-close; relabeling truncated pins fine without expansion or root cause; absorbing plan 14/20 science.
- Draft format followed: `/workspace/maps-design-drafts/26-search-fixtures-seven-state/DESIGN.md` and `/workspace/maps-design-drafts/23-copy-through-graphics-cmp/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction. Box draft only — no commit/push.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–23, 25; `/workspace/maps-design-drafts/` has **24** and **26** → this draft is **27**.

---

## Independent REVIEW (archived)

# Independent review: plan-16 / 3-90 check-3 strip

**Reviewer:** Open Pajero Maps Execute (plan 27 Phase 1) — fresh verification pass, not a copy of plan 16's Review section.
**Tip reviewed:** `a03c9bc2ec66399cd5634bdbb748e79a7f36a55f` (plan 27 DESIGN on `origin/master`; strip code ancestry includes plan 16 `d15a46f` / `2a9f3a7`).
**Method:** tip code + four fixture strip tests under pytest + live brief check 3 + light helper recompute. No disc mount, no 3-90 re-run, no full-AU encode, no heavy lock. Historical timing-only 3-90 FAIL rows are **not** treated as current strip defects.

## Stated outcome (plan 16 / brief check 3)

Reports that differ only in keys in `COMPARE_EXCLUDES` (`timing`, `wall_s`) compare equal after `strip_compare_excludes` / `normalise_k1_report_for_compare`; non-excluded diffs remain unequal; a timing-only strip leaves a `wall_s` mismatch; brief check 3 requires the shared helper, not timing alone.

## Evidence walked

| Surface | Tip cite |
| --- | --- |
| `COMPARE_EXCLUDES` | `parser/tools/quantisation_roundtrip.py:1250` = `["timing", "wall_s"]` |
| `strip_compare_excludes` | `parser/tools/quantisation_roundtrip.py:1253–1258` — shallow copy removing every top-level key in `COMPARE_EXCLUDES` |
| `normalise_k1_report_for_compare` | `parser/tools/quantisation_roundtrip.py:1261–1267` — canonical JSON of stripped report (dict or path) |
| Four fixture strip tests | `parser/tests/test_quantisation_roundtrip.py:451–518` |
| Live brief check 3 | `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md:31` — requires strip of `timing` **and** `wall_s` via `strip_compare_excludes` |
| Plan 16 self-Review | `docs/plans/16-k1-determinism-wall-s.md` Review: "This is not an independent review." — author/close-out only; does not discharge this ticket |

## Pytest (preferred gate)

Command (no `output/.heavy.lock`; used existing `.venv-rp` from main checkout, left untracked):

```text
.venv-rp/bin/python -m pytest parser/tests/test_quantisation_roundtrip.py -q \
  -k 'strip_compare_excludes_removes or reports_differing_only_in_excludes or non_excluded_field_difference or locked_strip_is_not_timing_only'
```

Result: **4 passed, 96 deselected in 4.21s**

| Test | Maps to clause |
| --- | --- |
| `test_strip_compare_excludes_removes_every_excluded_key` | Shared helper removes every `COMPARE_EXCLUDES` key; input untouched |
| `test_reports_differing_only_in_excludes_compare_equal` | Differ only in excludes → equal after `normalise_k1_report_for_compare` |
| `test_non_excluded_field_difference_still_unequal` | Non-excluded diffs remain unequal |
| `test_locked_strip_is_not_timing_only` | Timing-only strip leaves `wall_s` mismatch; locked strip equalises |

Light in-process recompute of the same four clauses against tip helpers also **PASS** (disclosure: corroborates pytest; not a substitute).

## PASS/FAIL per clause

| # | Clause | Verdict | Notes |
| --- | --- | --- | --- |
| 1 | Reports differing only in `COMPARE_EXCLUDES` (`timing`, `wall_s`) compare equal after strip helpers | **PASS** | pytest + light recompute; helpers strip both top-level keys |
| 2 | Non-excluded diffs remain unequal | **PASS** | `failing` / `levels` diffs stay unequal after normalise |
| 3 | Timing-only strip leaves a `wall_s` mismatch | **PASS** | `test_locked_strip_is_not_timing_only` asserts timing-only JSON unequal while locked strip equal |
| 4 | Brief check 3 requires the shared helper (`strip_compare_excludes`), not timing alone | **PASS** | Live brief L31 names `COMPARE_EXCLUDES` — `timing` **and** `wall_s` — and `strip_compare_excludes` |

**Overall strip-fix review: PASS** (all four clauses).

## Explicit non-claims

- Does **not** clear other 3-90 blockers (PSS contract, native classify joins, 3-11 vs 3-14 oracle cell identities, completeness / plan 14, OOM/CHM hold).
- Does **not** close plan 04 Phase 3; does **not** mega-close 3-90; does **not** claim WP3 / plan 06.
- Does **not** reseat 170 / 3-16 / 3-17.
- Historical timing-only 3-90 FAIL rows remain accurate history of a past defect; they are not current strip defects on tip.

## Residual

None within the plan-16 / check-3 strip contract. Truncated-pin ledger is Phase 2 of this plan (separate domain).

---

## Truncated-pin ledger (archived)

# Truncated-pin ledger (plan 27 Phase 2)

In-scope surfaces only (Assumption 2): live 3-90 brief Contract + check 6, OVERVIEW 3-90 paragraph short SHA, plan 04 DESIGN hard-gate truncations of the same oracles, and `pinned_candidates.tsv` truncation named by OVERVIEW. Historical IMPLEMENTATION quotes of past blocked runs may remain as history when live pins are ledger-mapped.

Proof tip at ledger write: `aaba108e8ab9de5f673158a201c22528142e0f40` (post Phase 1). No disc re-hash; expansions from tracked full forms + `git rev-parse`.

## Expansions

| path:line (pre-amend) | truncated | disposition | full value | proof |
| --- | --- | --- | --- | --- |
| `briefs/3-90-fresh-verify.md:23` (Contract) | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | plan 04 `DESIGN.md:47` (full form already present); `IMPLEMENTATION.md` build-gate rows; `briefs/2-06-…:77` |
| `briefs/3-90-fresh-verify.md:34` (check 6) | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | same |
| `briefs/3-90-fresh-verify.md:34` (check 6) | `da13a775…` | expanded | `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc` | `docs/provenance.md:517`; `IMPLEMENTATION.md:576` |
| `docs/OVERVIEW.md:50` | `5c5823e` | expanded | `5c5823e4c267dd64bc986038caddb3ed4b745f60` | `git rev-parse 5c5823e` → full object id |
| `docs/plans/04-c-core-orchestration/DESIGN.md:11` | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | DESIGN.md:47 same oracle |
| `DESIGN.md:47` | `da13a775…` | expanded | `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc` | provenance / IMPLEMENTATION |
| `DESIGN.md:50` | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | DESIGN.md:47 |
| `DESIGN.md:72` (hard gates) | `87a01b14…` / `da13a775…` | expanded | full forms above | DESIGN.md:47 + provenance |
| `DESIGN.md:152` | `87a01b14…` | expanded | full form above | DESIGN.md:47 |
| `DESIGN.md:184` | `87a01b14…` | expanded | full form above | DESIGN.md:47 |

### Minimum expansions also proven on tip (adjacent same-oracle; for ledger completeness)

| truncated | full | proof |
| --- | --- | --- |
| `4ed9cd80…` | `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` | `docs/provenance.md:601`; plan 14 / 3-17 records |
| `013586b5…` | `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` | `docs/provenance.md:388`; triage `causes_residual.md:7` |
| `04be2f6e…` | `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728` | `IMPLEMENTATION.md:505` (full form adjacent to truncated quotes) |

These three are **not** live brief check-6 pins (brief still cites the original `87a01b14…` / `da13a775…` oracles until a signed re-oracle); they are ledgered so OVERVIEW "truncated pins" for the same oracle family is discharged without hunting.

## Unverifiable

| path | truncated / issue | disposition | root cause |
| --- | --- | --- | --- |
| `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv` | content view `SHOWN=100` / footer `TRUNCATED=yes` | **unverifiable from git** | Brief-required 100-row candidate view, not an exhaustive pinned list. File sha256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a` (tracked; verified `sha256sum` at ledger write). Exhaustive group identity lives under non-committed scratch (`enumerate_*.tsv` / dump joins). Do **not** fabricate a full pin list without those artifacts. Material to a future 3-90 check 4 set-equality only when enumerate artifacts are authorised. |

## Counts

- Expanded (live surfaces amended or DESIGN gates expanded): **10** occurrence rows above (brief ×3 digest cites across Contract+check6, OVERVIEW ×1, DESIGN ×6 line sites).
- Minimum adjacent oracle expansions proven: **3** (`4ed9cd80…`, `013586b5…`, `04be2f6e…`).
- Unverifiable: **1** (`pinned_candidates.tsv` content truncation).

No fabricated full pinned enumerate list.
