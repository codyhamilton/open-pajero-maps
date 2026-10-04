# Zero-row classify verification

The worker demonstrated five failing regressions before the fix; the targeted
triage/inventory suite then passed 22 tests. The orchestrator ran:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B -m pytest parser/tests/test_k1_triage.py parser/tests/test_perf_inventory.py parser/tests/test_dump_join_memory.py parser/tests/test_extend_s02_memory.py -q
flock output/.heavy.lock /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B output/scratch-08-zero-row-classify/verify.py
cmp output/scratch-08-zero-row-classify/disc.before.sha256 output/scratch-08-zero-row-classify/disc.after.sha256
git diff --check
```

Test result: **41 passed in 11.89s**. The existing default zero-row rejections
in dump join and extension consumers remain covered.

| Existing kind view | Exit | Manifest / assigned / unclassified / cause sum | Result |
| --- | ---: | --- | --- |
| background | 0 | 0 / 0 / 0 / 0 | PARTITION OK for this kind |
| background_boundary | 0 | 0 / 0 / 0 / 0 | PARTITION OK for this kind |
| name_anchor | 0 | 1 / 1 / 0 / 1 | All output bytes match the 3-17 reference |

The two empty inputs were statted, opened, and read by classify; assignments are
zero bytes and count/group tables contain only their headers. Regressions also
cover a mixed empty/non-empty failure partition, stale assignment replacement,
and non-empty, malformed, missing, and unreadable files declared empty.

The replay used unchanged 3-17 manifest/rule projections over the unchanged
3-14 dump binaries. `inputs.json` and `verification.json` retain hashes,
commands, and results under the new ignored scratch directory. Reproduction is
documented in `docs/provenance.md`.

The existing disc SHA256 was measured before and after replay under the shared
heavy lock; both equal
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
No encode, checker, full dump, completeness recount, or rule edit was performed.
The changed-path audit excludes plan 07, the 3-17 record, and the 3-16 packet.
This replay proves the selected kind views; it makes no all-kind partition claim.
