# Oracle chain and live pin contract

Two contracts govern which G disc is the oracle and what a plan 04 Phase 3
close must compare. They were established by plan 31
([record](../plans/31-phase3-oracle-and-pin-gates.md)). The tools and tables
are in `docs/plans/04-c-core-orchestration/triage/oracle_chain/`.

## Oracle chain

Every move of the oracle disc's sha256 is a recorded re-oracle hop. The chain
table (`oracle_chain.tsv` / `.json`) has one row per hop, with these fields:

- full from/to digests and the unit that signed the hop;
- changed-cell (or changed-leaf) count, with the path and sha256 of the
  authoritative cell list;
- a confinement claim and an unexplained count. Unexplained cells are 0, or
  each is named with the reason it is open.

Cell identity is measured on independent layouts, so offsets, container,
index and sector padding are excluded. Two identities are used:

- **Whole-frame multiset per cell.** This is the sorted (length, sha256)
  frames indexed under each parent cell.
- **Routed footprint identity.** This is the sorted (exact footprint, length,
  sha256) triples for each base cell. It is strictly finer than the multiset
  identity: it catches a divided-leaf payload swap or a footprint change that
  leaves the multiset unchanged.

A changed-cell list counts as complete only when `routed-diff` finds 0
routed-only cells and 0 missing baseline cells against it. A hop never
overwrites a protected disc; a successor is written to a new path and recorded
as a new row or successor record.

Later successors follow the same discipline. Plan 34 recorded successor
`4e6b0de7…` from `2ee3456a…` with a classified per-cell diff
(`docs/plans/04-c-core-orchestration/triage/l0_empty_slot/successor_oracle_4e6b0de7.json`).

## Live pin contract

For a Phase 3 close, the pinned set is the set of spool-caused K1 failures on
the oracle disc in force at close time. It is not the historical S02
candidate view. If the live failing count is 0 for every K1 kind, the live
pinned set is ∅ and the close compares ∅ = ∅. A missing kind count, or any
positive one, keeps the contract open.

The historical `pinned_candidates.tsv` (100 shown of 26,650 groups /
1,939,931 rows, `TRUNCATED=yes`) stays a candidate view. Its disposition is
`residual-not-required-for-live-close`: the full enumerations were never
committed. Pin rows are never invented, and the 100-row view is never
rewritten as a full list.

A future close verify must re-measure live K1 on the disc in force and apply
this rule. Neither contract closes plan 04 Phase 3 by itself.

## Carried follow-ups

- AU 3-11 routed completeness: **discharged by plan 36 Phase 1.** The
  pre-3-11 disc was replayed byte-exact (`87a01b14…`), and `routed-diff`
  on the 3-11 pins gives 0 routed-only and 0 missing cells against the
  37-cell list. `oracle_chain.tsv` 3-11 row: `replay-routed-verified`;
  evidence is in `triage/oracle_chain/evidence/routed-3-11-au.json`.
- 3-14 payload cause attribution: the AU 246,123 and Perth 795 changed cells
  are listed with no attributed causes.
- AU 3-11's +60 B non-payload growth is attributed by plan 07
  (`docs/design/g-new-nonpayload-accounting.md`) to Map Frame allocation
  padding, 34×(−4)+7×(+28). Plan 36 Phase 1 reproduced it with
  `triage/oracle_chain/region_accounting.py`: the same 41 spans, +164
  payload, and 0 unaccounted bytes (`evidence/region-3-11-au.json`).
  The 3-14 container, index and padding scope is accounted by plan 36 Phase 2
  (`triage/oracle_chain/hop_3_14/container-{au,perth}.json`, 0 unaccounted).
- The historical `pinned_candidates` exhaustive identity is
  unverifiable from git. It is not required for a live close while live
  failing is 0.
