# Implementation — 24 quarantine pickle + sanitizer CI sketch

- Tool: Grok Bot / Maps Execute background (plan 24); assigned instance OpenCode DeepSeek Flash
- Started: 2026-10-06 ~00:45 Australia/Brisbane
- Refine: skipped (DESIGN approach known). One phase. Blank `design_id` — no workflow-service post.

## Phase 1 — Pickle quarantine + allowlist oracle + security-sketch CI

**Closed.**

| Artifact | Role |
| --- | --- |
| `parser/kiwiw/spool_legacy.py` | Trust gate: `enable_legacy_pickle_trust` / `LegacyPickleTrustError`; all loads via `_pickle_load` |
| `parser/tools/convert_spool.py` | Requires `--i-trust-this-pickle`; help states operator-trusted local only |
| `parser/tests/test_spool_binary.py` | Autouse fixture enables trust for lossless binary↔legacy proof |
| `parser/tests/test_pickle_quarantine.py` | AST allowlist oracle + production import freeze + trust unit checks |
| `.github/workflows/security-sketch.yml` | Sketch Actions: runs **only** the allowlist oracle (not plan 06) |
| `parser/osm_to_address_index.py` | Dump-only warn: lab-trusted `.pkl`; no in-tree load |
| `docs/ARCHITECTURE.md`, `docs/provenance.md`, `docs/WORKFLOW.md` | Pickle-free production + quarantine + sketch vs heavy vs future CI; ASan not default |

**Allowlist:** `parser/kiwiw/spool_legacy.py` only.

**Production freeze (no `spool_legacy` import):** `build_alldata.py`, `osm_to_parcel_geometry.py`, `quantisation_roundtrip.py`, `golden_capture.py`, `parcel_occupancy.py`.

No encode / K1 / cell_local / full-AU / disc mount as acceptance. No plan 06 full pytest+C gate. No 170 / 3-16 / 3-17 reseat. No Phase 3 / WP5 claim. `output/scratch-3-11/G_new` untouched; `.venv-rp` untracked.
