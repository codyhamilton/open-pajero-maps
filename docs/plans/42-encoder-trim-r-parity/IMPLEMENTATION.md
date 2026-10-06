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
- **Count gate:** the counts equal the full-AU absolutes on `4e6b0de7` (its
  manifest `trimmed_items`).

| run | command | trim lines (instrumented = plain = full AU) |
|---|---|---|
| L0 window | `--window 0 1755 591 1756 592 -j 1` | road 207/1,083 in 1 sub-cell; background 227/8,824 in 1 sub-cell |
| L8 level | `--levels 8 -j 1` | road 308/14,012 in 1 sub-cell |

- **Dumps:** `witness/trim_l0_1755_591.tsv.gz` (6,849 rows) and
  `witness/trim_l8_7_4.tsv.gz` (2,417 rows).
- **Where trimming happens:** all trimming is in the `shrink` tier (the
  whole sub-cell is over the 131,070 B ceiling). The `trim` tier fired 0
  times.
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

`witness/trim_witness.py` does bounded R leaf preads and writes
`witness/trim_witness.json`.

- **Match rule:** fixed before measuring, and recorded in the script and the
  JSON.
  - **Roads:** every vertex of the piece is within 1 parent-raw unit of the
    union of same-class R polylines in the parent.
  - **Backgrounds:** an R class-2 record of the same type whose vertices lie
    on the G ring or on the frame edge.

| parent | R topology | G topology |
|---|---|---|
| L0 (1755,591) | **undivided**, 1 leaf `[507]`, 23,680 B: 179 road links, 21 background records | 4 × 4 division, 16 frames, 310,268 B: 1,083 road pieces, 8,824 background items (8,801 of them type 288) |
| L8 (7,4) | **2 × 2**, leaves `[19,0..3]` = 6,176 / 106,400 / 12,448 / 31,104 B, with 30 / 750 / 25 / 124 links | 4 × 4, 6 non-empty frames; sub (3,0) holds 2,417 road pieces |

| level / kind | trimmed (D) | R-has | R-lacks | ambiguous | G control: kept (K) items in the same sub-cell |
|---|---|---|---|---|---|
| L0 road | 207 | **0** | 204 | 3 | none: 0 kept in this sub-cell |
| L0 background | 227 | **0** | 227 | 0 | 6,415 kept: 0 present / 6,415 absent |
| L8 road | 308 | **144** | 158 | 6 | 2,109 kept: **752 present** / 1,162 absent / 195 ambiguous |

- **The road rule finds known-present items.** It finds 752 of the L8 kept
  roads.
- **The background rule has no positive control here.** R's L0 leaf has 21
  background records for the whole cell, against 8,824 in ours, so the
  0-present result for kept items is consistent with R lacking the content.
  The background rule's validation is therefore limited, and that is stated.

### Verdict (Contract 4)

- **L0 road and background: `R-lacks-trimmed`.**
  - R-has 0, R-lacks 431, ambiguous 3.
  - R lacks the trimmed items, and also every kept background in the
    sub-cell. R's cell is a single 23,680 B frame.
  - The trim deletes nothing that R carries. The large L0 density gap (OSM
    type-288 content far beyond R's) is a source-content difference, not a
    trim effect.
- **L8 road: `R-has-trimmed` 144** (R-lacks 158, ambiguous 6).
  - R also lacks 1,162 of the roads we keep in that sub-cell.
  - R lacks a **different subset** from the one we trim. R's L8 road
    selection is not our priority order.
  - Per DESIGN Contract 2.4, the **priority difference is the named cause**,
    and Phase 2 attempts a fix under the landing gate.
  - Note: `dv_order` is consulted only by the trim and shrink tiers. A
    priority change therefore affects only cells that trim; at L8 that is
    this one sub-cell.
- **R topology difference:**
  - L8: R divides (7,4) 2 × 2, and its largest quadrant is 106,400 B with
    750 links. We divide it 4 × 4, and one sixteenth holds 2,417 pieces.
  - L0: R does not divide (1755,591); we divide it 4 × 4.
  - The difference follows from content volume. No division-depth rule
    alone would remove the trim while R carries this little content.

Not done in Phase 1: any encoder change (non-goal). Phase 2 (fix attempt
for the L8 priority, or proven cause) is open.
