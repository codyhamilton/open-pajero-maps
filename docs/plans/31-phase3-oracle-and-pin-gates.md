# Plan 04 Phase 3 — oracle chain and pin gates (slice 1)

Plan 31 was the first slice of the plan 04 Phase 3 close package. It proved
that every move of the oracle disc, from the pre-3-11 baseline to the plan 29
successor, is a recorded re-oracle with an exact changed-cell or leaf list. It
also stated the live pin contract a Phase 3 close must use, and disposed of
the historical 100/26,650 pinned-candidate view without inventing rows. Both
blockers it owned were discharged, with named residuals. It did not close
plan 04 Phase 3, and it did not set out to.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Draft the plan 04 Phase 3 close package. The full package (PSS PASS at ≤`-j6` / plan-20 re-verify; other-kind native classify joins; 3-11 versus 3-14 oracle; `pinned_candidates` set-equality) is too large for three phases, so this design is **slice 1 only**: the oracle exact-cell-identity gate and the `pinned_candidates` Phase-3 disposition. The provable final outcome of the *whole* package may later be an evidenced plan 04 Phase 3 close, or an exact named residual list; this slice never claims that close. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; no 3-90 re-run. Skip plan 29 close-out (Execute).

## Why This Existed
OVERVIEW listed two Phase 3 blockers with no committed gate artefact:

- **3-11 versus 3-14 oracle.** No table joined the 3-11, 3-14 and plan 29
  re-oracles to the disc in force.
- **`pinned_candidates` exhaustive set-equality.** It was unverifiable from
  git, because only 100 of 26,650 groups were ever committed. Plan 29 had
  also cleared every live K1 failure, so it was unclear what a close should
  compare.

## What Was Built
Both contracts are now in
[docs/design/oracle-chain-and-live-pin-contract.md](../design/oracle-chain-and-live-pin-contract.md).
The tools and tables are in
`docs/plans/04-c-core-orchestration/triage/oracle_chain/`:

- `oracle_chain.py`, `oracle_chain.tsv` and `oracle_chain.json`;
- `pin_contract.py`, `pin_contract.tsv` and `pin_contract.json`;
- `evidence/routed-3-14-{au,perth}.json`.

**Changed:**

- `parser/tests/test_oracle_chain.py` and `parser/tests/test_pin_contract.py`
  (49 synthetic tests);
- the plan-31 sentences in `docs/OVERVIEW.md`.

### Phase 1 — oracle chain
The chain table has six hop rows, each with full digests, the signing unit,
an artefact path and sha256, a count, a confinement claim and an unexplained
count:

| Hop | Changed cells | Unexplained |
|---|---|---|
| AU 3-11 (`87a01b14…`→`013586b5…`) | 37 L0 cells (retained list, hash verified) | 0 (37/37 predicted) |
| AU 3-14 (`013586b5…`→`4ed9cd80…`) | 246,123 measured (L0 244,060 / L2 1,944 / L6 118 / L8 1) | All listed by cell; payload causes not measured |
| Perth 3-14 (`da13a775…`→`04be2f6e…`) | 795 measured | All listed by cell; payload causes not measured |
| AU plan 29 (`4ed9cd80…`→`2ee3456a…`) | 1 L0 leaf, (0,541) leaf 928, 146 bytes | 0 |
| Perth 3-11 and plan 29 | 0 (recorded equality) | 0 |

The 3-14 diffs ran under the heavy wrapper, and the protected discs re-hashed
unchanged. Review remediation added a routed-footprint diff. On both 3-14
hops it found 0 routed-only cells and 0 missing cells, so the multiset lists
are complete under the finer routed identity.

### Phase 2 — live pin contract
Live K1 failing is 0 for every kind on `2ee3456a…`. The counts are cited by
sha256 from plan 29's compare and corroborated by plan 32's `-j6` report. The
live pinned set is therefore ∅, and the close contract is ∅ = ∅; a missing or
positive count keeps it open. The historical `pinned_candidates.tsv` has a
verified sha256 and the disposition `residual-not-required-for-live-close`.
No rows were invented.

## Deviations
- The Codex fixer seat was at its usage limit, so Execute (Grok Bot)
  implemented remediation-01 (routed diff) itself and disclosed it. The
  re-review was an independent clean seat.
- Plan 34 has since recorded successor `4e6b0de7…` from `2ee3456a…`. Live K1
  on it is also 0 failing in every kind, so the live pinned set stays ∅. The
  chain table here still ends at `2ee3456a…`; the plan 34 successor record
  extends it.

## Review
- **Terminal review (independent Codex seat): REMEDIATE.**
  - R1 (high): unordered per-cell frame multisets could miss a divided-leaf
    payload swap, so the completeness claim was unproven.
  - R2 (medium): the OVERVIEW wording overstated the measurements.
  - R3 (low): resolved in review.
- **Remediation-01.** It added `routed-diff` and its tests and ran it on both
  3-14 hops (0 routed-only cells). The OVERVIEW sentence was narrowed.
- **Re-review (independent clean seat, opencode deepseek-flash, while Codex
  and Claude were usage-limited): PASS_WITH_FOLLOWUPS.** R1 and R2 are
  resolved. The one new low follow-up, F1, is that AU 3-11 completeness is
  not re-proven under the routed identity.

## Residual Risks
- The 3-14 payload causes are unattributed. Post-close: the 3-14 container,
  index and padding scope is accounted by plan 36 Phase 2 (0 unaccounted).
  AU 3-11's +60 B was attributed by plan 07 and reproduced by plan 36
  Phase 1.
- The routed completeness proof covers only the two 3-14 hops.
- The historical exhaustive pin identity stays unverifiable from git.
- Plan 04 Phase 3 is not closed. PSS at ≤`-j6` and the close synthesis
  remain.

## Follow-ups
Carried in
[docs/design/oracle-chain-and-live-pin-contract.md](../design/oracle-chain-and-live-pin-contract.md)
§ Carried follow-ups:

- the AU 3-11 routed proof (discharged by plan 36 Phase 1:
  `replay-routed-verified`, 0 routed-only and 0 missing);
- 3-14 cause attribution;
- the 3-14 container scope. The 3-11 +60 B was already attributed by plan 07
  (padding, 34×(−4)+7×(+28)), and plan 36 Phase 1 reproduced it with 0
  unaccounted bytes;
- the historical pin identity.

PSS and the Phase 3 close synthesis stay plan 04 blockers in OVERVIEW.

Post-close note (plan 36 Phase 1, 2026-10-06): F1 is discharged. The 3-11
routed proof gives 0 routed-only and 0 missing cells. The "+60 B
unattributed" wording above is superseded: plan 07 attributed it, and plan 36
reproduced it with 0 unaccounted bytes (`oracle_chain.tsv` 3-11 row
`replay-routed-verified`).

## Decisions Worth Keeping
- With live failing at 0, the Phase 3 pinned set is the live failing set on
  the disc in force (∅), not the historical S02 candidate view.
- Completeness of a changed-cell list needs routed identity, not just
  multiset identity.
