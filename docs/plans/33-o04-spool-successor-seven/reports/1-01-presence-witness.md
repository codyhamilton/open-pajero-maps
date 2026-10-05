# Unit 1-01 handoff

Implemented explicit `--disc g_successor|g_historical|r` probes and `publish`.
The seven-row TSV/JSON preserve full native keys, demander IDs, hashed O04
proof references and the two penultimate strata. Full G pin checks, bounded
preads, hardened sentinel/index resolution, existing G count controls and
existing shape decoding are implemented. Publish replays retained index/frame
bytes and rejects missing, malformed, stale, duplicate or mismatched evidence.
Positive counts are named exceptions. No row receives a disposition.

Verification: the owned synthetic suite passed **31 tests**. Cases cover the
three format sentinel branches, resolved zero/present polygons, failed lookup,
non-sentinel zero-size block/slot, malformed frame/background structures,
forged zero counts, corrupted byte hashes, missing frames, altered native keys,
wrong pins, stale source/reader hashes, duplicate rows, and all-seven publish.
The exact test command is in `../phase1_note.md`. Light publish without probes
returned the expected exit 2 and wrote all seven exceptions, not absence claims.

No scope departures. The worker's binding instruction forbids disc/spool opens,
so the real byte/decode witnesses are intentionally pending. Retained scratch-14
summaries lack raw index/frame bytes for replay and were not promoted to fresh
absence evidence. The current table is a pending evidence census, not the
verified Phase-1 outcome. All changes are uncommitted as instructed.

Execute must run the three guarded commands listed exactly in
`../phase1_note.md`, then its light publish command. Resolve every named
exception before recording Phase 1 as verified. A successful handoff has seven
absence-proven rows and no exceptions. A positive covering-frame count needs
cell-local investigation; a sparse tile may alias neighbouring cells, so the
probe conservatively blocks closure on any positive count. A byte budget or
strict structure failure also blocks closure and must be investigated, never
treated as absence. R uses its cited historical pin rather than a fresh hash.
No production-disc behavior was validated in this worker run.
