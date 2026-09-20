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
| WP1 | Map layer (`ALLDATA.KWI`) and the evaluation harness | Built (plan 01); parity gaps being remediated (plan 03) |
| WP2 | Route planning frames and ext frames | Not started; first-pass writer exists |
| WP3 | Address and POI search | Not started |
| WP4 | Remaining `IDX/` families, `HWMAP`, `INDEXDAT` | Not started; bodies undecoded |
| WP5 | Disc stamp, coverage, image authoring, burn | Not started |

Build time for the map layer is about 32 s at `-j 12` (plan 02).

## Where to read next

| Question | Doc |
|---|---|
| What is the format, and how sure are we? | `docs/schema/README.md`, then the layer files; `docs/schema/UNKNOWNS.md` for everything not yet verified |
| How is the code organised? | `docs/ARCHITECTURE.md` |
| What are we building and how is it judged? | `docs/design/target-disc.md` |
| What is being changed now? | `docs/plans/03-map-layer-parity-remediation/` |
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
