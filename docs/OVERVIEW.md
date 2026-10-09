# Open Pajero Maps

## Goal

One DVD-R that a Mitsubishi Pajero MMCS head unit accepts as a navigation disc, with map,
routing, POI and address-search content generated entirely from an OpenStreetMap extract of
all of Australia, at parity with the manufacturer's 2007 WhereIS disc. The manufacturer no
longer publishes updates for this hardware. The vehicle is in Queensland.

The owner's own reference disc (R) is used only to learn the on-disc format and as the
offline oracle. It is not redistributed.

## The format

The disc is **KIWI-W**, a Japanese consortium format (Denso/Aisin/Toyota era). `.KWI` is
not a Kenwood extension. `SPEC.KWI` names Australia format/data version 2.64. It is a UDF
disc of about 2.4 GB: `ALLDATA.KWI` (map frames, about 1.5 GB), `IDX/` (99 search index
files, about 800 MB), `LOADING.KWI` (loader), `METADATA.KWI`, `HWMAP.KWI`, `INDEXDAT.KWI`
and small copy-through resources. Everything we know about the structure, and how sure we
are of each fact, is in `docs/schema/`.

## How we work

- **Offline oracle.** In-vehicle testing is last-mile only. Every evaluation before the
  final burn is byte-level and structural comparison of the generated disc (G) against R,
  using this project's parser (`parser/compare_disc.py`, `parser/harness/`).
- **No partial deliverable.** The first burn is full Australia, all seven map levels, all
  features. Regional subsets (Perth, region 178, a 2×2 grid) are development fixtures only.
- **Full regeneration.** Nothing that references link IDs, coordinates or place content is
  copied from R. Only content-independent resources (firmware, voice, UI graphics) are.
- **Natural deviations only.** A difference between G and R is acceptable only if it is
  derived from the source data. Differences caused by our processing are defects, and every
  accepted deviation is recorded and tested, never left undocumented.
- **The schema is what we build to.** `docs/schema/` always holds our best-known
  understanding, with each fact marked verified / observed / spec-only / assumed / unknown.
  A change that learns a format fact updates the schema in the same commit.

## Where things stand

| Package | Scope | State |
|---|---|---|
| WP1 | Map layer (`ALLDATA.KWI`) and the evaluation harness | Build and harness exist (plans 01–02); map parity is unfinished. Plan **04** C-core Phases 1–2 are closed; Phase 3 is not closed: plan **35**'s synthesis (residual branch) lists the blocking residuals after 3-14–3-17 landed. Phases 4–6 depend on that close. Plan **03** content phases remain frozen until 04 Phase 6. Heavy-job memory (05), padding attribution (07), classify fixes (08–09), the carried assembly-loader error (10), recorded triage summary determinism failures (11), carried density wording (12), the recorded fixture way precheck (13), SADSR SRMX STFG (15), and K1 determinism `wall_s` strip (16) are finished; records are under `docs/plans/`. Plan **14** completeness root-cause closed out at `3fb5a35`; record: `docs/plans/14-completeness-root-cause.md`. Plan **29** fixed the K1 name_anchor failure (verdict A: the original disc lacks the out-of-span O03 name). Its assembly drop guard produced successor `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae` (`output/scratch-29/G_new`), whose diff from `4ed9cd80…` is confined to the L0 (0,541) frame. Record: `docs/plans/29-k1-name-anchor-failure.md`. [Plan **34**](plans/34-l0-empty-slot-frame-parity.md) removed the remaining L0 empty-slot frames with a general outside-mask empty-shell rule and produced historical successor `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` (`output/scratch-34/G_new`; [oracle record](plans/04-c-core-orchestration/triage/l0_empty_slot/successor_oracle_4e6b0de7.json)). Its classified diff vs `2ee3456a…` removes 5 L0 outside-mask empty shells ((0,141), (0,176), (0,541), (0,562), (0,563)), all `empty_slot` on R. Plan **48** ([record](plans/48-eo-face-walk-decline.md)) then promoted the **oracle disc in force** to `88bd7852115988fc60441109bf44707c3156321fab47057443e0794b987f3b43` (`output/scratch-48/G_new`; [oracle record](plans/04-c-core-orchestration/triage/independent_reviews/3-14/conditions/eo_decline/p3_fix/successor_oracle_88bd7852.json)) after R-DVD no-worse on two L0 cells (then in force). Plan **50** ([record](plans/50-supply-path-successor-implement.md)) promoted successor `aeae426cc62b183a9f041418a0a9980ba596ef43cc9123e0c4ef30dbfb591221` (341 supply-path rows; 341 changed / 0 added / 0 removed vs `88bd7852…`). Plan **53** ([record](plans/53-l0-degenerate-east-edge-roads.md)) fixed the encoder `dv_assign` lon-wrap and promoted the **oracle disc in force** to `0c22b266e7b406bb0cabeee814c9f0cfeebebad6071e131252357f1d3e1aa25a` (565 changed / 0 added / 0 removed vs `aeae426c…`); Perth in force is `5b86d33ed5976e7bd4208fb46c4fdde14747c7f31d1d40d819e9e9b2bf5f00d9` (was `04be2f6e…`). `aeae426c…`, `88bd7852…`, `04be2f6e…`, `4e6b0de7…`, `2ee3456a…`, and `4ed9cd80…` are historical and kept protected. |
| WP2 | Route planning frames and ext frames | Not started; first-pass writer exists |
| WP3 | Address and POI search | Not started (plan 26: offline seven-state search fixtures/tests only — ≠ WP3 complete ≠ Australia-wide MMCS proof) |
| WP4 | Remaining `IDX/` families, `HWMAP`, `INDEXDAT` | Not started; bodies undecoded |
| WP5 | Disc stamp, coverage, image authoring, burn | Not started |

Full map-layer build is about **12.2 s** median at `-j 12` (3C close / plan 04 evidence; earlier plan-02 ~32 s is historical). At the `-j4` encode cap the full-AU build is **37.38 s** median after plan **41**'s two byte-identical fixes (it was 113 s; pre-regression 20.27 s). Every second of the 17.10 s gap is assigned to named causes (3-14 EO stitch about 16.1 s, plan 29 name guard about 0.9 s). The budget basis (`-j4` vs `-j12`) is open with Cody ([record](plans/41-encoder-build-close-gates.md)). Heavy K1/triage jobs use `flock output/.heavy.lock` and are not that wall.

The latest 3-90 record at `5c5823e4c267dd64bc986038caddb3ed4b745f60` reported repeated PSS failure, a
determinism comparison that retained varying `wall_s`, native dumps missing
classification joins, truncated historical pins, unresolved 3-11 versus 3-14
oracle evidence, and an incomplete independent-review chain. Plan **16** closed
the timing-only `wall_s` strip defect (strip now matches Phase 2
`COMPARE_EXCLUDES`: `timing` + `wall_s`); that strip is not a live blocker.
Plan **27** independently reviewed the plan-16 / check-3 strip (PASS) and expanded in-scope truncated oracle pins / the OVERVIEW short SHA to full digests (`docs/plans/27-independent-fix-review-truncated-pins.md`); `pinned_candidates.tsv` remains a brief-required 100-row candidate view (`TRUNCATED=yes`) whose exhaustive group identity is **unverifiable from git** (full enumerations are non-committed scratch) — see that plan's pin ledger. Plan **20** reframes the live PSS item as a **contract mismatch**: the signed
ceiling **9,726,501 kB** is the historical `-j 12` peak, while ops and the
3-90 gate must use ≤ `-j 6` — not an unexplained memory blow-up. The PSS bar is **cleared** under plan **35** at ≤ `-j 6` on
`4e6b0de7…`: the median of three is 79.661 s and the PSS max is 7,599,962 kB,
within the held ceiling. `-j 1` is deterministic, and the AU rebuild and Perth
reproduce their pins.

Plan 35's close synthesis (`docs/plans/04-c-core-orchestration/triage/phase3_synthesis/gates.tsv`)
ends on the **residual branch**: plan 04 Phase 3 is **not closed**. Live ownership of the
remaining rows is in
[`residuals.tsv`](plans/04-c-core-orchestration/triage/phase3_synthesis/residuals.tsv)
(post–plans 36–53 / 44–45 / 48–49 / 55; docs syncs plan **54**, refreshed by plan **60** on
2026-10-08). Do **not** read undifferentiated "G1 / G4 / G5 / G8 / G9 still open" — name the
child rows and their owners.

**Discharged gate bands (not live blockers):** all **G1** and **G4** rows (plans **36** /
**39**); parent R-G5-3 / R-G5-4 / R-G9-1 / R-G9-3 / R-G8-5 / R-G10-1 and the plan **40**
review-of-record parents; plan **43** light set; plan **47** completeness evidence set;
plan **48** discharged **R-G8-1-d-a**; plan **49** discharged **R-G8-2-f-a**; plan **55**
discharged **R-G8-1-b-a** (explained-dual-basis); plan **50** discharged **R-G9-2** (341/341
overlay; successor `aeae426c…`); plan **45** discharged **R-G8-1-f** (determinism
regenerated); plan **53** discharged **R-G9-3-d** (encoder lon-wrap fix; successor
`0c22b266…`, the live oracle; Perth `5b86d33e…`). Plan **46** discharged **R-G8-4-c** (8,876 identities committed)
and the proven part of R-G5-1 / R-G5-2 (4,214 rows build:eo_bg_stitch).

**Live `blocks-phase3` ownership** (rows still open in `residuals.tsv`):

| Owner | Rows | Status |
| --- | --- | --- |
| Design (plan **62** children) → Design drafts **63** (R-G5-4-a-1) / **64** (R-G5-4-a-2, R-G5-4-b-1) | R-G5-4-a-1 (222 producer_ambiguous), R-G5-4-a-2 (32 source-removed), R-G5-4-b-1 (545 source-removed) | Plan 62 re-decided the plan-44/45 R01 residual under the plan-46 producer: parents R-G5-4-a/b/c discharged (6,597 more rows proven-fixed, RC-attributed); these exact children remain; no waiver |
| Design (plan **46** children) → Design drafts **63** (R-G5-1-a, R-G5-2-a) / **64** (R-G5-1-b) | R-G5-1-a (4,594 producer_ambiguous), R-G5-1-b (50 source-removed), R-G5-2-a (18 producer_ambiguous) | Exact named children from plan 46's per-row decisions; no waiver |
| Cody via Design (no waiver) | R-G8-1-a | Budget basis (with R-G9-4) |

**`maps-parity-carried` ownership** (not Phase 3 product-close blockers — but **carried is
not closed for parity**: each row is a named deviation from the original DVD that still
stands against end-to-end parity until fixed or proven non-deviation):

| Owner | Rows | State |
| --- | --- | --- |
| Plan **51** (closed) → Cody | R-G9-3-a | Emission proven-cause (land-local catch-all); road volume open on Cody F6 / kind-order |
| Plan **52** (closed) → Design | R-G9-3-b | Fragmentation proven-cause; piece-count residual open |
| Plan **52** (closed) → Cody | R-G9-3-c | Under-selection proven-cause (L8 motorway-only); volume open on Cody L8 selection expand |
| Plan **53** (closed) → Design | R-G9-3-d-rem | 128 remaining parent-edge coincident links; mechanism TBD |
| Cody via Design (no waiver) | R-G5-5, R-G9-4 | Held |

Cody-open product questions (no waiver, no drafts here): F6 catch-all / kind-order (plan
**51**), L8 selection expand (plan **52**), and the R-G8-1-a / R-G9-4 / R-G5-5 holds.

Plan **39** proved 825,634 R01 rows fixed by the 3-14 build change (`build:eo_bg_stitch`);
plan **42** discharged parent R-G9-3 with the named children above. Memory-band plans
**56–59** are closed ops residency work — they are **not** residual-row owners. Plan **62** (closed)
re-decided the R01 residual (R-G5-4-a/b/c) under the plan-46 producer; R-G5-4-c is no longer
carried. Plan **61** (full-product RSS unknowns) exists only as a box draft; it is not landed.

No later phase is released below; the signed phase outcome remains in plan 04.

Already settled:

- **Oracle chain:** plan **31**
  (`docs/plans/04-c-core-orchestration/triage/oracle_chain/oracle_chain.tsv`),
  plus plan **34**'s successor record. AU 3-11's +60 B non-payload growth is
  attributed by plan **07** to Map Frame allocation padding,
  34×(−4)+7×(+28).
- **Pin contract:** ∅ = ∅ (`pin_contract.tsv`, re-applied on then-oracle `4e6b0de7…` by
  plan 35; live oracle is now `0c22b266…` per plan 53, over `aeae426c…` (plan 50) over `88bd7852…` (plan 48)). Historical `pinned_candidates.tsv` is
  residual-not-required-for-live-close.
- **Other-kind classify joins:** discharged under
  [plan **32**](plans/32-other-kind-classify-joins.md).
- **Completeness joins:** plan **28** (776 rows, 0 conflict-open).
- **O04 seven:** plan **33** (proven-non-deviation).
- **2-01 source-data parity:** plan **30**, closed
  (`docs/plans/30-2-01-source-data-parity.md`; disposition
  `docs/plans/04-c-core-orchestration/triage/source_parity/disposition.tsv`):
  341 supply-path and 0 unfixable-proven. The 341 were implemented by plan **50**
  (overlay assembler; R-G9-2 discharged; successor `aeae426c…`).
  - The one carried residual, dump_row 246, is closed by plan **38**
    (`docs/plans/38-row-246-type-321-clip-inclusion.md`) as a **proven
    cause, H3-other-feature**.
  - The clip-inclusion hypothesis is rejected. R's record is a 28-vertex
    interior park ring that the pinned OSM extract does not contain, a
    source-data difference.
  - `disposition.tsv` carries an append-only correction row.
  - The 341 rows were Maps parity carried (never Phase 3 blockers) until plan **50**
    discharged them (R-G9-2, 2026-10-08).
- **Plan-16 strip review:** closed by plan **27**.
- **Plan 25 CHM heavy hold:** cleared on 2026-10-06. Heavy work runs only
  under `flock output/.heavy.lock` + `run_heavy_python.py`.

No later phase is released. The signed phase outcome and
detailed evidence remain in plan 04. The repo contains no plan 06 design: the
earlier CI-gate draft is not a work unit on master.
WP2–WP5 labels below are program scope, not executable briefs.

The offline oracle (`parser/compare_disc.py`) defaults to `layers_present=["map"]`. Green exit under that map-only scope is **not** full-disc parity: WP2–WP4 register as NA negative controls; WP5 copy-through siblings are covered by `copy_through_graphics` on layer `meta` (also NA under map-only — missing G graphics do not PASS). The report sets `full_disc_parity: false`. WP5 copy writers remain **Not started**; the cmp contract does not close WP5 or Phase 3.

## Where to read next

| Question | Doc |
|---|---|
| What is the format, and how sure are we? | `docs/schema/README.md`, then the layer files; `docs/schema/UNKNOWNS.md` for everything not yet verified |
| How is the code organised? | `docs/ARCHITECTURE.md` |
| What are we building and how is it judged? | `docs/design/target-disc.md` |
| How do we run the workflow plugin (design → execute → close)? | `docs/WORKFLOW.md` |
| What remains unfinished? | `docs/plans/04-c-core-orchestration/` (blocked Phase 3 / 3-90; dependent Phases 4–6). The completeness successor items remain (2-01 source-data parity under plan 30: 341 supply-path rows, implemented by plan 50 (R-G9-2 discharged), 0 unfixable-proven, dump_row 246 closed by plan 38 as proven cause H3-other-feature (source-data); plan 30 closed, `docs/plans/30-2-01-source-data-parity.md`); plan **14** closed out at `3fb5a35` (`docs/plans/14-completeness-root-cause.md`). Plan 03's remaining content phases stay frozen. The closed records under `docs/plans/` describe completed work. |
| What was built before? | `docs/plans/01-…md`, `docs/plans/02-…md` |
| Where did each non-committed file come from? | `docs/provenance.md` |

## References

- Official KIWI-W v1.22 specification, on the Wayback Machine:
  `https://web.archive.org/web/20060616222450/http://kiwi-w.mapmaster.co.jp/format_english/format_kihon.html`
  (fetch with `curl`; `WebFetch` cannot reach it). Archived copy and reproduction steps are
  in `docs/provenance.md`.
- `https://github.com/jharg/kiwiread`: partial reverse-engineering reader for `ALLDATA.KWI`
  and `LOADING.KWI`. A study source, read-only, with no route planning or index support.
- An OSM forum thread on exporting OSM to KIWI-W concluded no public exporter existed. This
  is a large project, and the offline oracle is what makes it tractable.
