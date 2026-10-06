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
(`docs/plans/34-l0-empty-slot-frame-parity/successor_oracle_4e6b0de7.json`).

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

- AU 3-11 routed completeness: its 37-cell list is complete under the
  multiset identity, but no routed run has proven it. To prove it, run
  `oracle_chain.py routed-diff` with the 3-11 hop pins to a new scratch path.
- 3-14 payload cause attribution: the AU 246,123 and Perth 795 changed cells
  are listed with no attributed causes.
- AU 3-11's +60 B non-payload growth is unattributed. The 3-14 container,
  index and padding scope is unmeasured.
- The historical `pinned_candidates` exhaustive identity is
  unverifiable from git. It is not required for a live close while live
  failing is 0.
