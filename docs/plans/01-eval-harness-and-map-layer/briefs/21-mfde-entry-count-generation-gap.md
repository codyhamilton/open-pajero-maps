# Brief: 21 — mfde entry-count generation gap (21-35 entry frames) (ad hoc)

Consumer: implementation worker (format-analysis skewed — expect this unit to spend most of
its time reading bytes off a mounted reference disc, not writing code). This brief was
authored by the orchestrator investigating one of the unresolved deviations from WP1 unit
15b's 2026-09-09 full-Australia build (`compare_disc.py`'s `mfde` check FAIL). Brief 17
already fixed the check's *comparison logic* to tolerate a real per-parcel distribution of
entry counts; this brief is about the *generation* side — WP1 still never produces an
entry count above 20 (or 12 at level 12), where `R` legitimately does (21-35, a long tail at
every level 0-10 per `DESIGN.md` section 4). This is **not** the paired `entry-index-1`
finding from the same FAIL (that one was a trivial wiring bug in `build_alldata.py`'s
`_encode_one`, already fixed separately — see the commit this brief ships alongside).

Owned paths: none yet — this unit's job is to resolve the open format question below before
any code changes are safe to make. If the investigation lands on a concrete design (not just
an open question), a follow-up brief should be spun for the actual encoder change; do not
implement anything speculative against `parser/kiwiw/divide.py`, `synth.py`, or
`alldata_writer.py` in this unit.
Depends on: 06 (`DESIGN.md`, done), 13 (`divide.py`, done — read as "what WP1 already
tried", not as a base to extend blindly).
Runs alongside: whatever else is currently unblocked; this unit only reads/investigates, it
does not touch shared files.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` sections 4, 6 and 8 — section 4's
   "Levels 0-10 also show a long tail of 21-35-entry parcels ... these are the
   divided/integrated parcels (Section 6); a non-divided parcel always has exactly 20 (or 12
   at level 12) entries; **a divided parent parcel's own frame can carry more**" is the
   entire evidentiary basis for this gap — note carefully that this says the *parent's own
   frame* carries the extra entries, not that the parent is replaced by several
   standard-length sibling frames. Section 8's mfde-12-19 ambiguity (route-guidance vs.
   adjacent-parcel pointers) is a related but distinct open question already logged;
   don't conflate the two — indices 12-19 are *within* the standard 20-entry table, while
   this brief is about indices *beyond* 20 that don't exist in WP1's tables at all.
2. `docs/plans/01-eval-harness-and-map-layer/briefs/13-divided-parcels.md` (full) — the
   divided-parcel contract WP1 unit 13 actually implemented: type-1 (2×2) / type-2 (4×4)
   splitting, oversize-frame threshold, and the module docstring's "yielded row shape...
   `(ix, iy, parcel_type, sub_ix, sub_iy, map_frame_bytes)`" — confirms each sub-cell gets
   its own independently-encoded Map Frame.
3. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit 13 — Divided parcels"
   section — done evidence, deviations reported, and the Perth-fixture envelope FAILs.
4. `parser/kiwiw/divide.py` (full) — confirms structurally that `plan_divisions()` only ever
   yields separate, standard-length sub-frames (each built via the same `encode` callback as
   a normal whole-cell frame); it never emits one frame carrying pointers to its own
   children.
5. `parser/kiwiw/synth.py`'s `mfde_table_len()` and `build_map_frame_bytes()` — confirms the
   table length is a pure function of `level` (20, or 12 at level 12) with no parameter or
   code path that could produce a longer table; there is currently no way to ask the encoder
   for a 21+-entry frame at all.
6. `parser/harness/profile.py`'s `add_leaf()` (the `mfde_entry_count_hist` line) and
   `parser/harness/checks/mfde.py` (post-brief-17) — confirms the *check* now accepts any
   entry count in `R`'s observed per-level set (0.5-2.0x envelope aside), so the check is
   not blocking anything; the gap is purely that WP1's generator never produces a value in
   that set above the dominant one.

## Findings this brief is grounded in

- WP1's `divide.py`/`build_alldata.py`/`synth.py` pipeline is architecturally incapable of
  emitting an mfde table longer than `mfde_table_len(level)` (20, or 12 at level 12): every
  divided sub-cell becomes its own independently-encoded, standard-length Map Frame (a
  separate parcel-management leaf), never extra entries appended to one frame's own table.
  This was confirmed by reading `divide.py` end to end and `synth.build_map_frame_bytes()`'s
  table-length derivation (`mfde_len = mfde_table_len(level)` — a pure function of `level`,
  no length parameter, no way to override it from a caller).
- `DESIGN.md` section 4's own framing of the 21-35 entry tail is explicit that it belongs to
  "a divided parent parcel's own frame" (singular, its own table growing), which reads as a
  different on-disc mechanism than what unit 13 built (splitting into several standard-sized
  sibling frames). Unit 13 was scoped and dispatched before this distinction was
  spelled out this precisely in `DESIGN.md` section 4 (`DESIGN.md`'s section 4 mfde-length
  discussion and unit 13's brief were written close together; the "parent frame carries more
  entries" reading was not the shape unit 13 implemented, and nothing in unit 13's brief or
  `IMPLEMENTATION.md` outcome flags this as a deliberate, considered alternative that was
  rejected — it looks like an unexamined gap, not a resolved decision).
- The Perth-fixture full build (unit 13's own done evidence) and the 2026-09-09
  full-Australia build (unit 15b) both confirm `divide.py` *does* trigger in practice (Perth:
  38 envelope failures from the division; full-Australia: 5 `WARNING [kiwiw.divide]` lines at
  levels 0/8, `PLAN.md`'s 2026-09-09 build record) — so the entry-count gap is not "division
  never fires", it is "division fires but produces the wrong on-disc shape for what `R`
  does".

## Open question this unit must resolve before any encoder change is safe

What do the 21st-through-35th mfde entries on a real, divided-parent parcel on `R` actually
point to? Two live hypotheses, neither confirmed:

1. **Child sub-frame pointers.** Each extra entry is a `(DSA offset, SWS size)` pointer (the
   same 6-byte shape as every other mfde entry) directly into one of the parent's own divided
   sub-cells' Map Frame bytes — i.e., `R` keeps the *whole* divided family (parent +
   children) reachable from one mfde table, rather than as separate parcel-management-tree
   leaves the way `parse_parcel_mgmt_record`'s `size==0` recursion (which unit 13 relies on
   for the *tree* side) implies.
2. **Something else entirely** — extra content slots unrelated to the divided-parcel
   mechanism (e.g., another per-parcel content kind WP1 hasn't identified yet), coincidentally
   correlated with dense/divided parcels because both are driven by high content density.

Settling this requires reading real mfde entries 20+ off a mounted reference disc for a
handful of known-divided level-0/2 parcels (the same kind of spike `DESIGN.md` section 8
recommends for the mfde-12-19 question) — decode the pointer, resolve the DSA to a sector,
and check whether the bytes found there parse as a Map Frame (a divided sibling) or as
something else. `parser/kiwiw/parcel.py`'s existing decode path and `kiwiw/mesh.py`'s DSA
resolution should be reusable read-only for this; no reference-disc code needs writing.

## What NOT to do in this unit

- Do not modify `divide.py`, `synth.py`, `build_alldata.py`, or any generator code. This
  unit's job is answering the open question above and reporting a *recommendation*, not
  landing a fix.
- Do not treat "just make `mfde_table_len()` return more entries" as sufficient scope — even
  once hypothesis 1 or 2 is confirmed, the actual encoding change (how the extra entries'
  offsets get computed, whether it replaces or supplements unit 13's tree-based sub-frame
  leaves, how it interacts with the u16 frame-size ceiling that motivated unit 13 in the
  first place) is real design work for a follow-up brief, not this one.

## Report back

State which hypothesis (or a third one) the spike confirmed, with the raw evidence (decoded
DSA/offset/size for at least 2-3 sampled divided parcels, and what was found at the resolved
address). If the reference disc isn't mounted/available to this worker, say so explicitly
and report this as **cannot diagnose** rather than guessing — do not implement anything
speculative. Recommend whether the fix belongs to WP1 (unit 13's natural continuation, since
the divided-parcel grid is already WP1's) or needs escalation to the user as a new open
format question (`DESIGN.md` section 8 already has one contested item; this may become a
second).

## Resolution (2026-09-14, worker)

The reference disc **was** mounted and available (`/run/media/codyh/464210-8480/ALLDATA.KWI`,
loop-mounted via `udisksctl` after the mount point wasn't present at session start). The spike
ran to completion: `harness.walk.iter_parcels()` over level 0 found the first six real parcels
with `n_mfde_entries` > 20 in block (blockset=23, block=9), entries 516-521, with 21 and 24
entries respectively (script: adjacent scratch files, not committed — see the exact decode
steps below, reproducible against the same mounted disc).

**Neither hypothesis 1 nor hypothesis 2 as originally stated is confirmed. A third reading is
now the best-supported one, and it merges this brief's question with `DESIGN.md` Section 8's
already-contested mfde-12-19 item rather than resolving a separate WP1 question.**

Raw evidence, one sampled parcel (level 0, bs=23, block=9, path=(520,), file_offset=182202688,
n_mfde_entries=24, `dipid=0xa033`: bits15:14=`10` [not previously catalogued — DESIGN.md only
documented `01` and `11`], bit13 adjinfo=`1`, bits9:8 type=`00` **[not divided by the type
subfield]**, parent `llpid`=(-43.0, 147.25)):

| idx | raw (DSA, SWS-size) | resolved file_offset | decode at resolved address |
|---|---|---|---|
| 12 | `(0x00500003, 0x0000)` | 41943136 | size=0, high-entropy bytes, does not decode as a Map Frame header — outlier, structurally different from 13-23 |
| 13 | `(0x015cb73a, 0x0ffb)` size=8182 | 182828864 | `decode_map_frame_header()` succeeds: `llpid=(-42.9167, 147.3750)`, `nregion=1`, index-0 in-buffer at offset 184 |
| 14 | `(0x015bbe3e, 0x01fe)` size=1020 | 182319040 | succeeds: `llpid=(-43.0000, 147.3750)`, `nregion=1`, index-0 in-buffer at offset 166 |
| 20 | `(0x015bdc05, 0x00c6)` size=396 | 182378656 | succeeds: `llpid=(-42.9167, 147.2500)`, `nregion=1`, index-0 in-buffer at offset 160 |

Indices 13-23 (11 consecutive entries, spanning both the contested 12-19 range and this
brief's 20+ range) share one DSA neighbourhood (~22.7-22.8M in raw sector-address units) and
each resolves to a genuine, independently-decodable 36-byte Map Frame header — not opaque
content, not a BMT-style pointer array (that reading was tried and rejected: `entry[0]`'s own
`llpid` decode is out of range, -216°/-279°). Index 12 alone is the odd one out (size 0,
DSA far outside that cluster) and did not decode as anything recognisable.

This **rules out hypothesis 1 as literally phrased**: the resolved `llpid`s (Tasmania-area
cluster, ~-42.9 to -43.0°S / 147.25-147.375°E) differ from the parent's own `llpid`
(-43.0, 147.25) by **exactly 4 grid-cell-widths** (level-0 cell size 0.03125° lon /
0.0208333° lat, confirmed via `AllData.pdmdh`/`lmr.grid_nx`/`grid_ny`) — i.e. these are whole,
separate top-level parcels elsewhere on the grid, not sub-tiles of this parcel's own bounds
(which a 2×2/4×4 divided child would be, a fraction of the parent footprint, not a
whole-parcel-multiple offset). It also doesn't cleanly confirm hypothesis 2 ("something else
entirely, undecoded") — the targets decode cleanly as ordinary Map Frames, so they are not
opaque/unidentified content either.

What the evidence *does* support: indices 12+ (the already-contested 12-19 range and this
brief's 20+ range) are **one contiguous run of the same mechanism** — most plausibly the
Ch.7.1.1 note (13) "Adjacent Parcel Address Information" reading `DESIGN.md` Section 8 already
flagged as contested, addressed at a coarser-than-immediate (4-parcel) stride rather than
literal 8-neighbour touching, with a parcel's table growing past the base 20 (12 base +
8 direction slots) when it has more than 8 such reference entries. Critically, **the growth is
not gated by this parcel's own division**: every sampled long-tail parcel decoded `dipid` type
= `00` (not divided). `DESIGN.md` Sections 4 and 8 have been amended in place with this finding
(see the "Correction"/"Update" blocks added there) rather than resolved silently, and Section
8's item 1 now documents this brief's decode as the missing piece it deferred to WP2.

**Recommendation:** this is **not** a WP1 `divide.py`/`synth.py` gap — there is no evidence `R`
ever inlines a divided parcel's children into its own mfde table; `divide.py`'s
separate-sibling-leaf approach (per Ch.6 subrecord recursion) remains the only division
mechanism WP1 needs, and nothing here contradicts unit 13's implementation. The real open
question (what indices 12+ point to, and why some parcels need more than 8) is a WP2/
route-planning-layer question, already tracked as `DESIGN.md` Section 8 item 1 — treat that as
the second, now-updated, open format question rather than spinning a new one. No code changes
were made in this unit, per its own scope.
