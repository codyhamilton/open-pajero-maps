Verdict: FAIL

Plan 42 Phase 1 independent review. Seat: Claude CLI, clean context, disclosed (Codex is weekly-limited). Reviewed at detached HEAD e4d2dca. I authored none of the work. The work is sound up to the R decode. The match rule is not validated at L0. At L8 it produces a "R-has-trimmed 144" result that is an artefact. The verdict that drives Phase 2 ("priority difference") does not follow from the evidence. The fix is a light Phase 1 rework; no heavy runs are needed.

## Clause table

| Clause | Result | Basis |
|---|---|---|
| P1.1 Exact trimmed list (308+207+227) with identities | PASS (field gaps, F6) | The dumps match the run outputs. Counts are 207 / 227 (L0) and 308 (L8), all `shrink` tier, 1 sub-cell each. I checked further: all 16 L0 frames of (1755,591) and all 6 L8 frames of (7,4) occur byte-identical in `scratch-34/G_new/ALLDATA.KWI` (L0 at 352,210,976…, L8 at 1,691,875,968…). |
| P1.2 R division topology | PASS | Rerun confirmed. L0 (1755,591): undivided, leaf [507], 23,680 B. L8 (7,4): 2×2, leaves [19,0..3] = 6,176 / 106,400 / 12,448 / 31,104 B. Decoded R data falls in the correct quadrants. |
| P1.3 Per-item R presence with a validated match rule | **FAIL** | L0 roads: no control, and at 0.56 m the rule cannot match anything (F2). L0 background: the geometric rule never runs past the type gate (F2). L8: "present" means "near an R road", not "R carries this item" (F1). The class criterion mismatches between G and R (F3). |
| P1.4 Verdict per level and kind | **FAIL** | L0 `R-lacks` is probably right but rests on the wrong evidence (F2). L8 `R-has-trimmed 144` is an artefact. The "priority difference" naming does not follow (F1, F4). |
| C1 Item identity, bounded instrumented encode, count equality | PASS (F6, F7) | Instrumentation is read-only (`getenv` / `fopen("a")` / `fprintf`, no writes to state). The plain runs used the unpatched main worktree (`cwd` = 14-completeness, separate per-worktree `_cenc.so`; instr `.so` rebuilt 14:11). `cmp` shows `frames.bin`, `frames.tsv`, `ALLDATA.KWI` and `manifest.json` byte-equal for l0c/l0u and l8c/l8u. The worktree diff equals `instr_e2.patch`. Both tiers are hooked; `trim` fired 0 times. |
| C2 R decode and match rule as in DESIGN | PARTIAL | The code implements DESIGN's wording consistently: parent-cell raw units at the item's level, lat/lon order correct for both G and R (`model.py` (lat, lon)). But DESIGN's "1 raw unit" means 0.56–0.73 m at L0 and 145–190 m at L8, so it is not one rule (F1, F2). There is a latent bug in the R leaf rect (F5). |
| C3 G control | FAIL | L8 roads have a control. L0 roads have none (0 kept). The background "control" has no positives and never exercises geometry. Better controls are available (F2). |
| C4 Verdict with topology difference | PARTIAL | The topology difference is stated correctly. The verdict counts are unsupported (F1–F4). |
| "dv_order only in trim/shrink" | TRUE | `_e2.c` has 2 call sites, at L934 (`dv_trim`) and L988 (`dv_shrink`). "At L8 that is this one sub-cell" is true. A priority change would also hit the L0 (1755,591) (2,1) sub-cell. |

Witness rerun: `trim_witness.py` reproduces the summaries, and `git diff --stat` is empty.

## Findings

1. **HIGH: L8 "R-has-trimmed 144" is an artefact of tolerance and stub size.**
   - **Evidence** (my checks on the committed dump and R):
     - All 308 dropped pieces are 2-vertex pieces. Their length in parent raw units is q10/q50/q90 = 0.06 / 0.17 / 0.65, max 4.68, so the median is about 25 m. Kept pieces have median 1.15.
     - All 144 "present" pieces are 2-vertex pieces with median length 0.2 raw.
     - All 308 dropped pieces (including all 144 "present") lie entirely within 1 raw unit of *kept* G pieces.
     - At L8, 1 raw unit is about 145 × 188 m. R's divided leaves are decoded at range 4096 over the whole parent, so 1 raw unit is R's coordinate quantum, and these stubs are below R's resolution.
   - "Present" therefore means "within one R quantum of an R road that our kept pieces already draw". It does not mean R carries this item, so `R-has-trimmed 144` does not follow.
   - **Fix:** use a match rule that requires R evidence specific to the item:
     - one-to-one assignment, or R polyline length near the piece that kept G pieces do not already cover;
     - a minimum piece length of at least 1–2 R quanta;
     - sub-quantum stubs reported as their own category.
   - Then rerun the verdict.

2. **HIGH: the L0 rule cannot detect anything and has no control. The background rule is never exercised.**
   - **Evidence:**
     - At L0, 1 parent raw unit is 0.56 m (lat) by 0.73 m (lon).
     - The spool is OSM (`provenance.md`: `extract_timing/spool` comes from `osm_to_parcel_geometry.py --pbf australia-…`); R is vendor data.
     - Distance from the trimmed L0 roads to the nearest R road of any class: per-piece median q50 = 102 raw (about 57 m). 0% of pieces are entirely within 1 unit, 2.4% within 5, 7.7% within 20.
     - G's trimmed classes are mostly dc 2 (164 pieces). R's cell has no dc 2 (classes 7/10/4/9/3/12).
     - The road "control" is empty: 0 kept in sub-cell (2,1).
     - For backgrounds, R's cell has only types 1024 ×19, 321 ×1 and 291 (class 1). It has **no type 288**, so all 6,642 items fail the type gate and the ring geometry is never tested. The stated limit ("validation is limited") understates this: the geometric rule has zero coverage.
   - **Fix:**
     - **L0 roads:** build a control from the parent's other 15 sub-cells' emitted roads (decode `l0u/frames.bin`, or extend the dump to every cell's kept lists). Calibrate a tolerance in metres, or a multiple of the R quantum, on it, and report recall.
     - **L0 backgrounds:** state the real evidence, the type census (R carries 0 type-288 records in the cell, against 8,801 in G). Give the geometric rule a positive control where types overlap. One option is the L8 (7,4) G backgrounds (instrument or decode) against R's 446 class-2 records of types 289/290/291/321. Another is a cell where K1 background passes.

3. **MEDIUM: the class criterion is not a G↔R identity.**
   - **Evidence:** G puts all 2,417 L8 pieces in dc 12. R's quadrant [19,1] has dc 10 ×622 and dc 12 ×128; the other quadrants are dc 10 only. Same-class matching finds 752 of the kept pieces present; any-class matching finds 1,053, plus 241 ambiguous.
   - "R lacks 1,162 kept" is therefore inflated by class-code mismatch.
   - **Fix:** validate a G→R display-class mapping at L8 first, or report the any-class result as primary, with class agreement as a separate measure.

4. **MEDIUM: "priority difference is the named cause" does not follow.**
   - DESIGN 2.4 requires "R lacks a different subset", measured with a validated rule. F1–F3 void that measurement.
   - The evidence that does hold points elsewhere:
     - R puts 929 links in the *whole* (7,4) parent, and 750 in the quadrant that contains our sub-cell (3,0). We put 2,417 pieces in one sixteenth.
     - The dropped pieces are sub-quantum stubs next to kept roads.
   - The likely causes are upstream of the trim: L8 road selection and volume, and short stubs from clipping or ways that R's quantum would collapse. A Phase 2 priority fix would not reach trimmed = 0 at that volume.
   - **Fix:** restate the L8 verdict as open. List the hypotheses: (a) sub-quantum stubs, (b) L8 selection volume, (c) priority. Phase 2 must not start from "priority" until it is shown.

5. **LOW (latent bug): the R leaf rect for divided leaves is the parent, not the quadrant.**
   - **Evidence:** `rect_parent_raw` is [0,0,4096,4096] for all four [19,k] leaves. `frame_bounds` is the parent bbox, with `divided_parent` range 4096.
   - The background "on frame edge" clause would therefore test against the wrong edge, and R rings clipped at quadrant edges would be scored absent or ambiguous. It is not exercised in Phase 1 because no background is trimmed at L8. It will matter if the rule is reused for the Phase 2 gate ("added items present in R").
   - **Fix:** derive the quadrant rect from the leaf slot (`leaf_path[-1]` in the 2×2 grid) or from the walk's slot bounds.

6. **LOW: Contract 1 fields are incomplete.**
   - DESIGN asks for "spool shape id, priority, bytes". The dump has the encoder-internal `item` and `par`; for backgrounds `par == item`, and shapes shared in by the overlap pass lose their source cell. It has the rank, not the priority key, and no per-item bytes.
   - **Fix:** add a stable spool key (level, cell, record) for both own and shared shapes, the `dv_key` fields, and the encoded size per item (or the probe delta).

7. **LOW: evidence wording.**
   - The table header "instrumented = plain = full AU" holds only for the dropped absolutes. Window totals (1,083 / 8,824) are not full-AU totals (3,015,057 / 11,029,580).
   - **Fix:** say "dropped counts equal". Also record the stronger fact verified here: the parents' frames are byte-identical inside the oracle ALLDATA (offsets above), which proves the window builds reproduce the same trimmed item set.

8. **LOW: the shrink mechanism is not explained.**
   - L0 drops *all* 207 roads because the `dv_shrink` fallback loop cuts kinds in the fixed order road → background → name. The backgrounds alone overflow the ceiling, so roads reach 0 before 227 backgrounds are cut.
   - That kind order is a separate policy from `dv_order`, and any Phase 2 "priority" change must account for it.
   - **Fix:** state this in IMPLEMENTATION.

## Verified as claimed

- The instrumentation cannot change output.
- The byte equality is real (my own `cmp`).
- Both tiers are dumped.
- The counts equal the manifest's `trimmed_items` (207 / 227 / 308).
- The coordinate conversion (lat/lon order, parent offset, `Lattice` units) is consistent between G and R.
- `dv_order` is confined to the trim and shrink tiers.
- The JSON reproduces from the script.
