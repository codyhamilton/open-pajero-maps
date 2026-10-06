# Implementation — 42 encoder trim vs R parity

Master direct. Oracle in force: `4e6b0de7…`.

## Phase 1 — trimmed items identified and checked against R

### Item identity (Contract 1)

The trimmed items were dumped by a bounded instrumentation hook in a
**throwaway worktree** at `20b4bf9`. The hook is in
`witness/instr_e2.patch` and is not landed. It writes to
`KW_TRIM_DUMP=<path>` from both trim tiers in `_e2.c`: `dv_trim` (tag
`trim`) and `dv_shrink` (tag `shrink`).

- **Contents:** every item of a trimmed kind in the trimmed sub-cell, in
  priority order, kept (K) or dropped (D). Each row carries: level, parent,
  sub-cell, kind, rank, item id, parent-record index, and the geometry. Roads
  carry `dc=<display class>|lat,lon;…` for the chain piece. Backgrounds carry
  `tc=<type>|lat,lon;…` for the parent-record ring, which includes shapes
  shared in by the overlap pass.
- **Output unchanged:** the instrumented and plain builds produce byte-equal
  `--frame-dump` bins and TSVs for both runs below.
- **Count gate:** the **dropped** counts equal the full-AU absolutes on
  `4e6b0de7` (its manifest `trimmed_items`: 207 / 227 / 308).
  - The window totals (1,083 roads / 8,824 backgrounds) are window-only, not
    the full-AU totals (3,015,057 / 11,029,580).
  - Stronger check (review F7): all 16 L0 (1755,591) frames and all 6 L8
    (7,4) frames of the window builds occur byte-identical inside the oracle
    `ALLDATA.KWI`. The window builds therefore reproduce the oracle's
    trimmed item set.
- **Item key (review F6):** `item` / `par` are row indices into the level's
  E2 input table, which is built from the spool. `(level, kind, row)` is
  therefore a stable spool key.
  - For backgrounds `par == item`. A shape shared in by the overlap pass
    keeps its source row, but its source cell is not recorded in the dump.
  - **Not captured:** the `dv_key` priority fields and the encoded bytes per
    item; the dump has the rank only. This is a limit; no verdict below
    depends on these fields.

| run | command | trim lines (dropped counts: instrumented = plain = full-AU absolutes; window totals are window-only) |
|---|---|---|
| L0 window | `--window 0 1755 591 1756 592 -j 1` | road 207/1,083 in 1 sub-cell; background 227/8,824 in 1 sub-cell |
| L8 level | `--levels 8 -j 1` | road 308/14,012 in 1 sub-cell |

- **Dumps:** `witness/trim_l0_1755_591.tsv.gz` (6,849 rows) and
  `witness/trim_l8_7_4.tsv.gz` (2,417 rows).
- **Where trimming happens:** all trimming is in the `shrink` tier (the
  whole sub-cell is over the 131,070 B ceiling). The `trim` tier fired 0
  times.
- **Shrink mechanism (review F8):** `dv_shrink` first binary-searches each
  kind against its per-kind limit, in `dv_order`.
  - If the frame still does not fit, a fallback loop cuts kinds in the
    **fixed order road → background → name** until it fits.
  - At L0 (2,1) the backgrounds alone overflow the ceiling, so the fallback
    takes roads to 0 before cutting 227 backgrounds.
  - This kind order is a separate policy from `dv_order`. Any priority
    change has to account for it.
- **L0 parent (1755,591):** Melbourne, near Tullamarine (lat −37.6875 …
  −37.6667, lon 144.844 … 144.875).
  - Sub-cell (2,1) of the 4 × 4 division drops **all 207** road pieces
    (ranks 0–206; 0 kept).
  - It drops the lowest-priority **227 of 6,642** backgrounds, all type 288
    (ranks 6,415–6,641).
  - Its frame is 131,064 B.
- **L8 parent (7,4):** SE Queensland (lat −28.67 … −23.33, lon 146 … 154).
  - Sub-cell (3,0) drops the lowest-priority **308 of 2,417** road pieces
    (ranks 2,109–2,416), all display class 12.
  - Its frame is 131,056 B.

### R decode (Contract 2) and G control (Contract 3)

`witness/trim_witness.py` does bounded R leaf preads and bounded leaf
decodes of the oracle `4e6b0de7` (G, read only). It writes
`witness/trim_witness.json`.

| parent | R topology | G topology |
|---|---|---|
| L0 (1755,591) | **undivided**, 1 leaf `[507]`, 23,680 B: 179 road links, 21 background records | 4 × 4 division, 16 frames, 310,268 B: 1,108 kept road pieces, 8,945 background items (8,777 of them type 288) |
| L8 (7,4) | **2 × 2**, leaves `[19,0..3]` = 6,176 / 106,400 / 12,448 / 31,104 B, with 30 / 750 / 25 / 124 links | 4 × 4, 6 non-empty frames; 2,979 kept road pieces; sub (3,0) held 2,417 before the trim |

- **Leaf rects (review F5, fixed):** a divided leaf's rect is now its
  quadrant (2 × 2) or sixteenth (4 × 4), derived from the leaf index.
  - It was checked against the decoded data. R data and G backgrounds fall
    0.0 raw outside their rects.
  - G L0 road pieces extend up to 3,072 raw outside their sub-cell rect,
    because the pieces are not clipped to the sub-cell. G volumes below
    therefore count length inside the rect only.
- **R quantum:** every R leaf here has frame range 4096 over the whole
  parent, so one R coordinate step is **1 parent raw unit**. That is
  0.56 × 0.73 m at L0 and about 145 × 188 m at L8.

#### The v1 rule is superseded (review F1–F3)

The first rule was: every vertex within 1 parent-raw unit of a same-class R
polyline, plus a type-gated ring rule for backgrounds. It is kept in the
script and the JSON (`rule_v1_not_validated`, per-item `status`), but **it
drives no verdict**.

- At L0, one unit is below the OSM ↔ vendor offset: the control median is
  31 raw.
- At L8, one unit is R's quantum, so "present" meant "near an R road", not
  "R carries this item".
- The class code is not a G ↔ R identity: R has no dc 2 at L0, and has dc 10
  plus dc 12 at L8, where G has only dc 12.

**Corrected numbers (v2):**

| level / kind | dropped | evidence (v2, any class) |
|---|---|---|
| L0 road | 207 (all) | see "L0 roads" below |
| L0 background | 227 (type 288) | type census |
| L8 road | 308 | piece length plus redundancy against kept pieces |

#### L0 roads (control calibrated; review F2)

- **Control:** 1,108 kept G road pieces in the parent's other 15 sub-cells.
  The trimmed sub-cell has no kept road.
  - Metric: the per-piece median of the sampled distance to the nearest R
    road of any class.
  - Control quantiles: q10 / q50 / q90 = 2.2 / 31.1 / 228.0 raw.
  - Control recall: 3.6% at 1 raw, 40% at 20, 76% at 100, 88% at 200 and
    98.9% at 500.
  - The tolerance with 90% recall is **500 raw**, about half the sub-cell
    width, so **per-item R presence is not decidable at L0**. The OSM and
    vendor geometries differ by tens of metres.
- **Dropped 207:** q10 / q50 / q90 = 15.7 / 100.6 / 266.3 raw.
  - The distances are farther than the control: 50% within 100 raw against
    76%, and 26% within 50 against 59%.
  - 164 of the 207 are **dc 2**, a class R does not carry anywhere in the
    parent. G keeps 773 dc 2 pieces in the other sub-cells.
- **Volume** (length inside each G sub-cell rect, raw units):
  - Sub-cell (2,1): **G emits 0 after the trim; R has 3,695 raw** (about
    2.3 km).
  - G before the trim had 37,039 raw there, a G/R ratio of 10.0.
  - The other 15 sub-cells have G/R ratios of 0.79–12.7 (median 2.6). G is
    denser than R across the parent, and (2,1) is at the dense end.

#### L0 backgrounds (type census; review F2)

- R's whole leaf has **0 type-288 records**. Its class-2 types are 1024 ×19
  and 321 ×1, plus class-1 291 ×1.
- G's parent has 8,777 type-288 items. All 227 dropped items are type 288,
  and all 6,628 pre-trim type-288 items in (2,1) are absent from R by type.
- The geometric ring rule was never exercised, because of the type gate. The
  evidence is the census, not geometry. No positive control for the ring
  rule was built; that is a limit.

#### L8 roads (review F1, F3)

- **Shape:** all 308 dropped pieces are **2-vertex stubs**.
  - Length q10 / q50 / q90 / max = 0.06 / 0.17 / 0.65 / 4.69 raw. The kept
    pieces' median is 1.15 raw.
  - The total dropped length is **94 raw**, 2.0% of the sub-cell's
    pre-trim 4,738 raw.
- **Redundancy:** all 308 lie, at every vertex, within 1 R step of a kept G
  piece.
  - By category: **295 are sub-quantum** (shorter than 1 R step). The other
    **13 are redundant**: every sample along the stub is within 1 R step of
    a kept G piece.
  - **0** carry R-specific evidence: no sample lies away from kept G pieces
    and near an R road.
- **Control** (kept 2,109, any class): recall is 56% at 1 raw and 92% at
  10. The dropped stubs' distances match it: 57% at 1 raw and 94% at 10.
  - The v1 rule, any class: 1,053 kept present / 815 absent / 241
    ambiguous. Same class: 752 / 1,162 / 195.
- **Volume:**
  - R's road length inside sub (3,0) is 6,623 raw. G's is 5,373 decoded
    (4,738 exact, before the trim). **G does not over-select by length.**
  - G does over-fragment: 2,979 pieces in the parent against R's 929 links,
    and 2,417 pieces in (3,0) against 750 links in R's whole quadrant.

### Verdict (Contract 4; revised after review)

- **L0 roads: the deviation is real by volume; per-item identity is not
  decidable.**
  - Sub-cell (2,1) is drawn with 0 roads where R has 3,695 raw of road.
  - Most dropped pieces are G-only: farther from R than the control, and
    79% dc 2, a class absent from R. The geometry cannot say which of them R
    carries.
  - Mechanism, from the code and the dump: the backgrounds alone overflow
    the frame, and the shrink fallback cuts roads first. The overflowing
    backgrounds are 6,628 type-288 items, a type R lacks in the whole
    parent.
- **L0 backgrounds: `R-lacks-trimmed` by type census.** R has 0 type-288
  records in the parent. The trim removes content R does not have.
- **L8 roads: not a priority difference.** The earlier "priority difference
  is the named cause" is **withdrawn** (review F4).
  - The dropped items are sub-quantum or redundant stubs, totalling 2% of
    length, all within one R step of kept G roads.
  - At R's resolution the trim removes no distinguishable geometry. The
    count-based "2.198% > 1% BLOCKER" line counts fragments.
  - The underlying difference is **G fragmentation**: about 3× R's link
    count per parent, from short clipped or split stubs.
  - Hypotheses after review:
    - (a) sub-quantum stubs: **supported**;
    - (b) L8 selection volume: **not supported by length** (G is below R);
    - (c) priority: **not needed** to explain the drop.
- **R topology difference:**
  - L8: R divides (7,4) 2 × 2, and its largest quadrant is 106,400 B with
    750 links. We divide 4 × 4, and one sixteenth held 2,417 pieces.
  - L0: R does not divide (1755,591); we divide it 4 × 4.
- **For Phase 2:** no R-evidenced trim-priority rule exists.
  - The L0 loss comes upstream, from type-288 over-emission (the
    288-template completeness item) through the fixed shrink kind order.
  - The L8 count comes from fragmentation.

### Phase 1 review

Claude CLI clean-context seat (disclosed; Codex is weekly-limited):
**FAIL** on P1.3 / P1.4 / C3. The text is kept as `reviews/p1-REVIEW.md`.
Fixes:

- **F1:** the L8 rule now uses piece length, redundancy against kept pieces
  and R-specific evidence. The 144 "R-has" result is withdrawn.
- **F2:** L0 roads have a calibrated control and are declared not decidable
  per item, with volume evidence. L0 backgrounds rest on the type census.
- **F3:** any-class is primary, and class agreement is reported separately.
- **F4:** the L8 verdict is restated with hypotheses; "priority" is
  withdrawn.
- **F5:** the quadrant / sixteenth leaf rects are fixed and data-checked.
- **F6:** the item key is stated; the `dv_key` fields and per-item bytes are
  a stated limit.
- **F7:** the count wording is fixed, and oracle byte-identity is recorded.
- **F8:** the shrink kind order is stated.
