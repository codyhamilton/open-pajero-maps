# Quarantine pickle legacy + sketch sanitizer/CI gate

Trust-gated legacy pickle loads; offline `pickle.load` allowlist oracle; sketch
Actions workflow runs only that oracle. Production stays on binary spool. Plan
06 full pytest+C gate was not drawn. Phase 3 not closed.

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end
generation matches the original DVD in every aspect that can be verified, every
claim, assumption, and implementation aspect is verified and proven, and there
are no unexplained deviations — each has a root cause.

Quarantine pickle legacy + sketch sanitizer/CI gate (security). Offline-runnable
preferred (fixtures/tests). Land on master. No feature branch. No pull request.
Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not
mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

Production spool is pickle-free, but `spool_legacy` / `convert_spool` still
deserialized without a trusted-input gate, and no greppable allowlist or
security-sketch CI existed. Assessor Security named the gap; draft 06 full CI
remains forbidden as a work unit.

## What Was Built

**Changed:** `parser/kiwiw/spool_legacy.py` (trust gate + `_pickle_load`);
`parser/tools/convert_spool.py` (`--i-trust-this-pickle`);
`parser/tests/test_spool_binary.py` (autouse trust);
`parser/tests/test_pickle_quarantine.py` (new oracle);
`.github/workflows/security-sketch.yml` (oracle only);
`parser/osm_to_address_index.py` (dump-only warn);
`docs/ARCHITECTURE.md`, `docs/provenance.md`, `docs/WORKFLOW.md`.

- Allowlist: **`parser/kiwiw/spool_legacy.py`** only.
- Trust API: `enable_legacy_pickle_trust(reason)` / CLI `--i-trust-this-pickle`.
- Production freeze: `build_alldata`, `osm_to_parcel_geometry`,
  `quantisation_roundtrip`, `golden_capture`, `parcel_occupancy` must not import
  `spool_legacy`.
- Default `cbuild` CFLAGS unchanged; ASan/UBSan not default.
- Design: `88f1373`. Phase close: `2d83856`.

## Deviations

None in scope. Refine skipped. Execute implemented Phase 1 inline (Flash
assigned; one bounded unit). Blank `design_id` — no workflow-service post.

## Review

Terminal review: no blocker/high findings. Trust refused without enablement;
allowlist AST oracle green; lossless binary↔legacy proof still passes under
trust. Sketch workflow contract is oracle-only (not plan 06).

## QA

Offline pytest: **9 passed** (6 quarantine oracle/trust + 3 spool binary).
`py_compile` OK. No disc mount, encode, K1, cell_local, or full-AU as a gate.

## Residual Risks

- Operators converting real legacy trees must pass `--i-trust-this-pickle`
  consciously; do not weaken the gate.
- Address `.pkl` remains dump-only; a future load API needs its own design.
- Sketch Actions is not a substitute for Assessor Security D1/pointers/dump-join
  recipes.

## Follow-ups

- Opt-in ASan/UBSan for `ctest` as a later named sketch (still not default
  `cbuild`; still not plan 06).
- Do not claim Assessor Security / Phase 3 / WP5 / full-disc complete from this
  quarantine alone.
- Full master pytest+C CI stays undrawn until Cody lifts the plan-06 ban.
