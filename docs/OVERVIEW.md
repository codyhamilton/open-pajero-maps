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
| WP1 | Map layer (`ALLDATA.KWI`) and the evaluation harness | Build and harness exist (plans 01–02); map parity is unfinished. Plan **04** C-core Phases 1–2 are closed; Phase 3 is blocked at **3-90** after 3-14–3-17 landed. Phases 4–6 depend on that close. Plan **03** content phases remain frozen until 04 Phase 6. Heavy-job memory (05), padding attribution (07), classify fixes (08–09), the carried assembly-loader error (10), recorded triage summary determinism failures (11), carried density wording (12), the recorded fixture way precheck (13), SADSR SRMX STFG (15), and K1 determinism `wall_s` strip (16) are finished; records are under `docs/plans/`. Plan **14** completeness root-cause closed out at `3fb5a35`; record: `docs/plans/14-completeness-root-cause.md`. Plan **29** fixed the K1 name_anchor failure (verdict A: the original disc lacks the out-of-span O03 name). The assembly drop guard produces the successor oracle disc in force, `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae` (`output/scratch-29/G_new`). Its diff is confined to the L0 (0,541) frame, and live K1 exits 0. `4ed9cd80…` stays historical. Record: `docs/plans/29-k1-name-anchor-failure.md`. |
| WP2 | Route planning frames and ext frames | Not started; first-pass writer exists |
| WP3 | Address and POI search | Not started (plan 26: offline seven-state search fixtures/tests only — ≠ WP3 complete ≠ Australia-wide MMCS proof) |
| WP4 | Remaining `IDX/` families, `HWMAP`, `INDEXDAT` | Not started; bodies undecoded |
| WP5 | Disc stamp, coverage, image authoring, burn | Not started |

Full map-layer build is about **12.2 s** median at `-j 12` (3C close / plan 04 evidence; earlier plan-02 ~32 s is historical). Heavy K1/triage jobs use `flock output/.heavy.lock` and are not that wall.

The latest 3-90 record at `5c5823e4c267dd64bc986038caddb3ed4b745f60` reported repeated PSS failure, a
determinism comparison that retained varying `wall_s`, native dumps missing
classification joins, truncated historical pins, unresolved 3-11 versus 3-14
oracle evidence, and an incomplete independent-review chain. Plan **16** closed
the timing-only `wall_s` strip defect (strip now matches Phase 2
`COMPARE_EXCLUDES`: `timing` + `wall_s`); that strip is not a live blocker.
Plan **27** independently reviewed the plan-16 / check-3 strip (PASS) and expanded in-scope truncated oracle pins / the OVERVIEW short SHA to full digests (`docs/plans/27-independent-fix-review-truncated-pins.md`); `pinned_candidates.tsv` remains a brief-required 100-row candidate view (`TRUNCATED=yes`) whose exhaustive group identity is **unverifiable from git** (full enumerations are non-committed scratch) — see that plan's pin ledger. Plan **20** reframes the live PSS item as a **contract mismatch**: the signed
ceiling **9,726,501 kB** is the historical `-j 12` peak, while ops and the
3-90 gate must use ≤ `-j 6` — not an unexplained memory blow-up. The PSS bar
is **not** cleared; a later 3-90 re-run under the amended brief is still
required. Remaining open blockers: PSS contract (ceiling held; live gate at
ops ≤6), 3-14 oracle cause attribution
(plan **31** measured exact changed-cell identities for every re-oracle hop — AU 3-11 37 cells, AU 3-14 246,123, Perth 3-14 795, plan 29 one L0 cell — in `docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.tsv`; the 3-14 per-cell payload causes stay unattributed),
and `pinned_candidates` exhaustive set-equality (unverifiable from git until enumerate artifacts are authorised). Other kinds' native classify joins are discharged under plan **32** (`docs/plans/32-other-kind-classify-joins/census.tsv`): interior_cover, name_anchor, background and background_boundary each have 0 failing rows on successor `2ee3456a…` (K1 `-j6`), so their assignment artefacts are empty; historical causes stay in `phase2_disposition.md`. Completeness per-rule assignments and historic attribution are recovered and joined under plan **28** (`docs/plans/04-c-core-orchestration/triage/per_rule_phase2_reconciliation.md`): 776 rows, 769 consistent, 7 conflict-proven, **0 conflict-open**. The seven O04 spool rows (138, 236, 282, 284, 317, 496, 563) remain successor spool items; 2-01 source-data parity (342 rows) is dispositioned under plan **30** (`docs/plans/30-2-01-source-data-parity/disposition.tsv`): **243 supply-path** (OSM multipolygon relations the spool does not assemble; successor implement unit), **0 unfixable-proven**, **99 conflict-open** (PBF relation coverage gaps; discriminators named per row). The plan-16 strip independent-review gap is closed by plan **27**; other historical unreviewed fix units are out of that discharge. Plan **25** records the 2026-10-06 OOM RCA and memory guards; heavy-Maps **CHM hold** pending clear (`docs/plans/25-oom-memory-rca/`) — not auto-cleared. These still block Phase 3 closure; no later phase
is released; plan 04 Phase 3 is not closed. The signed phase outcome and
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
| What remains unfinished? | `docs/plans/04-c-core-orchestration/` (blocked Phase 3 / 3-90; dependent Phases 4–6). The completeness successor items remain (2-01 source-data parity: 243 supply-path rows to implement and 99 conflict-open under plan 30; the seven O04 spool rows); plan **14** closed out at `3fb5a35` (`docs/plans/14-completeness-root-cause.md`). Plan 03's remaining content phases stay frozen. The closed records under `docs/plans/` describe completed work. |
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
