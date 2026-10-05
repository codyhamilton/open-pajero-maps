# Plan 26 Phase 1 implementation

## Delivered

- `parser/refdata/state_partitions.json` — seven-row table (201 WA … 207 TAS)
- `parser/kiwiw/state_partitions.py` — loader + `resolve_suffix`
- `parser/tests/test_search_fixtures_seven_state.py` — table oracle + per-suffix
  synthetic `build_index` + SRMX round-trip + SADSR/POISR basename stubs
- `parser/tests/test_address_extractor.py` — WA bbox scoped to this module’s
  WA-only synthetics; non-WA fixtures owned by the seven-state module
- `parser/demo_address_search.py` — `--state` / `--suffix` (default 201 WA
  honesty note)
- Docs: `docs/schema/index-idx.md`, `docs/OVERVIEW.md` WP3 row (still Not
  started), `parser/refdata/README.md`

## Explicit non-claims

Offline seven-state fixtures ≠ WP3 complete ≠ Australia-wide MMCS proof.
No disc mount, no full-AU encode, no heavy.lock, no WP3 writers, no POISR
decoder bugfix, no Phase 3 / plan 04 P4–6 / plan 06, no 170 / 3-16 / 3-17
reseat.
