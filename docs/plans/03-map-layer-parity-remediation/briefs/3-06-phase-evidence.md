# Brief: 3-06 — Phase 3 evidence against the amended outcome

Consumer: the orchestrator, which records the phase verdict in `IMPLEMENTATION.md` and decides whether Phase 4 starts.
Owned paths: new `docs/plans/03-map-layer-parity-remediation/EVIDENCE-3.json`, and the untracked build outputs `output/ALLDATA.KWI` / `output/manifest.json`. Touch no source file.
Commits: Commit `EVIDENCE-3.json` to the current branch.
Depends on: 3-04, 3-05.
Runs alongside: nothing.
Budget: 6 files to read, about 150 lines to write, 40 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended" in full, and the Phase 3 entry under "## Phases".
2. The reports back from 3-01 through 3-05 (your orchestrator has them) — commands, signatures, shas, and every concern raised.
3. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-15.json` and `GATE-2.md` — the shape of a grounded verdict record in this plan. Match it; do not invent a new format.
4. 3-04's two modules, for their command lines and output shape.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Run each clause of the amended Phase 3 outcome, record what it returned, and say whether the clause is met — clause by clause, with the command that produced each answer. Nothing here is a judgement call dressed as a result.

## Contract

Cited, DESIGN.md, "#### Phase 3 — Outcome, as amended", verbatim and in full:

> Grounded: `range_for` feeds both encoders and no `COORD_RANGE` constant remains (a source check, not a judgement); the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1, 4 and 12; `pytest parser/tests` passes. The first clause is tightened: "coordinate maxima equal `coord_scale.json`" is content-dependent — a sparse cell legitimately never reaches its maximum — and is replaced by **zero parcels exceeding their class range**, the same invariant Phase 2 uses, plus a **per-vertex quantisation round-trip**: lat/lon to pixel to lat/lon agrees within half a pixel for every vertex written.

That is five clauses. Record each separately:

1. `range_for` feeds both encoders and no `COORD_RANGE` constant remains — a **source check**. `git grep -rn "COORD_RANGE\|COORD_MAX" -- parser/` plus a grep showing `range_for` reaching both `synth.py`'s path and `_cenc.c`'s parameter. Quote the output. The only permitted survivor is `COORD_RANGE_RL` in `parser/tools/header_word_census.py`, a route-planning-layer constant; note it explicitly so no later reader mistakes it for a miss.
2. Zero parcels exceeding their class range — the `coord_scale` check must **PASS** on the rebuilt disc, with the exceedance count zero. Also record its verdict on R (PASS) as the control.
3. The per-vertex quantisation round-trip within half a pixel — `parser/tools/quantisation_roundtrip.py` over the whole spool. Record the vertex counts per kind, the failure count, and the worst overshoot in raw units.
4. Two builds byte-identical at `-j` 1, 4 and 12 — from 3-05's six-row table. Do not re-run the matrix; if 3-05 did not complete it, that is a `blocked` report, not a re-run.
5. `.venv-rp/bin/python -m pytest parser/tests -q` passes — record the count and compare it to 407 at the start of the phase.

Binding:

- **Report the measurement, not a defence of it.** If a clause is not met, `EVIDENCE-3.json` records it as not met and your status is `done` with the verdict stated plainly. Phase 3 is not a gate phase (Phase 2 was) and has no bounce ritual, but a failed clause is the orchestrator's decision to make, not yours to soften. Do not adjust a threshold, do not re-scope a criterion, do not re-run a check hoping for a different answer.
- **Promote the disc.** Copy 3-05's retained build to `output/ALLDATA.KWI` and update `output/manifest.json` so the harness is manifest-bound to the new sha. The old sha `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743` is retired by this phase; record the retirement and the new sha in the evidence file. Do not repair `manifest.json`'s stale `spool_dir` worktree path — that is a pre-existing carried defect, out of this unit's scope; name it in your report.
- **Run the full harness once** (`parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report <scratch>/compare_report.json`) and record every check's status against `EXPECTATIONS.md`'s Phase 1 table. Coordinates changed on every parcel, so `envelope`, `mfde`, `spotcheck` and `vocab` may move. **Any check that moves from PASS to FAIL is a regression and must be called out by name**, with the message. Checks already expected to FAIL (`container`, `envelope`, `mfde`, `shape`, `vocab`) staying FAIL is not a finding; their *messages* changing may be. Do not edit `EXPECTATIONS.md` — the orchestrator owns it.
- `EVIDENCE-3.json` is deterministic: sorted keys, no timestamps beyond a single stated run date, no absolute paths outside recorded command lines.

R is at `/run/media/codyh/464210-8480`; Python is `.venv-rp/bin/python`. Never edit anything under `.claude/worktrees/`.

## Changes

`EVIDENCE-3.json`: one object per clause with `clause`, `command`, `result`, `met` (true/false), and the raw figures. Plus a `disc` block (new sha, size, retired sha), a `harness` block (every check's status and message, and any PASS→FAIL regression named), and a `concerns` list carrying forward every concern 3-01 through 3-05 raised that is still open.

### Keep untouched

Every file under `parser/`. `DESIGN.md`, `IMPLEMENTATION.md`, `EXPECTATIONS.md`, `GATE-2.md`, `EVIDENCE-2-*.json`. `output/spool`.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- All five clauses run, with their commands and outputs quoted in your report and recorded in `EVIDENCE-3.json`.
- `.venv-rp/bin/python -m pytest parser/tests -q` — count reported.
- The full harness run recorded, with the PASS/FAIL set compared to `EXPECTATIONS.md` and any regression named.
- `output/ALLDATA.KWI` promoted, its sha256 matching 3-05's, and `output/manifest.json` bound to it.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then a one-line verdict per clause (met / not met, with the number), the new disc sha, any harness regression by name, the carried concerns still open, and any deviation from this brief and why. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Amendment after 3-02 (orchestrator, 2026-09-24)

- **Spool path.** Use `output/extract_timing/spool` (binary `KWSPIDX1`, stats match the manifest's `spool_stats`) wherever this brief says `output/spool`; `output/spool` is a legacy pickle spool that `SpoolReader` rejects.
- **Baseline.** 3-02 removed the encoders' stored-pixel preference; road nodes' y moved from the spool's stale y-down pixels onto the settled y-up orientation. The pre-3-03 baseline is full disc `9407122122b9…` / Perth `99d72f0b1cf14b8b…`; `51c254ac…` / `e275879f…` are retired (they predate 2-06).
- **Scratch.** `/tmp` hits its disk quota on full builds; put scratch under `output/scratch-<unit>/` (gitignored) and set `TMPDIR` there.
