# Provenance: Build Performance

## Session

- Session: Initial plan (September 19, 2026)
- CWD: /home/codyh/workspace/open-pajero-maps/.claude/worktrees/brief-34-ceiling-only

## Initial Request (verbatim)

> The build time runs far too long in this repo. Lets investigate what can be done - profile the runtime. We would want to see something like an OOM improvement in the runtime or more. Lets profile where the time is being spent, and if there is a ceiling on performance due to using python for what is very computational and memory intensive work
>
> Ok plan the first four suggestions (leave our C hot path until after other stages)

## Planning Conversation

### Turn 1

**Agent asked:** numpy is not installed in `.venv-rp` (only osmium). May the build take numpy as a hard dependency, recorded in `docs/provenance.md`?

**User responded:** Yes, add numpy.

**Agent decisions:**

- numpy becomes a build dependency of the assembly stage; the spool format is columnar so it feeds numpy directly.

### Turn 2

**Agent asked:** How should the existing 6.8 GB pickle spool move to the new binary format: one-time converter, or re-extract from the PBF?

**User responded:** One-time converter.

**Agent decisions:**

- A converter tool is in scope; the extractor's `SpoolWriter` also writes the new format directly. No re-extraction is needed to validate byte-identity against the current baseline.

## Agent Decisions

- **Baseline is the brief-34 build**: `output/manifest.json` sha256 `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743`, 1,397,923,200 B, built after commit 7917b86 at HEAD 6ecd5c8. Rationale: the byte-identity constraint needs one fixed reference; a Perth-fixture baseline is captured at Phase 0 from the same commit.
- **Phase order is streaming, spool, vectorize, parallel** (not the order the user listed them). Rationale: parallel workers depend on the spill/streaming contract and on an mmap-able spool; vectorization is cleanest on the columnar spool.
- **Vectorization claim tempered**: the background-shape delta encoder is a clamped, quantized recurrence (`xc = clamp(xc + dx*mc)`), so only the lat/lon-to-pixel transform batches cleanly; road nodes carry precomputed integer x/y, so road gains come from packing, not float math. Rationale: my earlier "5-10x on encoders" was optimistic; acceptance criteria use measured floors, not that figure.
- **Challenge pass done inline, no subagent**: the session's instructions reserve subagents for explicit user requests, so the adversarial pass was self-run (recorded in the plan's Provenance Notes).
- **Extractor and compare_disc runtime out of scope**: the extraction pass (33 min to 1:27) and `compare_disc.py` (~22 min) are both slower than assembly's remaining cost; flagged as follow-up plans, not folded in. Rationale: user scoped this to the four assembly-side suggestions.
