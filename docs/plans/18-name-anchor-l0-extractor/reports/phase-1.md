# Plan 18 Phase 1 report

## Outcome

Extractor contract fix for O03-class out-of-span longitude.

## Changes

- `parser/osm_to_parcel_geometry.py` / `parser/kiwiw/mesh.py`: after
  `_lon_delta`, reject `dlon < 0 or dlon >= disc_lon_span` with `None`; remove
  clamp-into-edge. Fixture-precheck comment no longer claims edge columns
  accept clamped out-of-coverage longitudes.
- `parser/tests/test_parcel_geometry.py`: lon-out → `None`; O03 AU L0 case.
- `parser/tests/test_descriptor.py`: O03 + just-outside-span points in mesh≡extractor set.
- `parser/tests/test_name_anchor_o03_extractor.py` (new): synthetic PBF with
  O03 place node + in-span control; spool has no O03 name / no `(0,541)`
  admission; control present once in its cell.
- `parser/tests/test_extractor_scale.py`: oracle road-name count 3→2 when
  roads expected (`WAY_CROSS_180` centroid lon 0.0 now correctly dropped).
- Triage: `rules_other.json` O03 note; `cause_table.md` plan-18 pointer.
  On-disc pin language retained.

## Gates

```
.venv-rp/bin/python -B -m pytest \
  parser/tests/test_parcel_geometry.py \
  parser/tests/test_descriptor.py \
  parser/tests/test_extractor_scale.py \
  parser/tests/test_name_anchor_o03_extractor.py -q
→ 67 passed
```

Contract smoke: O03 / west-of-lo → `None`; in-span control assigns.

## Non-goals held

No encoder / `_cenc.c` / `dv_assign` edits. No G re-encode / full-AU / K1 live
gate. No plan 14 Phases 2–3. No plan 04 Phase 3 close. No 170 / 3-16 / 3-17
reseat. No PR / feature branch.

## Deviations

Flash (pid recorded by executor) implemented code + tests then exited before
commit/EXIT_DONE; executor finished triage docs, IMPLEMENTATION, report,
commit with `Workflow-Phase` trailer, and push/close-out. Tip rebased from
`00cabd8` onto `origin/master` (includes plan 17 close-out and later designs)
before commit.

`WAY_CROSS_180` name drop is the Assumption-4 caller disclosure: centroid
outside span was previously clamp-admitted; now skipped. Road geometry for
that way still splits by in-span points; only the name admission via centroid
changed.
