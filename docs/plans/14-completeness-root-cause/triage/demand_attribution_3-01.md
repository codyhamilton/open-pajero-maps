# Demand attribution — 3-01

Disc SHA256: `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.

Attributed 776/776 keys; error rows: 0.
One TSV row per distinct shape. Branch is the first matching a/b/c branch;
JSON records all matching branches. Shape ordinals and tall IDs are zero-based.

Per-branch distinct-demander counts: {'b': 797, 'c': 1, 'a': 1}.
All matching branch counts (overlap allowed): {'b': 797, 'c': 1, 'a': 1}.
Keys with all demanders unrepresentable (3-03 prediction): 776.

## dump_row 335

- `tall=39083:L0:home(1379,1143):ordinal=0`: branch `c`, 4 coordinates,
  bbox raw `[5650352.1247232, 5650750.806425601, 4649447.227391999, 4718873.149439999]`, home delta `[0, 5]`;
  TOL-only centre hit: True; mirror emits: False;
  production C records: 0; representable: False.

The ±32 search missed this shape because it tested strict per-ring EO,
which excludes the centre. Region.inside accepts it with TOL=0.5 along
the horizontal scan line. Its home is only five rows away; the radius
was sufficient. Tall selection supplies the shape to the checking block.

## Representable-demand exceptions

None.

## Findings and errors

[]
Mirror/C disagreements: [].
C/Python checker disagreements: [].

**Checker pin (review F6):** this attribution compares raw Python demands with the C missing set of the pre-3-03 checker. Reproduce it at `0b19b5e`, in a throwaway worktree with isolated scratch destinations. From `a890662` on, the C checker filters unrepresentable misses, so the zero-disagreement baseline cannot be reproduced at a later HEAD.
