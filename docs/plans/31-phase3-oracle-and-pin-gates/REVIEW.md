# Independent review — plan 31 oracle chain and pin gates

Verdict: **REMEDIATE**

Reviewed SHA: `ca55630cd3e6e2b04b6cbbedd2f1b21da1dffb91` (detached master
snapshot; local review, no PR). Reviewed only plan-31 commits `b831244`,
`f54a8fb`, `67d0a78`, `f636cd9`, `cb7d299`, `493a147`, `ca55630`, the specified
plan folder/two test files, and the plan-31 OVERVIEW hunks. Interleaved plans
30/32/33/34 and their current work are outside this review. Changes remain
uncommitted as requested.

One high finding is briefed. The cited hashes/counts and the Phase 2 live-empty
contract pass; the unrestricted Phase 1 changed-cell completeness claim needs
supplementary routing proof or an explicit residual. No Plan 04 Phase 3 close
is established or claimed by this review.

## Phase outcome assessment

### Phase 1 — partial

| DESIGN outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Chain table with full pins, list path/hash, count, confinement and unexplained count | **Partial** | Six JSON/TSV rows agree. AU 3-11: SHA-pinned retained 37-cell list, embedded exact identities. AU 3-14: 246,123; Perth 3-14: 795; retained TSV hashes/counts/levels match. AU plan 29: committed nine-range, 146-byte, L0 `(0,541)`, leaf `[928]` proof. Perth 3-11/plan 29: unchanged full pins with hashed records, correctly N/A rather than fabricated lists. The 3-14 proof is exact for frame multisets, but does not prove completeness for routed cell contents; see R1. |
| 2. Unexplained cells are zero or each named with why open | **Met for the measured scope** | AU/Perth 3-14 list selectors are `all rows`, with 246,123 / 795 unexplained and the reason “Payload causes not measured.” Hash-pinned identity lists plus that shared reason name each measured cell. No historical inference is promoted to proof. This is an honest use of Outcome 2, not a root-cause discharge. AU 3-11 and plan 29 have cell-scope zero; the +60 B non-payload gap remains separate. |
| 3. OVERVIEW narrows the oracle blocker to discharge or exact residual | **Partial** | “3-14 oracle cause attribution” accurately keeps measured payload causes open, but the accompanying complete-identity wording exceeds the routing evidence (R1). It also omits the table's historical 3-11 +60 B gap and unmeasured container/index/padding scope (R2). Corrections are provided below for the OVERVIEW owner. |
| 4. Protected discs rehashed unchanged when read | **Met by retained run evidence** | Both retained diff JSONs bind expected full before/after pins and `protected_unchanged: true`; both have zero frame-length fallbacks. Four wrapper records exit 0; the retained log has four `EXIT 0` entries and `ALLDONE`. Reviewer made no protected-input read or fresh hash. The unavailable pre-3-11 disc is explicitly a replay limitation. |
| 5. No close, PSS, other-kind joins, 3-90 or later-phase work | **Met in the reviewed slice** | Notes/tables explicitly keep Phase 3 open. The plan-31 changes record their two domains only. No release of later phases or reseat claim. |

The retained census audit agrees with the published 3-11 support:
3,951,970 rows, 37/37 expected cells, SHA-256
`5d1dde4d8c305a3d2d58d50e0b3f2986e3d7ed9405b1f45efea95e145c48b3c3`.
This is a retained audit of the new census, not an independent old-disc replay.
The embedded 37-cell list reconstructs the authoritative
`9f2b0e554465d030637fa7d19b4ceaf88b6283b1d4d86810de5ccd4dece50e5e`
hash and matches the signed 3-11 count/confinement record.

AU 3-14 levels are L0 244,060 / L2 1,944 / L6 118 / L8 1; Perth is L0 784 /
L2 11. Added/removed are zero in both retained reports. Their list hashes are
`77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f`
and `af26b6b48aef6e7b5a407b5db367894f28f7f6c1ea29a8ff31ab560b65d8355f`.
The large TSV was streamed for hashing/counting/order only.

### Phase 2 — met for the cited successor contract

| DESIGN outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Cited live counts, conditional empty pinned-failure set and equality rule | **Met** | All nine kinds match the `new` compare column and plan-32 report, including sums across all seven levels. Every failing count is zero. All source hashes match; JSON/TSV agree. Missing/invalid/positive counts and census disagreements remain open in the code and negative controls. |
| 2. Historical candidate digest/footer and honest disposition | **Met** | Digest `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a` matches the cited ledger. Exactly 100 distinct shown groups; footer claims 26,650 groups / 1,939,931 rows / `TRUNCATED=yes`. `residual-not-required-for-live-close`, identity `unverifiable`, exhaustive equality `null`. No exhaustive rows or joins are invented. |
| 3. OVERVIEW pin wording narrowed | **Met** | `ca55630` records live ∅ = ∅ on `2ee3456a…` and the historical residual separately. It does not claim recovered exhaustive historical identity. |
| 4. Phase 3 stays open; other gates remain outside this slice | **Met** | Both generated artifacts have `phase3_closed: false`; PSS remains a blocker. Other-kind joins are handed to plan 32, whose discharge is not assessed here. |
| 5. No full 3-90, invented list, later phase or reseat | **Met in the reviewed slice** | The publisher reads cited small evidence and stats empty bins; it does not run K1. No protected-input content was opened by the reviewer. |

Checked / failing totals:

| Kind | Checked | Failing |
| --- | ---: | ---: |
| background | 176,386,506 | 0 |
| background_boundary | 64,111,046 | 0 |
| completeness | 1,800,514 | 0 |
| interior_cover | 1,590,566 | 0 |
| name_anchor | 2,317,055 | 0 |
| range | 285,809,587 | 0 |
| road_node | 42,994,980 | 0 |
| road_point | 0 | 0 |
| step | 227,935,489 | 0 |

The primary compare SHA-256 is
`d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b`;
the corroborating report SHA-256 is
`ade63d88ec6b0cefb659e2ecff3db38cbb99e8e327666e0770b75529d19480dc`.
The four prescribed dump bins were checked by stat only and are zero bytes.
Successor identity is cited via the signed record/diff and the retained run
arguments, as disclosed in the note; it is not freshly byte-attested by the
reports. Zero checked road_point observations prove no reported failures,
not positive checker coverage.

## Findings by severity

### High

**R1 — briefed:** `oracle_chain.py:87`, `oracle_chain.py:163`, and the Phase 1
complete-identity claims. Unordered frame multisets discard divided-leaf
payload routing and fractional footprint identity. Swapping A/B between two
divided leaves within a base cell changes both routed contents while leaving
the signature equal. A light in-memory control confirmed this using the
committed `tree_leaves` and `cell_signatures` functions. Pure physical
relocation and padding are correctly ignored by this metric, and changes to
multiset membership/multiplicity are detected. The deficiency is a possible
false negative, not demonstrated count inflation from relocation. There is
no evidence that this counterexample occurred in the real hops, but neither
is there a routing invariant excluding it. Historical count agreement and
zero frame-length fallbacks do not establish that invariant.

Remediation: [briefs/remediation-01.md](briefs/remediation-01.md). Needs a proof
scope decision and supplementary evidence or an explicit routing/topology
residual; no structural fix attempted and no checker change made.

### Medium

**R2 — follow-up, non-blocking:** `docs/OVERVIEW.md`, plan-31 oracle hunk from
`f636cd9`, retained in `ca55630` (snapshot lines 61–62). The cause-attribution
label is accurate for the measured 3-14 payload cells, but is an incomplete
summary of already-carried residuals: AU 3-11's +60 B non-payload growth is
unattributed, and 3-14 container/index/padding changes are outside the census.
Also, “measured ... every ... hop” describes the 3-11 retained list and plan-29
reused proof as fresh measurements. Detailed plan artifacts disclose these
limits, so this documentation correction is non-blocking separately from R1.
OVERVIEW was not edited because another seat owns it.

### Low

**R3 — resolved in review:** `phase1_note.md:3` / its initial per-hop heading
presented pre-Execute missing-list/count claims without a clear temporal
boundary, although the final section records successful measurements. Added
an explicit handoff/measurement boundary and labelled the initial findings
as pre-Execute. Historical statements and measurement evidence are preserved.
Verified against the retained reports and final measured-result section;
this is a localized documentation correction. No brief or re-review required.

No blocker-severity findings.

## OVERVIEW corrections for the orchestrator

Do not modify adjacent plan-30/32/33/34 wording. Apply these only to the
plan-31 oracle sentence; leave the evidenced live-empty pin contract intact.

1. Replace the unrestricted “measured exact changed-cell identities for every
   re-oracle hop” claim with the actual evidence types: retained SHA-pinned
   AU 3-11 37-cell list, measured AU/Perth 3-14 whole-frame multisets, and the
   reused committed plan-29 single-leaf byte proof. State R1's routing/topology
   completeness gap unless supplementary evidence has discharged it.
2. Keep the AU 246,123 / Perth 795 payload cells explicitly unexplained. Carry
   AU 3-11's +60 B non-payload attribution gap and 3-14's unmeasured
   container/index/padding scope as well. “3-14 oracle cause attribution”
   alone is accurate only as one part of the residual list.

Suggested wording pending R1 remediation:

> Plan 31 records the retained SHA-pinned AU 3-11 37-cell list, measured AU
> 3-14 246,123 / Perth 3-14 795 whole-frame multiset differences, and the
> committed plan-29 L0 (0,541), leaf-928 successor byte proof. Routed-cell
> completeness still needs routing/topology evidence. All measured 3-14
> payload cells remain unexplained; AU 3-11 +60 B non-payload growth and
> unmeasured 3-14 container/index/padding changes remain residuals. Phase 3
> stays open and PSS remains a blocker.

This wording changes the scope of the claim, not the counts or cell labels.

## Intent and assumption ledger assessment

The slice follows the honesty/identity intent in several material respects:
it does not sign a new oracle, invent historical pins, loosen tolerance or
claim the whole Phase 3 complete. Named unexplained 3-14 cells are allowed by
this signed design even though the standing full-completeness rule still
requires their eventual root causes. R1 concerns proof completeness, not
the decision to leave causes open.

| Ledger entry | Assessment |
| --- | --- |
| 1. Live zero-failing successor uses an empty pinned-failure set, separate from historical candidates | Holds under the signed slice semantics and cited counts. A zero live failing set has no spool-caused failure members. Does not waive historical science or any later additional requirement. |
| 2. Missing enumerations need not be regenerated by default | Holds. Historical view remains truncated/unverifiable; recorded inventories are bounded non-recovery claims, not proof that external/renamed copies do not exist. |
| 3. Discharging these two topics does not close Phase 3 | Holds. PSS is still open; other-kind joins are owned separately. |
| 4. Plan-29 successor hop belongs in the chain | Holds. Full pins, equal sizes and nine changed ranges totaling 146 B support the single-cell/leaf witness. |

An additional implementation assumption is **unproven**: unordered frame
membership is sufficient to establish unchanged routed cell contents.
The divided-leaf counterexample defeats it generally. The ledger does not
authorize this equivalence; R1 is sized to the oracle proof domain.

## Plan-sufficiency judgment

The design is sufficient to determine the two domains, place findings, permit
honest residuals and derive the cited-count/hash/failure controls. Its pin
semantics and no-close limits are explicit. It does not define which
subcell/routing/geometry changes a “changed cell” proof must preserve; this
left a gap in both implementation and QA. A subsequent proof package needs
that identity contract plus relocation and divided-topology adversarial
controls. No workflow-tuning invocation was made.

## Validation and execution boundary

Only the requested two synthetic suites were run:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_oracle_chain.py parser/tests/test_pin_contract.py --basetemp output/scratch-31/review/tests
```

**44 passed in 0.33 s.** Log: `output/scratch-31/review/pytest.log`.

Light independent evidence/control audit:

```sh
.venv-rp/bin/python -B output/scratch-31/review/audit.py
```

Output: `output/scratch-31/review/audit.json`. It verifies published JSON/TSV
agreement, embedded 3-11 authority hash, retained census/run records, streamed
3-14 list hashes/counts/order, successor witness, pin source hashes, level
totals, footer, and empty-bin stats. It also records the R1 in-memory routing
counterexample. Historical output/git inventories were assessed as recorded;
no full output scan was repeated. The 317 MB 3-11 census and original scratch
list were not reread; their retained/embedded evidence was checked.

No ALLDATA.KWI, R disc or spool was opened. No K1, real-disc diff, full pytest,
3-90 or heavy measurement was run. The permitted tests exercise their
synthetic diff controls only. All runtime outputs are beneath
`output/scratch-31/review/`; retained scratch-31/32 evidence is unchanged by
the review. No heavy rerun is required to reproduce R1. Any supplemental
protected-disc audit must be prepared/reviewed by its implementer and run by
the orchestrator under the wrapper/lock, as specified in remediation-01;
the existing diff commands in `phase1_note.md` would only reproduce the
weaker multiset metric. No nonexistent supplemental command is asserted.

## Residual risks

- R1 leaves completeness of AU/Perth 3-14 routed changed-cell identities open.
- All 246,123 AU / 795 Perth measured payload causes remain unmeasured. The
  seven AU / three Perth historical non-payload explanations are inference.
- AU 3-11 pre-disc/census replay is unavailable, and +60 B non-payload
  attribution remains open. Perth unchanged hops reuse signed records.
- Container/index/padding changes are outside the 3-14 cell measurement.
  Physical relocation invariance of multisets does not prove those changes
  are semantically harmless.
- The live-empty pin proof applies to the cited successor only, with cited
  path/digest binding rather than fresh disc attestation. Changed disc or
  missing/positive counts require new evidence and a live pin set.
- Historical 26,650-group / 1,939,931-row identity and assignment equality
  remain unrecovered. Footer validation is not an exhaustive census.
- PSS at ops ≤ `-j6`, future close verification and all other plans remain
  outside this slice. Retained RSS/cgroup peaks do not clear the PSS gate.

## Files changed by this review

- `REVIEW.md` — this independent assessment.
- `briefs/remediation-01.md` — structural proof-gap brief.
- `phase1_note.md` — mechanical temporal clarification (R3).
- Runtime audit script/JSON, pytest log and synthetic test outputs under
  `output/scratch-31/review/` only.

No code, tests, OVERVIEW, other plan surfaces or protected inputs were edited.

---

# Re-review 2 — remediation 01 (R1 routed completeness, R2 OVERVIEW)

Date: 2026-10-06. Independent seat; did not build this plan and did not write the
remediation.
Seat: opencode `deepseek/deepseek-flash`, a clean context (Codex and Claude were at
usage limits until 11:19 / 11:20 AEST); this note was added by Execute.

Verdict: **PASS_WITH_FOLLOWUPS**

Reviewed SHA: `7913160af77dd05f829e37d8786070cba8e1c88` (detached master, ≥ the
named `4ab27e8`; contains the remediation results `452dcdd` and code `c2cc6dc`).
Reviewed the prior review, the plan-31 folder, the two named test files, the
committed `evidence/routed-3-14-{au,perth}.json`, and retained
`output/scratch-31/rem01/` output (read-only). Interleaved plans 30/32/33/34 are
outside this review. Implementation was by Execute (Grok Bot) after the Codex
usage limit, as disclosed; that does not change the assessment. Changes left
uncommitted.

## R1 — resolved in review

The R1 finding was that unordered per-cell frame multisets cannot prove routed
completeness of the 3-14 changed-cell lists: a divided-leaf payload swap (or a
subdivision-footprint change) preserves the multiset while changing routed cell
contents. The remediation's `routed_diff` closes it.

- `iter_frames(..., routed=True)` carries each leaf's exact absolute footprint
  (`x:y:w:h`, base-cell units, rational strings) via
  `tree_leaves(..., footprint=True)` and routes it to its owning integer base
  cell (`oracle_chain.py:87-173`).
- `routed_signatures` (`oracle_chain.py:188-202`) signs the sorted
  `(footprint, length, SHA-256)` triples per base cell, so which footprint routes
  to which whole frame is preserved; offsets and sector padding are excluded.
- `routed_diff` (`oracle_chain.py:295-388`) verifies the baseline hop pins, the
  baseline list SHA-256 and count, recomputes the routed changed set, and gates on
  zero baseline cells missing and zero routed-only cells
  (`multiset_list_complete_under_routing = not routed_only and not missing`).
  Routed-only is exactly the change class the multiset metric hides; a missing
  baseline cell raises `ValueError`.

Because the routed identity is strictly finer than the multiset signature,
`routed ⊇ multiset` always; both hops measure the two sets as equal, so the
retained multiset lists are exactly the routed changed-cell lists. The
counterexample is excluded for these hops (SHA-256 collision aside). Within a
base cell the routed signature is the full function footprint → (length, hash),
so any routed-content change alters at least one triple; a cell whose multiset
is unchanged but whose routing changed appears as routed-only. No false negative
remains for these two hops.

Evidence verified read-only (claim → actual):

| Item | Claim | Verified |
| --- | --- | --- |
| AU routed list sha | `9910056f…7a2a0` | match |
| Perth routed list sha | `6fab0975…28516` | match |
| AU multiset list sha / rows | `77ff1d86…8544f` / 246,123 | match / 246,123 |
| Perth multiset list sha / rows | `af26b6b4…8355f` / 795 | match / 795 |
| AU baseline JSON sha | `4e5f1b31…6fe04` | match |
| Perth baseline JSON sha | `51dd2ab8…5770d` | match |
| committed evidence JSON | byte-identical to `rem01/routed-3-14-{au,perth}.json` | match |
| AU routed run | changed 246,123, added 0, removed 0 | match |
| Perth routed run | changed 795, added 0, removed 0 | match |
| AU/Perth `in_multiset_list == 0` rows | 0 | none found |
| `routed_only_count` / missing | 0 / 0 | match |
| `multiset_list_complete_under_routing` | true | match |
| `protected_unchanged` | true | match |
| run log | exit 0 / `ALLDONE`, wall 226.07 s / 0.43 s | match |

The five tests added in `c2cc6dc` are meaningful, not vacuous, and exercise the
R1 contract directly (all pass): `test_routed_diff_detects_divided_payload_swap_
missed_by_multiset` (multiset 0 changes, routed-only 1, complete flag false),
`test_routed_diff_contains_every_multiset_change` (both detect, routed-only 0),
`test_routed_diff_invariant_under_relocation_and_padding`,
`test_routed_signature_detects_changed_footprint`, and
`test_routed_diff_rejects_wrong_or_tampered_baseline`. The permitted suites ran
49 passed (20 oracle + 29 pin, incl. parametrizations); no failures.

## R2 — resolved (OVERVIEW now accurate)

The current plan-31 sentence (`docs/OVERVIEW.md:62`, unchanged by later commits)
names the evidence types instead of an unrestricted claim: the retained
SHA-pinned AU 3-11 37-cell list; measured AU 3-14 246,123 / Perth 3-14 795
changed cells, complete under both the whole-frame multiset and the routed
footprint identity (0 routed-only cells); and the committed plan-29 L0 (0,541)
leaf-928 byte proof. It keeps all 3-14 payload causes unattributed and carries
AU 3-11's +60 B non-payload growth plus the unmeasured 3-14
container/index/padding scope as residuals. Each clause matches the verified
evidence. No corrections required. The removal of "measured … every … hop"
correctly stops describing the 3-11 retained list and the plan-29 reused proof
as fresh measurements.

## Phase outcome assessment update

- Phase 1 — **met for the routed-completeness claim**. Outcome 1's identity
  proof for the two 3-14 hops is now routing-aware and gated; Outcome 2's named
  unexplained cells are preserved. Outcomes 3–5 remain as in the original
  review. Previously "partial" solely because of R1; R1 is resolved.
- Phase 2 — **met** (unchanged; no regression). The pin contract and historical
  disposition are untouched by the remediation.
- No Plan 04 Phase 3 close is claimed (`phase3_closed: false` in both generated
  artifacts; OVERVIEW still says "plan 04 Phase 3 is not closed"). PSS remains a
  listed blocker. No tolerance/checker change, no relabel, no reseat, no
  protected-input mutation. R3's temporal clarification is intact.

## Findings by severity (re-review)

### High

**R1 — resolved in review.** See above. Evidence hashes, counts, run log and
synthetic controls all confirm routed-only = 0 and missing = 0 on the two 3-14
hops; the multiset lists are complete under the finer routed identity. No brief
or re-review of R1 is required.

### Medium

**R2 — resolved in review.** The narrowed OVERVIEW sentence is accurate; no
corrections. (Original R2 was a documentation correction, not a code defect.)

### Low

**R3 — remains resolved** (original review; no action).

**F1 — follow-up, non-blocking:** the routed-identity completeness proof was run
only for the AU/Perth 3-14 hops. The AU 3-11 changed-cell list is retained and
corroborated by a count-split scan, but its completeness under the finer routed
identity is not re-proven by remediation-01, so in principle the same
divided-leaf false-negative class is not excluded for that hop. The OVERVIEW
wording correctly limits "complete under … the routed footprint identity" to the
3-14 hops, so this does not affect the R1/R2 discharge. If a future close
package wants a uniform routing-aware proof, run `routed-diff` for the 3-11 hop
(or record the count-split scan as its routing-level witness). Listed as a
residual; no brief raised.

No blocker-severity findings. No new structural finding requiring
`briefs/remediation-02.md` — none is written.

## Intent and ledger assessment

The remediation follows the honesty/identity intent: it adds a strictly finer
identity without re-signing a hop, does not touch the recorded lists/digests/
counts/labels, does not promote historical causes to measurement, and keeps the
named-unexplained cells and prior residuals. The previously **unproven**
implementation assumption ("unordered frame membership is sufficient to
establish unchanged routed cell contents") is now discharged for the two 3-14
hops by direct evidence; ledger entries 1–4 still hold.

## Plan-sufficiency judgment

The design remains sufficient. Its prior gap — no defined identity contract for
what a "changed cell" proof must preserve — was the root of R1; remediation-01
supplied that contract (footprint + whole-frame identity) for the two measured
hops. A future 3-11 routing-aware proof and the separated payload-cause work are
the only design-level leftovers, both already named as residuals.

## Residual risks

- F1: AU 3-11 routed-identity completeness not independently re-proven.
- All 246,123 AU / 795 Perth 3-14 payload causes remain unmeasured; AU 3-11's
  +60 B non-payload growth and the unmeasured 3-14 container/index/padding scope
  remain open (now carried in OVERVIEW).
- R1's original claims relied on retained baseline lists; that is disclosed and
  hash-pinned, not freshly recomputed in rem01.
- PSS, future close verification and other plans remain outside this slice.

## Validation and execution boundary

Only the permitted suites were run:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_oracle_chain.py parser/tests/test_pin_contract.py --basetemp output/scratch-31/rereview/tests
```

**49 passed** (0.66 s). Evidence checks reread only committed JSON/TSV and the
retained `output/scratch-31/` routed lists/logs read-only (streamed for hashing
and counting). No ALLDATA.KWI, R disc or spool was opened; no K1, diff, encode or
full suite was run. No protected 170 / 3-16 / 3-17 reseat, no 3-90 re-run.

## Files changed by this re-review

- `REVIEW.md` — this appended re-review section (original review preserved).
- Runtime test outputs under `output/scratch-31/rereview/` only.

No code, tests, OVERVIEW, other plan surfaces or protected inputs were edited.
The follow-up command for a future 3-11 routing proof is the existing
`oracle_chain.py routed-diff` subcommand with the 3-11 hop pins and new scratch
paths; it is not run here.
