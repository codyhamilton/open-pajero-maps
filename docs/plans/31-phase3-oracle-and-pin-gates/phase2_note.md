# Phase 2 live pin contract and historical candidate disposition

`pin_contract.py publish` builds `pin_contract.json` and `pin_contract.tsv`
from SHA-256-verified cited evidence. On successor
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`,
every recorded K1 kind has zero failures. The live failing set and live
pinned-failure set are therefore both **∅**, and their equality holds for these
cited successor measurements. Missing/invalid counts, positive failures,
inconsistent totals or incomplete level coverage leave the affected kind
**open**; the publisher never substitutes zero for an unknown count.

Plan 04 Phase 3 is **not closed**. PSS (the ≤ `-j6` live gate) remains a blocker;
other-kind joins are handled by plan 32 and are outside this unit. Phase 1's
AU/Perth 3-14 cause-attribution residual also remains. This note neither runs
3-90 nor reseats 170 / 3-16 / 3-17.

## Cited live counts

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

The TSV cites the successor **`new`** totals in
`docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json`
(SHA-256 `d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b`),
corroborated by `output/scratch-32/k1_dump_report.json`
(`ade63d88ec6b0cefb659e2ecff3db38cbb99e8e327666e0770b75529d19480dc`).
Both sources agree for all nine kinds; each total also agrees with the sum of
its seven level records. `road_point` has no checked observations; its zero
failing count supplies empty-set evidence, not positive coverage evidence.

Plan 29's name drop reduced name_anchor checked from 2,317,056 to 2,317,055
and failing from 1 to 0. Range checked decreased by the same one, from
285,809,588 to 285,809,587. These are the successor totals, not the historical
baseline column.

The plan-32 dump corroboration is:

- `output/scratch-32/dump/dump_manifest.json`, SHA-256
  `c29ed9f0bd2fb382729f7fba2d200c9ab3b514aca8154a27e4aaa34a59536839`:
  background, background_boundary, interior_cover and name_anchor each have
  manifest rows 0 and a corresponding bin of **0 bytes**, checked by `stat`
  only. No bin contents were opened.
- `output/scratch-32/run_p1.log`, SHA-256
  `474573a96e1cdb0fb2cff826ac9386f3d77e74e3bcbe4dfd1b1be1a00de884f2`:
  retained PASS / `EXIT k1 0` and dump metadata.
- `output/scratch-32/runs/k1_dump.json`, SHA-256
  `4d3d893aedc3488ba5898768d8aef3de0a6a47731062975321ad7a24fa78d4ad`:
  exit 0; arguments identify C K1 at `-j6`, the report/dump paths and
  `output/scratch-29/G_new/ALLDATA.KWI`.

Disc identity is **cited**, not freshly byte-attested. The plan-29 signed record
and `successor_diff.json` (`a129b4f8e57643c94dea5c2b03a2bff57e9100b3fccf1f84a7181c809bf73172`)
bind that path to the full successor pin; the plan-32 wrapper arguments name
the same path. Neither the K1 report nor the dump manifest embeds a disc
digest. The publisher verifies all cited file hashes and bindings without
opening any disc or the real spool and without running K1. Every source's
path and full hash, including the plan-29 record, appear in the JSON.

## Historical view

`docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv` remains
byte-untouched. Its SHA-256 is
`7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`,
matching the full value in
`docs/plans/27-independent-fix-review-truncated-pins.md` (ledger SHA-256
`ba413f764e51437938970d3363d8c2c76e48a3d1efef6202dc4a2646ea9cdd12`).
There are exactly **100 distinct shown groups**; the footer records
`TOTAL_GROUPS=26650 TOTAL_ROWS=1939931 SHOWN=100 TRUNCATED=yes`.
The 26,650 / 1,939,931 values are verified **footer claims**, not a recovered
exhaustive group census or assignment proof.

Disposition: **`residual-not-required-for-live-close`**, with historical
identity status **`unverifiable`** and exhaustive set-equality JSON **`null`**.
The deliberately truncated candidate view cannot reconstruct the historical
S02 source-ring/source-name pins. The full native enumerations were
non-committed scratch; no historical exhaustive assignment equality proof was
recovered. Historical rows were not invented, relabelled or rewritten.

The publisher inventories `enumerate_*.tsv` and `pins_*.tsv` under `output/`
at any depth, following directory symlinks and deduplicating directory inodes.
It records errors and search boundaries. Protected spool/R paths are excluded
without entering them. The initial inventory found no matches; after the
synthetic suite, matches beneath this unit's `output/scratch-31/tests-p2`
are explicitly recorded as **synthetic fixtures**, never historical recovery.
There are **no non-fixture recovery candidates**. Searches of all locally
available git refs and tracked paths also found no matching enumerations;
commands, observed HEAD and results are in the JSON. This is non-recovery in
the recorded scope, not proof that no renamed or external copy exists.

A future close's check-4 comparison must use the live failing identities and
live pinned-failure identities on the **then-current disc in force**. For the
cited successor those are ∅ = ∅. If that disc changes or any count is missing
or positive, obtain the new failing identities and an evidenced pin set;
do not carry this empty set forward by default. Historical S02 exhaustive
identity is a separate residual, not a prerequisite for this live-empty pin
contract under the signed design's chosen semantics.

## Verification and Execute handoff

Only the owned synthetic test suite was run:

```sh
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_pin_contract.py --basetemp output/scratch-31/tests-p2
```

Result: **28 passed**. Controls exercise unknown/positive failures, missing
kind/level counts, census disagreements, SHA mismatch refusal before replacing
published artifacts, successor/run binding, empty-bin checks, candidate-view
integrity, symlink cycles, protected-input refusal and synthetic-match
classification. The light publisher itself also ran successfully on the cited
evidence:

```sh
.venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/pin_contract.py publish
```

No guarded measurement or regeneration is needed. If Execute wants a guarded
republication, this exact **optional command is prepared, not run** (the
wrapper acquires `output/.heavy.lock`):

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/p2_publish.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/pin_contract.py publish
```

OVERVIEW and IMPLEMENTATION are left to Execute. Suggested narrow OVERVIEW
replacement for the pin blocker: “Plan 31 records the successor's live pin
contract as ∅ = ∅ from SHA-pinned zero-failing counts in every K1 kind.
Historical `pinned_candidates` exhaustive identity remains unverifiable
(100/26650 candidate view; enumerations not recovered), separately disposed
as not required for that live-empty contract. Phase 3 stays open; PSS remains
a blocker and other-kind joins are handled by plan 32.” Do not claim those
other gates passed on the strength of this note.
