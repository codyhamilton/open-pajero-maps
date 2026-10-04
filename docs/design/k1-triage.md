# K1 classify partitions

`parser/tools/k1_triage.py classify` partitions each dump kind named by its
manifest. A zero-row background or background_boundary kind is a valid zero-row
partition. Existing non-empty kinds retain their rules, assignments, ordering,
and partition semantics.

Classify validates the actual file length against its declared row count. For
an empty kind it also opens the named file, checks the opened descriptor's
length, and reads it before accepting the partition. Missing, inaccessible,
malformed, and non-empty files declared empty cannot produce a successful
partition. An accepted empty kind writes a zero-byte assignment file, replacing
old assignments, and a partition line with all four counts zero. Empty-only
cause and unclassified tables contain their headers.

Classify clears an existing partition file before validating an invocation.
`PARTITION OK` applies to the kinds processed by that invocation. A mixed run
with unclassified non-empty rows still returns `PARTITION FAIL` and exit 1.
These partitions do not establish completeness attribution or close plan 04.

The empty-file opt-in belongs to classify. `dump_io.file_rows` rejects zero rows
by default, and the shared windowed reader/writers retain their zero-row guards.

## Malformed rules JSON

`cmd_classify` reports syntactically invalid rules JSON through the same input
validation path as schema-invalid rules: exit 2, no uncaught traceback, and no
stale success partition. Partition cleanup runs before rules loading. Valid
rules and empty-kind classification retain their existing behavior. Plan 09
landed this contract at `07c3918ace0f37b3c1a47c8e069c6e0e1a9cd783`.

## Triage report grouping

Summary, classify and enumerate group by declared field values. Their internal
structured keys are packed, with no unnamed padding bytes: uniqueness,
indexed copies and retained keys must preserve the same byte identity.
Retained keys own their storage. The aligned on-disk dump layout is separate
from these internal report keys and retains its manifest-defined offsets.

Summary group/source counts and TSV bytes are invariant across repeated runs
and window sizes. Source NaN sentinels retain their canonical key and print as
`nan`; formatting, ordering and the source-table cap remain unchanged.
Classify rule assignments and enumerate row totals use the same group identity.
This report contract does not establish cause attribution or close plan 04.
