# Report 2-03 — date-matched relation snapshot (Design Amendment 1, option a)

Seat: **Execute (Grok Bot), not Codex.** Codex was weekly-limited (reset
2026-10-10 11:50 AEST), so Execute implemented the brief and ran every
measurement itself.

## What changed (`disposition.py`; code `bf46547` + `617c7c8`)

- **Opt-in flags on `pbf-cache`:**
  - `--relation-snapshot` and `--relation-snapshot-sha256` (the digest and
    schema are verified; a mismatch is refused);
  - `--relation-snapshot-pin` (default `phase2_snapshot_pin.json`);
  - `--relation-requests` (default `relation_requests.json`).

  The snapshot path and sha are declared inputs (`relation_snapshot` and
  `inputs_sha256`). Without the flags, the output is unchanged: the r4
  no-flag control has proof-log sha `1868d852…`, the same as r2 and r3, and
  identical rows and gaps.
- **Eligible relations:** only the 61 requested ids, plus area-role child
  relations of requested nested parents. Any other relation in the snapshot
  is ignored.
- **Cache first.** Tags, members and ways come from the retained cache (the
  pinned PBF). The snapshot supplies only the ways absent from the cache.
  - A node shared by a cache way and a snapshot way must have identical
    coordinates, checked against cache ways and the nodes table.
  - A member-list mismatch becomes a `snapshot-member-mismatch` gap, and the
    legacy path is used for that relation.
- **Relations the cache never retained** (4095122, 15480206, 16308779,
  16308787, 16308826): their tags and members come from the snapshot, which
  is date-matched. The proof log records a `snapshot-tags-members` note for
  each.
- **Nested parents:** the union bbox of all descendant ways is the bound, and
  gives a `nested-outside-windows` note. Children carrying a code are
  assembled as their own sources. If any descendant way is missing, the gap
  is kept.
- **Vertex-limit relations:** validated geometry above 2,048 vertices goes
  through `boundary_clip` at the target cell. The result is a
  boundary-clipped production-C witness, or a `boundary-clip-empty` note.
  There is no longer a blanket vertex-limit gap.
- **Per-relation cap:** `RELATION_CAPS` gives r4095122 (Mainland Australia,
  766,271 vertices) `vertices` 800,000 and `topology_checks` 400,000,000.
  Topology is still validated. The run stayed within plan-25 guards:
  memory.peak 957,308,928 B, wall 166.8 s.
- **Antimeridian:** a ring split at ±180° (r20827987, Polynesian Triangle) is
  assembled in a 0–360 frame. It is bounded outside the windows, giving an
  `antimeridian-outside-windows` note, instead of an
  `ambiguous-antimeridian-source` gap on all 342 rows.
- **Supply preference:** when several sources supply a row, the
  `Accumulator` prefers a supply whose geometry is entirely pinned-cache
  over a snapshot-backed one. The 338 earlier rows therefore keep their r2
  sources.
- **Tests:** `test_parity_disposition.py` + `test_parity_fingerprint.py`
  give **75 passed**. They cover a sha mismatch refused, a member mismatch
  becoming a gap, a snapshot way completing a ring, a shared-node conflict
  refused, a non-requested relation ignored, nested bounding only when
  complete, the no-flag control, the antimeridian 0–360 frame and the
  pinned-first preference.

## Runs (Execute, guarded; `output/scratch-30/run_p2e.{sh,log}`, 11:55–11:59 AEST, HEAD `617c7c8`)

| Step | Output | Wall | Exit |
|---|---|---|---|
| reuse | `disposition_spool_r4.json` | 0.2 s | 0 |
| inventory | `disposition_inventory_r4.json` (sha `cfd2aa0e…`) | 0.1 s | 0 |
| pbf-cache, no flag (control) | `disposition_pbf_r4_noflag.json`: proof log `1868d852…` = r2 | 98.1 s | 0 |
| pbf-cache + snapshot `39a836dd…` | `disposition_pbf_r4.json` (sha `0200c592…`), proofs `ff67e0d9…` (12,209 lines) | 166.8 s | 0 |
| publish | `disposition.tsv` (sha `20cf5f53…`), `disposition_summary.json` (sha `1318c873…`) | 0.5 s | 0 |

The snapshot sha was the same before and after the run (`39a836dd…`).

## Result: 341 supply-path / 0 unfixable-proven / 1 conflict-open (was 338 / 0 / 4)

- **338 earlier supply-path rows:** no regression. All 338 keep the same
  source kind, id and variant, the same coords sha256 and the same
  production-C. The only difference is two provenance fields added to 174
  rows' source records: `geometry_ways.cache` and `tags_members`.
- **Rows 396, 397, 775 → supply-path.**
  - Source: r2647638 Australia (EEZ), `boundary=maritime`, 147 members.
    It is assembled from 131 cache ways plus 16 snapshot ways, then
    boundary-clipped at the target cell.
  - Witness: a positive production-C record of demanded code 288. Bytes are
    396: 20, 397: 20, 775: 218.
  - These supplies depend on the 16 snapshot ways, because the EEZ is clipped
    by the extract. A successor implement must assemble the complete
    relation; that input decision belongs to Design.
  - Row 396 also keeps a non-blocking r16623818 crossing/touching gap. It is
    covered by the positive.
- **Row 246 (L0 834,886; code 321; stratum 321-outlier) stays conflict-open,
  cause class `outlier/stratum evidence insufficient`.**
  - The PBF leg is now **gap-free** for this row, with `blocking_gaps` empty.
  - 284 code-321 candidates (275 ways + 9 relations; `natural=wood` 274,
    `natural=scrub` 10) reach the row's windows. Every variant (original /
    clipped / unit-mult) gives 0 in-cell records. The in-cell emitters are
    288 ×11 (including r4095122, now assembled under its cap) and 291 ×1,
    never 321.
  - So there is no supply-path.
  - It is also **not** `unfixable-proven` under Amendment 1 §4. Demanded-type
    features do reach the cell: the spool's own retained 321 demander
    (background ordinal 15, source cell (0,834,885)) touches the cell edge at
    vertex 18 (lat −31.5416545, lon 116.0931811). Its mechanism is
    `encoder_drops_clipped_source_sliver`. Absence of a 321 feature therefore
    cannot be proven.
  - The open question is not a source gap. It is whether an honest repair
    (sliver retention or a semantic mapping) would supply the record. The
    disposition records it as unresolved: "original/clip/unit-mult negative;
    no proof of all honest repairs or semantic mismatch".
  - Owner: Design.
- **Remaining gaps** in r4 (none blocks an open row):
  - r8602575 open/branched ring (supplied rows only);
  - r16623817 and r16623818 crossing/touching (rows 567, 617–627 and 396, all
    supplied);
  - r18183905 nested (row 252, supplied).
- **Notes:** `boundary-clip-empty` 1,038; `snapshot-tags-members` 5;
  `nested-outside-windows` 2; `no-area-geometry` 1;
  `antimeridian-outside-windows` 1.

## Not done

No disc, spool, encoder, vocabulary or selection change, and no R geometry.
The PBF, the cache `p2_pbf_cache_01` and the snapshot are untouched. Phase 2's
outcome (0 conflict-open) is **not met**, so plan 30 stays open.
