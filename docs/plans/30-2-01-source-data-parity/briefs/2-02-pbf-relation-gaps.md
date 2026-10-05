# Brief: 2-02 — resolve the 99 conflict-open rows (PBF relation coverage gaps)

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/30-2-01-source-data-parity/` (edit `disposition.py`; regenerate `disposition.tsv`, `disposition_summary.json` only through Execute's guarded `publish`; new `phase2_gaps.md`, report `reports/2-02-pbf-relation-gaps.md`) and `parser/tests/test_parity_disposition.py`.
Touch nothing else. Commits: none.

## Why

DESIGN Phase 2's outcome is every row `supply-path` or `unfixable-proven`. Unit 2-01 left **99 conflict-open** (98 type-288, 85 south_offshore; row 246 type 321). All 99 are open only because the PBF probe recorded coverage gaps whose affected-row lists include them; the spool scan was complete with 0 gaps.

Execute's light scan of the retained evidence (`output/scratch-30/disposition_pbf.proofs.jsonl`, cache `output/scratch-30/p2_pbf_cache_01/geometry.sqlite`, result `output/scratch-30/gap_scan/gap_relations.json`):
- 7,943 gap events: 7,922 `missing/nested relation member`, 8 vertex limit, 7 topology edge limit, 5 member limit, 1 open/branched ring. **7,937 of the gap relations map to code 288** under the production `bg_type` vocab at L0 (one maps to 289), so they are code-matching and do block a 288 negative.
- Most are `boundary=administrative` (7,809), plus protected_area (64), place (39), timezone, maritime, political, a few multipolygons. Examples: suburbs (Ryde, Gladesville, Sutherland …), states, "Australia" 80500, "France" 2202162.
- `disposition.py` `pbf()` raises `missing/nested relation member` for **any** non-way member (`m["type"] != "w"`), i.e. node members such as `admin_centre` / `label` and relation members such as `subarea`, as well as genuinely absent ways. Those roles carry no area geometry. Because the bounds stay unknown, the gap is applied to every row.

## Outcome

1. Correct the probe's relation assembly to match how an area relation is formed: only way members with area roles (`outer`, `inner`, empty) form rings; node members and non-area roles (`label`, `admin_centre`, `subarea`, …) are ignored and recorded, not gaps. State the rule and its source (OSM multipolygon/boundary conventions, and the production successor path text) in `phase2_gaps.md`.
2. For relations with **genuinely absent** way members (outside the AU extract) and for limit gaps: bound them soundly or resolve them.
   - Bounds from the present members alone do not bound a ring with missing parts; do not use them as proof.
   - Acceptable: an argument from the extract's own clipping (state it exactly and prove it from the PBF header/bbox if used), raised per-relation caps within plan-25 memory guards, or complete geometry from a pinned external snapshot. If you need external data, write a fetch script for Execute (Overpass attic query at the PBF's replication timestamp, saved under `output/scratch-30/relations_full/` with sha256); do not fetch yourself.
3. Avoid a 40-minute PBF re-scan if you can: add a mode that reuses the retained cache **read-only** (`file:…?mode=ro`), verifying its provenance against `output/scratch-30/disposition_pbf.json` / `runs/p2_pbf.json` (PBF stamp and sha), and re-assembles relations only. Write its proofs to a fresh JSONL path. `publish` must accept the new probe JSON and keep all existing validation (exact keys, pins, hashes, wrapper logs, proof SHA256).
4. Re-decide: positives still override; a negative needs both probes with no gap that touches that row; `unfixable-proven` keeps its cause rules. Target **0 conflict-open**. Any row still open is named with the exact relation IDs and gap classes that keep it open and what would resolve them.
5. Synthetic tests: node/label/admin_centre members are ignored; a truly missing way still gaps; the read-only cache mode refuses a cache whose provenance does not match; previous tests keep passing.
6. List exact guarded Execute commands (`.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2b_<name>.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py …`), then `publish`.

## Rules

- Never open any `ALLDATA.KWI`, the R disc, the spool or the PBF yourself; you may read the retained cache and proof logs read-only with small bounded queries.
- Run only `parser/tests/test_parity_disposition.py` and `parser/tests/test_parity_fingerprint.py` with `--basetemp output/scratch-30/tests-p2b`.
- No vocabulary, extractor, encoder or disc change. No R geometry copied.

## Not done

No implement unit for the supply rows, no OVERVIEW edit (Execute), no Phase 3 close.
