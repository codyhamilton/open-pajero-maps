# Phase 1 oracle-chain evidence

The existing oracle chain is published by `oracle_chain.py publish` in
`oracle_chain.json` and `oracle_chain.tsv`. No new re-oracle is signed. Plan 04
Phase 3 remains open. The tables now include the guarded Execute measurements
in the final section below. The worker findings and prepared commands preceding
that section describe the handoff before those measurements ran. Unknown measured
counts use JSON `null` / blank TSV fields; historical aggregates remain separate
`recorded_*` fields, never substitutes for measurements.

The worker read small text/JSON evidence only. No ALLDATA.KWI or spool was opened,
hashed, decoded, built, or changed. Disc locations below came from directory
entries and sizes; their pins came from sidecars or committed records.

## Per-hop findings before Execute measurements

| Region / signing unit | Finding | Remaining evidence gap |
| --- | --- | --- |
| AU / 3-11 | Retained authoritative list has 37 unique L0 cells; SHA-256 `9f2b0e554465d030637fa7d19b4ceaf88b6283b1d4d86810de5ccd4dece50e5e` matches the signed record. Expected list is byte-identical. `Gnew.scan.json` maps 41 multi-unit elements to precisely those 37 cells, with no count mismatch and maximum unit declaration 4095. Exact identities are embedded in the published JSON as well as referenced by path/hash. Cell-scope unexplained count: 0. | Pre-3-11 disc `scratch-3-11/G/ALLDATA.KWI` and `G.cells.tsv` were not located. No fresh byte replay is possible from the identified inputs. Large new census audit remains for Execute. The historical review separately carries +60 B of non-payload growth unattributed; cell-scope zero does not dispose of it. |
| AU / 3-14 | Signed census records 246,123 cells: L0 244,060; L2 1,944; L6 118; L8 1; added/removed 0. This is a quotation, not a re-measurement. | Exact changed-cell and explanation lists not found. Entire `013586b5… → 4ed9cd80…` hop is an identity residual; unexplained count is unknown. Seven historical non-payload explanations were inference. |
| Perth / 3-14 | Signed census records 795 cells: L0 784; L2 11; added/removed 0. | Exact list not found. Entire `da13a775… → 04be2f6e…` hop is an identity residual; unexplained count is unknown. Three historical non-payload explanations were inference. |
| AU / plan 29 | Committed `triage/name_anchor/witnesses/successor_diff.json`, SHA-256 `a129b4f8e57643c94dea5c2b03a2bff57e9100b3fccf1f84a7181c809bf73172`, binds both full disc digests. All nine disjoint ranges, totaling 146 bytes, map to L0 (0,541), leaf [928], on both layouts. Equal disc sizes. One changed cell / one changed leaf; unexplained count: 0. | Existing committed proof reused; no fresh disc read by this worker. |
| Perth / 3-11 | N/A, unchanged at full digest `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc`, recorded in plan 04 IMPLEMENTATION. | Recorded equality, no fresh hash. |
| Perth / plan 29 | N/A, unchanged at full digest `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`, recorded in collapsed plan 29. | Recorded equality, no fresh hash. |

Full from/to pins and evidence hashes are in both generated tables. Plan 29's
closed-out tools and witnesses were read at their current triage paths; its
collapsed record is `docs/plans/29-k1-name-anchor-failure.md`.

## Inventory and regeneration boundary

On 2026-10-06 the worker listed outputs beneath
`/home/codyh/workspace/open-pajero-maps*/output`, deduplicating resolved output
roots. Traversal excluded spool directories and test directories; it did not
follow nested directory symlinks. The populated independent roots included the
main output and the 3-14 checkout output. The other independent output roots
examined were 07, 08-zero-row-classify, 10-summary-byte-identity, 16, 17, 18,
3-15, 3-16, 3-17, 3-90, flash-3c12 and status-continue-2. This is evidence of
non-recovery within the inventoried roots, not proof that no arbitrary renamed
copy exists elsewhere. No sidecar identified a surviving `87a01b14…` disc.

Identified AU inputs: `output/scratch-3-11/G_new/ALLDATA.KWI` (1,731,021,792 B)
and `output/scratch-14/G_new/ALLDATA.KWI` (1,692,105,152 B). The latter's sidecar
records `4ed9cd80…`; `scratch-14/{protected_before,verify_3-11_untouched}.sha256`
record `013586b5…`. Perth candidates:
`output/scratch-3-11/perth_fix/ALLDATA.KWI` (31,707,680 B) and
`output/scratch-29/perth_base/ALLDATA.KWI` (31,546,688 B). Execute must verify
their expected full pins before comparing; the tool fails before creating
measurement outputs if either pin differs.

`Gnew.cells.tsv` survives at 316,946,747 B. The small scan supports its historical
scope; the census itself was not opened by the worker. The guarded audit below
streams its five-field rows, checks the recorded 3,951,970-row count and the
presence of all 37 expected cells, and hashes the census.

The new diff generalizes plan 29's bounded metadata/frame mapping to independent
layouts. It uses exact rational slot arithmetic, reads at most 8 MiB at once,
holds one block's alias hashes, and stores both full leaf censuses in SQLite
with an 8 MiB page cache and disk sorting. Cell comparison uses sorted
`(whole-frame length, SHA-256)` multisets, preserving occupied alias slots and
grouping divided leaves into their base cells, matching the historical
`cells.py` / `group_cells.py` definition. Relocation and sector padding do not
inflate the changed-cell list. It distinguishes changed, added, and removed
cells and reports counts by level. Whole-disc SHA-256 is checked before and
after; protected inputs are opened read-only. Existing output files/work
directories are refused. Allow disk space for two complete leaf censuses and
the SQLite index; choose a new scratch path on retry.

This diff supplies identities, not explanations. Every regenerated changed,
added or removed cell remains unexplained and is named by the output TSV
(`unexplained_cells.selector = all rows`). Container/index/padding changes are
outside the cell census and explicitly remain a residual. No inference is
promoted to byte proof. Measured counts differing from the historical census
are reported as an additional residual when publishing.

## Guarded commands for Execute

Run serially from `/home/codyh/workspace/open-pajero-maps-14-completeness`.
The wrapper takes `output/.heavy.lock` and records memory peaks. These commands
were prepared, **not run by the unit worker**. Their output paths are fresh.

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/census-3-11.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py check-census --path output/scratch-3-11/Gnew.cells.tsv --expected output/scratch-3-11/Gnew.expected37.txt --out output/scratch-31/census-3-11.json

.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/diff-3-14-au.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py diff --old output/scratch-3-11/G_new/ALLDATA.KWI --new output/scratch-14/G_new/ALLDATA.KWI --old-sha 013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04 --new-sha 4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72 --out output/scratch-31/diff-3-14-au.json --cells output/scratch-31/diff-3-14-au.cells.tsv --work-dir output/scratch-31/diff-3-14-au-work

.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/diff-3-14-perth.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py diff --old output/scratch-3-11/perth_fix/ALLDATA.KWI --new output/scratch-29/perth_base/ALLDATA.KWI --old-sha da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc --new-sha 04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728 --out output/scratch-31/diff-3-14-perth.json --cells output/scratch-31/diff-3-14-perth.cells.tsv --work-dir output/scratch-31/diff-3-14-perth-work

.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/publish.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py publish --au-diff output/scratch-31/diff-3-14-au.json --perth-diff output/scratch-31/diff-3-14-perth.json --census output/scratch-31/census-3-11.json
```

If a measurement fails, retain its artifacts, fix the cause, and choose new
output/work/log names. Do not publish a failed result as measured. `publish`
without measurement arguments reproduces the current honest residual table
using only small retained/committed evidence. With measurements it streams and
hash-checks the generated cell lists before accepting their counts.

## Execute handoff

OVERVIEW was outside worker ownership and was left untouched. Suggested narrow
wording: “Oracle chain: 3-11's exact 37-cell list hash verified; plan 29's single
L0 (0,541) leaf-928 successor proof verified; AU and Perth 3-14 exact-cell lists
remain missing, with guarded regeneration prepared in plan 31. Historical
3-11 +60 B non-payload growth and 3-14 inference explanations remain explicit
residuals.” After measurements, narrow this to the newly observed identities
and the specific remaining explanation/metadata gaps. Do not claim Phase 3
closed. PSS, other-kind joins and the Phase 2 pin disposition remain outside
this unit; no 3-90 rerun, reseating or later-phase work occurred.

## Execute measured result (2026-10-06, guarded)

Run chain `output/scratch-31/run_p1.{sh,log}`, serialised behind plan 30's PBF probe; every step exit 0 under `run_heavy_python.py`.

| Step | wall s | cgroup peak | Result |
|---|---|---|---|
| check-census 3-11 | 2.6 | 355 MB | pass; 37/37 expected cells present in `Gnew.cells.tsv` (3,951,970 rows, sha256 `5d1dde4d…`) |
| diff AU `013586b5…`→`4ed9cd80…` | 137.7 | 2.73 GB (page cache incl.; RSS 51 MiB) | **246,123 changed cells**, 0 added, 0 removed; L0 244,060 / L2 1,944 / L6 118 / L8 1. List `output/scratch-31/diff-3-14-au.cells.tsv` sha256 `77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f` (40 MB, retained scratch) |
| diff Perth `da13a775…`→`04be2f6e…` | 0.4 | 106 MB | **795 changed cells**; L0 784 / L2 11. List `output/scratch-31/diff-3-14-perth.cells.tsv` sha256 `af26b6b48aef6e7b5a407b5db367894f28f7f6c1ea29a8ff31ab560b65d8355f` |
| publish | 1.1 | 37 MB | six hop rows |

Both diff probes re-hashed their discs after reading: `protected_unchanged: true` for `013586b5…`, `4ed9cd80…`, `da13a775…` and `04be2f6e…`.

The 3-14 hop now has **exact changed-cell identities** (whole-frame multiset by cell; container, index and padding excluded). Per-cell payload **causes** are not measured; every 3-14 cell is listed as unexplained, with that reason. The 3-14 brief's stated mechanism (EO-stitch rewrite of background boundaries; see plan 04 IMPLEMENTATION §3-14/3-15) is consistent with an L0-dominated change but is not a per-cell proof.
