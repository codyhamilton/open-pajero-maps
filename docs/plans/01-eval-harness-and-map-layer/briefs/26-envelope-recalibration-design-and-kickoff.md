# Brief: 26 — Envelope recalibration: rebuild #3 KICKOFF ONLY (revised 2026-09-19)

Supersedes the original bundled 26 (design+implement+kickoff), which stopped at its escape
valve (see IMPLEMENTATION.md, unit 26). The design is now split out: **26a** (name-emission
decoupling + name recalibration) and **26c** (parcel_count occupancy diagnosis/fill) land first,
committed and pushed. This unit is now only the kickoff, in the 15/25 wait-split shape.
Owned paths: none in the repo (writes `/tmp/wp1-unit26-logs/`, clears `output/`).
Do not edit code or `selection.json`. Depends on: 26a and 26c committed (`git log` confirms
both; if 26c ended in the "declared deviation" branch it counts as done) and the concurrent
assembler/PDMDH work committed. Runs alongside: nothing.

## Steps
1. Copy `output/report.json` (if present) to `/tmp/wp1-unit26-prior-report.json` (already
   exists from the aborted attempt; keep it).
2. `.venv-rp/bin/python -m pytest parser/tests -q` must pass on the committed tree.
3. Disk check: `df -h /home`, `du -sh output/`; after `rm -rf output/` need comfortably more
   than ~6.9 GB spool + ~0.8 GB `ALLDATA.KWI` (+ 26c's filled empty frames, use 26c's capacity
   number) + margin. Stop and report if not adequate.
4. `rm -rf output/`, then start the pipeline exactly as brief 25 does (nohup, logs in
   `/tmp/wp1-unit26-logs/`: extract then `build_alldata.py`, both under `/usr/bin/time -v`).
5. One liveness check (`pgrep -f osm_to_parcel_geometry.py`); end the turn. Do not poll.

## Report back
Commit SHAs of 26a/26c verified, disk numbers and go/no-go, PIDs, log paths.
