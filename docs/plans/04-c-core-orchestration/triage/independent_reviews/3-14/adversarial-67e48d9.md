# Adversarial Review — Open Pajero Maps PR #2 (unit 3-14, EO bg stitch)

- **PR:** #2 — `Plan 04 Phase 3 unit 3-14: EO-aware background stitch (re-oracle, done with concerns)` (draft)
- **HEAD (PR):** `67e48d92c3e8654b47bdfcc4a6e371036acc8e55`
- **Base:** `master` @ `f3def00be6e387bccd3f4cd18e3841f061861f9a`
- **Local worktree HEAD:** `e276eab513bd9e530aa6092cfd57146acf02e7a3` (rebased equivalent; not an ancestor of PR head)
- **Reviewer seat:** OpenCode `deepseek/deepseek-flash` (adversarial; no Claude, no heavy rebuilds, no flock)
- **Timestamp (Australia/Brisbane):** `2026-10-03 06:38 AEST`

## Verdict

**BOUNCE**

The change is not landable as presented. The author report itself says "done with concerns — NOT land-ready", and independent inspection confirms an unresolved regression (completeness 776 = +37 vs pre-edit 739), an uncommitted/divergent PR head that is not clean-checkout-consistent, and later workspace artifacts that both contradict the report and add a new `>1% BLOCKER`. These are not cosmetic; at least two land-blockers stand. A merge must not occur from this seat or any other until they are resolved.

## Findings

### 1. Completeness regressed to 776 (+37) with no root cause — **HIGH — land-blocker: yes**
`k1_full.json` reports `completeness.failing = 776` (all L0) against the pre-edit baseline `classify_before/partition.txt` `completeness 739`. Delta is exactly `+37`. K1 is already `pass=false` (`failing = 777` = 776 completeness + 1 name_anchor). No artifact links the +37 to the EO stitch or to changed cells; the report says "not root-caused". The coincidence with the change is unproven but uncleared. A seemingly similar 37 appears in `output/scratch-3-11/Gnew.*`, but nothing ties those cells to these failures. This is an unexplained regression coincident with the change, in a run that is already failing. **Land-blocker.**

### 2. PR head is stale/divergent and not clean-checkout-consistent — **HIGH — land-blocker: yes**
PR #2 contains **no golden recaptures** (`git show --stat 67e48d92` shows 6 files, no `parser/tests/fixtures/goldens/**`). Yet the code change re-oracles frames, so a clean checkout fails `test_goldens`/`test_e2` for `l2`, `l0_dense`, `l0_divided_halo`. Those recaptured goldens exist only as **uncommitted working-tree modifications**. The `test_d1_frames.py` capacity accommodation (`cap_hint=1<<20`, +12 lines) needed to pass the full suite is also uncommitted. Local HEAD `e276eab` is not an ancestor of PR head `67e48d9`; the branch is ahead 3 / behind 1 vs `origin/feat/3-14-bg-shape-eo-stitch`. The artifact under review and the branch under review do not agree. **Land-blocker.**

### 3. Working tree rewrites land-readiness to "ready-for-merge" against the evidence — **HIGH — land-blocker: yes**
Uncommitted `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` replaces the committed "Sonnet review NOT obtained … not marked landed" with "`finish_gates.py`: determinism `-j1 == -j4` … golden recapture … committed" and "**Not merged** — ready-for-merge pending only review once gates green." The supporting evidence does not bear this out:
- `pytest_full.log` is **truncated at ~24% with 3 `F` markers and no summary line** (`pytest_full.log` won't serve as a full-suite pass).
- `finish_gates.log` emits two new blockers: `TRIM road: dropped 207/1,083 (19.114%) ** >1% BLOCKER **` and `TRIM background: dropped 227/8,824 (2.573%) ** >1% BLOCKER **`; `full_build.log` level 8 adds `TRIM road: dropped 308/14,012 (2.198%) ** >1% BLOCKER **`. None appear in the report/PR body.
This narrative must not be committed as-is. **Land-blocker.**

### 4. "0 unexplained" is arithmetically clean but rests on speculative inference cells — **MED — land-blocker: no (requires ruling)**
`Au.explanations.tsv` buckets sum exactly to the totals: AU `246116 + 4 + 3 = 246123`; Perth `792 + 3 = 795`; key-join residual 0; `exceptions.json = []`. So no row is silently UNEXPLAINED — the classifier emitted none. However:
- 4 AU + 3 Perth "division topology changed **with background budget**" cells are labelled as budget-contacting, but `explain_cells.py:45` fires on `x.keys() != y.keys()` alone and never measures background; the "with background budget" wording claims proof the code does not perform.
- 3 AU "shared frame ceiling changes trim" cells are **proximity-labelled**, not proven: `explain_cells.py:55` only checks `u >= 130900 or v >= 130900`. All three AU rows show *no trim* (two grew `131044→131054`, one is length-identical `131062→131062`, hash-only). The label is unsupported for 3/3.
- The reason string for background buckets hashes only `sha256(buf[2:36])` plus payload kinds 0 and 2; any payload kind >2 is never hashed and would be silently attributed to "background payload only". Header/road/name are interpretive labels — the classifier parses no road/name field.
Net: "0 unexplained" should be read as "the script emitted no UNEXPLAINED", not "correctness independently established". The 7 AU / 3 Perth inference cells are disclosed (not smuggled), which respects the brief's disclosure rule, but the causation is unproven. CHM/Design ruling needed.

### 5. AU and Perth differing-cell lists are not disjoint — **MED — land-blocker: no**
The 3 Perth topology cells `0/828/862`, `0/827/869`, `0/832/856` are byte-identical (same old/new sizes and SHA256) to rows in `AU.differing_cells.tsv`. The same frames are counted as differing in both regions independently. This inflates the apparent distinct-cell population and undermines the "full set of differing cells, each attributed" framing. Data-hygiene defect, not a safety defect.

### 6. EO stitch edge cases: no HIGH memory-safety defect; several MED/LOW residuals — **MED — land-blocker: no**
Adversarial read of `parser/kiwiw/_cenc.c` HEAD:
- Safe (verified): zero/short fragments (`eo_left` guards `length`; `g_es` excludes degenerate segments); touching/coincident edges (modulo-2 cancellation; `(v,v)` cuts dropped); hole-vs-separate-ring is a deliberate OR-of-per-ring contract (brief line 21) and `eo_pip` is orientation-independent within a ring; winding normalized to CCW (`:925-930`); frame clips inclusive with zero-direction guards; buffer sizing (`g_es` grows to `n+4`, at most `n`+4 written; `ne` nowhere near int64 overflow); ownership/leaks clean (`cuts` freed on all paths; `grow` preserves buffer on failure); no NDEBUG-dependent asserts.
- **LOW — unguarded progress invariant:** `eo_connect`'s `for(;;)` (`:751`) has no iteration counter. It terminates (each path strictly reduces component count), but the invariant is subtle; a future edit could hang. Add a cap/assert.
- **LOW — perf regression on ordinary rings:** a whole-ring O(n²) repeated-vertex scan (`:810-813`) is added to *every* fully-inside ordinary polygon, plus worst-case O(n²) pair loops and `eo_vertex` linear scans. Build-stall/DoS vector on pathological input.
- **LOW — portability:** new `M_PI` use (`:883`) without `#define _GNU_SOURCE`; compiles under the project's default flags but fails a strict-ISO build. Sibling units define `_GNU_SOURCE`.
- **LOW — isinf not checked:** `bg_shape` checks `isnan` (`:915`) but not `isinf`; upstream `dlon==0` can produce `±inf`, making qsort comparators non-transitive (UB). Predates the change but the new qsort widens exposure.

### 7. Test coverage gaps; "stress proof" is scratch-only — **MED — land-blocker: no**
`test_bg_eo_stitch.py` has 32 parametrized cases (verified). Covered: even-odd parity, OR-not-XOR, ordinary-ring byte hashes, subrect/room retry, 100 seeded rings, short-fragment side classification. **Not covered:** integer overflow / capacity-boundary / large-input; non-termination (no timeout/watchdog); empty/degenerate fragment (`n<3`, all-zero-length); touching-ring contact cusp (the `distance > 1` filter at `:109` excludes the contact vertex); seeded test is only 100 rings / 80 pts, not stress. The claimed 1,000-ring / 99,717-query `review_stress` proof lives only in gitignored `output/scratch-3-14/review_stress.py`, is not committed, and is not invoked by the suite; its only retained log is a *stale failure* at ring 20.

### 8. Classify CLI abort — caveat is NOT material — **LOW — land-blocker: no**
The `k1_triage.py:76` `_memmap` `ValueError` fires in `cmd_classify` on a zero-row `background` dump, i.e. **after** the K1 run completed (`k1_full.log`: `K1_FULL_DONE`; background-family checkers actually executed: 176,386,506 / 64,111,046 / 1,590,566 checked). It cannot truncate or falsify S02–S05 = 0; it only suppresses an attribution table for an empty residual. S02–S05 = 0 is corroborated both globally (`k1_full.json`) and locally (nine windows all-zero in `windows.json`/`windows.log`), not solely by empty dumps. Reproducibility gap: the current committed `k1_triage.py` has no `_memmap` at line 76 (traceback matches the `k1_triage_memmap.py` fixture), so the cited abort is not reproducible from the tree.

### 9. name_anchor residual (1) is pre-existing — **LOW — land-blocker: no**
`classify_before/partition.txt` (pre-edit) already shows `name_anchor 1`, and `cause_counts.tsv` records `O03 spool name_anchor 0 1 1` for cell `[0,541]`. The new failure is the same cell, `lon 90.0`, reason "no spool record within half a raw unit". Non-regressing; not caused by this unit.

### 10. finish_gates determinism deviation undisclosed — **LOW — land-blocker: no**
Brief step 5 requires `-j1 == -j12`; the executed `determinism.json` is `-j1 == -j4` (equal hashes `c4965442…`), with `finish_gates.py` noting a "hard four-worker cap, overriding brief's j12". Deviation is not disclosed in report/PR. Determinism at `-j4` passes; the brief's `-j12` case is unproven.

### 11. Fixture parity after rebase HOLDS — **LOW — land-blocker: no**
`simple_sha256.json` records sha256 of E2 Map Frames for the 6 SIMPLE rings. `git diff 8b9a65e f3def00` touches only Plan-05 tooling (`dump_io.py`, `dump_join.py`, `k1_triage.py`, tests) — nothing the hash depends on (`_cenc.c`, cenc/descriptor/mesh/coordconv/model, harness). The 6 `test_ordinary_ring_bytes` assertions pass at runtime. So parity is base-invariant and holds. Caveat: the `8b9a65e` provenance claim in `docs/provenance.md` is an author attestation — the fixture is first committed at `67e48d9`/`e276eab`, not `8b9a65e`, so VCS cannot prove capture-at-`8b9a65e`.

### 12. Report status is stale and understates blockers — **MED — land-blocker: no**
The report (and PR body) says `finish_gates` and full pytest were "not run" and `goldens_changes.json` "is absent". Later artifacts contradict this: `determinism.json`, `goldens_changes.json`, `finish_gates.log`, `pytest_full.log` all exist. Those artifacts introduce the new `>1% TRIM BLOCKER` and show a truncated, failing full-suite run. Report wording is honest about "not land-ready" but is now factually stale.

## Explicit rulings

- **"0 unexplained":** Holds only in the narrow sense that the classifier emitted no `UNEXPLAINED` row (bucket sums == totals; residual join 0). It is **not** independent proof: 7 AU / 3 Perth cells are inference-only, the "ceiling" label is unsupported for 3/3 AU rows (none shows a trim), and the "with background budget" topology branch never measures budget. Treat as "no row tagged UNEXPLAINED", not "each attributed by proof".
- **Completeness +37:** Real, unexplained, and a **land-blocker**. Requires root-cause or an explicit Design/CHM ruling that it is unrelated residual.
- **Classify abort caveat:** **Not material** to S02–S05 = 0 (occurs post-K1 on a zero-row dump).
- **EO edge-case residual risk:** No HIGH memory-safety/crash risk found. Residual LOW/MED (unguarded `eo_connect` invariant, O(n²) ordinary-ring cost, `M_PI`/`_GNU_SOURCE`, `isinf` qsort). Not land-blocking on their own.
- **Design call on completeness +37 before merge:** **YES, required.** An unexplained +37 regression must be ruled on by Design/CHM before this can be considered for merge.

## Recommended next actions for Maps Execute

1. Root-cause completeness +37, or obtain an explicit Design/CHM ruling that it is unrelated residual; do not silently absorb it.
2. Commit the golden recaptures (`l2`, `l0_dense`, `l0_divided_halo`, `l0_divided_trim_halo`) and the `test_d1_frames.py` capacity accommodation to the PR branch, or revert the re-oracle. Ensure PR head is a rebase of the actual reviewed tree.
3. Do **not** commit the working-tree `IMPLEMENTATION.md` "ready-for-merge" wording as-is; reconcile it with the real gate results.
4. Resolve/justify the two new `>1% TRIM BLOCKER` lines (road 19.114% / background 2.573%) and the level-8 road 2.198% line.
5. Complete a full `parser/tests` run to a summary line (current log truncates at 24% with failures) and run `finish_gates` determinism at the brief-mandated `-j1 == -j12` (or get the `-j4` cap ratified).
6. Have CHM/Design rule on the 7 AU / 3 Perth inference cells; relabel or prove the "ceiling"/"background budget" causation, and de-duplicate the AU/Perth cell lists.
7. Consider adding tests for large/overflow input and non-termination, and committing the stress harness rather than leaving it in scratch.

_No merge performed; no push; no disc regeneration; no lock taken. Review is read-only against existing evidence._
