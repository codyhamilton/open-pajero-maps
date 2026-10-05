# Remediation 01 — establish the scope of the changed-cell completeness claim

Severity: **high**. Finding R1 in `../REVIEW.md`. Independent review of
`ca55630cd3e6e2b04b6cbbedd2f1b21da1dffb91`; plan-31 commits only.

## Defect and location

`oracle_chain.py:87` maps divided leaves to their containing integer base
cell. `iter_frames` retains the leaf path, but `cell_signatures` at line 163
selects only `(level, ix, iy, length, hash)` and sorts the frame multiset.
Consequently it discards which subcell routes to which payload and the
subcell's rational footprint. This is correct for an unordered whole-frame
inventory, but does not establish that every cell whose routed contents
changed appears in the changed-cell list.

Concrete counterexample: base cell `(0,0)` contains two divided leaves with
different payloads A and B. Old routing is `0.0 -> A`, `0.1 -> B`; new routing
is `0.0 -> B`, `0.1 -> A`. Both leaves map to the same integer cell, and both
multisets are `{A,B}`. The cell signatures are equal although the contents
returned for each subcell changed. Changing subdivision footprints can also
preserve this multiset. Absolute DSA relocation is a different case and should
continue to compare equal when routing and payloads are preserved.

The retained 3-14 reports prove **246,123 AU / 795 Perth multiset differences**,
with SHA-pinned lists, zero frame-length fallbacks and unchanged protected
input hashes. They contain no routing/footprint comparison proving that
unchanged multisets hide no such changes. Matching the historical aggregate
counts does not supply that proof. This finding does **not** assert that a
swap occurred on these discs, or that the measured counts/hashes are wrong.

Affected claims: `IMPLEMENTATION.md` Phase 1 verification/outcome;
`phase1_note.md` final measured-result paragraph; and the plan-31 oracle hunk
in `docs/OVERVIEW.md` introduced by `f636cd9` and retained in `ca55630`.
The design requires exact changed-cell/leaf proof, but never signs unordered
frame membership as a complete equivalence of routed cell contents.

## Reproduction without disc reads or a diff

From the repository root, this light in-memory control imports the committed
signature function. The existing `tree_leaves` divided-child test confirms
that both child paths belong to the same base cell.

```python
import hashlib
import runpy
import sqlite3

scope = runpy.run_path('docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py')
signature = scope['cell_signatures']
a = hashlib.sha256(b'AAAAAA').hexdigest()
b = hashlib.sha256(b'BBBBBB').hexdigest()
with sqlite3.connect(':memory:') as db:
    db.execute('CREATE TABLE frames(side TEXT, level INTEGER, ix INTEGER, '
               'iy INTEGER, length INTEGER, hash TEXT, leaf TEXT)')
    db.executemany('INSERT INTO frames VALUES (?,?,?,?,?,?,?)', [
        ('old', 0, 0, 0, 8, a, '0.0'),
        ('old', 0, 0, 0, 8, b, '0.1'),
        ('new', 0, 0, 0, 8, b, '0.0'),
        ('new', 0, 0, 0, 8, a, '0.1'),
    ])
    assert list(signature(db, 'old')) == list(signature(db, 'new'))
```

The review's fuller `output/scratch-31/review/audit.py` also walks synthetic
divided records through `tree_leaves`; `audit.json` records distinct old/new
leaf routing and identical signatures. No image or disc is opened by this
control. The 44 existing permitted tests pass; none establishes the missing
routing invariant.

## Fix approach and ownership

1. Preserve the recorded lists, digests, counts and cell labels. Do not
   re-sign the hops or promote the historical cause census to proof.
2. Resolve the proof gap explicitly: supply supplementary evidence that
   routing/footprints cannot hide any cell changes for the named AU and Perth
   3-14 hops, or carry that unmeasured routing/topology scope as a named
   residual and qualify the complete-identity discharge. The latter is
   consistent with DESIGN Decision 4's residual alternative. A documentation
   change must acknowledge the gap, not merely rename the same complete proof.
3. If adding evidence, compare payload membership at a stable geographic
   footprint, including subdivision geometry. Raw offsets must not enter
   that equivalence. Leaf ordinals alone are insufficient when layouts change.
   A supplementary audit can preserve the existing multiset measurement;
   no K1/checker or tolerance change is authorized.
4. Keep Phase 1's named-unexplained payload cells and other residuals intact.
   Update the owned plan-31 notes/verification claims with the resulting
   scope and evidence. The OVERVIEW owner must apply the corresponding
   correction; this review cannot edit that file.

Allowed implementation surfaces for a separately authorized fixer: the
plan-31 folder and `parser/tests/test_oracle_chain.py`. Other seats own plans
30/32/33/34, `parser/build_alldata.py` and OVERVIEW. No protected disc/spool
mutation, tolerance loosening, checker change, relabel, 3-90, Phase 3 close,
or reseat of 170 / 3-16 / 3-17.

## Done evidence

- The leaf-swap counterexample is either detected by a supplementary
  identity proof or explicitly outside a clearly qualified claim with the
  two full 3-14 hops named as remaining routing/topology residuals.
- If a supplemental measurement is chosen, it demonstrates detection of
  swapped divided payloads and changed footprints, and invariance under
  pure physical relocation and padding changes. Its per-hop evidence has
  paths, SHA-256, coverage/counts and explicit unexplained scope.
- Existing 246,123 / 795 multiset lists and hashes remain intact. Historical
  causes are not silently treated as measured; no Phase 3 close is claimed.
- Owned light tests pass, and the plan verification/OVERVIEW claims describe
  only what the evidence proves.

## Heavy boundary for the orchestrator

No heavy command was run for this finding. Any protected-disc reread requires
the orchestrator's guarded execution with `run_heavy_python.py`, its lock and
fresh outputs (for example beneath `output/scratch-31/review/remediation-01/`).
The exact supplementary command depends on the reviewed approach/tool and
must be supplied by its implementer; no nonexistent command is prescribed
here. The existing AU/Perth `oracle_chain.py diff` commands in
`../phase1_note.md` only reproduce the multiset measurement and cannot alone
discharge this finding. Do not run them as a substitute for routing evidence.
