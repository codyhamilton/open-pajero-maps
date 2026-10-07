# L8 (7,4) road fragmentation + under-selection (plan 52)

Oracle tip `aeae426c…`. Plan 42 counts **still valid** on re-measure:
G 2979 pieces all dc12; R 929 links (801 dc10 + 128 dc12); trim drop 308 all 2-vert.

## R-G9-3-b — fragmentation

**Mechanism:** `extract-short-motorway-ways`

- Spool parent has 3281 roads, **1 piece per way_id** (no duplicate splits).
- **1089** already have `npts==2` in spool (all interior to parent geo; p50 ≈46 m).
- Sub (3,0) shrink drops **308** of these 2-vertex stubs (plan 42: ≤0.768 raw from kept, 2.0% length).
- **R-quantum coverage (threshold 0.95 committed before measure):**
  - All R length: **17.0%** (fails — dominated by omitted dc10).
  - R **dc12 only: 100%** covered within 1 parent-raw of G vertices.

Proven-cause: short records are extract-emitted short motorway/motorway_link ways;
shrink drops no geometry at R’s 1-raw step for the motorway class G actually selects.
Piece-count inflation (G 2979 vs R 128 dc12) remains a named residual of G’s finer
motorway segmentation, not lost centreline at R quantum.

## R-G9-3-c — under-selection + dc 10

**Drop stage:** extract `selection.json` L8 `highway=["motorway"]` only.

| Vocab L2–8 | OSM | dc |
| --- | --- | ---: |
| motorway | motorway(_link) | 12 |
| trunk | trunk(_link) | 0 |
| primary | primary(_link) | 4 |
| secondary…track | collapsed | 10 |

G never emits dc 10 at L8 because those classes are not admitted. Deliberate
calibration subset (selection note: motorway count near ceiling). Volume gap is
that rule’s residual.

### Focus leaves (G local raw vs R length in leaf rect)

| G leaf | G n / raw | R raw in leaf (dc10 / dc12) |
| ---: | --- | --- |
| 2 | 41 / 225 | 4443 (4443 / 0) |
| 3 (sub 3,0) | 2109 / 5373 | 6388 (3693 / 2696) |
| 7 | 829 / 3003 | 3375 (3021 / 354) |
| 11 | 0 / 0 | 846 (846 / 0) |
| 14 | 0 / 0 | 3205 (3205 / 0) |

## Disposition

Both children **proven-cause** (no code/oracle change). No F6 / kind-order work
(steering hard). Expanding L8 selection beyond motorway is a Cody/Design product call.

See `frag_mech.json`, `remeasure.json`, `underselect/volume_table.json`.
