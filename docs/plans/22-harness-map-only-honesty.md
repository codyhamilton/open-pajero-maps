# Harness map-only honesty + WP2–WP5 N/A negative controls

Docs and harness honesty landed on master so a green map-only `compare_disc.py` run cannot be read as full-disc parity. WP2–WP5 appear as NA negative controls. No real WP2–WP5 science. Phase 3 not closed.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Harness map-only honesty + WP2–WP5 N/A negative controls (e2e) — green CLI ≠ full-disc parity. Offline-runnable preferred (docs/tests/harness flags). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

Default discover listed only map-layer checks. Green exit with no WP2–WP5 rows looked like disc parity done.

## What Was Built

**Changed:** `parser/harness/checks/wp_na.py` (new); `parser/harness/report.py`; `parser/compare_disc.py`; `parser/tests/test_harness_map_only_honesty.py`; `docs/OVERVIEW.md`.

- Four checks `wp2_route` / `wp3_address` / `wp4_index` / `wp5_meta` on layers `route` / `address` / `index` / `meta` — NA under `layers_present=["map"]`.
- Report JSON: `layers_present`, `scope`, `full_disc_parity: false`; stdout footer for map-only.
- Exit 0 still means no FAIL (PASS and NA OK).

## Deviations

`full_disc_parity` stays false for non-map-only configs too until real WP checks exist (conservative honesty).

## Review

Inline docs/harness review; unit tests lock the contract.

## QA

Not applicable (no deploy). Offline pytest: 4 passed.

## Residual Risks

Readers who ignore the report footer may still over-read green map-only runs; OVERVIEW and docstring state the rule.

## Follow-ups

- Future WP designs replace sentinels with real checks and promote matching layers into `layers_present` + build manifest together.
