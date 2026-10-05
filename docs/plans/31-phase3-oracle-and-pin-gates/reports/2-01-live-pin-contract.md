# 2-01 — live pin contract handoff

Implemented the cited-evidence publisher and published the successor contract:
all nine K1 kinds have failing 0, with checked counts and full source hashes
in the TSV/JSON. The primary values are plan 29's **new** totals, corroborated
by the plan-32 `-j6` report and checked against all seven levels in both
sources. All four diagnostic bins have manifest rows 0 / stat size 0. Every
cited evidence file's SHA-256 is verified before publication. No K1 was run,
no protected disc or real spool was opened, and no commits were made.

Live outcome: **`live-empty`**, live failing set = live pinned-failure set =
∅; set equality true for the cited successor. Missing/invalid or positive
failure counts and incomplete/conflicting census evidence leave a kind open.
`phase2_note.md` states the future check-4 comparison and its disc-in-force
boundary. This is not a new byte attestation: reports lack embedded disc
digests; identity comes from the signed plan-29 pin plus retained run paths.

Historical outcome: **`residual-not-required-for-live-close`**, identity
**`unverifiable`**, exhaustive equality **null**. The untouched candidate TSV
matches plan 27's full `7dfe6ed7…8855a` digest, 100 distinct shown groups and
the 26,650-group / 1,939,931-row footer. Symlink-following, unlimited-depth
output inventory recovered no non-fixture enumerations; git history across
all local refs and the tracked-path inventory also have no matches. Matches
created by this unit's synthetic tests are explicitly marked as fixtures.
No historical rows or assignment equality were invented.

Verification: the owned synthetic suite passed **28 tests** with
`--basetemp output/scratch-31/tests-p2` and pytest cache disabled. It includes
negative controls for missing/positive counts, conflicts, altered evidence
hashes, incorrect successor/run paths, missing/nonempty bins, truncated-view
integrity, symlink loops and protected-path refusal. The light `publish`
entry point ran successfully against the retained cited evidence. The note
contains exact test/publish commands and an optional guarded republish command
for Execute; no measurement command is required.

Departures: none. OVERVIEW and IMPLEMENTATION were not edited because they
are outside this unit's allowed outputs; the note provides the narrow
OVERVIEW wording for Execute. All changes remain uncommitted as instructed.

Unfinished work for Execute: record the unit in IMPLEMENTATION and update
the OVERVIEW pin wording from the note; verify the Phase-2 outcome and commit
the authorized artifacts. Historical exhaustive identity would require
recovery of SHA-consistent original enumerations **and** historical
spool-assignment joins before claiming `reproduced-exhaustive`; none is
available in the searched scope. No regeneration is proposed here.

Known limitations remain explicit: no proof of renamed/external historical
copies, no fresh disc-byte attestation, no Phase-3 close, no PSS-gate clearance,
and no assessment of plan 32's other-kind joins. Phase 1's AU/Perth 3-14
cause-attribution residual also remains.
