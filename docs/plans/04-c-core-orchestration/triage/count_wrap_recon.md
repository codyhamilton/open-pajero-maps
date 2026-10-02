# 3-10 Count-wrap recon: multiple background units of one class

Scripts and raw data (git-ignored): `output/scratch-3-10/` (`scan.py` per-element unit scan, `unit_detail.py` R unit semantics, `table.py`/`table2.md` the 37-cell table, `G311b.json`, `orig.json`, `unit_detail_full.json`, `known9.json`). G = `output/scratch-3-11/G/ALLDATA.KWI`; R = original disc `/run/media/codyh/464210-8480/ALLDATA.KWI`.

## Verdict (Q6, first)

Split into several same-class units is supported by the readers (Q1) and by the spec's per-type unit design, but it is NOT proven for firmware and it is NOT what the original does. Plain split of a class by record count is unsafe on a second ground: in all 37 cells a single type code has more than 4095 records (max 6401), so a split by type code cannot work; any fix must split units of the SAME type code. R never does that (all 57,693 multi-unit elements are type-disjoint). That is a format risk the orchestrator must put to Cody before 3-11. Last-mile risk: the firmware's walk of the unit table and of the unit's type code is unobserved; D1, Python and kiwiread are host tools only.

## Q1 Readers

All consumers loop over `n` unit headers, accept the same class repeatedly, take each unit's own count, and ignore the offset word:
- `parser/kiwiw/_d1.c` L205-262 (unit loop) and `parser/kiwiw/background.py` (same walk): units are appended to the flattened shape tables, so counts effectively SUM across same-class units (no overwrite).
- `tools/kiwiread/kiwiread.c` `dumpbkgd`: same walk.
- K1 reads only D1's flattened shape tables, so it also sees the sum.
- Evidence the walk tolerates it: my R scan decodes 57,693 elements with 2 to 4 units of the same class without mismatch (`mism: []`).
Caveat: these readers are ours; none proves firmware behaviour.

## Q2 Original disc (R), own scan of 4,157,312 elements

- Units per element: 1 unit 4,099,619; 2 units 52,895; 3 units 4,771; 4 units 27. So 57,693 elements have more than one unit; in all of them units are same-class (class 2: 52,096 two-unit; class 1: 799) and type-code-disjoint (`dup_overlap` 0, `dup_disjoint` 57,693). Typical signature: class 2 units with type codes 291 / 289 / 290 (and 1024 / 640, 288) as separate units.
- Max records in one class unit: 517 (`max_unit_decl`); max per class per element 585. Zero cells at 4095 or more. Reserved bit 12 and height flag bit 13 are always 0.
- Offset word: nonzero and equal to the true offset in all 4,157,312 elements (`boff_eq_actual`). G writes 0 in the offset word (`_cenc.c` L789 area). This is a separate difference from R, already present for every G element and noted, not new to the split.
- Conclusion: R evidences "n_units may exceed one per class, one unit per type code". It gives no evidence for two units of the same class AND same type code, and no evidence for counts near 4095.
- G scan for comparison: 1,420,999 bg elements in G (bg-bearing frames 3,954,156), every one single-unit; max physical 6415.

## Q3 Sizing in `enc_bg`

`class_n[c] & 0xFFF` wraps silently at 4096 while all records are still written (physical minus declared is 4096 in every one of the 41 elements). Each extra unit costs 4 bytes in the unit table. All 41 elements need exactly 1 extra unit (physical at most 6415, under 2 x 4095). Against the 3-09m worst-case headroom (974 B) and the 131070 ceiling: minimum bg sub-frame headroom after the extra unit is 970 B, so none exceeds it. `n_in`/`unit_off`/`rec0` capacity is 4 units today by construction; splitting needs capacity for up to 5 (not edited here). Whole-map-frame headroom is tighter than the bg sub-frame figure: golden `l0_divided_trim_halo` contains a frame of 131060 B (cell (1755,591)), so +4 leaves 6 B to 131070. My scan's `frame_end` capture is unreliable (values are not frame-relative) so whole-frame headroom is measured only for that golden frame, not for the other 36 cells. This is an open item for 3-11 (E2/kind limits are whole-frame).

## 37-cell table (41 elements; 4 cells have more than one element)

All declared units are class 2, all at level 0, so the "level" column is the zoom level 0 index of the scan. Headroom after = 131070 - bg sub-frame bytes - 4 x extra.

| level | cell ix,iy | declared | physical | extra units | bg sub-frame bytes | headroom after (131070-bg-4*extra) | type codes | max recs one code | in 3-08 nine |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 872,880 | 106 | 4202 | 1 | 85128 | 45938 | 3 | 4198 | yes |
| 0 | 1530,843 | 282 | 4378 | 1 | 87798 | 43268 | 2 | 4377 |  |
| 0 | 1530,844 | 1987 | 6083 | 1 | 122736 | 8330 | 2 | 6082 |  |
| 0 | 1583,707 | 843 | 4939 | 1 | 102470 | 28596 | 5 | 4926 | yes |
| 0 | 1669,748 | 485 | 4581 | 1 | 92548 | 38518 | 3 | 4579 | yes |
| 0 | 1672,748 | 1106 | 5202 | 1 | 106292 | 24774 | 3 | 5186 |  |
| 0 | 1673,718 | 184 | 4280 | 1 | 85904 | 45162 | 3 | 4278 |  |
| 0 | 1673,719 | 1253 | 5349 | 1 | 107324 | 23742 | 3 | 5347 |  |
| 0 | 1681,729 | 2243 | 6339 | 1 | 128130 | 2936 | 3 | 6335 | yes |
| 0 | 1687,735 | 1207 | 5303 | 1 | 106298 | 24768 | 3 | 5298 |  |
| 0 | 1688,734 | 1120 | 5216 | 1 | 104462 | 26604 | 2 | 5215 |  |
| 0 | 1711,729 | 497 | 4593 | 1 | 92018 | 39048 | 1 | 4593 |  |
| 0 | 1711,729 | 403 | 4499 | 1 | 90126 | 40940 | 1 | 4499 |  |
| 0 | 1712,729 | 461 | 4557 | 1 | 91736 | 39330 | 1 | 4557 |  |
| 0 | 1712,730 | 1018 | 5114 | 1 | 103460 | 27606 | 1 | 5114 |  |
| 0 | 1732,1493 | 63 | 4159 | 1 | 84212 | 46854 | 3 | 4157 | yes |
| 0 | 1755,591 | 2319 | 6415 | 1 | 130096 | 970 | 3 | 6401 |  |
| 0 | 1769,587 | 289 | 4385 | 1 | 96444 | 34622 | 5 | 4364 |  |
| 0 | 1789,731 | 301 | 4397 | 1 | 106430 | 24636 | 3 | 4393 |  |
| 0 | 1793,737 | 227 | 4323 | 1 | 86636 | 44430 | 1 | 4323 |  |
| 0 | 1794,736 | 250 | 4346 | 1 | 87138 | 43928 | 1 | 4346 |  |
| 0 | 1795,647 | 20 | 4116 | 1 | 83294 | 47772 | 3 | 4104 | yes |
| 0 | 1796,648 | 48 | 4144 | 1 | 88196 | 42870 | 3 | 4132 |  |
| 0 | 1814,1467 | 634 | 4730 | 1 | 94856 | 36210 | 3 | 4727 |  |
| 0 | 1830,1447 | 25 | 4121 | 1 | 83358 | 47708 | 3 | 4116 |  |
| 0 | 1842,1303 | 1021 | 5117 | 1 | 102882 | 28184 | 1 | 5117 |  |
| 0 | 1886,839 | 72 | 4168 | 1 | 83878 | 47188 | 2 | 4167 |  |
| 0 | 1903,846 | 878 | 4974 | 1 | 100318 | 30748 | 2 | 4973 | yes |
| 0 | 1911,1139 | 161 | 4257 | 1 | 86098 | 44968 | 3 | 4254 |  |
| 0 | 1915,980 | 1768 | 5864 | 1 | 117378 | 13688 | 1 | 5864 |  |
| 0 | 1915,980 | 1325 | 5421 | 1 | 108486 | 22580 | 1 | 5421 |  |
| 0 | 1915,980 | 670 | 4766 | 1 | 95412 | 35654 | 1 | 4766 |  |
| 0 | 1915,980 | 1062 | 5158 | 1 | 103226 | 27840 | 1 | 5158 |  |
| 0 | 1929,1121 | 2145 | 6241 | 1 | 125672 | 5394 | 2 | 6237 | yes |
| 0 | 1936,1119 | 1534 | 5630 | 1 | 112804 | 18262 | 2 | 5627 |  |
| 0 | 1941,1105 | 74 | 4170 | 1 | 83404 | 47662 | 1 | 4170 |  |
| 0 | 1948,1098 | 807 | 4903 | 1 | 99176 | 31890 | 2 | 4890 |  |
| 0 | 1957,771 | 338 | 4434 | 1 | 91074 | 39992 | 7 | 4396 |  |
| 0 | 1969,1069 | 1622 | 5718 | 1 | 115410 | 15656 | 2 | 5717 | yes |
| 0 | 1969,1070 | 690 | 4786 | 1 | 97020 | 34046 | 2 | 4784 |  |
| 0 | 2007,1179 | 517 | 4613 | 1 | 93076 | 37990 | 1 | 4613 |  |

Cross-check: my own scan reproduces all 9 cells of the 3-08 `format_wrap` list (`known9.json`, marked "yes"); 28 more cells found beyond them, matching the 37 in 3-09m. Declared = physical - 4096 in all 41.

## Q4 What compares ALLDATA bytes

Changing the 37 cells changes: the full-AU sha re-oracle (87a01b14...) and Perth (da13a775...) per Assumption 1 in `briefs/3-fix-template.md` (Perth overlap with the 37 cells not measured here); golden `output/goldens-3C/l0_divided_trim_halo` (window 1755 591 1756 592 contains cell (1755,591), whole frame 131060 B); `-j1 == -j12` compares are unaffected in kind (both change equally); K1 `completeness` record counts go from declared (wrapped) to physical, which is the intended fix. The other goldens do not contain these cells.

## Q5 Alternatives without a format guess

- Split by type code into same-class units (R's convention): impossible here, a single type code exceeds 4095 in every one of the 37 cells (max 6401 in (1755,591)).
- Split at the shape/cell level (smaller cells): changes the tiling and the cell index, a larger format change; decoder sees more cells, each under the limit. Not evidenced as feasible; unexamined beyond this.
- Same-class same-type second unit: decoder sees summed records (Q1); firmware behaviour unknown.
- Not emitting records is clipping and is excluded.

## Q6 Open items for Cody

1. Is a same-type same-class second unit acceptable to the firmware? Nothing on disc or in the repo proves it.
2. G zero offset words vs R true offsets, an existing difference for every element.
3. Whole-frame headroom for the other 36 cells (6 B for the golden cell).
