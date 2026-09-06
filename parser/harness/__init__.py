"""Offline comparison harness for `ALLDATA.KWI` (and, in later units, the
route-planning/index/metadata layers), per `docs/design/target-disc.md`'s
"Evaluation: the offline oracle".

This package is a separate module tree from the encoder/assembler side of
the parser: it must import only the parser's *reading* paths
(`kiwiw.volume`, `kiwiw.parcel`, `kiwiw.parcel_mgmt`, `kiwiw.mesh`,
`kiwiw.disc`, `kiwiw.model`, `kiwiw.bitutils`, `kiwiw.coordconv`,
`kiwiw.roadtypes`, `kiwiw.grid`, and the sub-frame decoders). It must never
import any content-generation module, the whole-file assembler module, any
module whose name ends in a suffix meaning "produces bytes", or any
OSM-extraction module -- so a harness change can never alter a build. See
`parser/tests/test_harness_core.py` (the forbidden-import test spells out
the exact banned name fragments it greps for).
"""
