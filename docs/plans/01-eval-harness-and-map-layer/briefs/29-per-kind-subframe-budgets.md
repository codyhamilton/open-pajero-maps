# Brief: 29 -- Per-kind sub-frame size budgets in division (envelope sub-frame max rows)

Consumer: implementation worker (code + tests; NO full rebuild, do NOT touch `output/`).
Owned paths: `parser/kiwiw/divide.py`, `parser/build_alldata.py` (`_load_level_thresholds`, `_encode_one`,
`_encode_level` plumbing only), `parser/tests/test_divide.py`, `parser/tests/test_build_alldata.py`.
Do not touch `synth.py` (brief 30 owns it), `mesh.py` (28), `parser/harness/`, `selection.json`,
`osm_to_parcel_geometry.py`. Commit and push when `pytest parser/tests -q` passes and the fixture
gate below is clean.
Depends on: 26b record. Runs alongside: 28, 30 (disjoint files). Verified by the assembly-only rebuild
(31/31b); the spool from rebuild #3 stays valid (no extraction change).

## Diagnosis (live `output/ALLDATA.KWI`, `/tmp/diag28/scan.py`)

`envelope` fails 13 rows where G's road/background/name *sub-frame* byte max exceeds R's per-level max
(`harness/profile.py` measures the mfde-declared size of idx 0/1/2 for every leaf slot, divided
sub-frames included). Cause: `divide.plan_divisions` triggers only on the *whole Map Frame* size
vs `min(R mapframe max, 131070)` (`build_alldata._load_level_thresholds`), so a background- or
name-dominated frame that fits the total ceiling is left whole although one kind is 2-5x R's max
(R L0 bg max 25,908 vs G whole cell 125,760; total 127,072 <= 131,070). G leaves over R's kind max
(count, worst) by level/kind/parcel_type:
L0 bg: t0 1130 (125,760), t1 968 (109,994), t2 81 (130,106); L0 name: t0 39 (35,676), t1 12 (42,930), t2 2 (32,280);
L2 bg t0 17 (101,242) t1 2 t2 10; L2 name t0 8 (3,048); L2 road t0 1 (114,370 vs 110,132);
L4 bg t0 5 (116,746) t1 1; L4 name t0 27 (700 vs 370); L6 bg t0 6 (107,650); L6 name t0 6 (1,298 vs 610);
L8 bg t1 1 (123,092) t2 1 (130,558 vs 120,946); L8 name t0 1 t1 4 t2 1 (1,118 vs 366); L8 road t1 1 (103,146) t2 3 (121,906 vs 99,794);
L10 bg t1 1 (1,858 vs 1,802).
Two classes: (i) type-0/1 leaves that division can fix (escalate); (ii) leaves already at type 2 (4x4,
the largest tier) still over R's max -- L0 bg/name t2, L2 bg t2, L4/L8 bg, L8 name/road t2: content is
too dense for 16 sub-cells (e.g. L8 sub-cell with 2,054 links / 1,767 bg shapes, L0 Tullamarine/
Mildura cells with ~2,200 small `background_all` polygons). Those need a bounded, deterministic
content trim, not more division. Also note `divide._shrink_to_fit` (hard-ceiling fallback) already
exists and drops by count, not by kind budget or priority.

## Changes
1. `_load_level_thresholds` additionally returns per-level kind budgets
   `{road, background, name}` = R's `frame_kind_max_bytes` (from `parser/refdata/profile/map.json`);
   kinds with R max 0 (L10/L12 road) get budget 0 only if G would emit none; do not budget an absent
   kind.
2. `_encode_one` (or a sibling `_measure_one`) exposes per-kind sub-frame byte lengths
   (`len(road_bytes)`, `len(bg_bytes)`, `len(name_bytes)`; note `_pad_even`) alongside the frame, e.g.
   returning a small dataclass or a `(bytes, sizes)` pair; `divide.plan_divisions` accepts
   `kind_limits` (default `None` = unchanged behaviour so existing tests hold).
3. `plan_divisions`: a frame is "fits" only if total <= threshold AND every kind <= its limit.
   Escalate 0 -> type 1 -> type 2 on any kind breach exactly as for total oversize.
4. At the final tier (type 2) when a kind is still over its limit, apply a deterministic priority
   trim of only the offending kind until <= limit (bisect on the kept prefix of a priority-sorted list):
   - background: drop smallest-area / fewest-coords shapes first (keep large features);
   - road: drop lowest road class first (`road_type`/display class, then shortest), tie -> highest
     `(osm_way_id, ordinal)`; never trim below the connectivity of motorway/trunk at L>=2;
   - name: drop in this order: duplicate `(text, string_type)` within the sub-cell (keep the first),
     POI/background names (string_type 6), then place names, road names (string_type 5) last -- so the
     spotcheck road names (Queen/York/Swanston/... Street) survive.
   Print a stderr WARNING per trimmed sub-cell (kind, dropped/total) and aggregate a per-level summary
   counter that `build_alldata.run` prints (and adds to `manifest.json` under a new
   `trimmed_items` key). Trim is a last resort: report totals per level; a level whose trim drops
   >1% of a kind's items is named in the report with its blocker.
5. Do not change the total-size threshold semantics; keep the 131,070 hard ceiling path.
6. Tests: unit tests for kind-triggered escalation (bg-dominated frame that fits total but breaches
   bg budget divides; road/name analogues), trim priority order (synthetic content: duplicate names,
   POI vs road names), determinism, `kind_limits=None` regression, budget 0 kinds. Fixture gate:
   `python parser/build_alldata.py --fixture perth --levels 0 2 4 6 8 --spool <perth fixture spool>
   --out /tmp/perth29.kwi` (do NOT write to `output/`); decode it with `harness.profile.build_profile`
   and assert kind maxima <= R's per level (Perth cells only; report any exceptions).

## Done evidence
pytest green; kind-limit table vs fixture maxima; trim counters; explicit statement of which of
the 13 rows the fixture cannot exercise (the full-scale rows are verified by 31b).

## Report back
Escalation vs trim split expected at full scale (use `/tmp/diag28` counts above), whether L0 type-2
name trim touches any spot-check city cell (Melbourne CBD sub-cell had 32,280 B of names), and any
row that cannot be brought under R's max without a declared deviation (name it with evidence).
Do not raise R's maxima or loosen `envelope.py`.
