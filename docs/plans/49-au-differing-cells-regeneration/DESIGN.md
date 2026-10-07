---
design_id:
---

# Regenerate AU.differing_cells.tsv from sha-pinned inputs and compare it with plan 31's list

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ruling (2026-10-06, 19:34 AEST), for R-G8-2-f-a: regenerate it.

1. Rebuild or locate both input discs with shas matching the recorded ones (plan 36's replay reproduces `87a01b14` byte-exactly; check what the original file diffed).
2. Run a pinned, deterministic, tracked diff tool to regenerate the list.
3. Commit it with its input shas, and compare it to plan 31's list.

It stays a named unverifiable residual only if an input disc can't be reproduced to its recorded sha; record the root cause if so. The work is light unless a rebuild is needed; a rebuild runs under flock plus the wrapper at `-j4`.

Constraints:
- Master direct.
- Never relabel.
- No plan 04 Phases 4–6.
- Do not run the 3-90 brief.
- Design grants no waivers.

## Problem

The 3-15 text says "30 O05 and 1 O04 on `AU.differing_cells.tsv` cells were zeroed". The file was a 3-14 unit artefact. It was never committed and no producer is in the repo. Plan 43 proved the forced-zero identity per row with plan 31's `diff-3-14-au.cells.tsv` (`77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f`, 246,123 cells). That leaves the literal equality of the two lists unproven.

**What the original diffed** (the inputs are a design decision, settled from the ground):
- **3-14 adversarial report** (`independent_reviews/3-14/adversarial-67e48d9.md` L37–38): the file had per-cell old and new sizes and SHA256. Three Perth topology cells (`0/828/862`, `0/827/869`, `0/832/856`) appeared "byte-identical (same old/new sizes and SHA256)" to AU rows. It is therefore a **per-cell frame diff of the 3-14 hop**: old = the 3-11 oracle `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, new = the 3-14 disc `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
- The 3-15 use (cells whose `other_mechanism` bytes were inherited into the 3-14 dump) only makes sense for cells changed by 3-14.
- **`87a01b14` (3C-04) is not an input** of this file. Its replay is the basis for the 3C-04 → 3-11 hop, which is plan 31's `diff-3-11-au`.
- **Plan 31's list** was produced by the tracked `triage/oracle_chain/oracle_chain.py diff` on exactly that pair (`oracle_chain.tsv` row AU 3-14: 246,123 changed; L0 244,060 / L2 1,944 / L6 118 / L8 1). It lives at `output/scratch-31/diff-3-14-au.cells.tsv` in the host's 14-completeness worktree, and only its sha is committed.

**Input availability:**
- Plan 36 P3 rebuilt both endpoints at `33006aa` and `d35b565` and "reproduce[d] all four pins" (AU `013586b5`, `4ed9cd80`; Perth both), in throwaway worktrees.
- The retained discs are `scratch-3-11/G_new` (`013586b5`) and `scratch-14/G_new` (`4ed9cd80`), on Cody's host.
- The host has been offline since about 19:19 AEST. Execute runs there once it is back; Design read only GitHub.

**Column format:** `oracle_chain.py diff` writes `level ix iy status old_bytes new_bytes old_cell_sha256 new_cell_sha256 old_leaves new_leaves` (see the committed `evidence/diff-3-11-au.cells.tsv`). Those are the fields the adversarial report describes.

## Solution shape

### Domain: pinned inputs

- **Owns:** `triage/independent_reviews/3-15/conditions/differing_cells/inputs.json`.
- **Contract:**
  1. Locate the retained `013586b5` and `4ed9cd80` discs and hash them.
  2. If either is missing or its sha differs, rebuild it in a throwaway worktree: `013586b5` at `33006aa`, `4ed9cd80` at `d35b565` (plan 36 P3 recipe; `-j4`, under the lock).
  3. Record the path, sha, size and producer commit for each.
  4. If a rebuild cannot reach the recorded sha, stop. The row becomes `unverifiable:<input>-not-reproducible`, with the root cause: the first differing cell and frame of the rebuild against the recorded per-cell shas in plan 31's `cells` columns (or plan 36's container ledger).
- **Non-goals:** new disc producers.

### Domain: regenerated list and comparison

- **Owns:**
  - `triage/independent_reviews/3-15/conditions/differing_cells/AU.differing_cells.tsv`, committed (gz if it exceeds the repo's small-file rule; the sha is of the uncompressed bytes);
  - `regen.json`;
  - `compare.py` → `compare.json`;
  - `README.md`.
- **Contract:**
  1. **Tool:** the tracked `oracle_chain.py diff`, pinned by commit and file sha, in a fresh scratch path with `--old-sha` / `--new-sha` enforced (it refuses on mismatch). It is deterministic: it streams frames to sqlite and writes in sorted order. Determinism is shown by running it twice and getting equal output shas, or by citing an existing test if one covers it.
  2. The regenerated file is named `AU.differing_cells.tsv`. Its header and provenance record that it is the regenerated 3-14 hop diff, not the lost original bytes.
  3. **Comparison with plan 31:**
     - (a) file sha equal to `77ff1d86…` means the lists are literally identical;
     - (b) otherwise, the cell-key set and per-cell old/new sha equality, with every difference listed.
     - Plan 31's file is re-hashed from the host when it is reachable. If it is gone, the comparison is to its committed sha plus the committed per-level counts, and that is recorded.
  4. **Consistency checks:**
     - the 3 Perth-shared cells (adversarial L38) are present, with the stated old/new sizes and shas (from the Perth diff `routed-3-14-perth.json` / container ledger);
     - re-applying plan 43's `forced_zero.py` with the regenerated list gives the same 34 rows.
  5. `residuals.tsv` R-G8-2-f-a moves to `regenerated` (equal), or names the difference with a root cause, or goes to `unverifiable:<root cause>` only by the input rule above.
- **Non-goals:**
  - claiming the lost file's original bytes. Equality to it is inferred from same tool class, same inputs and same fields; the README states that boundary;
  - changing plan 31's list.

## Decisions

1. Plan number 49. Master direct. Two phases.
2. **Inputs are `013586b5 → 4ed9cd80`, not `87a01b14`.** The adversarial report's field description and the 3-15 use both bind the file to the 3-14 hop. Cody's mention of the `87a01b14` replay concerns the hop before. If Cody meant a 3C-04-based diff, add a third input from the plan 36 replay at `b7c7c42`; this is a one-line change to Phase 2.
3. Reuse `oracle_chain.py diff` rather than a new tool. It is tracked, sha-guarded and is plan 31's producer, so equality tests the inputs, not the tool.

## Assumption ledger

### Assumption 1

- **Question:** Was the lost file's cell set "frame bytes differ" rather than "routed footprint differs"?
- **Answer chosen:** Frame bytes. The adversarial report cites sizes and SHA256 equality per cell.
- **Rationale:** `routed-diff` columns are routed shas; the report uses cell bytes.
- **If wrong:** `routed-diff` is also run (plan 31 R1) and both comparisons are committed.

### Assumption 2

- **Question:** Do the retained host discs still exist?
- **Answer chosen:** Probably. Plan 43 used `scratch-14` and plan 36 used both.
- **Rationale:** Recent reads.
- **If wrong:** Phase 1 rebuilds (about 30–40 s each at `-j4`, plus worktree setup).

## Open questions

1. Whether the regenerated TSV (246,123 rows, roughly 40 MB uncompressed) is committed as gz, or kept in scratch with only its sha and a gz excerpt. The repo's evidence convention (`diff-3-11-au.cells.tsv` is committed) suggests committing it as gz.

## Phases

### Phase 1: Inputs located or rebuilt to recorded sha

- **Outcome:** `inputs.json` with both shas equal to the recorded ones, or the residual stated with its root cause.
- **Surfaces:** `triage/independent_reviews/3-15/conditions/differing_cells/`.
- **Approach:** known. **Depends on:** the host being online. **Refine:** skipped.

### Phase 2: Regenerate and compare

- **Outcome:**
  - the regenerated `AU.differing_cells.tsv` committed with its input shas;
  - `compare.json` against plan 31 `77ff1d86…`;
  - the Perth-shared-cell and forced-zero consistency checks done;
  - R-G8-2-f-a discharged or named.
- **Surfaces:** `…/differing_cells/`, `residuals.tsv`, `docs/provenance.md`.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `607e5b6`. Sources:
  - `residuals.tsv` R-G8-2-f, R-G8-2-f-a;
  - `independent_reviews/3-14/adversarial-67e48d9.md` L37–38;
  - `independent_reviews/3-15/REVIEW.md` G3e;
  - `independent_reviews/3-17/conditions/{README.md, forced_zero.py, forced_zero.json}`;
  - `oracle_chain/{oracle_chain.py, oracle_chain.tsv, evidence/}`;
  - plan 36 record L64, L93;
  - plan 31 record L51;
  - `per_rule_phase1_f2_identity.md` L50–62.
- Host not read. Box draft only.
