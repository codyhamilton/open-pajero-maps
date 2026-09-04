# Provenance: WP1 — Offline evaluation harness + full-Australia map layer

## Session

- Session: Initial plan (September 04, 2026)
- Timestamp: 2026-09-04T00:00:00Z
- CWD: /home/codyh/workspace/open-pajero-maps

## Initial Request (verbatim)

> Check the current implementation status of our plan. It is currently tracked in docs, lets form it into a more formal plan, filling gaps and ensuring the target meets our goal.

## Planning Conversation

### Turn 1

**Agent asked:** (1) Should the first burn be a rebuilt copy of the original disc, before any OSM-content disc? (2) What should the first OSM-content in-vehicle milestone contain? (3) How will discs get burned?

**User responded:**

- "No, we won't do original first. This is conservative yes, but expensive. We can do an original burn if the OSM fails as a debugging tool. However, it's extremely difficult to get useful data out of a vehicle test that will inform debugging, we are almost certain to be relying on byte analysis between old and new to find issues."
- "Not sure why WA is the focus, given we are in QLD. Perth would be useless since the vehicle gps won't be able to navigate. I don't see the value in a partial in-vehicle milestone. The first in-vehicle milestone will contain all data across australia. There's nearly no marginal utility in a data subset, in fact it would hide errors only visible in a full dataset (esp sizing or performance). To repeat, in-vehicle testing is last-mile, not an early feedback mechanism. It's not an effective loop for evaluation."
- Burning: "Burner on this machine."

**Agent decisions:**

- The stable docs' "frequent in-vehicle validation / test after each sub-checkpoint" framing is superseded. The plan's evaluation loop is offline: byte-level and structural comparison of the generated disc against the original, using the project's own parser as the oracle. In-vehicle is the final acceptance step only.
- Target for the first burn: full Australia, full feature set (map display, routing, POI, address search), all levels, on one disc. No partial-region or partial-feature milestone is a deliverable; regional subsets remain useful only as fast development fixtures.
- The Perth/WA defaults baked into the pipeline scripts are development fixtures inherited from the reference disc's index content, not a scope choice; they must not remain the shape of the deliverable.
- A rebuilt-original burn is kept as a contingency debugging tool, not a gate.
- Disc authoring and burning happen on this machine; installing UDF/ISO tooling is in scope.
### Turn 2

**Agent asked:** The reference disc holds ~14 index families under `IDX/` plus `HWMAP.KWI`/`INDEXDAT.KWI`; only SADSR and POISR are decoded and writable. What does "all data" mean for the first burn?

**User responded:** "Full parity: decode and regenerate every family." No file on the disc is to be copied with stale content; every index family and `HWMAP.KWI`/`INDEXDAT.KWI` are decoded and regenerated before the first burn.

**Agent decisions:**

- The program scope includes a format-analysis track for every undecoded file that carries map-dependent content. Only content-independent resources (firmware, voice, UI graphics) remain copy-through.
- The `2##` filename suffix on `SADSR`/`POISR`/`ITSSR`/`FWYSR`/`POIAS` is confirmed to partition by state (201=WA, 202=NT, 205=NSW, 207=TAS by decoded bounding boxes), not by zoom level. The inventory doc's zoom-level hypothesis is corrected in this plan run.

## Agent Decisions

- **Plan shape**: the program is multi-PR, so per the plan skill it is a stable design-intent doc (`docs/design/target-disc.md`) plus one plan folder per work package. This folder is WP1. Rationale: the user asked for a formal plan for the whole goal; a single plan folder cannot hold five dependent work packages without becoming a program hierarchy.
- **WP1 = harness + map layer**: the harness is the evaluation loop the user described; the map layer is the most mature from-scratch pipeline and has concrete known deviations to fix. Rationale: gives the earliest pass/fail signal on the largest byte share of the disc.
- **Stable-doc edits kept minimal**: scope decisions and the index-suffix hypothesis are corrected in place with dated notes; the phase docs' historical narrative is left intact and the design doc declares precedence.
- **Capacity assumption**: single-layer 4.7 GB, stated in PLAN.md Intent Validation rather than asked, since the reference disc fits with 2.3 GB headroom and the question only matters if the full build overflows.

## Adversarial review (2026-09-04)

A clean subagent reviewed the plan and design doc; 23 findings. Applied
(plan and design doc edited accordingly):

1. mfde "20 entries" was evidenced on 4 level-0 parcels only → phase 1 censuses the table per level, including the absent-slot encoding; phase 2 depends on it.
2. The 4096..6144 frame's layer was unknown → identified during planning as 0-based MHT record 29 = spec Ch.5.2 record 30 (RESERVED, extended part 1), content a language/country code list; classified copy-through, owned by WP1.
3. Synth grid stops at level 8 and no per-level selection contract → grid contract now names levels 12..0 and per-level census matching; level 0 bound by size/capacity.
4. Grid contract vs flat assembler (one BSMR/BMT, `n_blocksets=0`) → per-level LMR/BSMR/BMT shape must equal `R`; harness check + acceptance criterion added.
5. Determinism broken by the `os.path.exists(alldata_path)` synthetic-grid fallback → reference LMR parameters become checked-in data; build never reads the mounted disc; AC requires identical output on a machine without the reference.
6. Harness applicability, config files and check selection undefined → `--checks`, `--config`, per-layer profile, N/A status, applicability rule stated.
7. Pointer rule too strict for mfde entries ≥3 that point outside the parcel → rule allows censused absent-slot value or valid in-file sector.
8. Absent-slot encoding must be profiled before it can be emitted → moved to phase 1.
9. `LinkIdRegistry` key → `(osm_way_id, ordinal)` contract + AC with a two-parcel test.
10. Phase order → scale (one-pass extractor) now precedes all-levels.
11. Level 0 count envelope unrealistic for OSM density → exempt from count envelope; trade-off reported, user decides.
12. Container byte-diff check with allowlist added.
13. Spot checks become a fixture table consumed by the harness.
14. Profiler splits reference bytes per layer.
15. Ext frames assigned to WP2.
16. WP2 RP-placement spike may overlap with WP1 after phase 2; unrecoverable format questions go to the user.
17. Open questions rephrased: `name.py` already decodes types 5/6 (question is the OSM mapping); state mapping now fully confirmed; record 29 identified.
18. Status column and module names dropped from the stable design doc's file table.
19. Test command and venv stated in acceptance criteria.
20. Anti-meridian coverage box (E90..W142) recorded as a grid-contract requirement and open question.
21. Phase 1 marked independently reviewable / possibly its own PR.

Reported, not applied (no plan change needed):

22. Capacity is likely to bind at level 0; whether the head unit reads dual-layer media is unknown. Recorded as an expectation in the capacity contract; the decision is deferred to the user when the harness reports the number.
23. `dump_parcel.py` crash confirmed: `to_jsonable` passes `bytes` through. Already a phase 1 item.
