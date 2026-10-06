# Review — plan 36

## Phase 1 (Claude CLI clean-context seat, reviewed 0cb872e, 12:31–12:35 AEST)

Verdict: PASS_WITH_FOLLOWUPS

Reviewer: independent clean-context seat (Claude CLI, disclosed; Codex weekly-limited). Reviewed SHA: `0cb872e` (plan 36 Phase 1). No repo files modified.

## Phase 1 outcome assessment

| # | Outcome | Assessment | Evidence I checked |
|---|---|---|---|
| 1 | `region_accounting.py` + tests | **met** | Read the tool and tests in full. `pytest test_region_accounting.py test_oracle_chain.py`: 33 passed. The partition is complete and disjoint (`check_partition`: sorted sweep, gaps and overlaps, beyond-EOF). Comparison is by `(level, blockset, block, slot path)` key via `np.intersect1d`, never by offset. The run exits 2 on an incomplete partition, unaccounted ≠ 0 or a bad extent. Both shas are checked before scanning. It refuses existing outputs. Reads are per-allocation preads. The committed tool sha `ed6e6511…` equals `tool_sha256` in `region-3-11-au.json`. |
| 2 | `G_pre311` sha `87a01b14…` | **met** | `sha_pre311.json` (scratch and evidence copies are identical) gives `87a01b14b612…7862`. The file on disk is 1,731,021,568 B. The manifest `total_size`/`sha256` agree. In `run_p1_replay.log` the WT HEAD is `b7c7c42ba458…` (= `b7c7c42`), the run is guarded, and the L0 frame bytes are 1,597,341,290 (= plan 07's manifest figure). `region_accounting` re-hashed it independently (`old_sha256` in the region JSON). The protected before/after evidence copies are byte-identical (`27560c1a…`). |
| 3 | Plan 07's 41 rows reproduced, 0 unaccounted | **met** | I parsed the plan 07 table (`docs/design/g-new-nonpayload-accounting.md`) and the spans TSV (scratch == evidence, `cmp`). All 41 rows match as a set on (key, old offset, old bytes, new offset, new bytes, delta). There are 34×(−4) + 7×(+28) = +60 B. Every span has payload +4 (Σ +164). There are 7 allocation changes, and the spans are disjoint in each file. The region totals also match plan 07: DV/MHT/rec-29 2,048 each, equal. PDMDH records 7,230, BMT arrays 15,648, sector pad 2. PDMDH has 1,695 differing bytes, all in BMT address fields. There are 2,139 PMR buffers: 24,488,126 + 58,690 = 24,546,816 B. Of these, 1,548 relocated, with 0 masked-content differences and 0 nonzero tails. There are 3,954,156 frames, with 0 nonzero padding and 0 bad extents. Padding goes 21,570,746 → 21,570,806. File +224 = 164 + 60, 0 gaps, 0 overlaps, unaccounted 0. The payload-basis difference (1,684,874,982 vs the manifest's 1,597,341,290) is explained in IMPLEMENTATION; the delta is +164 on both bases. |
| 4 | 3-11 routed-diff 0/0 vs 37 | **met** | `routed-3-11-au.json`: `routed_only_count` 0, `baseline_cells_missing_from_routed` 0, changed 37/0/0, `multiset_list_complete_under_routing` true, fallbacks 0/0. The pins are `87a01b14 → 013586b5`. The sha links match: baseline JSON `074e8cc8…`, baseline cells `f03ebaab…`, routed cells `17be31b3…`. The baseline 37 cells equal both `output/scratch-3-11/Gnew.diff_cells.txt` and `Gnew.expected37.txt`, as does the routed cell set. All 37 plan 07 span cells are in the list. |
| 5 | oracle_chain 3-11 row, publish validation, wording, provenance | **met** | TSV/JSON 3-11 row: `replay-routed-verified`, residuals `[]`, and 8 supporting-evidence entries. The `replay_3_11` summary matches the artefacts, and the TSV and JSON evidence are equal. The plan 29 signing-record sha refresh (`ca1278f8…` → `7fb15a4d…`) matches the current file and is explained by plan 37's edit. `replay_3_11()` is validated by 1 accept test and 5 tamper rejects. The wording is replaced in the contract, the plan 31 record (plus a post-close note) and OVERVIEW. In `residuals.tsv`, R-G1-4 and R-G10-1 are `discharged`, leaving 13 `blocks-phase3` rows (counted). There is a provenance entry for `scratch-36`. The `perf_inventory.json` surface is omitted, and this is a disclosed deviation: the inventory only covers `parser/**`. |

## Findings

1. **medium (follow-up, before Phase 2 reuse): the tool counts nonzero "padding" and "tail" bytes as padding instead of failing closed.**
   - **Evidence:** `region_accounting.py:220-221,185-186,346-347`. `frame_pad_nonzero` and `pmr_tail_nonzero` are reported but are not part of `ok`.
   - **Further gap:** padding ≥ one logical sector (`alloc − payload ≥ ls`), which the writer's `ceil(len/32)*32` rule makes impossible, is not checked at all.
   - **Why it matters:** on 3-11 every value is 0, so P1 is unaffected. On the 3-14 hop (Phase 2), a misread extent or stale bytes in an allocation would be labelled "frame_padding", still sum to 0 unaccounted, and the region names would be wrong.
   - **Why unaccounted = 0 doesn't catch it:** `unaccounted_bytes` is identically 0 whenever the partition has no overlaps or gaps, so it adds no independent signal.
   - **Fix:** add `a/b['frame_pad_nonzero'] == 0`, `a/b['pmr_tail_nonzero'] == 0`, and a new `frame_pad_oversize == 0` (`(fa - fpay) >= ls`) to `ok`.
   - **Tests:** add a synthetic test that corrupts one padding byte (or one PMR tail byte) in a copied disc and asserts `rc == 2`.

2. **low (follow-up): no account-level fail-closed test.**
   - **Evidence:** `parser/tests/test_region_accounting.py`. Gap and overlap logic is only unit-tested through `check_partition`. Nothing asserts that `account()` returns 2 on a real disc with a gap, or that it refuses an existing output (the IMPLEMENTATION record notes this).
   - **Fix:** add a test that appends 32 zero bytes to disc `b` and expects `rc == 2`, `partition.gap_bytes == 32` and `complete_and_accounted` false.
   - Add a test that pre-creates `out` and expects `SystemExit`.
   - In `test_grown_frame…`, assert `c['frames']['relocated'] > 0` or `c['pmr']['relocated'] > 0`. This proves the "relocation is not content" path is actually exercised.

3. **low (follow-up): `replay_3_11` gates the span delta multiset, not the 41 plan 07 rows.**
   - **Evidence:** `oracle_chain.py` `replay_3_11` checks only `sorted(deltas) == [-4]*34 + [28]*7`. Row-by-row equality with plan 07 (keys and offsets) is asserted only in prose in IMPLEMENTATION. I re-verified it here: 41/41 exact.
   - `sha_pre311.json` is cited as `replay_disc_witness` but is neither read nor sha-pinned in `supporting_evidence`.
   - `region-3-11-au.spans.tsv` is committed but not referenced.
   - **Fix:** in `replay_3_11`, compare `{(key, old_pad_offset, old_bytes, new_pad_offset, new_bytes, delta)}` from `padding_spans` against a committed constant (or a parse of the plan 07 table). Load `sha_pre311.json` and check `sha256 == AU0`. Append `evidence()` for `sha_pre311.json` and `region-3-11-au.spans.tsv`. Add a tamper test for an offset change.

4. **low (follow-up): residual stale wording.**
   - `docs/plans/31-phase3-oracle-and-pin-gates.md:92-93` (Residual Risks) still says "AU 3-11's +60 B non-payload growth … unmeasured". The post-close note covers it only implicitly ("wording above").
   - `triage/phase3_synthesis/gates.tsv:11` and `synthesis.md:29,56` still describe the correction as pending. These are historical synthesis records, so leaving them is defensible.
   - **Fix:** amend plan 31 L92 to say "The 3-14 container, index and padding scope is unmeasured (AU 3-11's +60 B: attributed, plan 07; reproduced, plan 36 P1)". Optionally add "(discharged plan 36 P1)" to the gates.tsv G10 note.

5. **low (note for Phase 2):** the plan 07 partition lists a "whole-file trailing pad" region. The tool has no such region, so a trailing pad would show up as a partition gap and the run would exit 2 rather than name it. That is safe (fail-closed). If Perth or 3-14 has a legitimate trailing pad, add an explicit all-zero `trailing_pad` region (and gate on its zeroness) rather than treating it as accepted. The `compare()` inline report iterates only old-side inline indexes, so a new-only inline target would appear only in `sizes`. When touching that code, iterate the union.

## Intent and ledger

- The implementation matches the verbatim intent. The tool reproduces plan 07 as a control without reopening its conclusion. The replay is byte-exact and was not re-pinned. The routed proof is on the exact 3-11 pins and against the retained 37-cell list.
- No assumption failed. The payload-basis difference is definitional and documented.
- Non-goals respected: no encoder change, and the protected snapshots are unchanged.

## Plan sufficiency

- The design was sufficient. The contract's six items mapped one-to-one onto checkable artefacts, and the control numbers (+164, padding pair, 41 spans) made reproduction mechanically verifiable.
- One gap: the design did not say whether "0 unaccounted" should include zeroness of padding and tails. Finding 1 closes it.

## Residual risks

- Finding 1 matters for Phase 2, where content changes are expected and the tool's region labels become the attribution.

## Phase 2 (Claude CLI clean-context seat, reviewed b10e787, 12:40–12:44 AEST)

Verdict: PASS_WITH_FOLLOWUPS

# Plan 36 Phase 2 review: 3-14 container/index/padding accounted

**Seat:** Claude CLI, clean context, disclosed (Codex is weekly-limited).
**Reviewed:** master `b10e787`. No repo files were modified.
**Scratch outputs:** `output/scratch-36/review-p2/`.

## Phase 1 remediation (REVIEW.md F1–F5) in `b10e787`: verified

- **F1.** `ok` now also requires these three counts to be 0 on both sides: `frame_pad_nonzero`, `pmr_tail_nonzero` and the new `frame_pad_oversize` (`(fa-fpay) >= ls`).
  - See `region_accounting.py` around L224 and L353.
  - The committed tool sha is `183d0ee0…`. This equals `tool_sha256` in all `r2/` outputs.
- **F2.** Account-level tests cover a trailing gap, a nonzero pad byte, refusal of an existing output, and the relocation path.
- **F3.** `replay_3_11` checks the spans row by row:
  - against the `plan07_spans()` parse of the ledger, and against the spans TSV;
  - the `sha_pre311.json` witness must equal `AU0`;
  - three new evidence pins were added.
- **F4.** Plan 31 L92 and gates.tsv G1/G10 now carry post-close notes. The plan 31 edit is now stale for 3-14: see finding 2.
- **F5.** The inline compare now iterates the union of old and new indexes.

**Tests:** `pytest test_region_accounting.py test_oracle_chain.py` gives **46 passed**.

## Phase 2 outcomes: all met

Each check below is my own recomputation.

**1. Region accounting committed, with 0 unaccounted.** Met.
- I ran `container_summary.py` again on the `r2/` inputs into `review-p2/`. Both `container-au.json` and `container-perth.json` are **byte-identical** to the committed files, and both pass.
- From `r2/region-3-14-{au,perth}.json`:
  - **AU:** Σ of named region deltas = −38,913,410 − 3,198 − 12 − 20 = **−38,916,640** = file delta.
  - **Perth:** −161,380 + 388 + 16 − 16 = **−160,992** = file delta.
  - Partition: complete on both sides, gap 0, overlap 0.
  - `frame_pad_nonzero`, `frame_pad_oversize`, `pmr_tail_nonzero` and `frame_bad_extent` are all 0 on both sides.

**2. Payload delta = Σ per-cell deltas.** Met.
- I summed `new_bytes − old_bytes` from `scratch-31/diff-3-14-{au,perth}.cells.tsv`:
  - AU: 246,123 rows, **−38,913,410**;
  - Perth: 795 rows, **−161,380**.
- Both equal `frame_payload.delta`.
- The cells TSV shas (`77ff1d86…`, `af26b6b4…`) match the cell-diff records and the oracle row lists.
- This is a real cross-check: two independent tools, the plan 31 multiset diff and the region partition, give the same figure.

**3. Residual replaced by evidence.** Met in JSON; partial in TSV (finding 1).
- `oracle_chain.json` 3-14 rows carry `container_account` (sha-pinned summary, region deltas, unaccounted 0). Only the payload-causes residual remains.

**PDMDH size fields.** Each BMT entry is 6 bytes (4-byte address + 2-byte big-endian size), so entry offset 5 is the size's low byte. I checked every outside byte:

| Block | Size (sectors) | Low byte |
| --- | --- | --- |
| AU 23/16 | 386 (0x182) → 385 (0x181) | 130 → 129 |
| 51/9 | 426 (0x1AA) → 424 (0x1A8) | 170 → 168 |
| 51/10 | 395 (0x18B) → 397 (0x18D) | 139 → 141 |

- Perth has the same two 51/9 and 51/10 bytes, at entry offsets 7338 and 7344.
- The high bytes (offset 4) are unchanged, as expected. That gives 3 (AU) and 2 (Perth) non-address bytes, and all of them are explained.

**PMR records and tails.** With `ls` = 32, each `size` equals `ceil(rec/32)`.
- Record deltas: −28, −56 and +72, so Σ AU −12 and Σ Perth +16. Both are correct.
- Tails (old → new):
  - 23/16: 4 → 0;
  - 51/9: 20 → 12;
  - 51/10: 24 → 16.
- Σ AU −20 and Σ Perth −16, both correct. Every tail is below 32.
- Buffer sectors: AU −1 sector = −32 B = −12 − 20. Perth 0 = +16 − 16.

**Topology keys.**
- The only-old/only-new frames sit entirely in the size-changed PMR blocks:
  - AU: 12 old / 15 new;
  - Perth: 8 old / 14 new;
  - 23/16:1285, 51/9:988 and 51/9:1211 each merge 4 children into 1 leaf;
  - 51/10:768 gains children /4…/15.
- PMR `masked_content_differs_keys` equals exactly the size-changed set.

**Is the "frame_padding" / "pmr_tails" naming honest?** Yes, given the F1 gates:
- every padding and tail byte is proven zero;
- frame padding is proven to be under one logical sector, so it is fully determined by `ceil(payload/32)*32`;
- the tails of the changed blocks follow exactly from record size → sector count, as recomputed above.

The padding delta splits as follows. Neither component is itemised separately in the summary, but both are implied:

| Hop | Common-frame spans | Added/removed topology frames | Total |
| --- | --- | --- | --- |
| AU | −3,302 | +104 | −3,198 |
| Perth | +264 | +124 | +388 |

## Findings

1. **low: the TSV rows drop the residual without citing the evidence.**
   - **Evidence:** `oracle_chain.tsv` AU/Perth 3-14 rows. `supporting_evidence` is empty, and `container_account` exists only in `oracle_chain.json` (`oracle_chain.py` `container_account`).
   - **Fix:** in `container_account`, also append `evidence(path)` to `row['supporting_evidence']` (creating the list if needed). Then re-run `publish` so that the TSV row cites `hop_3_14/container-{au,perth}.json` with its sha.

2. **low: stale "3-14 container unmeasured" wording.**
   - **Evidence:**
     - `docs/design/oracle-chain-and-live-pin-contract.md:69`;
     - `docs/plans/31-phase3-oracle-and-pin-gates.md:92-93` (rewritten in this same commit);
     - `triage/phase3_synthesis/residuals.tsv:4` (R-G1-3, still `blocks-phase3`);
     - `gates.tsv` G1 note;
     - OVERVIEW L68 ("3-14 container accounting (plan 36)").
   - **Fix:** in the Phase 2 close commit:
     - change these to "3-14 container accounted: plan 36 P2, `hop_3_14/container-{au,perth}.json`, 0 unaccounted";
     - mark R-G1-3 `discharged`, mirroring the P1 treatment of R-G1-4 and R-G10-1.

3. **low: the PDMDH check in `container_summary` accepts any byte at entry offset 4/5 of a size-changed block, without checking its value.**
   - **Evidence:** `hop_3_14/container_summary.py` (the `field_offset_in_entry not in (4, 5)` test). In `pdmdh_fields.py`, `max(k for k in oblk if k <= off)` is unbounded by `entry_len`. An offset after the last entry would still map to it.
   - The values are correct today: I verified them above.
   - **Fix:**
     - require `field_offset_in_entry < entry_len == 6`;
     - require `old_byte == (old.size_sectors >> 8*(5-fo)) & 0xFF`, and the same for `new`.

4. **low: the tails and padding totals are gated only through the generic `ok`.**
   - **Evidence:**
     - `region_accounting.py` has no `pmr_tail_oversize` (tail ≥ `ls`) check, the counterpart of `frame_pad_oversize`.
     - `container_summary.py` does not reconcile `pmr_tails.delta` with the size-changed blocks (it does for records).
     - It does not gate `region_tool_sha256` to the fail-closed tool.
     - It omits `frame_pad_oversize` from `nonzero_padding_or_tail`.
   - **Fix:**
     - add `pmr_tail_oversize = sum(len-rec >= ls)` to `scan` and `ok`;
     - in the summary, check `Σ(new.size*ls − new.rec) − Σ(old.size*ls − old.rec) == pmr_tails.delta` over the size-changed blocks;
     - record `frame_pad_oversize`;
     - fail if `tool_sha256` ≠ the committed `region_accounting.py` sha.

5. **low: `container_account` does not tie the summary's cell list to the row.**
   - **Evidence:** `oracle_chain.py` `container_account`. It checks the `changed_cells` count only. The shas match today: `77ff1d86` / `af26b6b4`.
   - **Fix:** require `c['inputs']['cells']['sha256'] == row['authoritative_list']['sha256']`, and add a tamper test.

6. **note: workflow.**
   - The Phase 2 artefacts landed in `b10e787` under the `Workflow-Phase: …:1` trailer.
   - Phase 2 still needs its own close commit, with the `:2` trailer, the review record and fixes 1–2.
   - The full AU region JSON and spans stay uncommitted, but they are sha-pinned and listed in provenance. That is acceptable, and the summary reproduces byte-exact from them.


## Phase 3 (Claude CLI seat, reviewed af0178b, 13:28–13:32 AEST)

Verdict: PASS_WITH_FOLLOWUPS


Reviewed: master `af0178b` (repo `open-pajero-maps-14-completeness`). Read-only; no builds, K1, diff, sections/detail/k1_rows runs.
Tests: `test_hop_3_14_causes.py` + `test_oracle_chain.py` → **56 passed**.

## Independent checks performed
- **Patch composition:** `git show 33006aa:parser/kiwiw/_cenc.c` + `git apply eo_only.patch` + `git apply chord_only.patch` → sha `5c43e00d…` == `git show d35b565:parser/kiwiw/_cenc.c`. The chord patch also applies alone to 33006aa. The run worktrees `open-pajero-maps-36-{eo,chord}-only` are at `33006aa`. Their `_cenc.c` is byte-equal to my patch-applied files (`dba9f5e6…`, `40afa697…`). `_cenc.so` was rebuilt after the source edit (12:44:11 vs 12:42:15). The run-log diff shas (`cdd2146a`, `cdb84c06`) differ from the committed patch shas only by the post-image `index` line.
- **Shas:** the mech.json endpoint, EO-only and chord-only shas equal `output/scratch-36/sha_{E_pre314,E_at314,M_eo,M_chord}{,_perth}.json`. `run_p3_endpoints.log` / `run_p3_mech.log`: every step `rc 0`, then `ALLDONE`. W0 = `33006aa`, W1 = `d35b565`.
- **Cell sets:** `sections-{au,perth}.tsv` keys == `diff-old-eo-*.cells.tsv` == `scratch-31/diff-3-14-*.cells.tsv` (246,123 / 795). `diff-eo-new-*` has 0 rows. The gz rows equal the list.
- **Class recount:** recomputed from the sections TSV plus detail JSON, with all input/gz/raw/tool shas matching the summaries:
  - AU: 246,041 / 75 / 4 / 3, with 0 unattributed;
  - Perth: 792 / 3, with 0 unattributed;
  - detail cells are exactly the non-`background` rows (AU 82, Perth 3).
- **Predicate margins:**
  - Name trades (all three cells hold):

    | cell | Δbg | Δname | larger-name side with the other bg |
    |---|---:|---:|---:|
    | (1739,569) | +102 | −92 | 131,146 |
    | (1892,711) | +916 | −906 | 131,960 |
    | (1974,820) | +202 | −202 | 131,264 |

  - Division: merges leave headroom of 374 / 250 / 48 B. The split's old leaf is 131,052 B.
- **K1:** recomputed from `p3/k1/rows-*.tsv`:
  - band totals equal `k1_311.json`, `k1_live.json` and `k1-perth-{old,new}.json` for every kind;
  - whole Δ equals the in-changed-band Δ;
  - 0 delta bands lack a changed cell (AU 29,790 ⊂ 29,824; Perth 107 = 107).
- **Code read:** `_k1.c` `kw_k1_band`, `_k1_bg.c` (around lines 600–697), `_k1_cmp.c` (around lines 499–535).

## Outcomes
1. **Met.** All four endpoint rebuilds reproduce byte-exact. Beyond the design, the EO-only build (hunks 1–4) equals `4ed9cd80` / `04be2f6e`. That makes hunks 1–4 the whole-disc cause and leaves the chord hunk at 0 bytes.
2. **Met.** One row per cell. Each of the four classes has a stated byte predicate, and the counts are published.
   - Disjointness is structural: each class requires a different `(footprints_equal, sections_changed)` pattern.
   - Attributing background-only cells to "EO" is justified. Everything in hunks 1–4 sits in `bg_shape` and its helpers, and `bg_shape` emits only background records. The per-cell predicate then confirms that only the background sub-frame changed.
   - The predicates are not tautological for the 7 special cells, but they are mode labels resting on the whole-disc counterfactual (F3).
3. **Met.** The 7 AU and 3 Perth cells are byte-predicated: 4 + 3 division-ceiling and 3 name-ceiling, matching the historical census of 4 topology + 3 frame-ceiling. The limits are disclosed under "Not claimed".
4. **Met (row-band empirical, cell-level by code argument).**
   - The code argument is sound for `checked`:
     - range, step and point kinds increment once per decoded item of the leaf's own frame;
     - background, boundary and cover kinds count per leaf vertex or per leaf shape;
     - spool context affects only `failing`;
     - completeness `nreq` is spool/cell-driven, and its Δ is 0.
   - The empirical band is coarse. AU changed bands are 32 cells wide, with a median 16% of band cells changed. Disclosed.
5. **Met in `oracle_chain.{tsv,json}`.** Both 3-14 rows are `measured-identities-causes-attributed`, with `unexplained_count` 0 and no residuals.
   - `causes_account` fails closed on: kind, hop shas, cell count, class sum, list sha, unattributed length, the EO flag and a missing residual.
   - **But** the companion docs that carry the same residual were not updated (F1).

## Findings
1. **medium — stale blocker wording / missing phase surface.**
   - Problem:
     - `docs/OVERVIEW.md:68` still lists "3-14 per-cell payload causes (plan 36 Phase 3)" as a remaining Phase-3 blocker. OVERVIEW is a declared Phase 3 surface.
     - `triage/phase3_synthesis/residuals.tsv` rows R-G1-1 and R-G1-2 (payload causes) and R-G4-2 (checked moves not confined) are not marked discharged. Phases 1 and 2 did mark R-G1-3, R-G1-4 and R-G10-1.
   - Fix:
     - Append "— DISCHARGED by plan 36 Phase 3 (2026-10-06): hop_3_14/summary-{au,perth}.json, unattributed 0" to R-G1-1 and R-G1-2.
     - Append "— confined at row-band level: hop_3_14/k1-confine-{au,perth}.json; cell level by code argument" to R-G4-2.
     - Change the OVERVIEW bullet to "discharged by plan 36 Phase 3". Do not claim plan 04 Phase 3 closed.
2. **medium — BOM gap (CLAUDE.md hard rule).**
   - Problem: `docs/provenance.md` § `output/scratch-36/` has no entries for the Phase 3 material:
     - `E_pre314{,_perth}`, `E_at314{,_perth}`, `M_eo{,_perth}`, `M_chord{,_perth}`;
     - `sha_E_*`, `sha_M_*`;
     - `p3/` (diff-*, sections-*, `k1/rows-*`, `k1-perth-*`, `confine-*`, `full.patch`);
     - `run_p3_*.{sh,log}`, `protected_*_p3*`;
     - the throwaway worktrees `../open-pajero-maps-36-{eo,chord}-only`.
   - Fix: add one bullet per group with sha, origin and reproduction (the commit plus the patch file).
3. **low — division predicate is weakly discriminating.**
   - Problem: `p_division_ceiling` compares Σ background over different topologies. The fine side includes shared-shape duplication and halo, so "coarser side has fewer bg bytes" holds for almost any 4× step, and |Δbg| is inflated by dedup. The predicate bounds plausibility. It does not show the background change crossed the ceiling, and the causal link rests on the whole-disc EO counterfactual.
   - Location: `hop_3_14/cells_causes.py` `p_division_ceiling`.
   - Fix (follow-up, no re-run needed now): add a one-line caveat to the `eo_division_ceiling` predicate text (or to IMPLEMENTATION "Not claimed"). Optionally, a later per-cell encoder probe could log the coarse-frame size under 33006aa vs EO for the 4 cells.
4. **low — overstated guard.**
   - Problem: the docstring and IMPLEMENTATION say the tool "fails if two [predicates] hold". The `if/elif` means `eo_bg_stitch` is never co-tested, so the guard can only fire among the three detail predicates, which are already pattern-exclusive.
   - Fix: reword the claim to "disjoint by section pattern", or evaluate all four predicates unconditionally.
5. **low — doc count error.**
   - Problem: IMPLEMENTATION Phase 3 says detail covers "78 AU". `detail-au.json` has **82** cells (75 + 4 + 3).
   - Fix: change 78 → 82.
6. **low — run ↔ patch linkage.**
   - Problem: mech.json pins the committed patch shas, but the run logged the worktree `git diff` shas (`cdd2146a…`, `cdb84c06…`), which differ by the `index` line. Nothing recorded joins the two.
   - Fix: add `worktree_cenc_sha256` to mech.json for each variant (EO `dba9f5e6…`, chord `40afa697…`, verified here equal to the patch-applied result).
7. **low — causes_account coverage.**
   - Problem: publish does not check the summary's `out.sha256_gz` against the committed gz. A test covers it, but publish does not. Publish also does not check that `classes_by_level` sums to the row's `counts_by_level`.
   - Fix: add both checks in `causes_account`, with tamper tests.
8. **info — whole-report identity.** `k1_311.json` and `k1_live.json` carry `disc: ALLDATA.KWI` and no sha. The disc identity comes from provenance, corroborated by exact total equality with the sha-checked `k1_rows run`. No action.

## Intent and ledger
- **Assumption 2 holds.** Per-cell byte predicates sit on top of the endpoint and EO-only counterfactual, and no rule-order resolution was needed.
- **Assumption 3 holds.** Bounded preads were used under the wrapper.
- **Plan sufficiency:** the design was enough to place every finding. The OVERVIEW and residuals updates were implied by "Surfaces" but not by the outcome text, which is why they were missed.
