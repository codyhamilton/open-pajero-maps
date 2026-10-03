---
design_id: 170
---

# Phase 1 — Named: Map Frame allocation padding (+60 bytes)

The non-payload structure is the zero-filled padding between each encoded Map
Frame's end and the end of its allocated buffer. On the existing 3-11 pair its
size is 21,570,746 → 21,570,806 bytes, a net **+60 bytes**. The disjoint changed
spans below account for it exactly: **34 × (−4) + 7 × (+28) = +60**.

## Preconditions and fixed contract

- C1 passed: `DESIGN.md` has `design_id: 170` in its frontmatter and its body
  describes this residual, not design id 2.
- C2 passed: both existing files and their adjacent manifests are present:
  `/home/codyh/workspace/open-pajero-maps/output/scratch-3-11/G/ALLDATA.KWI` and
  `/home/codyh/workspace/open-pajero-maps/output/scratch-3-11/G_new/ALLDATA.KWI`.
  They were opened read-only in place.
- C3: the recorded figures in
  `../04-c-core-orchestration/triage/review_3-11.md`, findings 2–3, are
  “1,597,341,290 -> 1,597,341,454” (**+164 payload**) and **+224 total_size**;
  the adjacent manifests record total_size 1,731,021,568 → 1,731,021,792.
  These are the cited 3-11 figures, not a new payload measurement.

## Region diff

Offsets are decimal bytes from the start of each `ALLDATA.KWI`; ranges are
half-open. Compare structures by index path so relocation does not masquerade
as new content.

| Non-payload region | Old → new size (bytes) | Diff |
|---|---:|---|
| Data Volume `[0,2048)` | 2,048 → 2,048 | Byte-identical, including reserved fields and logical/physical sector sizes 32/2048. |
| Management Header Table `[2048,4096)` | 2,048 → 2,048 | All 113 records and tail byte-identical. Only inline targets are PDMDH (record 0) and the language/country frame (record 29). Named-file targets are outside this pair; other inline targets are absent. |
| Record-29 language/country frame `[4096,6144)` | 2,048 → 2,048 | Byte-identical. |
| PDMDH header, LMRs (including display-class index tables), BSMRs `[6144,13374)` | 7,230 → 7,230 | Byte-identical; dimensions, counts, BMT locations and sizes unchanged. |
| Sector-address map: BMT/BMR arrays `[13374,29022)` | 15,648 → 15,648 | 1,548 BMR addresses relocate; every BMR size is unchanged. PDMDH has 1,695 differing byte positions, all in these address fields. |
| PDMDH trailing pad `[29022,29024)` | 2 → 2 | Identical zeros. |
| 2,139 Parcel Management Record buffers, including divided subrecords | 24,546,816 → 24,546,816 | 1,548 buffers relocate and differ in pointer/allocation fields. After masking only live leaf DSA/BS fields, each buffer is byte-identical at its matching index path. |
| Parcel Management Record tails (included in previous row) | 58,690 → 58,690 | Every byte is zero; no size change. |
| Map Frame allocation padding (listed below) | 21,570,746 → 21,570,806 | Every byte is zero; changed spans sum to +60. |
| Whole-file trailing pad | 0 → 0 | The final block buffer ends at EOF in each file. |
| Other gaps or unaccounted container bytes | 0 → 0 | Fixed prefix, frame allocations and block buffers partition each file without overlaps or gaps. |

There are 3,954,156 physical frame allocations (including divided leaves), not
3,951,970 grouped cell keys. Seven live leaf BS fields increase by one 32-byte
logical sector each. They belong to cells (1673,719), (1795,647), (1915,980)
(two leaves), (1969,1069), (1948,1098), and (2007,1179). The index entries
occupy the same number of bytes before and after; they do not supply the +60.

## Structure paths, offsets and disjoint byte deltas

Each row identifies
`ALLDATA.KWI / PDMDH / BSMR(level=0, blockset) / BMT[block] /
ParcelManagementRecord[slot path] / MapFrame / allocation-padding`.
A slash in the slot path selects a divided leaf. The cell is the parent L0
cell. The old and new offsets point to the start of the padding, and its
length gives the half-open span. A zero length denotes an empty span.
All spans lie outside encoded Map Frame bytes and are mutually disjoint in
each file. All listed cell keys occur in the existing
`scratch-3-11/Gnew.diff_cells.txt` record; that membership check does not
repeat the recorded 37-cell payload comparison.

| L0 cell (ix,iy) | blockset/block: slot path | Old pad offset | Old bytes | New pad offset | New bytes | Delta |
|---|---|---:|---:|---:|---:|---:|
| 1755,591 | 38/14: 507/6 | 355,895,988 | 12 | 355,895,992 | 8 | -4 |
| 1769,587 | 38/15: 361/1 | 392,631,804 | 4 | 392,631,808 | 0 | -4 |
| 1583,707 | 38/25: 111 | 453,000,042 | 22 | 453,000,046 | 18 | -4 |
| 1673,718 | 38/28: 457/3 | 470,959,004 | 4 | 470,959,008 | 0 | -4 |
| 1673,719 | 38/28: 489/1 | 471,134,624 | 0 | 471,134,628 | 28 | +28 |
| 1681,729 | 38/28: 817 | 465,640,438 | 10 | 465,640,442 | 6 | -4 |
| 1688,734 | 38/28: 984/13 | 471,357,410 | 30 | 471,357,446 | 26 | -4 |
| 1687,735 | 38/28: 1015/3 | 471,663,926 | 10 | 471,663,962 | 6 | -4 |
| 1669,748 | 38/28: 1413 | 468,046,700 | 20 | 468,046,704 | 16 | -4 |
| 1672,748 | 38/28: 1416 | 468,188,792 | 8 | 468,188,796 | 4 | -4 |
| 1711,729 | 38/29: 815/0 | 477,136,302 | 18 | 477,136,338 | 14 | -4 |
| 1711,729 | 38/29: 815/1 | 477,226,644 | 12 | 477,226,680 | 8 | -4 |
| 1712,729 | 38/29: 816 | 474,093,232 | 16 | 474,093,268 | 12 | -4 |
| 1712,730 | 38/29: 848 | 474,349,286 | 26 | 474,349,322 | 22 | -4 |
| 1789,731 | 38/31: 893 | 481,469,452 | 20 | 481,469,488 | 16 | -4 |
| 1795,647 | 39/16: 227 | 523,282,688 | 0 | 523,282,724 | 28 | +28 |
| 1796,648 | 39/16: 260 | 523,569,510 | 26 | 523,569,578 | 22 | -4 |
| 1794,736 | 39/24: 1026/3 | 559,181,988 | 28 | 559,182,056 | 24 | -4 |
| 1793,737 | 39/24: 1057 | 556,695,700 | 12 | 556,695,768 | 8 | -4 |
| 872,880 | 51/11: 1544 | 673,266,212 | 28 | 673,266,280 | 24 | -4 |
| 1530,843 | 53/15: 378/3 | 733,604,786 | 14 | 733,604,854 | 10 | -4 |
| 1530,844 | 53/15: 410 | 732,605,754 | 6 | 732,605,822 | 2 | -4 |
| 1957,771 | 55/5: 101/9 | 851,563,592 | 24 | 851,563,660 | 20 | -4 |
| 1886,839 | 55/10: 254/1 | 872,663,750 | 26 | 872,663,818 | 22 | -4 |
| 1903,846 | 55/11: 463 | 874,035,752 | 24 | 874,035,820 | 20 | -4 |
| 1915,980 | 55/27: 667/10 | 926,636,714 | 22 | 926,636,782 | 18 | -4 |
| 1915,980 | 55/27: 667/11 | 926,745,418 | 22 | 926,745,486 | 18 | -4 |
| 1915,980 | 55/27: 667/14 | 926,841,536 | 0 | 926,841,604 | 28 | +28 |
| 1915,980 | 55/27: 667/15 | 926,944,958 | 2 | 926,945,058 | 30 | +28 |
| 1969,1069 | 71/5: 1457 | 1,086,883,840 | 0 | 1,086,883,972 | 28 | +28 |
| 1969,1070 | 71/5: 1489 | 1,087,110,378 | 22 | 1,087,110,542 | 18 | -4 |
| 1911,1139 | 71/11: 1655 | 1,137,938,104 | 8 | 1,137,938,268 | 4 | -4 |
| 1948,1098 | 71/12: 348 | 1,139,139,166 | 2 | 1,139,139,330 | 30 | +28 |
| 1941,1105 | 71/12: 565/3 | 1,142,262,128 | 16 | 1,142,262,324 | 12 | -4 |
| 1936,1119 | 71/12: 1008/0 | 1,142,797,004 | 20 | 1,142,797,200 | 16 | -4 |
| 1929,1121 | 71/12: 1065 | 1,140,969,314 | 30 | 1,140,969,510 | 26 | -4 |
| 2007,1179 | 71/22: 887 | 1,179,739,774 | 2 | 1,179,739,970 | 30 | +28 |
| 1732,1493 | 86/30: 676 | 1,337,589,770 | 22 | 1,337,589,998 | 18 | -4 |
| 1842,1303 | 87/1: 754 | 1,342,188,824 | 8 | 1,342,189,052 | 4 | -4 |
| 1814,1467 | 87/16: 1910/1 | 1,363,593,490 | 14 | 1,363,593,718 | 10 | -4 |
| 1830,1447 | 87/17: 1254/3 | 1,366,762,788 | 28 | 1,366,763,016 | 24 | -4 |

The assemble step in `parser/kiwiw/frame_table.py`, `IndexedLayout`, allocates
`ceil(frame_length / 32) * 32` bytes per frame and stores that allocation in
its BS field; `place()` propagates the resulting offsets into the index.
For the 34 shrinking padding spans, the existing allocation absorbs the
frame growth. For the seven growing padding spans, the BS field adds a
32-byte logical sector and the padding grows by 28 bytes. The observed
spans, their zero bytes, and the changed BS fields name **Map Frame allocation
padding** as the structure, rather than offering an unexplained rounding
label. This is distinct from the rejected 512/2048-byte rounding hypotheses.

## Verification and deviations

Read-only evidence and the diff script are in this worktree's ignored
`output/scratch-07/evidence.json` and `output/scratch-07/diff_container.py`.
The script compares container fields and padding only. It reads each frame's
two-byte extent marker solely to locate its padding, without comparing those
markers, frame content, frame hashes or payload-length deltas. It verifies
all allocation padding bytes are zero, identical container topology, and
complete non-overlapping file coverage. The recorded +164 remains untouched;
adding the named +60 accounts for the recorded +224 total_size delta.

No schema edit is needed: `docs/schema/disc-layout.md`, “Allocation rules used
by the writer”, already describes this exact padding field. No encode, disc
copy/write, checker change or build-sha edit occurred. Plan 04 and the 3-16
worktree/results were untouched. No substantive deviation.
