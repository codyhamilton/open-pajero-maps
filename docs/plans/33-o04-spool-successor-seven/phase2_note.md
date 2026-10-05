# Phase 2 disposition handoff

The seven rows independently satisfy the brief's presence rule and are
`proven-non-deviation`. There are **7 proven-non-deviation, 0 fix-landed and
0 conflict-open** rows. The light publisher exited 0 using retained JSON/TSV
only, including per-row index/frame-byte replay; `disposition.json` records
`phase2_verified: true`. Execute's guarded publication and phase record are
still pending. No disc, R disc or spool was opened, and K1 was not run.

| dump_row | Native cell/type | Stratum | Verdict |
| ---: | --- | --- | --- |
| 138 | (0,1695,699,288) | emit-piece | proven-non-deviation |
| 236 | (0,913,876,578) | demand-removed | proven-non-deviation |
| 282 | (0,1915,1030,288) | demand-removed | proven-non-deviation |
| 284 | (0,1411,1044,288) | emit-piece | proven-non-deviation |
| 317 | (0,1945,1110,578) | demand-removed | proven-non-deviation |
| 496 | (0,1248,1253,288) | emit-piece | proven-non-deviation |
| 563 | (0,1505,1315,288) | demand-removed | proven-non-deviation |

Each row has zero demanded-type polygons on G successor, G historical and R;
all slots in these measured witnesses are resolved with retained frame bytes.
No row depends on an empty slot or a lookup failure. Publish also supports
empty slots only when the hardened index replay proves a format sentinel.
The TSV retains every native key field, demander identities, O04 proof
references, the witness TSV row reference, JSON/TSV and probe hashes, disc in
force, empty fix artefact paths and a null fix-disc SHA256.

The historical completeness demand was checker-over-demand on unrepresentable
crossing-closing geometry, as established by plans 14/28. Root cause remains
**O04 / spool** for every row. All seven source defects remain named spool
hygiene residuals. Nothing is relabelled to checker or absorbed into 2-01.
The emit-piece penultimate counterfactual for 138, 284 and 496 stays evidence
only: applying it would invent presence that R lacks. The demand-removed rows
take the permitted non-deviation route; no optional hygiene patch is applied.
This is a cell-local demanded-type presence result, not broader geometry
parity or completion of plan 04 Phase 3.

## Evidence pins and retained K1 result

The publisher defaults to the measured Phase 1 JSON SHA256
`0f03858f350f6fcc3e14dc6bea83e1a1d641fb8644640d8c920dcd2a9ea62458`.
Phase 1 TSV SHA256 is
`b3302fb107be9b3a709fe0f336830abd7925932274facd4e928b0ad1606b4045`;
publish checks its row contents against the pinned JSON.

The three probe hashes are remeasured and checked against that JSON:

- `output/scratch-33/g_successor.json`:
  `d3f23cbf886db4c9e45a1d4f5fc1f6188e0606299ecd7f9ec67d5e5025513895`.
- `output/scratch-33/g_historical.json`:
  `9831eeff35d0f19fa3083addc75746e9a08428bd5ca269dce1bbcd31d71669e9`.
- `output/scratch-33/r.json`:
  `43ff796b6378a82a111f30121c8ccf839dc73a13780bbf02a27145156316183b`.

O04 source identities and hashes are reverified from light evidence. The
original reader hashes are retained as historical probe-producer provenance
and must agree across all probes; current reader code replays the bytes. An
import-path-only close-out edit to `presence_witness.py` does not require disc
probes to be regenerated. No edit to that file is part of this unit.

Disc in force is
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.
The retained successor K1 comparison is
`docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json`,
SHA256 `d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b`:
**1,800,514 completeness checked, 0 failing**. Publish verifies the passing
comparison, expected kind results, and totals against per-level counts without
counting the stored `totals` entry twice. This cites the existing measurement;
there is no fresh K1 run or disc hash measurement in this unit. Phase 1's G
pins were fully streamed, while its R pin is a historical citation.

## Execute commands

Run from `/home/codyh/workspace/open-pajero-maps-14-completeness`:

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/p2_publish.json -- .venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/disposition.py publish
```

The wrapper obtains `flock output/.heavy.lock` and memory accounting. This
guarded command was **not run by the unit worker**. It uses the pinned inputs
and explicit default paths listed above and replaces only `disposition.tsv`
and `disposition.json`. Exit 2 means evidence was rejected or conflicts were
written; do not close the phase or use stale output after a refusal. Require
exit 0, `phase2_verified: true`, and verdict counts 7/0/0 before recording
the phase outcome. No disc, spool, encode or K1 command is needed.

The only test suite run was the owned synthetic suite, **50 passed**:

```bash
.venv-rp/bin/python -B -m pytest -q parser/tests/test_o04_disposition.py --basetemp output/scratch-33/tests-p2
```

It covers failures on each disc, missing witnesses/inputs, mismatched hashes,
forged zero summaries, TSV/JSON disagreement, large retained CSV fields,
empty-slot sentinel replay, retained K1 counts/totals, and all-seven output
with an I/O guard rejecting disc/spool opens.

## Execute-owned narrowing

Execute owns the OVERVIEW and plan-28 follow-up edits and the phase record.
Suggested factual wording, after guarded publication passes:

> The seven O04 spool-successor rows (138, 236, 282, 284, 317, 496, 563)
> are closed as proven-non-deviation by their per-row G successor, G historical
> and R absence byte/decode witnesses: 7 proven-non-deviation, 0 fix-landed,
> 0 conflict-open. All seven retain O04 spool hygiene residuals; no source
> repair was applied. Plan 04 Phase 3 remains open.

Changes remain uncommitted. No completeness reseat or other plan work is
included.
