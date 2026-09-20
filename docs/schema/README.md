# Schema

The authoritative, validated definition of the KIWI-W disc structure as this project
understands it. It is what the writer builds to. It always holds our **best-known
understanding**, drawn from any source (R measurement, tests, the spec, other
repositories), and it says how sure we are of each fact.

It describes the **format**. Differences between the reference disc (R) and a generated
disc (G) belong in the plan ledger, not here.

## Files

| File | Covers |
|---|---|
| `disc-layout.md` | Files on disc, container and volume layer, ALLDATA top-level frame |
| `parcel-management.md` | PDMDH, LMR/BSMR, BMT, parcel placement and order |
| `map-frame.md` | Map Frame header, region list, sub-frame directory (mfde), divided parcels |
| `map-road.md` | Road link records, link flags, node bits |
| `map-background.md` | Background/polygon records, type and display-class vocabulary |
| `map-name.md` | Name records and string types |
| `route-planning.md` | Region data, route-planning frames, ext frames |
| `index-idx.md` | IDX container, STFG, RLXY, record families, state partition |
| `parameters-metadata.md` | Small files, parameters, metadata, copy-through blocks |
| `flags.md` | Every flag across layers: status, R census, OSM source, G value, pending test |
| `UNKNOWNS.md` | Generated index of every row that is not `verified` (do not hand-edit) |

## Row format

Every field, flag or enum row lives in a table with these columns, in this order:

`| Field | Meaning | Status | Evidence | Code |`

- **Field**: offset, width and name (or value, for enum tables).
- **Meaning**: one line.
- **Status**: exactly one of the values below.
- **Evidence**: what backs the status. A repo path in backticks, a spec chapter
  (`spec ch.7.2`), or a census figure with its source.
- **Code**: the module that reads or writes it, in backticks, or `-`.

### Status vocabulary

| Status | Meaning | Evidence required |
|---|---|---|
| `verified` | A check fails if the row is wrong (byte-identical round-trip, R census with a count, spec-conformance test). | A path to the check or census that resolves. |
| `observed` | Seen on R; no test fails if it is wrong. | What was seen, where. |
| `spec-only` | From the specification; not confirmed on this disc. | The spec chapter. |
| `assumed` | We build to it; it is neither observed nor specified. | Why we assume it. |
| `unknown` | Carried verbatim, omitted, or not understood. | What is known about it. |

Nothing is promoted to `verified` on reasoning alone.

## Sources and conflicts

Sources, strongest first: a passing byte-level test on R; a census of R; `kiwiw` code that
round-trips; the spec (`spec/format_english/`); `tools/kiwiread`; analysis. Where sources
disagree, record **both** in the row's Evidence, name the winner, and never resolve
silently. A disagreement that cannot be decided is `unknown`.

## Change rules

1. Learning something updates the schema in the same PR.
2. A change to a field's encoding starts in the schema; code cites the row in its
   docstring.
3. Changing a row's status needs its evidence in the same change.
4. `UNKNOWNS.md` is regenerated, never hand-edited.

## Lint

```
.venv-rp/bin/python parser/tools/lint_schema.py          # check
.venv-rp/bin/python parser/tools/lint_schema.py --write  # regenerate UNKNOWNS.md
```

It checks the column header, the status vocabulary, that `verified` rows have evidence,
that repo paths in Evidence and Code resolve, and that `UNKNOWNS.md` is current.
