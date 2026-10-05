# Truncated-pin ledger (plan 27 Phase 2)

In-scope surfaces only (Assumption 2): live 3-90 brief Contract + check 6, OVERVIEW 3-90 paragraph short SHA, plan 04 DESIGN hard-gate truncations of the same oracles, and `pinned_candidates.tsv` truncation named by OVERVIEW. Historical IMPLEMENTATION quotes of past blocked runs may remain as history when live pins are ledger-mapped.

Proof tip at ledger write: `aaba108e8ab9de5f673158a201c22528142e0f40` (post Phase 1). No disc re-hash; expansions from tracked full forms + `git rev-parse`.

## Expansions

| path:line (pre-amend) | truncated | disposition | full value | proof |
| --- | --- | --- | --- | --- |
| `briefs/3-90-fresh-verify.md:23` (Contract) | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | plan 04 `DESIGN.md:47` (full form already present); `IMPLEMENTATION.md` build-gate rows; `briefs/2-06-…:77` |
| `briefs/3-90-fresh-verify.md:34` (check 6) | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | same |
| `briefs/3-90-fresh-verify.md:34` (check 6) | `da13a775…` | expanded | `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc` | `docs/provenance.md:517`; `IMPLEMENTATION.md:576` |
| `docs/OVERVIEW.md:50` | `5c5823e` | expanded | `5c5823e4c267dd64bc986038caddb3ed4b745f60` | `git rev-parse 5c5823e` → full object id |
| `docs/plans/04-c-core-orchestration/DESIGN.md:11` | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | DESIGN.md:47 same oracle |
| `DESIGN.md:47` | `da13a775…` | expanded | `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc` | provenance / IMPLEMENTATION |
| `DESIGN.md:50` | `87a01b14…` | expanded | `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` | DESIGN.md:47 |
| `DESIGN.md:72` (hard gates) | `87a01b14…` / `da13a775…` | expanded | full forms above | DESIGN.md:47 + provenance |
| `DESIGN.md:152` | `87a01b14…` | expanded | full form above | DESIGN.md:47 |
| `DESIGN.md:184` | `87a01b14…` | expanded | full form above | DESIGN.md:47 |

### Minimum expansions also proven on tip (adjacent same-oracle; for ledger completeness)

| truncated | full | proof |
| --- | --- | --- |
| `4ed9cd80…` | `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` | `docs/provenance.md:601`; plan 14 / 3-17 records |
| `013586b5…` | `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` | `docs/provenance.md:388`; triage `causes_residual.md:7` |
| `04be2f6e…` | `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728` | `IMPLEMENTATION.md:505` (full form adjacent to truncated quotes) |

These three are **not** live brief check-6 pins (brief still cites the original `87a01b14…` / `da13a775…` oracles until a signed re-oracle); they are ledgered so OVERVIEW "truncated pins" for the same oracle family is discharged without hunting.

## Unverifiable

| path | truncated / issue | disposition | root cause |
| --- | --- | --- | --- |
| `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv` | content view `SHOWN=100` / footer `TRUNCATED=yes` | **unverifiable from git** | Brief-required 100-row candidate view, not an exhaustive pinned list. File sha256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a` (tracked; verified `sha256sum` at ledger write). Exhaustive group identity lives under non-committed scratch (`enumerate_*.tsv` / dump joins). Do **not** fabricate a full pin list without those artifacts. Material to a future 3-90 check 4 set-equality only when enumerate artifacts are authorised. |

## Counts

- Expanded (live surfaces amended or DESIGN gates expanded): **10** occurrence rows above (brief ×3 digest cites across Contract+check6, OVERVIEW ×1, DESIGN ×6 line sites).
- Minimum adjacent oracle expansions proven: **3** (`4ed9cd80…`, `013586b5…`, `04be2f6e…`).
- Unverifiable: **1** (`pinned_candidates.tsv` content truncation).

No fabricated full pinned enumerate list.
