# Remediation 01 — R absence index proof

Status: **done with concerns**. The code and synthetic verification are
complete. R1's measured evidence gate remains pending the orchestrator's
bounded R runs and appended independent assessment. No measured R result
or regenerated witness is claimed by this fixer.

Applied the remediation brief and REVIEW finding R1 under Execute's worker
conventions. The invoker's narrower ownership and heavy-run rules take
precedence over the brief's broader witness/implementation ownership and
the skill's commit convention: all changes remain uncommitted.

The reader now retains absolute offsets, lengths, hex and SHA-256 for the
volume header, embedded management-header entry, PDMDH header and
LMR/BSMR directory, selected LMR and BSMR, selected BMT entry, and the
parcel-management block/selected slot paths when those structures exist.
Decoded sector sizes, management DSA/size, BMT offset/extent, block
DSA/size and parcel-slot DSA/size accompany the bytes. A malformed selected
slot retains its raw entry and decoded fields before recursive parsing.
Outside-coverage cells retain the same header/LMR bytes and decoded L0
grid/coverage geometry; their exclusion is recomputed from those bytes.
Structures below an absence sentinel do not exist and are not fabricated.

The legitimate absence contracts are:

- An absent BMT requires a raw BSMR offset of `FFFFFFFF` and zero size.
  `volume.parse_pdmdh_full` documents this pair, and
  `alldata_writer.EMPTY_BMT_OFFSET/EMPTY_BMT_SIZE` emits it. The decoded
  offset is `0x1fffffffe` because the shared SWS decoder doubles the raw
  32-bit value. An arbitrary out-of-buffer offset or zero size alone fails.
- A BMT entry's `FFFFFFFF` DSA proves that block absent, matching the
  shared reader's `NO_DATA_DSA` contract. A non-sentinel DSA with zero
  size is unresolved and cannot prove absence.
- A mapinfo slot's `FFFFFFFF` DSA proves that parcel absent. A
  non-sentinel DSA with zero size points to a nested record, as specified
  in `parcel_mgmt.py`; it must decode successfully. A divided tree with
  no covering leaf is empty only if every terminal slot has the sentinel.

Missing/ambiguous lookups, bad record sizes, BMT bounds/extent failures,
malformed slots and frame/name decode failures carry `lookup_failed` and a
specific reason. `r-witness` saves this unresolved result and exits 2.
It preserves the nine requested cells and historical R pin without a
full-disc hash.

`verdict` replays the index lookup using only the saved bytes, checks their
hashes and decoded identities, and rechecks geometry and frame ownership.
Resolved frames retain their name-directory and name-subframe bytes; the
verdict decodes those bytes again to validate the name census. Truncated
name lists/records fail rather than becoming an empty decoded list. Old
label-only witnesses, altered/missing proofs and every `lookup_failed`
cause drift and exit 2. A requires proven sentinel absence or validated
resolved frames excluding the searched name. A searched string present
without a proven position match also yields drift for investigation.
The generated note records each cell's reason and points to the byte proof.

The control has an import-safe `main`, required `--out`, and explicit
`--disc` (default R). It retains Perth's complete index/frame identities,
name-directory/subframe byte proofs, and a decoded name record with
absolute offset, record hex and SHA-256. It retains Perth's existing
status/frame/name aggregates and the 2,048-cell target census, adding
status counts, failures and the target cell's index proof. Failed Perth
or target-block lookups make the control exit 2. The refreshed control
reads R only; the prior G aggregates are not remeasured in this bounded R
handoff. This is a deliberate reduction from the original R/G script,
which also opened the protected historical G disc unconditionally.

Verification:

```sh
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_r_absence_witness.py parser/tests/test_successor_oracle_tools.py --basetemp output/scratch-29/rem01/tests
```

**25 passed in 0.77 s** on the final run. Controls exercise the real empty
sentinel, populated slot, missing lookup, invalid table offset, malformed
slot, malformed name record, non-sentinel zero-size block and invalid
extent. Additional controls validate absent-table/absent-block sentinels,
a resolved nameless frame, and rejection of missing/tampered index,
geometry and name proofs and duplicate requested cells. The control's
import and required output argument are also tested without disc access.
The first test invocation encountered a missing basetemp parent; creating
`output/scratch-29/rem01/` resolved that setup failure. `git diff --check`
passes. Only the two permitted test files ran; bytecode and pytest cache
writes were disabled. No R disc, any ALLDATA.KWI, or spool was opened.
No committed witnesses, implementation record or review were edited.

Run these exact commands sequentially from the repository root:

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/rem01/r_index_run.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py r-witness --disc /run/media/codyh/464210-8480/ALLDATA.KWI --keep-names --out output/scratch-29/rem01/r_index.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/rem01/r_control_run.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/r_reader_control.py --disc /run/media/codyh/464210-8480/ALLDATA.KWI --out output/scratch-29/rem01/r_reader_control.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/rem01/verdict_run.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py verdict --r output/scratch-29/rem01/r_index.json --out output/scratch-29/rem01/verdict.json --note output/scratch-29/rem01/phase1_witness.md
```

The third command reads saved JSON only, including the existing committed
G/spool/scan witnesses; it does not open those protected inputs. No other
heavy run is needed. The orchestrator must inspect nonzero exits and
contrary observations, regenerate/refresh the committed R and successor R
witnesses/control/verdict/note from measured outputs, append the
implementation entry, and obtain an appended independent assessment while
preserving REVIEW. Do not infer six empty sentinels or renewed verdict A
from these synthetic results. No independent live assessment was possible
within the fixer's binding input restriction.
