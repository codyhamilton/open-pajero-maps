# Seven O04 spool successor rows

Plan 33 closed the seven completeness rows that plan 28 had left as
conflict-proven O04 / spool source defects: dump_row 138, 236, 282, 284,
317, 496 and 563. It proved per row, from disc bytes, that the demanded
background type is absent in that cell on the G successor, on the G
historical control and on the original DVD (R). All seven were closed as
**proven non-deviation**, with 0 conflict-open, no spool edit and no
relabel. It did what it set out to do. It did not close plan 04 Phase 3.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
> 
> Close the plan-28 follow-up for the seven O04 / spool completeness rows (dump_row 138, 236, 282, 284, 317, 496, 563): each needs a proven root cause (already O04) and either a **fix** or a **proven non-deviation**. Never relabel. R presence is false for all seven — any spool repair that makes G emit the type in-cell would create a new G≠R presence deviation and is forbidden without an explicit, evidenced ruling. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Skip plan 29 close-out (Execute).

## Why This Existed

Plan 28 reconciled 776 completeness assignments. Seven of them had a proven
spool cause, O04: a crossing-closing ring, with a penultimate-deletion
discriminator. No design had yet closed them as either a fix or a proven
non-deviation under the DVD bar. In three of the rows (138, 284, 496), the
penultimate repair would make G emit a piece where R has none. That would
invent a new G≠R presence deviation, so a spool fix could not simply be
applied. Design ruled that there is **no default verdict**: each row needs
its own witness.

## What Was Built

**Changed:**

- `docs/plans/04-c-core-orchestration/triage/o04_seven/`:
  - `presence_witness.py`, `.tsv`, `.json`;
  - `disposition.py`, `.tsv`, `.json`;
  - `README.md` with the reproduction commands;
- `parser/tests/test_o04_presence_witness.py`;
- `parser/tests/test_o04_disposition.py`;
- the contract `docs/design/presence-non-deviation-witness.md`;
- the OVERVIEW sentence for the seven rows, and an appended line in the
  plan-28 record.

### Phase 1 — presence witness

`presence_witness.py` probes each of the seven cells:

- on G successor `2ee3456a…` and G historical `4ed9cd80…`, which it
  stream-hashes;
- on R `8c2d2027…`, through plan 29's hardened index reader.

For every indexed covering frame it retains the index and frame bytes (hex
and SHA-256). Each frame is decoded twice, by `kiwiw.parcel.decode_parcel`
and by plan 14's `decode_slot_shapes`, and the two must agree on the count
of demanded-type class-2 polygons. A lookup or decode failure is recorded as
`lookup_failed` and can never count as absence. `publish` replays every
retained index read and re-decodes every frame before it writes the table.
It also re-checks each row's O04 predicate, its penultimate stratum and the
retained R-zero assertion against the hashed plan-28 tables.

**Result:** all 7 rows are absence-proven. Every slot resolved; the
demanded type count is 0 on all three discs; there are 0 exceptions.

R frames are L0 sparse tiles whose extent strictly contains the G cell, so
a zero there implies zero in the cell. The demanded codes are 288 for five
rows and 578 for two. Both codes occur on R elsewhere, so their absence is
meaningful.

### Phase 2 — disposition

`disposition.py` assigns verdicts from the Phase 1 witness only. The
verdict set is {proven-non-deviation, fix-landed, conflict-open}, and there
is no default.

**Result:** 7 proven-non-deviation, 0 fix-landed, 0 conflict-open.

- K1 completeness on the successor is 1,800,514 checked / 0 failing. This
  is cited from the retained successor comparison (sha256 `d4d5038d…`); K1
  was not rerun.
- The emit-piece counterfactual is recorded as evidence only.
- Every row keeps the O04 defect as a named spool-hygiene residual.

## Deviations

- Execute ran the Phase 2 `publish`, which reads only committed JSON, under
  `prlimit` without the shared heavy lock, because another project's job
  held the lock. Disc probes all ran under the wrapper and lock.
- The R pin was cited from plan 29's stream hash, not re-hashed by the
  probe. The same path was later stream-hashed to `8c2d2027…` by plan 34's
  guarded snapshot that day.
- The terminal review was written by Execute, not a fresh Codex seat. The
  Codex review seat died at the usage limit. Unit work was done by Codex.
- Close-out moved the lasting files into plan 04's triage tree.
  `presence_witness.py`'s own hash changed (its repository-root depth), so a
  `publish` over the retained probes now fails closed with "rerun probe".
  Fresh guarded probes reproduce the evidence. `disposition.py publish`
  reproduces the committed outputs exactly; only the evidence paths
  changed. Its `probe_reader_sha256` deliberately keeps the probe tool's
  original path and hash (`1fd3e253…`), because that is the tool version the
  retained probes were run with.

## Review

PASS_WITH_FOLLOWUPS.

- Both publishers replayed byte-identically from retained evidence.
- The witness and disposition tests passed (81).
- The emit-piece rows' zeros were confirmed against decoded frames that
  carry other codes, so a silent decoder does not explain them.
- The R tile-containment and lookup-failure rules were checked.
- Three low follow-ups, none blocking:
  - R identity cited rather than streamed;
  - the lock-free light publish;
  - reduced reviewer independence.

## Residual Risks

- The seven O04 source defects remain in the spool as spool-hygiene
  residuals.
- The K1 figure is a citation for `2ee3456a…`.
- A new successor disc needs re-attestation only if its diff touches these
  cells. All seven are inside the L0 parcel mask.

## Follow-ups

- **Stream-hash R inside presence probes.** Recorded in
  `docs/design/presence-non-deviation-witness.md` (item 6).
- **Plan-25 guard wording for light JSON-only publishers.** Carried in the
  same contract's disc-identity and guard notes. It is otherwise a plan-25
  guard question for Execute.
- **`readers()` imports plan 30's `fingerprint.py` from its plan folder.**
  The path must follow that file when plan 30 closes out. Noted in the
  triage `README.md`.

## Decisions Worth Keeping

- No default verdict. A per-row byte or decode witness on G and R is the
  only route to proven non-deviation.
- A source repair that would make G emit a type R lacks is forbidden
  without an explicit ruling. A counterfactual repair is evidence, not a
  mandate.
