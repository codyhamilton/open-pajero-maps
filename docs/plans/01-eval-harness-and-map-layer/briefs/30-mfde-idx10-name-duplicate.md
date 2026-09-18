# Brief: 30 -- Emit mfde entry 10 as a duplicate of the name sub-frame (mfde L12 entry-index 10)

Consumer: implementation worker (code + tests + doc edits; NO rebuild, do NOT touch `output/`).
Owned paths: `parser/kiwiw/synth.py` (`build_map_frame_bytes` only), `parser/tests/test_synth_map_frame.py`,
`docs/design/target-disc.md` (only the mfde index 10 wording), `docs/plans/01-eval-harness-and-map-layer/DESIGN.md`
(only the section-4 mfde index 10 row and the section-8 slot table row for indices 4/10).
Do not touch `divide.py`/`build_alldata.py` (brief 29), `mesh.py` (28), `parser/harness/`.
Commit and push when `pytest parser/tests -q` passes.
Depends on: 26b record. Runs alongside: 28, 29 (disjoint files). Verified by rebuild 31/31b.

## Diagnosis (R census, `/tmp/diag28/r12.py`, `/tmp/diag28/idx10.py`, R read-only)

`mfde` FAIL: level 12 entry-index 10 presence class `absent` in G, not in R. R's single L12 parcel
(3,808 B) has mfde[10] = in_buffer, off 3556, size 236, and its content is BYTE-IDENTICAL to the
name sub-frame (mfde[2], off 3320, size 236: the 8 capital-city labels). It is not an "undecoded"
frame: it is a duplicate of the name frame. Census of R (levels 2-12; L0 first 400k leaves):
- L6: name present 274, idx10 in_buffer 274, size equal in all 274; name absent -> idx10 absent (665). 100%.
- L8: 43/43 name-present leaves have idx10 == name size; L10: 3/3; L12: 1/1. 100% iff name present.
- L2/L4: idx10 mostly a same-size duplicate (L2 15,917 equal, 6,369 different size; L4 1,165/520) and
  idx10 present without a name in 1,383/1,287 leaves -- variant rule unexplained; absent dominates
  (L2 ~90%). L0: idx10 in_buffer ~10% (378,274/3.7M), unexplained.
G writes idx10 absent everywhere (DESIGN.md section 4/8 deliberately: "matches dominant state; undecoded"),
which is a valid class at L0-L10 (R has both) but not at L12 (R only in_buffer).
`synth.build_map_frame_bytes` already supports `ext_frames={10: ...}`.

## Changes
1. In `build_map_frame_bytes`, when `level >= 6` and a name sub-frame is present and no caller-supplied
   `ext_frames[10]`, populate mfde[10] with a byte-identical copy of the (padded) name sub-frame.
   L0-L4 unchanged (absent). Caller-supplied `ext_frames` still wins. Frame size accounting
   (total_size u16 check, in-buffer offset < frame size) must include the copy.
2. Tests: L12/L8/L6 frames with names have mfde[10] in_buffer bytes == name bytes; no name -> absent;
   L0/L2/L4 unchanged; round-trip through `parcel.decode_parcel` (`ext_frame_raw[10]`); explicit
   `ext_frames` override; total-size ceiling still raises correctly.
3. Docs: replace the "undecoded / open question" wording for index 10 with the census rule above
   (L6-L12: duplicate of name frame, 100% of name-present leaves; L0-L4: residual variant rule still
   undecoded, emit absent = dominant class).
4. Impact note to report: mapframe byte growth at L6-L12 = name-frame size per leaf (tiny), effect on
   `mapframe_size.max` (R max L6 158,560, L8 151,712 vs G 107,904/131,072).

## Done evidence
pytest green; hexdump of a synthetic L12 frame showing idx2/idx10 equal; decode round-trip.

## Report back
Any interaction with brief 29's divide threshold (dup name adds <= name-frame bytes to each leaf),
and whether `pointers`/`container` unit tests moved.
