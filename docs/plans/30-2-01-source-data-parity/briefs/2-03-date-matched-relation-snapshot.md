# Brief: 2-03 — resolve the 4 conflict-open rows with the date-matched relation snapshot

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths:
- `docs/plans/30-2-01-source-data-parity/`: edit `disposition.py`; new report
  `reports/2-03-date-matched-relation-snapshot.md`; new `phase2_snapshot.md`.
  `disposition.tsv` and `disposition_summary.json` are regenerated only by
  Execute's guarded `publish`.
- `parser/tests/test_parity_disposition.py`.

Touch nothing else. Commits: none.

## Why

Unit 2-02 left **338 supply-path / 0 unfixable-proven / 4 conflict-open**:
dump_row 246 (834,886; code 321), 396 (2049,1224; 288), 397 (2050,1224; 288)
and 775 (1363,1958; 288). None has an in-cell supply witness, and 47 relation
gaps (39 common to all four) block a negative. `open_rows_account.md` gives
the per-row lists.

Design ruled option (a): DESIGN.md § Amendment 1. Execute has proven the
class-1 root cause, extract clipping: all 3,619 missing member ways existed
at 2026-08-24T20:20:50Z and lie outside the extract polygon
(`missing_way_attic_proof.json`). Execute fetched a date-matched Overpass
attic snapshot of the 61 relations in `relation_requests.json`. It covers:

- the relations themselves (tags, members, version, timestamp);
- their direct child relations;
- every member way of both, with node ids and coordinates;
- member nodes.

It was then normalised into one canonical, sha256-pinned file. The path, sha
and schema are in `phase2_snapshot_pin.json`, written by Execute before you
start.

## Outcome

1. **Snapshot input on `pbf-cache`.**
   - Add `--relation-snapshot <path>` and `--relation-snapshot-sha256 <hex>`.
     Verify the digest and schema before use; refuse a mismatch.
   - Record the snapshot path and sha as a declared input in the result
     document and in `inputs_sha256`.
   - Without the flag, behaviour and outputs are unchanged.
2. **Use it only to supply member geometry for the 61 relations**
   (DESIGN Amendment 1 §2). Fill the existing `full` hook in `pbf_cache`, or
   an equivalent:
   - **Relation in the retained cache:** take tags and members from the cache
     (the pinned PBF). The snapshot's member list must equal the cache's.
     If it differs, the snapshot is not used for that relation; record a
     `snapshot-member-mismatch` gap. Way geometry comes from the cache where
     present and from the snapshot only for absent ways. A node shared by a
     cache way and a snapshot way must have identical coordinates.
   - **Relation the legacy cache never retained** (member limit: 4095122,
     15480206, 16308779, 16308787, 16308826): tags and members may come from
     the snapshot, which is date-matched, but say so per relation in the
     proof log.
   - **Nested area relations** (12026353, 18183905, 18194886): when every
     descendant way is in the snapshot or the cache, the union bbox of those
     ways is a sound bound for the parent's area. Use it for
     outside-window negatives, and assemble child relations as their own
     sources when they carry a code. Otherwise keep the gap.
   - **Vertex-limit relations** (80500 and others): with complete geometry,
     use the existing boundary-clipped production-C witness path. You may
     raise caps per relation within plan-25 memory guards, with topology
     validated; state the caps.
   - Relations outside the 61, and any feature not in the snapshot, are
     never added.
3. **Re-decide every row with the same rules.**
   - Positives override.
   - A negative needs every probe complete, with no gap touching that row.
   - `unfixable-proven` only by proving that no feature of the demanded type
     from the date-matched source reaches the cell (Amendment 1 §4), under
     an allowed cause class.
   - Option (b) is not available.
   - The 338 supply-path rows must not regress. Explain any change.
4. **Synthetic tests.** Cover each of these:
   - a sha mismatch is refused;
   - a member-list mismatch becomes a gap and the snapshot is not used;
   - a missing way supplied by the snapshot completes a ring;
   - a shared-node coordinate conflict is refused;
   - a non-requested relation in the snapshot is ignored;
   - a nested parent is bounded only when all descendant ways are present;
   - the no-flag output is identical.

   Run only `parser/tests/test_parity_disposition.py` and
   `parser/tests/test_parity_fingerprint.py`, with
   `--basetemp output/scratch-30/tests-p2d`.
5. **Commands for Execute.** List the exact serial guarded commands, then
   `inventory` (if needed) and `publish` to fresh output names
   (`disposition_pbf_r3.*`). Use the form
   `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/p2d_<name>.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py …`.
6. **Report** (`reports/2-03-…`): what changed, the rule for each gap
   class, and the expected effect on each of the 4 rows. `phase2_snapshot.md`
   states the snapshot's role and its limits.

## Rules

- Never open any `ALLDATA.KWI`, the R disc, the spool or the PBF. You may
  read the retained cache
  (`output/scratch-30/p2_pbf_cache_01/geometry.sqlite`, read-only URI) and
  the snapshot with small bounded reads. Do not run `pbf-cache` on real
  inputs; Execute runs it under the lock.
- No network access, no fetching, no vocabulary, extractor, encoder,
  selection or disc change, and no R geometry.
- Keep `output/scratch-30/p2_pbf_cache_01` and the PBF untouched.

## Not done

No disc change, no OVERVIEW edit (Execute), no Phase 3 close.
