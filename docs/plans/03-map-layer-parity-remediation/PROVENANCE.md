# Provenance: Map-layer parity remediation

Interactive posture only. Headless runs carry intent, the assumption ledger, and decisions in `DESIGN.md` alone.

## Session

- Session: Initial design (September 20, 2026)
- Timestamp: 2026-09-20T10:49:19Z
- CWD: /home/codyh/workspace/open-pajero-maps

## Initial Request (verbatim)

> produce using the /workflow:design

(Preceded in the same session by: "research each deviation and explain causes, not just the measured deviation. Further, conduct an analysis of what else is different between reference and target. In principle, we want to see the only deviations be natural - meaning they are derived from the source data, not out of the way we have processed it. Even so, we should look critically at structural differences in source data and how that might lead to problems in the generated disc. Structural differences in the source are worth calling out and may require compensation. So our analysis needs to understand root causes", then "Hand to a number of subagents", then "produce a design  which captures these changes".)

## Design Conversation

### Turn 1

**Agent asked:** Scope of this design; what happens if the coordinate-range test fails; how to emit accented names; which phases are genuinely unsettled (Open approach).

**User responded:** Scope: "just produce the WP1 remediation but the spikes should be documented in architecture as unknowns". Gate: hard stop and re-analyse. Names: fold to ASCII uppercase. Approach: "Effectively all are known or will resolve to known (there's one canonical approach, whether we know it now or not). If we don't have enough information to discover the known we will do pre-work researching it. This isn't a case of try-multiple and iterate".

**Agent decisions:**

- Design covers WP1 map-layer remediation only; WP2/WP3 spikes go into `docs/ARCHITECTURE.md` as unknowns.
- Phase 2 is a hard gate; failure bounces the design.
- Names are ASCII-folded uppercase.
- Every phase is flagged `known`; missing information is handled by research at the start of the phase.

## Agent Decisions

- **Phase 10 owns the ledger**: deviations are regenerated from a single final build rather than accepted piecemeal now. Rationale: the current evidence is a mix of stale-report and direct-decode measurements, and many listed deviations may disappear once the processing artifacts are fixed.
- **Foreign land and G-only edge cells** left as an open question for the user to accept at Phase 10, not decided now. Rationale: acceptance should be against the final measured ledger.
- **Rebuild dependency recorded**: coordinate range is baked into the spool at extraction, so Phase 3 re-extracts. Rationale: found in recon (`spool.py`, extractor `latlon_to_xy`, `_cenc.c` constant).

### Turn 2

**Agent asked:** Accept the foreign-land tail, the 102 G-only edge cells, and R-copied unverified flags?

**User responded:** Lack of foreign lands is a natural deviation; explain the 102 edge cells. "No we don't just blindly accept flags, we can create a table of the flags and document known and unknown. We'll record the deviation and test later, never leave undocumented".

**Agent decisions:**

- Foreign-land absence is natural.
- The 102 cells are unexplained until Phase 6 lists and classifies them.
- Flags go in `docs/design/flag-table.md` (known/unknown, R census, OSM source, G value, pending test); ledger class is *documented-unknown*.

### Turn 3 (docs consolidation, 2026-09-20)

**User responded:** A docs area of authoritative, validated schema definitions, broken into files, that establishes what is verified vs assumed or unknown and always holds the best-known understanding from any source.

**Agent decisions:**

- Unknowns and the flag table move from `docs/ARCHITECTURE.md` / `docs/design/flag-table.md` to `docs/schema/` (`UNKNOWNS.md`, `flags.md`). Surface amendment only; no outcome, contract or phase change.
- Each phase that learns a format fact updates the schema rows it touches in the same change.

### Turn 4 (build hot path to C, 2026-09-25)

**User responded** (relayed by the orchestrator):

- One C call per cell range. C takes spool bytes plus pre-pass data and returns finished frame bytes plus declined cells. C owns overlap, clip, `mult_const`, encoding, division, retile and halo. Python owns planning, mask and thresholds, CLI, the pool, the manifest, assembly orchestration, and verification. "It has to be absolutely clear, since our main problem is new work (tests and build) hit python and then we have to refactor later onto C. Clearer boundaries on both sides will avoid this."
- Hot paths are design contracts. The full-AU `-j 12` wall is under 60 s. Budgets are per level. Any unit touching a hot path reports a Python / C / handoff split.
- Tests have three layers: pytest boundary tests decoded by the Python decoder (the default), a small C unit binary run from pytest, and goldens captured before each port and matched byte for byte. No Python copy of build logic may exist, not even as an oracle.
- Worker waiting rules are a process contract that every brief carries.
- Port in profile order: the overlap scan with merge first, then divide. Every step is gated on the full-disc sha and deletes the Python it replaced. Verification-tool speed is its own item.

**Agent decisions:**

- Placement: a lettered Phase 3C between Phase 3's done units and its remaining ones, so later phases keep their numbers.
- Two entry points: E1 (the pre-pass, once per spool chunk) and E2 (the range encode, once per cell range).
- Declined cells are transitional: "needs division" only, and the list is empty at close.
- 3-12 is withdrawn, and its size question becomes 3-13 on the C pipeline.
- 3-10 is held until after 3C: its extractor half stays Python and its drop guard goes into C.
- 3-05 and 3-06 run on the C pipeline.
- `quantisation_roundtrip` becomes a check of the decoded disc against the spool with no build imports. This drops the per-origin breakdown and supersedes "pass a pool to `build_level`".
- `coord_scale` becomes parallel and raw.
- Per-level budgets are derived from the 3-07 and 3-11 profiles.
- Open for the user: an extraction boundary, the C build mechanism, and golden fixture size.
