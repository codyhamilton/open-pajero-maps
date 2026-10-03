# Completeness 3-16 — 89-key original-spool window counterfactual

Unit 3-16 only; [brief](../briefs/3-16-completeness-89-window-cf.md).
Local Codex Sol; branch `feat/3-16-completeness-89-window-cf`; base
`9b44b595787656ba0311dd5c1641aa1d588d5310`. Evidence is private,
git-ignored `output/scratch-3-16/`.

## Pre-edit checks

- C1 PASS: `git merge-base --is-ancestor 6b8a68a HEAD` succeeds.
- C2 PASS: science commit `7a12618` identifies the retained 3-15 packet.
  `open-pajero-maps-3-15/output/scratch-3-15/contract_comparison.json`,
  filtered only to `set == added_89`, supplies 89 unique full keys;
  `mechanism_776_recomputed.jsonl` supplies their meeting-source identities.
  `keys89.json` copies only these rows. No disc diff or completeness census.
- C3: cited 3-15 arithmetic, not recomputed:
  **776 = O01 363 + O05 132 + O04 7 + unattributed 274;
  key churn = 687 shared + 89 added + 52 cleared.**

## Counterfactual and its limits

The 3-15 claim is contract-level: a complex source ring emits under the legacy
probe and emits nothing under EO stitch. Its `contract_comparison.json` uses a
nominal raw cell frame, rather than an original-spool builder window. It names
an EO-stitch side-effect, but no particular faulty C statement or proposed patch.
The tested hypothesis here is that complex-ring stitching loses a representable
piece of the original even-odd region.

For each enumerated key `(0, ix, iy, type, p0…p6, shape)`, build the one-cell,
half-open window `(0, ix, iy, ix+1, iy+1)` from the unchanged original spool with
the unchanged production encoder. Compare target-cell frames byte-for-byte with
the stored 3-14 AU disc, allowing only zero sector padding. Decode the frames
through C D1 and require the target class-2 type to be absent; C K1 against the
original spool must contain the target completeness failure. A baseline that
cannot satisfy these controls is **untested**, never fail.

The intervention bypasses complex-ring stitching by supplying the original
ring's exact rational bounded EO faces separately to the same builder. It uses
the retained 3-13 `split.decompose` algorithm directly on original spool degree
doubles, then serializes face vertices back to doubles. It preserves the closing
chord, the even-odd region, class, type, mult_const, flags and labels. It does not
move an outline to make a demanded piece larger. The private spool replaces only
the 34 meeting source rings named by these 89 keys; all other background records,
road/name columns and remote spool sources remain available. One private L0 copy
is shared across these bounded windows; no full disc is encoded.

The counterfactual uses the same production clip/densify/round, routing and frame
assembly as its baseline. C D1 supplies the target geometry/record-byte witness;
C K1 checks the counterfactual disc against the **original** spool. No checker
rule or tolerance changes. Any target piece that reappears triggers immediate
stop, leaving all subsequent keys explicitly untested. A fail means this bypass
does not restore the piece; it does not exclude every conceivable C patch.

## Outcome

**Status: done. Gate (b): 0 pass / 89 fail / 0 untested.**
All 89 one-cell original-spool baselines pass the 3-14 frame byte gate.
All 89 counterfactual frames are byte-identical to their baselines, emit zero
target-class records, and retain the exact original completeness key under K1
against the original spool. The window run completed in **1,213.8 s**.

The private intervention decomposes 34 source rings into 156 EO faces. The
cold audit checks every full key, every before/after dump and decoded witness,
frame equality, and exact original/serialized-face interior witnesses. Maximum
face-coordinate serialization error is **1.8617682673836184e-9 raw units**.
Original source-home record hashes and the original L0 index hash remain equal
at the end of the run. The retained legacy probe, fed original spool degrees,
still emits for **89/89** keys; the legacy-vs-stitch emission difference remains
real at contract level. It is not evidence that a valid missing EO piece can
be recovered: the topology-preserving window intervention restores none.

Disposition: **accept-with-honesty for all 89 tested keys**. The 3-15
"build regression" claim does not survive this counterfactual as a recoverable
EO-stitch defect. No pass is strong enough to justify a later C amendment;
no new representability witness is produced. Design gate (c) is unchanged.
**Untested keys: none.** No rule or ledger reclassification is implied.

Every full key, half-open window, source identity, outcome, frame SHA and witness
path is retained in [completeness_3-16_outcomes.tsv](completeness_3-16_outcomes.tsv).
The table separately labels sector-padded frame hashes and unpadded raw
frame-dump hashes; each pair is equal before/after. Per-window discs/dumps
remain scratch evidence. `key_00` is
`(0,906,1225,291,0,0,0,0,0,0,0,-1)`; its baseline and counterfactual padded frame
SHA is `b71240ecd3a04672c894a3476345ee13adf7a65988a2f5e8aac8e01cf142ca28`.

## Evidence and reproduction

`inputs.json` pins the key packet SHA
`1fe735cf9ee4fa9f1cdd62983afc49d28da5e26e5358d86df62f83fb8c3636a2`, meeting
source packet SHA `bd123cd75b1370340a23167ec9dd3d8a1b8810185fa33427b9777f38964d99ea`,
and stored 3-14 AU disc SHA
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
`source_changes.json`, `home_audit.json`, `region_audit.json`,
`legacy_spool_degree_control.json`, `results.json`, `tally.json`,
`audit_summary.json` and `SHA256SUMS` retain the supporting records. Each
`key_NN/` contains `baseline_byte_gate.json`, `outcome.json` and
`original/` + `faces/` frame bytes, C geometry witnesses, original-spool K1 JSON
and completeness dumps.

The private `run.py` and copied `split.py` record the exact transformation and
builder/K1 calls. To repeat without touching retained evidence, use a fresh
sibling worktree at the same base, copy `keys89.json`, `run.py`, `split.py` and
`audit.py` into its fresh `output/scratch-3-16/`, and link `output/.heavy.lock`
to the main checkout lock. From that worktree, under `flock output/.heavy.lock`, use
`env PYTHONDONTWRITEBYTECODE=1 /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python
output/scratch-3-16/run.py` on a **fresh** scratch destination (the script refuses
to overwrite its private spool/windows). Audit retained results with the same
command ending in `audit.py`. Compile-on-demand points only to private
`scratch-3-16/libkiwiw.so`, using unchanged production sources. The heavy lock
links to the main checkout's lock. All builds and K1 runs use **one worker**;
compilation is serial. No full-AU encode and no cache drops.

## Deviations and boundary

The packet supplies a contract-level defect category, not a localized C defect.
The intervention is therefore a geometry-preserving bypass of complex-ring
stitching, not a proposed encoder patch. This limit is explicit rather than
silently promoting the 3-15 attribution to a byte-pinned build fix. No other
scope deviation. No encoder/checker/rule diff; no O07 registration; no existing
oracle overwritten; no historic attribution or 9,064-row ledger reopened.
The final cold audit reports PASS. Phase 3 remains open; Execute owns landing.
