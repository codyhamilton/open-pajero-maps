# Demand attribution — 3-01

Disc SHA256: `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.

Attributed 26/776 keys; error rows: 0.
One TSV row per distinct shape. Branch is the first matching a/b/c branch;
JSON records all matching branches. Shape ordinals and tall IDs are zero-based.

Per-branch distinct-demander counts: {'b': 27, 'c': 1}.
All matching branch counts (overlap allowed): {'b': 27, 'c': 1}.
Keys with all demanders unrepresentable (3-03 prediction): 26.

## dump_row 335

- `tall=39083:L0:home(1379,1143):ordinal=0`: branch `c`, 4 coordinates,
  bbox raw `[5650352.1247232, 5650750.806425601, 4649447.227391999, 4718873.149439999]`, home delta `[0, 5]`;
  TOL-only centre hit: True; mirror emits: False;
  production C records: 0; representable: False.

The ±32 search missed this shape because it tested strict per-ring EO,
which excludes the centre. Region.inside accepts it with TOL=0.5 along
the horizontal scan line. Its home is only five rows away; the radius
was sufficient. Tall selection supplies the shape to the checking block.

At centre y=4663296, the triangle's horizontal interval is
[5650431.651297411, 5650431.651967155] raw: width 0.000669744 raw.
The centre x=5650432 lies 0.348032845 raw to its right, within TOL=0.5.
The clipped, densified footprint collapses to q=2, area2=0.

## Representable-demand exceptions

None.

## Findings and errors

[]
Mirror/C disagreements: [].
C/Python checker disagreements: [].

## Timing stop and remaining work

The 25-key wrapper logged 19.377 s, projecting 601.5 s (10.02 min) for
776 keys. This meets the brief's ≥10 min stop condition. Its internal
script timer logged 18.889 s, projecting 586.3 s; the wrapper includes
startup and is the authoritative elapsed cost used for the stop decision.
The full run was not attempted. Counts above cover only dump_rows 0–24
and 335; the other 750 keys have no attribution or prediction yet.
