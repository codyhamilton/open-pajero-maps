# Fixture precheck evidence

- Before the fix: `test_disjoint_fixture_way_avoids_split` failed at the
  original splitting entry point.
- Final six-suite run: 84 passed in 28.41 s, no skips. Suites: extractor_scale,
  parcel_geometry, selection, link_id_registry, spool_binary, name_record_vocab.
- Enabled/bypassed byte equality: three fixture PBF runs, with whole-cell
  margins, roads, names, background and antimeridian coverage.
- Existing full-grid extraction remained covered. `git diff --check` passed.
- All test material was isolated in newly created `/dev/shm` paths. No
  blocked verification, full-disc run or country-scale benchmark was rerun.
