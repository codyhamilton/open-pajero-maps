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
