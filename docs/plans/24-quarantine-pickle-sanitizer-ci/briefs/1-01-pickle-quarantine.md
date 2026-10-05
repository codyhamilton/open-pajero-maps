# Brief 1-01 — Pickle quarantine + allowlist + security sketch

Assigned: OpenCode DeepSeek Flash (Execute may implement inline).

## Goal

Land plan 24 Phase 1: trust-gate every legacy `pickle.load`, offline allowlist
oracle, sketch Actions job that runs only that oracle, docs.

## Do

1. Quarantine `parser/kiwiw/spool_legacy.py`: explicit trust enablement before any
   `pickle.load`; clear error otherwise.
2. Gate `parser/tools/convert_spool.py` with `--i-trust-this-pickle`.
3. Enable trust inside `test_spool_binary` only; keep lossless proof.
4. Add `parser/tests/test_pickle_quarantine.py` (allowlist + production freeze).
5. Add `.github/workflows/security-sketch.yml` — oracle only, not full suite.
6. Warn on `osm_to_address_index` dump-only `.pkl`; no load API.
7. Update ARCHITECTURE / provenance / WORKFLOW (sketch vs heavy vs future CI;
   ASan not default `cbuild`).

## Do not

- Draw plan 06 full pytest+C(+Perth) gate.
- Encode, K1, cell_local, full-AU, disc mount as acceptance.
- Reseat 170 / 3-16 / 3-17; claim Phase 3 / WP5.
- Touch `output/scratch-3-11/G_new`; track `.venv-rp`.
- Mega-close Assessor Security / full-disc.
