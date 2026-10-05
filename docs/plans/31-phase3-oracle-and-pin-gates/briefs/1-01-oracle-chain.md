# Brief: 1-01 — re-oracle chain table with exact changed cells

Consumer: Codex `gpt-6.1-sol` (high), sandboxed. Owned paths: `docs/plans/31-phase3-oracle-and-pin-gates/` (new `oracle_chain.py`, `oracle_chain.tsv`, `oracle_chain.json`, `phase1_note.md`, report `reports/1-01-oracle-chain.md`) and the synthetic test `parser/tests/test_oracle_chain.py`. Touch nothing else (not OVERVIEW; Execute narrows it). Commits: none.

## Outcome (DESIGN Phase 1)

A committed chain table, one row per hop, for these hops:
- `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862 → 013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` (unit 3-11);
- `013586b5… → 4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (unit 3-14);
- `4ed9cd80… → 2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae` (plan 29).

Each row carries: full digests, the signing unit, changed-cell (or changed-leaf) count by level, the authoritative list's path and sha256, the confinement claim, and the unexplained count (0, or each one listed). Add Perth hops (`da13a775… → 04be2f6e…` at 3-14; unchanged at plan 29), or mark them N/A with proof.

## Known evidence (verify; do not assume)

- **3-11:** `output/scratch-3-11/Gnew.diff_cells.txt`, recorded sha256 `9f2b0e55…0e5e`, "exactly 37 differing cells, all L0, 37/37 predicted" (`Gnew.expected37.txt`). Also check `Gnew.cells.tsv` and `Gnew.scan.json`.
- **3-14:** plan 04 `IMPLEMENTATION.md` (around L414 and L578) quotes "AU 246,123 (L0 244,060 / L2 1,944 / L6 118 / L8 1), Perth 795 (L0 784 / L2 11), added 0 / removed 0", with an explanation census. Find the authoritative artefacts by read-only listing of `output/` and sibling worktrees (`/home/codyh/workspace/open-pajero-maps*/output`). If no list survives, regenerate: both discs exist (`output/scratch-3-11/G_new`, `output/scratch-14/G_new`). Write a cell-granular streaming diff subcommand in `oracle_chain.py`, generalising `docs/plans/29-k1-name-anchor-failure/diff_disc.py` (bounded reads, frame-to-cell mapping on both layouts). Execute runs it.
- **Plan 29:** `witnesses/successor_diff.json` (146 bytes, L0 (0,541) leaf 928). The plan-29 folder may be collapsing concurrently into `docs/plans/04-c-core-orchestration/triage/name_anchor/`; read from whichever path exists.
- **87a01b14:** inventory whether a pre-3-11 disc survives (read-only `ls`/`find`, sha from sidecar files only). If not, the 3-11 hop's authority is its retained list plus the recorded sha. State whether the list can be byte-checked against the recorded sha256. Regenerating `87a01b14` (a pre-3-11 code build) is out of scope unless trivial; name it as a residual instead.

## Heavy-run rule (binding)

- Never open any `ALLDATA.KWI` or the spool yourself.
- Light reads of small scratch text/JSON lists are fine. Hash them with python.
- Run only your synthetic test, with `--basetemp output/scratch-31/tests`.
- List the exact guarded commands for Execute: `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-31/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py ...`.
- The table is built from measured outputs by a `publish` subcommand.

## Report back

Status, files, tests, the per-hop findings, residuals, and the Execute commands.
