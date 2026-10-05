# Live completeness evidence — Phase 1

**Failing: 776. Verified attributed-by-rule: O01 0, O04 0, O05 0, O06 0,
other 0; total 0. Unattributed in this evidence table: 776, all assignment
evidence gaps; confirmed `NO_RULE`: 0.** Definitive live per-rule and
unclassified counts are unknown because classify could not read the missing
`other_mechanism` column. Zero here counts verified assignments in this table,
and does not assert that the historical assignments have disappeared.

**Numeric drift:** failing vs 3-17's 776: **0**. Unresolved evidence entries
vs 3-17's 308 unclassified: **+468**; vs 3-15's 274 unattributed: **+502**.
Those latter differences measure unavailable assignment evidence, rather than
a measured movement in the classifier partition. The historical 3-17
partition (O01 363, O04 3, O05 102; assigned 468, unclassified 308) and the
3-15 recount (O01 363, O04 7, O05 132; assigned 502, unattributed 274) remain
inputs, and are not substituted as fresh assignments.

G SHA256:
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
The existing restored disc was used; there is no new oracle. Fresh K1 checked
1,800,514 completeness requirements and emitted 776 rows, all L0. Its exit 1
is the measured K1 failure. The primary dump contains completeness only.

[completeness_evidence.tsv](completeness_evidence.tsv) has exactly one row
per `(level, ix, iy, code, p0..p6, shape, vert)`, in native dump order.
`dump_row` is zero-based. Membership uses the full identities preserved in
3-17, including its shared fields, and 3-16's TSV keys with `vert=-1`.
All **188** historic keys and all **89** added keys are present; the sets are
disjoint. **499** live keys belong to neither set. No historical file changes.

Each R/G witness names the disc, the covering leaf paths, coordinate frames,
file byte offsets and lengths, SHA256 hashes, decoded polygon-type counts,
and the target type count. Counts use K1's class-2 / at-least-three-coordinates
presence contract. Covering divided leaves are enumerated; sparse slots may
alias a shared frame. This is a decoded frame-presence witness, and does not
assert geometric intersection of each R piece with the target slot. A decode
error is explicitly an `evidence-gap`, rather than a zero count.

Measured R counts: **433** rows with zero qualifying target polygons,
**342** with one, and **1** with eleven. Measured G counts: **776** with zero.
Both discs have **0** enumeration/decode gaps. R SHA256 is
`8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275`.

Each requirement witness identifies the raw K1 row and reason. Where a
source was recovered, it additionally identifies the spool cell's byte
offset, length and hash, the background record ordinal, and a concrete
requirement trigger using `_k1_cmp.c`'s single-cell rounded-area (a) or
cross-cell deep-vertex (b) arithmetic. The fresh dump establishes the actual
K1 demand; this source scan does not independently repeat K1's complete
block-local/tall-source selection. Centre-based (c) source enumeration is
left as an explicit open question wherever needed. Requirement evidence
does not establish an `other_mechanism` assignment or a cause.

**775** rows have a concrete source trigger. The remaining source-evidence
open question is native row **335**, `(level=0, ix=1379, iy=1138, code=288,
p0..p6=0, shape=-1, vert=-1)`: which exact source and requirement branch
establish its live K1 demand? Its raw K1 requirement witness is retained;
the source column is explicitly `evidence-gap` in its referenced JSON.

The cleaned side tables were not recovered. `dump_ext/` therefore preserves
the raw 144-byte rows byte-for-byte, with an `evidence_gaps` manifest entry
instead of manufactured mechanism bytes. Unchanged-rule classify exits **2**
with `rule O01: unknown column 'other_mechanism'`; no partition totals or
assignment array are produced. The TSV's `evidence-gap:other_mechanism`
records that rejection per row. Open question: what reproducible mechanism
witness supports each assignment? No cause or new rule is proposed.

Reproduce from the repository root, retaining the current discs and spool:

**Checker pin (review F6):** the expected 776 failures need the pre-3-03 completeness checker. Run these commands from a throwaway worktree at `0b19b5e` (`git worktree add --detach <tmp> 0b19b5e`), with isolated scratch destinations, so the recorded outputs are not overwritten. At or after `a890662`, the same K1 command gives 0 completeness failures.

```sh
flock output/.heavy.lock /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B parser/tools/quantisation_roundtrip.py --disc output/scratch-14/G_new/ALLDATA.KWI --spool output/extract_timing/spool --out output/scratch-14/k1_full.json -j 6 --engine c --dump-failures output/scratch-14/dump_raw --dump-kinds completeness
flock output/.heavy.lock /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B docs/plans/14-completeness-root-cause/triage/build_evidence.py
flock output/.heavy.lock /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B docs/plans/14-completeness-root-cause/triage/verify_evidence.py
```

Expected exits: K1 1; builder 0 after retaining classify's exit 2; audit 0.
Scratch retains `k1_full.log`, `dump_raw/`, `dump_ext/`, `classify_invocation.json`,
`classify.{stdout,stderr}`, `witnesses/`, `evidence_inputs.json`,
`evidence_summary.json` and `evidence_verification.json`. The committed helpers
write only plan-14 evidence and scratch-14 products. Protected scratch-3-11,
rules, encoder/checker sources, historical science packets and plan 15 are
unchanged. This table does not close plan 04 Phase 3.

Validation: **PASS** for 776 unique keys, exact historic/added flags and all
referenced witnesses; **1,791 distinct byte ranges** re-hashed against the
current discs/spool. The raw and gap-annotated completeness binaries are
byte-identical, SHA256
`1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323`.
G's oracle hash was checked again after witness generation. Protected
scratch-3-11 remained
`013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`;
rule files and encoder/checker source checksums also remained unchanged.
