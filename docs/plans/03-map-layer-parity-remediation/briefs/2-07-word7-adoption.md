# Brief: 2-07 — Adopt the word-7 (pmcode) model rule in the census and the profile

Consumer: implementation worker; result consumed by 2-04 (schema rows and gate verdict) and by Phase 4 (header-word generator).
Owned paths: `parser/tools/header_word_census.py`, `parser/tests/test_header_word_census.py`, `parser/refdata/profile/coord_scale.json` (the `header.words.7` section only), `docs/plans/03-map-layer-parity-remediation/WORD7-ANALYSIS.md` (append only). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing (2-02 is already done and committed).
Runs alongside: 2-05, 2-06, 2-08 — all four own disjoint paths.
Budget: 6 files to read, about 200 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/WORD7-ANALYSIS.md` — whole file (86 lines). This is the authoritative analysis; you are adopting it, not redoing it.
2. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart", item 3; and "Domain: Native encoding model" (the `coord_scale.json` contract and the header-word exemption list).
3. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the `2-02 header-word-census` record (what the tool already computes, the held-out split rule, the "word 7 blocked, not tuned" paragraph).
4. `parser/tools/header_word_census.py` — `collect`, `_work`, `_accumulate`, `parse_header`, `constant_rule`, `w7_subframe_rule`, `build_header_section`, `divided_adjacency_census` (the existing example of a geometric, cross-parcel census inside this tool), `main`.
5. `parser/refdata/profile/coord_scale.json` — `header.words.7` as it stands (`status: "blocked"`, `subframe_presence_rule`, `fit_modal_share`, `heldout_*`), and `header.split_rule`.
6. `parser/tests/test_header_word_census.py` — the synthetic-fixture style the new tests must follow.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Replace word 7's `status: "blocked"` with the adopted model rule, scored by the checked-in census tool against R, so that `coord_scale.json` stays a generated artefact and Phase 4 has a rule it can implement.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-22 item 3: "**Word 7 (pmcode) is resolved, not blocked.** `WORD7-ANALYSIS.md` is adopted as the model rule: Area Number 18 (`0x1200`) iff road data exists at L0 (for L2, iff any L0 descendant has a road sub-frame), else 255 (`0xFF00`); L4 and above always `0xFF00`; word 8 = 0 and word 7's low byte = 0. The 28 single-link L0 misses are a recorded residual **tolerance**, not an exemption. ... the generator's need for an L2 post-pass (L2 headers read their L0 children) is recorded as Phase 4 scope. The meaning of area 18 in the metafile stays documented-unknown."

Cited, `WORD7-ANALYSIS.md` "Best rule and recommendation":

```
pmcode_word7(L0 parcel)  = 0x1200 if parcel has road sub-frame with >=1 link else 0xFF00
pmcode_word7(L2 parcel)  = 0x1200 if any L0 parcel inside it has road sub-frame else 0xFF00
pmcode_word7(L>=4)       = 0xFF00
word 8 = 0, word 7 low byte = 0
```

with recorded accuracy "L2 100% (231,548/231,548 tested); L0 99.99924% (28 exceptions, single-link road parcels stored 0xFF00...)".

Cited, DESIGN "Domain: Native encoding model": `coord_scale.json` is "Generated from R, checked in, never read from the mounted disc at build time". This is why the rule is implemented **in the tool**, not hand-written into the JSON: a hand edit is silently reverted by the next regeneration.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. Python: `.venv-rp/bin/python`. Census tools read R only through `parser/harness/` reading paths and must not import writer modules. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

- Implement the rule as a scored rule inside `header_word_census.py` — a `w7_road_presence_rule(...)` alongside the existing `w7_subframe_rule`. It needs two things the tool does not yet have: L0 road-sub-frame presence with a link count, and, for each L2 parcel, whether any L0 parcel geographically inside it has a road sub-frame. `divided_adjacency_census` is the precedent for a second, geometry-keyed pass over R inside this tool; follow its shape (a separate pass with its own bbox keying) rather than trying to thread cross-level state through `_accumulate`. Scoring may use the whole disc — as `WORD7-ANALYSIS.md` notes, the rule has no fitted parameter, so fit and held-out coincide — but report the held-out figure under the existing `header.split_rule` as well, so word 7 is comparable with words 0/6/9/10/11.
- Rewrite `header.words.7` from the tool: `rule` stating the rule in the three-line form above; `status` no longer `"blocked"`; per-level accuracy and exception counts; the exception population characterised (`WORD7-ANALYSIS.md` says the 28 are all single-link L0 road parcels stored `0xFF00`). Record the 28 explicitly as a **residual tolerance** with that name, not as an exemption, and give the field a value a Phase 4 check can compare against. Keep `subframe_presence_rule` and the existing `finding` text as recorded evidence of what was tested and rejected — do not delete the history, and make clear in `finding` which rule is now the model.
- Record, as a machine-readable note in the same section, that the generator needs an L2 post-pass (L2 headers read their L0 children) and that this is **Phase 4 scope**; and that the meaning of Area Number 18 in the metafile stays documented-unknown (the metafile is not on the disc and not in the archived spec).
- `status` values in this file come from `build_header_section`'s own vocabulary (today `"blocked"` / `"ok"`). Whatever value you choose must be produced by the code, and the `>= 0.99` threshold that `build_header_section` applies must be the thing that decides it. Do not special-case word 7 past the threshold.
- Append to `WORD7-ANALYSIS.md` a short "Adoption" section: which rule was implemented, the numbers the checked-in tool reproduced, and any discrepancy against the analysis's own figures. A discrepancy is reported, not reconciled by adjusting the rule.
- The caveats in `WORD7-ANALYSIS.md` (16 divided L2 parcels and 22 zero-height L0 integrated parcels not separately scored) must either be scored now or be carried into the JSON as a named caveat with its parcel count. Say which you did.

### Keep untouched

`header.ranges`, `header.class_rule`, and `header.words` entries 0, 6, 9, 10, 11 — 2-02's evidence is that these regenerate byte-identically, and that invariance is your regression check. `header.wp2_exempt`, `header.word0_exceptions`, `header.pointer_nonframe_targets`, `header.rl_table`. `docs/schema/**` — the pmcode row is 2-04's. `parser/harness/checks/**` — no check is added in Phase 2.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- New tests in `parser/tests/test_header_word_census.py`, synthetic fixtures in the existing style, that fail before the rule exists: an L0 parcel with a >=1-link road sub-frame scores `0x1200`; one without scores `0xFF00`; an L2 parcel with no road sub-frame of its own but an L0 descendant that has one scores `0x1200`; an L4 parcel scores `0xFF00` regardless of content.
- `.venv-rp/bin/python -m pytest parser/tests/test_header_word_census.py -q` passes (report counts before and after).
- The tool run against R twice with identical output (report the `sha256` of `coord_scale.json` both times), and `header.ranges`, `header.class_rule` and words 0/6/9/10/11 byte-identical to HEAD (`git diff --stat` plus a targeted diff of those keys).
- The accuracy the tool reports for the adopted rule, per level, against `WORD7-ANALYSIS.md`'s L0 3,704,843/3,704,871 and L2 231,548/231,548. State both sets of numbers.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the checked-in tool cannot reproduce `WORD7-ANALYSIS.md`'s accuracy, report the numbers and say `blocked` — this is a gate phase and the rule is not adjusted to fit.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
