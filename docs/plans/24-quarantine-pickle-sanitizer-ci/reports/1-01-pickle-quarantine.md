# Report 1-01 — Pickle quarantine + allowlist + security sketch

Status: **done**

## Outcome

Trust gate + allowlist oracle + security-sketch workflow landed on master tip.
Production remains binary spool. Sketch CI does not implement plan 06.

## Evidence

- Allowlist path: `parser/kiwiw/spool_legacy.py`
- Trust API: `enable_legacy_pickle_trust(reason)` / `--i-trust-this-pickle`
- Local: `pytest -q parser/tests/test_pickle_quarantine.py` + `test_spool_binary.py`
- No disc / encode / K1 / Phase 3 claim

## Deviations

None. Execute implemented Phase 1 inline (Flash assigned; one bounded unit).
