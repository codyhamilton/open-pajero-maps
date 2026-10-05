# Copy-through graphics cmp contracts (GRA256D/KGRA256…)

Byte-identical R↔G harness contracts for the ten target-disc content-independent
copy files landed on master. Under default map-only config the check is NA; when
layer `meta` is in scope, missing or mismatched siblings FAIL. No WP5 copy
writer; Phase 3 not closed.

## Intent

User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Copy-through graphics cmp contracts GRA256D/KGRA256… (ui) — byte-identical R↔G contracts for target-disc copy-through resources; missing files are missing verification, not successful copying. Offline-runnable preferred (fixtures/tests). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

Assessor UI `cmp` of GRA/KGRA (and the full target-disc copy list) lived only
outside the harness. `compare_disc` resolved disc roots to ALLDATA alone, so
sibling paths were invisible. Map-only green could not prove copy-through
presence, and absent G siblings looked like silence rather than FAIL.

## What Was Built

**Changed:** `parser/harness/context.py` (`reference_root` / `generated_root`);
`parser/compare_disc.py` (`_resolve_disc_paths`);
`parser/harness/checks/copy_through.py` (new);
`parser/harness/checks/wp_na.py` (dropped `wp5_meta`);
`parser/tests/test_harness_copy_through_graphics.py` (new);
`parser/tests/test_harness_map_only_honesty.py`;
`docs/schema/parameters-metadata.md`; `docs/design/target-disc.md`;
`docs/OVERVIEW.md`.

- Check id **`copy_through_graphics`**, layer **`meta`** (plan 22 alignment;
  subsumes `wp5_meta` so one WP5 row remains).
- Ten basenames: LOADING, DICVCE56, GRA256D, KGRA256, PCT256D, KPCT256,
  PCT2DAT, KPCT2DT, KGRPDAT, VAR256D (`.KWI`).
- Default `layers_present` stays `["map"]` → check NA.
- Design: `e6a9b13`. Phase close: `e9afab8`.

## Deviations

None in scope. Refine skipped. Execute implemented Phase 1 inline (Flash
assigned; one bounded unit). Blank `design_id` — no workflow-service post.

## Review

Terminal review: no blocker/high findings. Outcome table all PASS against
fixtures and docs.

## QA

Offline pytest: **13 passed** (9 copy-through + 4 map-only honesty).
`py_compile` OK. No disc mount, encode, or K1 as a gate.

## Residual Risks

- Readers who force `meta` into `layers_present` without a copy step will see
  FAIL on missing G siblings — intentional; do not weaken to PASS.
- Live R/G `cmp` on mounted discs is still optional confirmation only.

## Follow-ups

- WP5 design owns copying the ten files and promoting `meta` into
  `layers_present` + build manifesto together.
- Do not claim WP5 / Phase 3 / full-disc complete from these contracts alone.
