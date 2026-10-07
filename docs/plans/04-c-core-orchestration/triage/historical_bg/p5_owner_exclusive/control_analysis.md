# Plan 44 Phase 1 control analysis (stopped)

## Smoke (`--smoke`, n=12, seed=44)

`agree=3 disagree=9 skip=0 rate=0.25` → `CONTROL_FAIL`.

## Home-with-backgrounds diagnostic (n=60, seed=44)

`agree=19 disagree=41 rate=0.3167`. Every disagreement was `prod_none`. Every unique-producer row then passed the owner-exclusive / new-disc check (`agree` path). So the OE limb works when a byte-exact `33006aa` producer exists; the control population does not supply one often enough.

## Why identity-proven rows miss producers

On cell `(0,1980,896)` leaf `(28,)`: 20 class>0 records → 13 unique producers, 7 none. **All** R01 `identity_proven` rows in that cell sit on shapes 1 and 2 (the producer-none shapes). Shape 1 shares Jaccard 0.65 with home spool bg 1, but clip sizes differ (220 B probe vs 140 B disc) — same source ring, non-byte-identical fragment (edge-heavy: 20/65 verts on the leaf boundary). Shape 2 similarly fragments against the same bg.

So plan 39's identity-proven set is biased toward records that are **not** byte-exact `kw__bg_shape` outputs into the full leaf rect. DESIGN's producer rule (byte-equal clip at `33006aa`) therefore systematically disagrees with that population.

## Neighbourhood widening

`neighbourhood=2..3` recovered 1/9 smoke disagreements. Not sufficient.

## DESIGN gate

> Control: … ≥ 99% must agree … A systematic disagreement stops the phase.

Rate ≪ 0.99 with a single dominant disagreement class (`producer_none` on R01-carrying shapes) → **Phase 1 stopped**. Phase 2 not started. Needs Design revision (producer definition for EO fragments / cover pieces) or a proven alternate control population.
