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
| WP1 | Map layer (`ALLDATA.KWI`) and the evaluation harness | Build and harness exist (plans 01–02); map parity is unfinished. Plan **04** C-core Phases 1–2 are closed; Phase 3 is blocked at **3-90** after 3-14–3-17 landed. Phases 4–6 depend on that close. Plan **03** content phases remain frozen until 04 Phase 6. Heavy-job memory (05), padding attribution (07), classify fixes (08–09), the carried assembly-loader error (10), recorded triage summary determinism failures (11), carried density wording (12), and the recorded fixture way precheck (13) are finished; records are under `docs/plans/`. |
| WP2 | Route planning frames and ext frames | Not started; first-pass writer exists |
| WP3 | Address and POI search | Not started |
| WP4 | Remaining `IDX/` families, `HWMAP`, `INDEXDAT` | Not started; bodies undecoded |
| WP5 | Disc stamp, coverage, image authoring, burn | Not started |

Full map-layer build is about **12.2 s** median at `-j 12` (3C close / plan 04 evidence; earlier plan-02 ~32 s is historical). Heavy K1/triage jobs use `flock output/.heavy.lock` and are not that wall.

The latest 3-90 record at `5c5823e` reports repeated PSS failure, a
determinism comparison that retains varying `wall_s`, native dumps missing
classification joins, truncated historical pins, unresolved 3-11 versus 3-14
oracle evidence, and an incomplete independent-review chain. Historic
completeness attribution is still open. These are blockers to Phase 3 closure,
not a reason to repeat the same verification unchanged. The signed phase
outcome and detailed evidence remain in plan 04; no later phase is released.
The repo contains no plan 06 design: the earlier CI-gate draft is not a work
unit on master. WP2–WP5 labels below are program scope, not executable briefs.

## Where to read next

| Question | Doc |
|---|---|
| What is the format, and how sure are we? | `docs/schema/README.md`, then the layer files; `docs/schema/UNKNOWNS.md` for everything not yet verified |
| How is the code organised? | `docs/ARCHITECTURE.md` |
| What are we building and how is it judged? | `docs/design/target-disc.md` |
| How do we run the workflow plugin (design → execute → close)? | `docs/WORKFLOW.md` |
| What remains unfinished? | `docs/plans/04-c-core-orchestration/` (blocked Phase 3 / 3-90; dependent Phases 4–6). Plan 03's remaining content phases stay frozen. The closed records under `docs/plans/` describe completed work. |
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
