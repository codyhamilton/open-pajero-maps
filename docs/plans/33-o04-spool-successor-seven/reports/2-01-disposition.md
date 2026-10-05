# Unit 2-01 handoff

Implemented per-row disposition publication from the pinned Phase 1 evidence.
Light publication exited 0 and produced seven `proven-non-deviation` rows,
zero `fix-landed` and zero `conflict-open`. Every row passed its own retained
index/frame-byte replay with integer-zero G successor, G historical and R
counts and no exceptions. JSON/TSV agreement, probe hashes, full native keys,
O04 identities and source hashes are checked; missing or invalid evidence
cannot receive a default verdict. Publication rejects a changed Phase 1 JSON
unless an expected hash is explicitly supplied.

The outputs retain witness row references and SHA256 provenance, disc in
force, no fix artefacts and the cited successor K1 result of 1,800,514 checked /
0 failing. K1 comparison hash is
`d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b`.
It is checked as retained evidence; K1 was not rerun. Original reader hashes
remain historical probe provenance; live retained-byte replay permits an
import-path-only close-out edit without reopening discs.

The owned synthetic suite passed **50 tests**. Lookup failures, positive
counts on any disc, missing witnesses, hash mismatches, forged zero summaries,
invalid empty slots, valid sentinel slots, CSV fields beyond Python's default
limit, and K1 totals/kind inconsistencies are covered. The success case guards
publisher I/O against disc/spool opens and verifies all seven output rows.
Exact test and guarded publication commands are in `../phase2_note.md`.

No scope departures. No spool edit, disc/R-disc open, encode, K1 run,
completeness reseat, OVERVIEW edit or plan-04 Phase-3 close was performed.
All seven crossing-closing ring defects remain **O04 / spool hygiene
residuals**. The penultimate emit-piece repairs for 138/284/496 remain evidence
only because applying them would invent R-absent presence; the four other rows
use the permitted non-deviation route without an optional hygiene patch.
No implementation problems remain known in this unit.

Execute must run the guarded publish command in `../phase2_note.md` and require
exit 0, `phase2_verified: true`, verdict counts 7/0/0. The worker's light replay
does not replace that guarded measurement or the phase-closing record. Execute
then narrows OVERVIEW and the plan-28 follow-up to these counts, names all seven
spool hygiene residuals, and records Phase 2 without claiming Phase 3 closed.
Those Execute-owned steps remain unfinished. Changes are uncommitted as
instructed.
