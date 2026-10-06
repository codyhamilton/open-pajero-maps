# Implementation — 36 3-14 cause and container attribution, AU 3-11 routed proof

- Tool: the orchestrator is the Execute background worker. Unit workers would
  be Codex `gpt-6.1-sol`, but Codex is weekly-limited until 2026-10-10
  11:50 AEST, so Execute does the units and discloses it here and in each
  report.
- DESIGN landed at `233d09e`. Oracle in force: `4e6b0de7…`, unchanged by
  this plan.
- Scratch: `output/scratch-36/`. New discs are written only under that
  directory.
- Protected discs and the spool are hashed before and after each heavy
  chain by the plan-34 `snapshot` gate.
- Every heavy step runs under `run_heavy_python.py` + `output/.heavy.lock`.
  Encode is at most `-j4` and K1 at most `-j6`.
- Refine is skipped for all phases (DESIGN).

## Phase 1 — Region tool, 3-11 replay, routed proof

### 3-11 predecessor replay (Execute, guarded)

- Throwaway detached worktree
  `/home/codyh/workspace/open-pajero-maps-36-pre311` at `b7c7c42`, the
  parent of 3-11 code `9269ebb`.
- Chain: `output/scratch-36/run_p1_replay.{sh,log}`.
- Command: the same recipe as the 3-11 G build
  (`output/scratch-3-11/G_build.log`:
  `build_alldata.py --spool output/extract_timing/spool --out … -j 12`),
  run at `-j 4`.
- Pin gate: `87a01b14…`, 1,731,021,568 B. A mismatch is recorded as
  `replay-mismatch` and never re-pinned.
- **Result: PASS.**
  - `output/scratch-36/G_pre311/ALLDATA.KWI` has sha256 `87a01b14…`, size
    1,731,021,568 B (`sha_pre311.json`).
  - Encode wall 26 s (12:15:43–12:16:09 AEST).
  - Protected snapshot before and after: equal.
  - No `replay-mismatch`.

### Region-accounting tool (Execute)
- **Tool:** `docs/plans/04-c-core-orchestration/triage/oracle_chain/region_accounting.py`
  (`account --old --new --old-sha --new-sha --out [--spans]`).
- **Partition.** Each file is split into these named regions:
  - the fixed data_volume / MHT sectors and the MHT inline (leaf 29);
  - every unique Map Frame;
  - frame payload, read from the two-byte extent marker ×2;
  - frame allocation padding;
  - PMR records and tails;
  - PDMDH records, BMT arrays, record tail and sector pad.

  The partition must be complete and disjoint: Σ = file size, with 0 gaps
  and 0 overlaps.
- **Comparison is by index path,** never by offset:
  - frames and PMR buffers are matched by structure key;
  - PMR leaf DSA/BS fields are masked;
  - PDMDH bytes are compared outside the BMT address fields.
- **Fail-closed checks.** It refuses an existing output, checks both shas
  first, uses bounded preads, and exits 2 on an incomplete partition,
  unaccounted bytes or a bad extent.
- **Tests:** `parser/tests/test_region_accounting.py`, 6 synthetic tests
  passed:
  - key round-trip;
  - partition gap/overlap detection;
  - identical discs fully accounted;
  - grown frame named as payload + padding (parametrised ×2);
  - sha mismatch refused.

  Output-reuse refusal is in code, not covered by a dedicated test.
- **Deviation (surfaces):** no `parser/perf_inventory.json` entry.
  - That inventory classifies only modules under `parser/`
    (`test_perf_inventory.py`), and it lists no triage tool, including the
    sibling `oracle_chain.py`.
  - The tool lives in the DESIGN-owned triage directory.

### 3-11 multiset diff, routed proof, region accounting (guarded)
- **Chains:** `output/scratch-36/run_p1_routed.{sh,log}` (12:19–12:26 AEST)
  and `run_p1_region.{sh,log}` (12:26–12:28 AEST).
  - Every step ran under `run_heavy_python.py` + lock, with a protected
    snapshot before and after; all equal.
  - The first routed attempt (`run_p1_routed.attempt1.log`) refused a
    pre-existing work dir. The re-run used a fresh path; no output was
    reused.
- **Multiset diff** `87a01b14 → 013586b5` (`diff-3-11-au.json`, 140 s):
  - 37 changed L0 cells, 0 added, 0 removed;
  - frames 3,954,156 each side;
  - the cell list (sha `f03ebaab…`) equals the retained
    `Gnew.diff_cells.txt` (`9f2b0e55…`).
- **Routed diff** (`routed-3-11-au.json`, 225 s):
  - `routed_only_count` 0, `baseline_cells_missing_from_routed` 0,
    `routed_changed_total` 37;
  - `multiset_list_complete_under_routing` true;
  - frame-length fallbacks 0/0.
  - **Plan 31 F1 is discharged.**
- **Region accounting** (`region-3-11-au.json`, 62 s, max RSS 2.0 GiB):
  - **Totals:**
    - `complete_and_accounted` true, partition complete on both sides
      (3,956,302 regions, 0 gaps, 0 overlaps);
    - **unaccounted 0**;
    - file +224 = frame payload **+164** + frame padding **+60**
      (21,570,746 → 21,570,806).
  - **Frames:**
    - 41 frames changed payload; 7 changed allocation; 2,763,363 relocated;
    - frame padding nonzero bytes 0/0;
    - alias pattern equal.
  - **Other regions:**
    - PMR: 0 content differences after masking; 1,548 buffers relocated;
    - PDMDH: 1,695 differing bytes, all in BMT address fields;
    - data_volume, MHT and inline 29 equal.
  - **The 41 padding spans** (`region-3-11-au.spans.tsv`) equal plan 07's
    table (`docs/design/g-new-nonpayload-accounting.md`) on every row:
    - same old/new offset, old/new bytes and delta, with the same index-path
      label;
    - 34 × (−4) + 7 × (+28) = +60.
  - **Payload basis:** plan 07 quotes the manifest payload metric
    (1,597,341,290 → 1,597,341,454). The tool sums unique frame extents
    (1,684,874,982 → 1,684,875,146). Both bases give the same delta, +164.
    The absolute figures differ by definition, not by an unaccounted byte.

### Publication and wording
- **`oracle_chain.py publish`** gains `--routed-3-11` / `--region-3-11`.
  It validates the committed witness copies:
  - pins and protected flags;
  - 0 routed-only / 0 missing;
  - baseline list equal to the retained 37;
  - shas of the sibling cell lists;
  - region: complete, 0 unaccounted, +164, the padding pair, and deltas
    `[-4]×34 + [28]×7`.

  It then sets the 3-11 row to `replay-routed-verified`, drops the two stale
  residuals (no pre-3-11 disc; +60 B unattributed) and adds `replay_3_11`.
- **Evidence copies** in `triage/oracle_chain/evidence/`:
  - `{routed,diff,region}-3-11-au.*`;
  - `sha_pre311.json`;
  - `protected_{before,after}_3-11.json`.
- **Republish:**
  - Before the change, the publish command (`--au-diff`/`--perth-diff`
    from `output/scratch-31`, `--census output/scratch-31/census-3-11.json`)
    reproduced the committed `oracle_chain.{tsv,json}` except for one field:
    the plan 29 record sha (`ca1278f8…` → `7fb15a4d…`), from plan 37's
    legitimate R4 pointer edit.
  - Republishing refreshes that field.
- **Tests:** `parser/tests/test_oracle_chain.py` adds the committed-witness
  accept test and 5 tamper rejects. Oracle-chain, region, pin-contract and
  successor tests: 64 passed.
- **Wording.** The "+60 B unattributed" / "3-11 routed unproven" text is
  replaced by citations to plan 07 and this reproduction in:
  - the oracle-chain contract § Carried follow-ups;
  - the plan 31 record follow-ups (plus a post-close note);
  - the OVERVIEW blocker bullet.

  `residuals.tsv` R-G1-4 and R-G10-1 are marked `discharged`, leaving 13
  `blocks-phase3` rows.
- **Provenance:** a `docs/provenance.md` § `output/scratch-36/` entry.

### Phase 1 review and remediation
Review: an independent Claude CLI clean-context seat (disclosed; Codex is
weekly-limited), on `0cb872e`. Full text: `REVIEW.md` § Phase 1.

- **Verdict: PASS_WITH_FOLLOWUPS.** All five Phase 1 outcomes were met.
  The reviewer re-checked the 41 plan-07 rows itself (41/41) and the 37-cell
  links.
- **F1 (medium): padding fail-closed.**
  - `region_accounting.py` now refuses (exit 2) when any of these is
    nonzero on either side:
    - frame padding;
    - PMR tail bytes;
    - frame padding of at least one logical sector (`frame_pad_oversize`).
  - All three pairs were re-run with the stricter tool (sha `183d0ee0…`):
    - chain `output/scratch-36/run_r2_region.{sh,log}`, 12:37–12:39 AEST,
      guarded;
    - protected snapshots before and after equal;
    - outputs in `output/scratch-36/r2/`.
  - All three are `complete_and_accounted`, with 0/0/0/0 for nonzero
    padding, nonzero tails, oversize and bad extents on both sides.
  - The spans files are byte-identical to the first runs.
  - The committed evidence is refreshed from `r2/`.
- **F2 (low): account-level tests added.**
  - A trailing 32-byte gap gives rc 2 and `gap_bytes` 32.
  - One nonzero padding byte gives rc 2.
  - An existing output is refused.
  - The relocation path is asserted when an allocation grows.
  - Region tests: 9 passed.
- **F3 (low): `replay_3_11` now checks the rows themselves.**
  - It compares the 41 spans row by row with the plan 07 ledger, parsed from
    `docs/design/g-new-nonpayload-accounting.md`, and with the committed
    spans TSV.
  - It reads `sha_pre311.json` and requires `87a01b14…`.
  - It sha-pins the spans TSV, the disc witness and the ledger in
    `supporting_evidence`.
  - New tamper tests: offset change and disc-witness change.
- **F4 (low): wording.**
  - Plan 31's Residual Risks line now names the 3-14 container scope only
    (+60 B: attributed by plan 07, reproduced here).
  - `phase3_synthesis/gates.tsv` G1/G10 carry post-close discharge notes.
- **F5 (low):**
  - The inline compare now iterates the union of inline indexes.
  - No pair has a trailing whole-file pad: every partition is complete, so
    no `trailing_pad` region was added.

## Phase 2 — 3-14 container/index/padding accounted

### Runs
- `output/scratch-36/run_p2_region.{sh,log}`, 12:32–12:33 AEST, with the
  first tool; then `run_r2_region` with the fail-closed tool.
- Both were guarded, with protected snapshots equal.
- PDMDH field classification: `hop_3_14/pdmdh_fields.py`, small preads,
  guarded (`runs/p2_pdmdh_fields.json`).
- `hop_3_14/container_summary.py` (no disc reads) validates each hop and
  writes `hop_3_14/container-{au,perth}.json`. It checks that:
  - every byte delta is named by region and unaccounted is 0;
  - payload delta = Σ per-cell frame deltas over plan 31's changed-cell list;
  - every PDMDH byte outside BMT address fields is a BMT size field of a
    size-changed PMR block;
  - PMR content changes and leaf-topology changes are confined to those
    blocks;
  - the PMR record delta is explained by those blocks.

### AU `013586b5 → 4ed9cd80` (file −38,916,640 B)
- **Partition:** complete both sides, unaccounted 0.
- **Named deltas:**
  - frame payload **−38,913,410**;
  - frame padding −3,198;
  - PMR records −12;
  - PMR tails −20;
  - every other region 0 (data volume, MHT, inline 29, all PDMDH
    sub-regions).
- **Payload vs cells:** Σ per-cell frame deltas over the 246,123 changed
  cells = −38,913,410 (**equal**).
- **Frames:**
  - 3,954,156 → 3,954,159; 247,961 payload changed; 230,608 allocations
    changed; 3,665,474 relocated;
  - alias pattern equal; nonzero padding / tail / oversize 0.
- **Leaf topology:** 12 only-old / 15 only-new frames.
  - `L0 23/16: 1285`, `L0 51/9: 988` and `L0 51/9: 1211` each go from 4
    children to 1 undivided leaf.
  - `L0 51/10: 768` gains children `/4…/15`.
- **PMR:** 3 buffers changed size and masked content, exactly `L0 23/16`,
  `L0 51/9` and `L0 51/10`:
  - record bytes 12,348→12,320, 13,612→13,556 and 12,616→12,688
    (Σ −12 = PMR record delta);
  - sectors 386→385, 426→424 and 395→397.
- **PDMDH:** 5,946 differing bytes.
  - 5,943 are in BMT address fields.
  - 3 are in BMT size fields, the low byte (entry offset 5) of those three
    blocks' entries.

### Perth `da13a775 → 04be2f6e` (file −160,992 B)
- **Partition:** complete, unaccounted 0.
- **Named deltas:**
  - frame payload **−161,380**;
  - frame padding +388;
  - PMR records +16;
  - PMR tails −16;
  - others 0.
- **Payload vs cells:** Σ per-cell deltas over the 795 changed cells =
  −161,380 (**equal**).
- **Frames:** 1,943 → 1,949. Topology: 8 only-old / 14 only-new (the same
  51/9 merges and 51/10:768 split as AU).
- **PMR:** 2 blocks (`L0 51/9`, `L0 51/10`).
- **PDMDH:** 20 differing bytes; 18 address bytes and 2 BMT size bytes of
  those blocks.

### Publication
- **`oracle_chain.py publish --container-3-14-au/--container-3-14-perth`**
  validates each summary:
  - `pass` true, with the hop pins;
  - unaccounted 0;
  - payload equals the cell sum;
  - changed-cell count equals the row's count.

  It drops the 3-14 residual "Container/index/padding relocation is outside
  this cell-identity measurement" and adds `container_account`.
- **Remaining 3-14 residual:** payload causes (Phase 3).
- **Committed:**
  - `hop_3_14/{container_summary.py, pdmdh_fields.py, pdmdh-fields-3-14.json,
    container-au.json, container-perth.json, region-3-14-perth.spans.tsv}`.
  - Not committed: the full AU region JSON (57 MB) and spans TSV (14.5 MB).
    They stay in `output/scratch-36/r2/`, sha-pinned in
    `container-au.json` → `inputs`.
- **Tests:** container_account accept (AU, Perth) and 4 tamper rejects;
  container_summary synthetic pass and payload-mismatch fail. Oracle /
  region / pin / successor tests: 77 passed.
