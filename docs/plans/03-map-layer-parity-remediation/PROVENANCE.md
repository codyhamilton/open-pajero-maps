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
