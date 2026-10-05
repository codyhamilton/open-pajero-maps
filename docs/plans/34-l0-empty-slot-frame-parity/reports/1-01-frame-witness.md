# Unit 1-01 frame-witness handoff

Implementation passed synthetic verification and is ready for guarded Execute probes.
Real byte witnesses and Phase 1 closure remain pending; this worker has not
opened any protected disc or live spool.

The disc probe covers all 2,048 L0 blockset-32/block-0 cells on each pinned G
disc and R. It uses the hardened reader from the plan-29 close-out location,
retains replayable index paths and full frame bytes, and records frame identity,
leaf path, class, road/background/name counts and a complete header/content/
zero-padding byte partition. G's full pin is verified before lookup; R's pin
is cited. Failures stay unresolved.

The spool probe streams all L0 source rows with bounded preads, retains own
source records and borrowed background source shapes with absolute index/data
offsets, and uses the existing E1 routing code on one bounded record at a time.
Same-level E1/E2 ownership excludes other spool levels. The publisher replays
index and frame proof, validates retained source bytes and routing, and lists
every G-frame/R-empty cell, including extras requiring Phase 2 disposition.

Synthetic test result: **32 passed in 41.05s**, exit 0, using only
`parser/tests/test_l0_frame_witness.py` with
`--basetemp output/scratch-34/tests`, bytecode disabled and pytest's cache
provider disabled. The exact command is in `commands.md`. Tests cover full
2,048-cell census/replay, an additional G-frame/R-empty cell, historical names,
empty/background/name/road payloads, exact byte partitions, malformed extents,
failed lookups, pin checks before lookup, wrapper/held-lock enforcement,
tampered publication evidence, absolute spool offsets, pre-guard names and
distant E1 background source routing. No other test file was run. The owned-path
`git diff --check` also returned exit 0.
Synthetic routing-library build products are isolated under the requested
test basetemp; the production routing-library path is reserved for Execute.

Departures: none from the unit's implementation rules. The brief's real-disc
witness outcome is deliberately deferred to Execute under the explicit
never-open binding. No commit was made, as instructed. `IMPLEMENTATION.md`
was left to the orchestrator because this worker owns only new plan files.

Execute's remaining work is concrete: run the five commands in
[commands.md](../commands.md); inspect wrapper exit/memory logs and generated
JSON/note; verify actual frame counts, names, payload classes, source rows and
any extra cells; record the phase outcome and commit if appropriate. A failed
probe or publisher is an unresolved investigation, not absence or parity.

Known limitations: R's full pin is historical rather than remeasured. Spool
source relationships are parent-cell inputs before admission, division and
trimming; exact per-record emission and the frame-occupancy cause are Phase 2
work. Records exceeding the explicit 64 MiB pread ceiling fail rather than
load unboundedly. No fix, K1 rerun, O03 reseat or Plan 04 Phase 3 close occurred.
