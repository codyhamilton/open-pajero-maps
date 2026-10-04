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

## Follow-up: malformed rules JSON

`_load_rules` can raise `JSONDecodeError` for syntactically invalid JSON, while
`cmd_classify` catches only `BadRules` in that loading path. This pre-existing
case exits with a traceback rather than the usual input-validation exit 2.
Normalize that error reporting in a separately scoped change, with a regression
that checks exit 2 and the absence of a stale success partition. Partition
cleanup already runs before rules loading; the behavior does not affect valid
empty-kind classification.
