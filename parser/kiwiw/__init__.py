"""kiwiw - a Python parser for the KIWI-W automotive navigation map format.

Ported and extended from the validated C reference tool at
``tools/kiwiread/kiwiread.c`` (see docs/phases/00-inventory.md for how that
tool was built/validated against the real disc). This package targets the
"Main Map Data Frame" (spec chapters 5, 6, 7) of ``ALLDATA.KWI``:

- ``bitutils``: byte/bitfield helpers shared by every decoder (big-endian
  int decode, the SWS/D "stored-as-half, multiply-by-2" convention, sign
  extension, bitfield extraction, geonum -> decimal degrees).
- ``volume``: Data Volume header (Ch. 5.1) + Management Header Record table,
  and the Parcel Data Management Distribution Header / Level Management
  Record / Block Set Management Record / Block Management Table walk
  (Ch. 6).
- ``mesh``: coordinate -> parcel locator (rewritten from scratch, not a
  port of kiwiread's ``isin()``/global-state approach, to fix the
  antimeridian bug found in Phase 0 and to be reentrant).
- ``road`` / ``background`` / ``name``: Ch. 7.2 / 7.3 / 7.4 sub-frame
  decoders, producing structured dataclasses instead of only rendering to
  SVG.
- ``model``: the shared dataclasses / JSON-serializable IR.
"""
