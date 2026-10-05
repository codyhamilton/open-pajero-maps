# Phase 1 recovery note

The original mechanism bytes cannot be restored. On the recorded host search,
`output/scratch-3-07/`, `scratch-3-08/`, `scratch-3-13/`, `scratch-3-14/` and
`scratch-3-15/` targets were absent; the older worktree's 3-07/08/13 links were
dangling. `scratch-3-11/` had no `dump_new_ext/` or `classify_new/`, and 3-12
retained only plan 17's `extend.py`. Plan 14's
`output/scratch-14/mechanism_recovery_search.txt` was empty. These are the
read-only Ground findings recorded in the plan 28 record ([28-phase1-per-rule-classify-recovery.md](../../28-phase1-per-rule-classify-recovery.md)); this worker did
not repeat a host-wide search.

The producer and side tables had lived only in ignored scratch. No tracked
code produced `other_mechanism`, so the old provenance instructions depended
on deleted scripts. Plan 14 unit 1-01 selected brief fallback (c), recording
`evidence-gap:other_mechanism` for every row instead of recomputing (b). Phase
2 rejected recovery as its gate, without subsequently scheduling it. This is
[plan 14's F3 follow-up](../../14-completeness-root-cause.md).

There were two classifier gates: the 144-byte dump lacked `other_mechanism`
(exit 2, unknown column), and its completeness-only manifest cannot accept
O02/O03's other kinds (unknown kind). Plan 28 generates the completeness-only
projection of O01/O04/O05/O06, preserving every rule object's literal JSON
bytes and order and recording the source and projection hashes. The classifier
code remains unchanged; exit 1 / NO_RULE is a valid measurement.

The new [producer](per_rule_completeness_mechanism.py) recomputes against the
current contract. It checks the baseline hash before use, checks each native
key and every 3-01 demander against the saved proof, imports the plan-04
clip/densify and production-C probe helpers, and uses exact rational topology
contacts (including non-adjacent touches and overlaps). O01/O04/O05 require
one predicate to hold for all demanders. Multiple matches are recorded and
resolved in source-rule order. O04 probes deletion of exactly the stored
penultimate coordinate: crossings must disappear and the raw a/b/c demand
must disappear or gain a C record. Missing or contradictory proof raises an
error; it never becomes mechanism 0. Current C probes use rings already in
memory, converting their raw lattice coordinates back to degrees; original
record counts must agree with the saved direct-degree probe.

O06 is excluded by a contract proof under the pinned `_cenc.c` SHA256
`5c43e00dd0c6215123e6713423e8a8981d95ea9e06d95cbbd5e1b7b2249e2af0`:
`enc_bg` splits physical class records into units of at most 4095, so the
12-bit declared count equals the physical count. This does not infer hidden
records from decoded counts. Plan 14 records that a current-contract
re-encode is byte-identical to the disc in force. A changed source pin fails
closed and needs a new count-contract proof. No disc is opened here.

Every side row records its full key, original dump_row, demander identities,
bbox, exact source area2, topology, clip area2, original C results, repair
probe and count-contract evidence, path and multiple matches. All processed
rows use the light path. No spool/disc fallback is implemented: missing saved
proofs require a separately bounded heavy probe, never an implicit read.
The optional legacy-contract control is skipped.

The new dump join copies raw bytes, including padding and NaN payloads, into
152-byte rows; checks all 144 original bytes independently; zeros byte 144
and unused tail bytes; and records selected original row ids in the manifest.
Window assignments thus keep their baseline dump_row identity. The publish
step reads the actual classify u16 array, verifies first-match consistency
and count/partition outputs, and generates both the assignment TSV and
controls. It does not edit plan 14's historical table or reconcile causes
(Phase 2 owns reconciliation).

## Worker evidence and remaining execution

The 25-row window is under `output/scratch-28/window25/`: O01 2, O04 6,
O05 3, NO_RULE 14, no evidence-gap; classifier exit 1 / PARTITION FAIL.
Historic selected rows are all NO_RULE. Full 776-row side/assignment TSVs and
controls are deliberately pending the guarded commands in
[the plan 28 record](../../28-phase1-per-rule-classify-recovery.md) and
[provenance](../../../provenance.md). This note does not claim Phase 1 closed.

The new fixture first failed because the mode/function did not exist; its
byte preservation, full item key, noncontiguous mapping, pre-write rejection,
exact topology, all-demander and first-match checks now pass. Existing dump
join tests also pass. Their replay root is relocated at test runtime into
scratch-28, preserving the brief's scratch-write scope.

**Contradiction requiring Execute/Design attention:** the quoted 3-15 totals
502 assigned / 274 NO_RULE versus 3-17's 468 / 308 differ by 34. Specifically
O05 loses 30 and O04 loses 4. The stated explanation names only 30 O05 + 1
O04 = 31 forced-zero rows. Three rows are not explained by that statement.
The generated controls state this arithmetic and list predicate inputs for
all applicable per-row identity mismatches and differing aggregate buckets.
Without the deleted inherited table, aggregate bucket candidates cannot be
claimed as exact 3-17 identity differences. No prediction forces a code.
