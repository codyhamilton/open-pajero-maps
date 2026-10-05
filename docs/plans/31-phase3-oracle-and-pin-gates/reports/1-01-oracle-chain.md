# 1-01 oracle chain — worker handoff

Status: implemented, with named evidence residuals for Execute. Changes are
uncommitted as required. No ALLDATA.KWI or spool was opened. No other unit's
files/tests were touched or run. OVERVIEW remains Execute-owned.

The publisher verified the retained 3-11 list against its full recorded SHA,
its byte-identical prediction list and the small scan's exact 37-cell/41-element
scope. It verified both full plan-29 pins, all nine nonoverlapping byte ranges,
the 146-byte sum and leaf [928] confinement on both layouts. Six table rows
include Perth's 3-14 move and the recorded unchanged Perth dispositions at
3-11 and plan 29. Current 3-14 counts remain unknown measured values alongside
clearly marked historical aggregates. `publish` ran successfully using small
evidence only; no new oracle or Phase 3 close is asserted.

The bounded streaming diff and census audit are ready for Execute. The diff
uses independent cell maps and disk-backed frame multisets, so unequal disc
sizes and relocated frames do not corrupt the cell-identity comparison.
Protected disc hashes are checked before and after, inputs are read-only,
and fresh scratch output paths are required. Regenerated changed cells are
all explicitly unexplained; the tool does not recreate missing explanations
or silently promote the historical inference census to proof.

Validation: only `parser/tests/test_oracle_chain.py` ran, with
`--basetemp output/scratch-31/tests`, bytecode and pytest cache disabled.
Final result: **16 passed in 0.26s**, using exactly:

```sh
.venv-rp/bin/python -B -m pytest parser/tests/test_oracle_chain.py -q -p no:cacheprovider --basetemp output/scratch-31/tests
```

Synthetic
controls cover independent relocated layouts, changed/add/remove identities,
divided and integrated slots, alias membership, multisets across levels,
wrong SHA, mid-run mutation, output reuse, malformed frame lengths, bounded
reads, list tampering, missing-evidence publication and false successor
confinement. An initial divided-layout fixture had the wrong subrecord offset;
that fixture was corrected before the passing runs.

The final light publication command
`.venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py publish`
exited 0 and emitted six hop rows. No guarded census or disc comparison was run
by the worker.

Residuals/actions, in order:

1. Execute must run the guarded new-census audit and AU/Perth 3-14 comparisons,
   then republish from measured outputs. Exact commands, input pins and fresh
   output paths are in [phase1_note.md](../phase1_note.md#guarded-commands-for-execute).
   The required old/new discs are identified by listing; worker authorization
   deliberately excluded their contents. The missing 3-14 lists are an exact
   named residual for both hops, not zero unexplained cells.
2. No inventoried sidecar identifies a surviving pre-3-11 disc, and its old
   census was not located. The hash-verified retained 37-cell list is the
   available authority. A pre-3-11 rebuild is out of scope. Keep the historical
   +60 B non-payload-growth review residual separate from cell-scope zero.
3. The historical 3-14 record's 7 AU / 3 Perth non-payload explanations were
   inference. Missing `explanations.json` and cell identities prevent replay;
   regenerated identity lists will not settle those causes. All cells in new
   diff TSVs remain named unexplained, and container/index/padding relocation
   remains outside the identity census. Separate explanation evidence is
   needed to discharge these root-cause gaps.
4. Perth unchanged-at-3-11 and unchanged-at-plan-29 rows reuse hashed committed
   records; they are not fresh protected-disc measurements by this worker.
5. Execute narrows OVERVIEW to these exact remaining gaps and records the
   outcome. PSS and other-kind joins still block Phase 3; Phase 2 owns pins.

Departures: no implementation scope change. Heavy reads and large-census
validation are deferred to Execute by the binding brief; retained 3-14
artifacts could not be recovered, so the published table names missing evidence
instead of presenting historical aggregates as measurements. Plan 29 paths
use the user's closed-out locations. No commit was made.
