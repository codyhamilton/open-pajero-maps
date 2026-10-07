# EO face-walk decline diagnostics (plan 48 Phase 1)

- `decline_rings.json` — seed 4314 / N=20000 rings that decline (r359, r8475, r11892, r14503, r19650).
- `dumps/*.json` — `EO_DIAG` arrangement dumps at the EO_DIAG decline site (_cenc.c:~866) (compile probe with `-DEO_DIAG`, `EO_DIAG_OUT=...`).
- `mechanisms.json` — named H1/H2/… from `parser/tools/eo_walk_diag.py`.

Production `_cenc.c` builds omit `-DEO_DIAG` (zero cost). Hook is `#ifdef EO_DIAG` only.
