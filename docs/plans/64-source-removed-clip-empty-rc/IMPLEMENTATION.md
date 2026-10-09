# Plan 64 — implementation log

Seat: Codex on codyh-ubuntu (master direct). Draft re-copied from `/workspace/maps-design-drafts/64-source-removed-clip-empty-rc/` at start (14:31 AEST, sha `42447564…`), and re-copied again after the Design scope revision (14:45 AEST note; DESIGN.md + REVISION-NOTE.md). Tip `61d2fe8`.

## Phase 1: producer and source trace — DONE

### Scope (revision 2026-10-09)

23 groups / 627 rows: R-G5-1-b (1 group, 50 rows; plan 46), R-G5-4-a-2 (1 / 32) and R-G5-4-b-1 (21 / 545) from `p9_r01_residual/transitions.json` `source_removed_groups` (sha `d51baafb…`). 17 distinct producer homes, 23 leaf cells.

### Tools (committed under `triage/historical_bg/p8_source_removed/`)

- `reextract_cell.py`: output-neutral provenance re-extract. One streaming pyosmium pass (location index `flex_mem`, as the production extractor) using the extractor's own functions (`_osm_tags_to_bg_type`, `selection.level_filter`, ring closure, `_centroid`, `assign_to_parcel` on `TileGrid.from_reference(0)`). Lists every background ring per producer home in PBF order and compares it ring-by-ring (type and coordinates) with the spool cell; lists every way and tagged relation whose bbox meets each group cell (+0.002°) with tags, level-0 type mapping and `level_filter` result (H4 proof (i) input).
- `trace.py build|analyze`: sidecar window builds (plan 63's committed `sidecar_33006aa.patch` in throwaway worktree `../open-pajero-maps-64-33006aa`), then per group: G1 output-neutral gate, sidecar emitter vs recorded producer, 33006aa/d35b565 clipper probes of the producer ring, plan-46 unique-byte scan, shape on-frame counts, producer ring vs clip rect, footprint on R / 013586b5 / 4ed9cd80 / 0c22b266, extract join.

### Inputs

- PBF `australia-260824.osm.pbf` sha256 `433a1da21d4b39bdbbb79cb6ee5865e9ade308bae62226a4398d5fe3a3ec99c0` (= the pinned `433a1da2…`; open question 2 answered: byte-identical on the host).
- Discs: R mounted `/run/media/codyh/464210-8480`; `013586b5` = `output/scratch-45/ref_33006aa`; `4ed9cd80` = `output/scratch-45/ref_d35b565`; `0c22b266` = `output/scratch-53/G_new` (manifest shas). R reader = plan 48's (`overlay_test.RReader` + `r_neighbours.LeafIndex` + `decode_parcel`, via `trim_witness.r_parent`), answering open question 1.

### Run notes

- First re-extract launch (single-home tool) was stopped by pid before it finished, after the scope revision arrived; an earlier launch lost its shell to a `pkill -f` pattern that matched the launching shell (orphan python killed by pid, scope gone). Neither produced output. The re-extract was re-run once for all 17 homes / 23 cells.

### Outcome (`p8_source_removed/trace.json`, `471366e1…`)

- **Gate (output neutrality):** 23 single-cell sidecar windows at `33006aa`: every window frame is byte-equal to a 013586b5 leaf of its cell and every 013586b5 leaf is matched (26 leaves; the divided cell (1738,570) has 4). The sidecar parses (hash, record count, unit class) for every frame.
- **H1 (wrong producer): false for 23/23.** The sidecar emitter of each group's 013586b5 shape is the recorded producer (21 routed, 2 own; R-G5-1-b's is routed from (1751,594)). Independently, the producer's 33006aa clip reproduces the shape's bytes, and it is the only same-type ring of Moore(8) ∪ FarHomes whose 33006aa clip does (plan-46 unique-byte scan, 1 hit each). The 113 RC3/RC4 rows (groups at (1152,1401), (1152,1448), (1248,1005), (1248,1625), (1738,570) 1866.3) were checked the same way; none is H1.
- **d35b565 clip:** the producer's d35b565 clip into the leaf writes 0 bytes for 23/23 (reproduces `clip_size_d35b565` 0).
- **H5 (extract defect): false for 23/23.** All 17 producer homes reproduce their spool cell ring-for-ring (6,608 rings, type and coordinates equal, PBF order = spool order). Each producer ring equals its OSM way's node coordinates plus the extractor's ring closure, and its type 288 is the documented level-0 mapping (the first matching `bg_type.json` rule is rule 11, the catch-all `{}` → 288).
- **Finding for Design and Cody (not a fix; F6 / kind-order stays Cody-held):** all 17 producers are **open** OSM ways (first node ≠ last node) that `osm_to_parcel_geometry.py` closes into polygon rings (`ring.append(ring[0])` for any non-road way with ≥3 coordinates) and maps through the level-0 catch-all to type 288. Their tags: 5 ways only `source:geometry=PSMA_Admin_Boundaries`, 2 only `source=CAPAD 2016 - Terrestrial`, 8 with no tags at all, 1 `barrier=fence`, 1 `natural=tree_row`. 16 of 17 rings self-intersect once closed. These are linear features or bare relation members, not areas.
- **Piece geometry:** every 013586b5 shape is a large frame-hugging polygon: it covers 3 %–100 % of its leaf rect (R-G5-1-b: the whole rect, all 134 vertices on the frame), while the producer ring's exact even-odd region inside the leaf is 0.9–497 raw units² (Phase 2 `classify.json`). Producer rings have 0–4 vertices inside the leaf rect.
- **Footprints:** R has **no** type-288 record covering any part of any group's footprint. 013586b5 covers it fully by construction; 4ed9cd80 / 0c22b266 cover 3 %–100 % of it with other type-288 records. Records meeting each footprint on all four discs (type, class, leaf, wire sha) are in `trace.json`.

| Group (leaf, shape) | Row | Rows | Producer | Sidecar emitter | 33006aa clip → shape bytes | d35b565 clip | Shape: on-frame W/E/S/N, off | Shape area / rect | Ring n, verts in rect, self-x | OSM way (closed?) tags | R / 4ed9 / 0c22 same-type cover of footprint |
| --- | --- | ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| (808,1121) 1064 s0 | R-G5-4-b-1 | 32 | (808,1121,0) | own (808,1121,0) = | 296 B, yes | 0 | 12/2/34/0, 97 of 143 | 2,091,504 / 16,777,216 | 5, 1, 1 | 961577161 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1059,1248) 1027 s1 | R-G5-4-b-1 | 32 | (1061,1248,0) | routed (1061,1248,0) = | 150 B, yes | 0 | 5/1/34/0, 32 of 70 | 549,362 / 16,777,216 | 13, 0, 2 | 964224756 (open) {"source": "CAPAD 2016 - Terrestrial"} | 0.0 / 1.0 / 1.0 |
| (1109,1181) 949 s0 | R-G5-4-b-1 | 17 | (1109,1193,0) | routed (1109,1193,0) = | 186 B, yes | 0 | 0/34/23/1, 32 of 88 | 5,228,171 / 16,777,216 | 30, 0, 1 | 853069217 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 0.1719 / 0.1719 |
| (1152,1401) 1824 s0 | R-G5-4-b-1 | 32 | (1152,1422,0) | routed (1152,1422,0) = | 208 B, yes | 0 | 0/34/34/1, 32 of 99 | 8,041,193 / 16,777,216 | 15, 0, 9 | 853069378 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1152,1417) 288 s0 | R-G5-4-b-1 | 32 | (1152,1422,0) | routed (1152,1422,0) = | 208 B, yes | 0 | 0/34/34/1, 32 of 99 | 8,042,062 / 16,777,216 | 15, 0, 9 | 853069378 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1152,1432) 768 s0 | R-G5-4-b-1 | 32 | (1152,1422,0) | routed (1152,1422,0) = | 208 B, yes | 0 | 0/34/34/1, 32 of 99 | 8,042,496 / 16,777,216 | 15, 0, 9 | 853069378 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1152,1448) 1280 s0 | R-G5-4-b-1 | 32 | (1152,1422,0) | routed (1152,1422,0) = | 208 B, yes | 0 | 0/34/34/1, 32 of 99 | 8,042,496 / 16,777,216 | 15, 0, 9 | 853069378 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1248,908) 384 s0 | R-G5-4-b-1 | 32 | (1248,910,0) | routed (1248,910,0) = | 280 B, yes | 0 | 34/0/2/5, 96 of 135 | 515,102 / 16,777,216 | 15, 1, 3 | 516574447 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,918) 704 s0 | R-G5-4-b-1 | 32 | (1248,910,0) | routed (1248,910,0) = | 148 B, yes | 0 | 34/0/1/4, 32 of 69 | 515,040 / 16,777,216 | 15, 0, 3 | 516574447 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,939) 1376 s1 | R-G5-4-b-1 | 32 | (1248,935,0) | routed (1248,935,0) = | 148 B, yes | 0 | 34/0/1/4, 32 of 69 | 513,551 / 16,777,216 | 13, 0, 1 | 460118552 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,970) 320 s1 | R-G5-4-b-1 | 26 | (1248,980,0) | routed (1248,980,0) = | 264 B, yes | 0 | 34/0/1/5, 89 of 127 | 510,448 / 16,777,216 | 28, 1, 6 | 459544152 (open) {} | 0.0 / 0.9637 / 0.9637 |
| (1248,1005) 1440 s1 | R-G5-4-b-1 | 28 | (1248,980,0) | routed (1248,980,0) = | 264 B, yes | 0 | 34/0/1/5, 89 of 127 | 507,904 / 16,777,216 | 28, 1, 6 | 459544152 (open) {} | 0.0 / 0.98 / 0.98 |
| (1248,1321) 1312 s0 | R-G5-4-b-1 | 32 | (1248,1313,0) | routed (1248,1313,0) = | 208 B, yes | 0 | 0/34/34/1, 32 of 99 | 8,246,055 / 16,777,216 | 20, 0, 4 | 575140882 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,1443) 1120 s1 | R-G5-4-b-1 | 32 | (1248,1444,0) | routed (1248,1444,0) = | 342 B, yes | 0 | 0/34/35/2, 97 of 166 | 8,254,062 / 16,777,216 | 43, 1, 5 | 41029322 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,1456) 1536 s1 | R-G5-4-b-1 | 32 | (1248,1444,0) | routed (1248,1444,0) = | 342 B, yes | 0 | 0/34/35/2, 97 of 166 | 8,254,868 / 16,777,216 | 43, 1, 5 | 41029322 (open) {} | 0.0 / 1.0 / 1.0 |
| (1248,1625) 800 s0 | R-G5-4-b-1 | 5 | (1248,1608,0) | routed (1248,1608,0) = | 342 B, yes | 0 | 0/34/36/2, 96 of 166 | 8,264,983 / 16,777,216 | 25, 1, 6 | 591101742 (open) {} | 0.0 / 0.1391 / 0.1391 |
| (1248,1644) 1408 s14 | R-G5-4-b-1 | 1 | (1248,1642,0) | routed (1248,1642,0) = | 340 B, yes | 0 | 0/34/36/1, 96 of 165 | 8,266,100 / 16,777,216 | 11, 2, 4 | 591106133 (open) {} | 0.0 / 0.0269 / 0.0269 |
| (1268,1152) 20 s3 | R-G5-4-b-1 | 32 | (1257,1152,0) | routed (1257,1152,0) = | 282 B, yes | 0 | 6/2/34/0, 96 of 136 | 571,764 / 16,777,216 | 37, 1, 2 | 589762366 (open) {"source": "CAPAD 2016 - Terrestrial"} | 0.0 / 1.0 / 1.0 |
| (1323,1686) 715 s2 | R-G5-4-a-2 | 32 | (1323,1675,0) | routed (1323,1675,0) = | 190 B, yes | 0 | 0/34/25/1, 32 of 90 | 5,909,783 / 16,777,216 | 9, 0, 5 | 854815947 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 1.0 / 1.0 |
| (1645,1269) 1709 s0 | R-G5-4-b-1 | 32 | (1645,1269,0) | own (1645,1269,0) = | 256 B, yes | 0 | 1/34/25/34, 32 of 123 | 14,232,731 / 16,777,216 | 5, 0, 1 | 731816618 (open) {} | 0.0 / 1.0 / 1.0 |
| (1695,700) 1951 s7 | R-G5-4-b-1 | 4 | (1695,699,0) | routed (1695,699,0) = | 288 B, yes | 0 | 0/34/6/2, 99 of 139 | 756,705 / 16,777,216 | 10, 4, 3 | 853079791 (open) {"source:geometry": "PSMA_Admin_Boundaries"} | 0.0 / 0.0841 / 0.0841 |
| (1738,570) 1866.3 s2160 | R-G5-4-b-1 | 16 | (1738,570,6105) | own (1738,570,6105) = | 146 B, yes | 0 | 1/18/18/18, 16 of 68 | 4,154,850 / 4,194,304 | 7, 0, 2 | 1239544336 (open) {"barrier": "fence"} | 0.0 / 1.0 / 1.0 |
| (1750,594) 598 s171 | R-G5-1-b | 50 | (1751,594,16) | routed (1751,594,16) = | 278 B, yes | 0 | 34/36/34/34, 0 of 134 | 16,777,216 / 16,777,216 | 8, 2, 0 | 903365395 (open) {"leaf_type": "broadleaved", "natural": "tree_row"} | 0.0 / 0.6876 / 0.6876 |

### Phase 1 scratch receipt

1. `du -sb output/scratch-64`: before 12,823,738 B (`p1/` 9,505,761 B: re-extract output, 23 sidecar window dirs, trace output, wrapper logs, probe tmp; `p2/` 3,312,616 B is Phase 2's in-progress scratch, already started because Phase 2's runs queued behind Phase 1 on the lock). After: 3,312,616 B, `ls -A` = `p2` only. `output/scratch-64/p1` is gone.
2. Kept, all committed: `p8_source_removed/trace.json` (`471366e1…`), `trace.py` (`6fb211bb…`), `reextract_cell.py` (`5f4bdcce…`), the `docs/provenance.md` entry, `ledger/source_removed_plan64.json` + SUMMARY row. No `keep/`. Phase 2 reads only `trace.json`.
3. Worktrees: `../open-pajero-maps-64-33006aa` removed (`git worktree remove` + `prune`); `git worktree list` has no `64-33006aa`. (`../open-pajero-maps-64-d35b565` is Phase 2's and is removed in its receipt.)
4. Temp dirs and scopes: the run temp dirs lived under `p1/tmp` (deleted with `p1/`); 0 `/tmp/p64_*`; 0 `maps-heavy` scopes.
5. Peaks copied to the ledger before deleting the wrapper logs: re-extract max RSS 4,264,296 KiB / memory.peak 4.57 GB, 390 s; trace analyze 3,894,272 KiB / 0.40 GB, 43.5 s; final p1ab run 4,274,144 KiB / 4.68 GB, 425.5 s.
6. `df -h /home`: 11 G free (97 %).

## Phase 2: empty-clip cause decided — DONE

### Refine: hook point (fixed before the run)

- `p8_source_removed/stage_d35b565.patch` (vs `d35b565`, `7395df53…`) = plan 63's sidecar (applies unchanged) + per-`bg_shape` stage counters (`_cenc.c` TLS `KwSt`, reset at entry): ring points, inside, clipped chains, whole, `eo_clip` result and the reason the EO arrangement ran, clipped / atomic edges, faces walked, faces with positive area, faces judged interior (`eo_left`) and sent to `emit_piece`, pieces dropped at round/clean split by line (fewer than 3 lattice points `_cenc.c:586`, zero lattice area `_cenc.c:592`), records written, legacy path taken.
- `enc_bg` appends one entry per class>0 input background (`SW` / `SP` lines next to the sidecar's `W` / `P`, same frame hash). Divided leaves: `_e2.c` `dv_bg_cells` pushes a parent background onto a sub-cell only if its clip there writes a record (`_e2.c:647` at d35b565), so that assignment clip is logged too (`SD` lines). Logging only; gate below.
- Tool: `stage.py` (build / analyze). Classifier: `classify.py` (H1–H5 per group; commits `classify.json`).

### Outcome

- **Gate (output neutrality):** 23 single-cell windows from a throwaway `d35b565` worktree with the patch: 26/26 window frames byte-equal to a 4ed9cd80 leaf of their cell, 0 unmatched 4ed9cd80 leaves (`stage.json`, `ccd57f1e…`).
- **Stage trace (23/23 groups, each its own call):** the producer ring reaches `bg_shape` for its leaf (22 via `enc_bg`; (1738,570) 1866.3 via the `dv_bg_cells` assignment clip of sub-cell 3, which is why that ring is never in the sub-cell's list). In every call:
  1. clip: chains exist (the ring does enter the leaf);
  2. `eo_clip` takes the EO arrangement path (`_cenc.c:940`): 22 because two clipped segments properly cross (`:803`; the extractor-closed open way self-intersects), R-G5-1-b because a chain is not locally CCW (`:806`);
  3. the arrangement walks 5 faces (R-G5-1-b 3); the faces judged interior to the ring (`:889`) are 2 (R-G5-1-b 1). The large frame-bounded faces are judged exterior. These are the faces the 33006aa legacy chain walk emitted as its frame-hugging piece;
  4. **first empty stage: `emit_piece` round/clean.** Every interior face is a sub-unit sliver. After densify and `rint` it has fewer than 3 distinct lattice points (`_cenc.c:586`) or zero lattice area (`:592`), so 0 records are written.
- **Why the 33006aa record is an artefact:** the producer's exact even-odd region inside the leaf is 0.9–497 raw units². The 013586b5 shape it produced is 1,935× to 9,007,839× larger (R-G5-1-b: the whole 4096² leaf from a 5.8 unit² sliver). That is the legacy chain walk closing a sliver chain the long way round the frame.
- **R comparison (mandatory):** R has **0 type-288 polygons anywhere in each of the 23 leaf cells** (parent-raw decode of every R leaf of the cell), so R has no coverage of either the exact region or the 013586b5 footprint. 4ed9cd80 has 1–2,275 type-288 polygons meeting each leaf rect, all from other producers (R-G5-6 / F6 territory, not this plan's).
- **Verdict per group (classifier, each on its own evidence): H3 for 23/23.** H1 false, H5 false (Phase 1). The 013586b5 record is a legacy artefact (ratio ≥ 100×). d35b565 removes it at a named step that drops only sub-lattice slivers. R has no such coverage either. H2 is not supported: the stage trace names no defect, since EO picks the ring's own interior faces and only lattice rounding empties them. H4 is not needed.

  | Row | Groups | Rows | Verdict |
  | --- | ---: | ---: | --- |
  | R-G5-1-b | 1 | 50 | H3 |
  | R-G5-4-a-2 | 1 | 32 | H3 |
  | R-G5-4-b-1 | 21 | 545 | H3 |

| Group (leaf, shape) | Row | Rows | d35b565 call | EO trigger | faces / pos-area / interior | pieces dropped: <3 pts (:586) / zero area (:592) | records | exact in-leaf region (raw²) | 013586b5 shape / region | R same-type polygons in cell | 4ed9 same-type in leaf | Verdict |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| (808,1121) 1064 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 66.0308 | 31,674.7× | 0 | 5 | **H3** |
| (1059,1248) 1027 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 15.7726 | 34,830.1× | 0 | 1 | **H3** |
| (1109,1181) 949 | R-G5-4-b-1 | 17 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 496.6567 | 10,526.7× | 0 | 1 | **H3** |
| (1152,1401) 1824 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 1.0567 | 7,609,613.3× | 0 | 1 | **H3** |
| (1152,1417) 288 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 1.0354 | 7,767,433.4× | 0 | 1 | **H3** |
| (1152,1432) 768 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 1.2686 | 6,339,784.8× | 0 | 2 | **H3** |
| (1152,1448) 1280 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 0.8928 | 9,007,839.1× | 0 | 1 | **H3** |
| (1248,908) 384 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 4.591 | 112,197.8× | 0 | 1 | **H3** |
| (1248,918) 704 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 5.7478 | 89,605.7× | 0 | 1 | **H3** |
| (1248,939) 1376 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 7.3157 | 70,198.9× | 0 | 2 | **H3** |
| (1248,970) 320 | R-G5-4-b-1 | 26 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 4.5643 | 111,835.3× | 0 | 2 | **H3** |
| (1248,1005) 1440 | R-G5-4-b-1 | 28 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 3.5101 | 144,697.1× | 0 | 2 | **H3** |
| (1248,1321) 1312 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 5.622 | 1,466,758.9× | 0 | 1 | **H3** |
| (1248,1443) 1120 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 197.7695 | 41,735.8× | 0 | 1 | **H3** |
| (1248,1456) 1536 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 7.6684 | 1,076,485.1× | 0 | 1 | **H3** |
| (1248,1625) 800 | R-G5-4-b-1 | 5 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 4.4977 | 1,837,605.1× | 0 | 8 | **H3** |
| (1248,1644) 1408 | R-G5-4-b-1 | 1 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 3.4365 | 2,405,375.8× | 0 | 26 | **H3** |
| (1268,1152) 20 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 1 / 1 | 0 | 295.4396 | 1,935.3× | 0 | 1 | **H3** |
| (1323,1686) 715 | R-G5-4-a-2 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 1.459 | 4,050,508.6× | 0 | 2 | **H3** |
| (1645,1269) 1709 | R-G5-4-b-1 | 32 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 1.8489 | 7,697,741.2× | 0 | 3 | **H3** |
| (1695,700) 1951 | R-G5-4-b-1 | 4 | enc_bg bg_shape, eo_faces | proper crossing | 5 / 4 / 2 | 0 / 2 | 0 | 12.5069 | 60,503.2× | 0 | 5 | **H3** |
| (1738,570) 1866.3 | R-G5-4-b-1 | 16 | dv_bg_cells assignment clip, eo_faces | proper crossing | 5 / 4 / 2 | 2 / 0 | 0 | 2.1421 | 1,939,642.8× | 0 | 2275 | **H3** |
| (1750,594) 598 | R-G5-1-b | 50 | enc_bg bg_shape, eo_faces | chain not locally CCW | 3 / 2 / 1 | 1 / 0 | 0 | 5.7873 | 2,898,959.1× | 0 | 140 | **H3** |

### Phase 2 scratch receipt

1. `du -sb output/scratch-64`: before 3,533,979 B (`p2/`: 23 stage windows, stage / classify outputs, wrapper logs, run scripts; empty `tmp/`). After: `output/scratch-64` gone (`test ! -e`).
2. Kept, all committed: `stage.json` (`ccd57f1e…`), `classify.json` (`1ffb9e0c…`), `stage.py` (`b0250061…`), `classify.py` (`d4cacf14…`), `stage_d35b565.patch` (`7395df53…`), ledger row. No `keep/`.
3. Worktrees: `../open-pajero-maps-64-d35b565` removed (`git worktree remove` + `prune`); `git worktree list` has no plan-64 worktree.
4. Temp dirs and scopes: run temp dirs lived under `p2/tmp` (removed by atexit, then deleted with `p2/`); 0 `/tmp/p64_*`; 0 `maps-heavy` scopes.
5. Peaks copied to the ledger first: final stage + classify run max RSS 3,897,480 KiB / memory.peak 0.35 GB, 45.3 s (windows 25 s, FarHomes L0 in classify); first stage run 1,106,504 KiB / 0.31 GB, 30.3 s.
6. `df -h /home`: 11 G free (97 %).

### R-G5-1-b early read (pre-revision, exploratory; superseded by the outcome above)

- `013586b5` leaf (0,1750,594,(598,)) shape 171 is a 134-vertex type-288 record whose vertices all lie on the leaf frame: a densified whole-frame square.
- Producer (1751,594,16) is an 8-coordinate ring (bbox x 4034–4731, y 3351–3550 relative to cell (1750,594)). Exactly one distinct vertex lies inside the leaf; its exact polygon ∩ leaf area is ≈ 4 raw units² (a 62-unit-long sliver, about 0.13 units wide at x=4096).
- R has no type-288 record in cell (1750,594).

## Phase 3 — act and update residuals (2026-10-09)

No code fix: every group is H3 (correct removal), so the build stays as it is and no oracle moved (nothing has to land before plan 68).

- `residuals.tsv`: R-G5-1-b (50), R-G5-4-a-2 (32) and R-G5-4-b-1 (545) → `discharged-plan-64`, owner `Design → plan 64 (discharged)`. Each row cites `classify.json` (`1ffb9e0c…`), `trace.json` (`471366e1…`), `stage.json` (`ccd57f1e…`). Parents R-G5-1, R-G5-4-a, R-G5-4-b blocking text updated (R-G5-4-a-1 stays `blocks-phase3`, carried by Design draft 68 Phase 1).
- Row sum check: 32×15 + 17 + 26 + 28 + 5 + 1 + 4 + 16 + 50 = 627 = 50 + 32 + 545.
- `causes_residual.md`: Plan 64 note (H1/H5 false per group, mechanism, H3, finding). `synthesis.md` and `OVERVIEW.md` live-ownership table synced.
- **Finding for Design and Cody (not a fix; F6 / kind-order are Cody-held).** All 17 producers are open OSM ways that `osm_to_parcel_geometry.py` closes into rings and `bg_type.json` level-0 rule 11 (catch-all `{}`) types 288: 5 tagged only `source:geometry=PSMA_Admin_Boundaries`, 2 only `source=CAPAD 2016 - Terrestrial`, 8 untagged, 1 `barrier=fence`, 1 `natural=tree_row` (R-G5-1-b). 16/17 self-intersect once closed. Whether open ways should become polygons at all is a mapping question for Design / Cody.

### Phase 3 scratch receipt

1. No scratch created: `output/scratch-64` absent before and after (`test ! -e`); `du -sb` n/a (0 B).
2. Kept: only committed docs edits. No `keep/`.
3. `git worktree list`: no plan-64 worktree.
4. 0 `/tmp/p64_*`; 0 `maps-heavy` scopes.
5. No heavy run, so no ledger peak; ledger note added.
6. `df -h /home`: 11 G free (97 %).

## Review 1 (Codex, read-only): FIX → fix

- First attempt aborted before reading anything: the shell carried a stale `TMPDIR` / `KW_SIDECAR_DIR` pointing into the deleted `output/scratch-63/p2/`. Both unset; review re-run.
- Finding 1 (medium): R-G5-4-a-1 still named plan 63 as owner in `residuals.tsv` and `synthesis.md`, while OVERVIEW routes it to Design draft 68 Phase 1. Fixed: owner `Design → plan 68 Phase 1`, routing note appended; row stays `blocks-phase3`.
- Reviewer: the 23 per-group H3 verdicts, the 627-row split, R witnesses, stage counters, output-neutral gate, cited code lines and the P1–P3 receipts otherwise check out.
- Interrupted ~15:26 AEST after the fix; resumed from observed state (origin 61d2fe8, local ccbe5fa + fix uncommitted, lock free, no heavy jobs or scopes, `output/scratch-64/review` only).
