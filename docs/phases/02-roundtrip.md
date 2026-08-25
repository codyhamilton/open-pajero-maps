# Phase 2 — Writer prototype: round-trip the existing disc

## Goal
Prove format understanding by re-serializing the parsed intermediate representation
back into byte-identical (or documented-diff-only) files, then burning and testing
that regenerated-but-unchanged disc in the vehicle.

## Status: first real round-trip wins landed (2026-08-25)

Targeted the small metadata/manifest files decoded in Phase 1 sub-task 3
(`parser/kiwiw/misc.py`) rather than `ALLDATA.KWI` or the `IDX/` search
frames — these are the smallest, most fully-understood files on the disc,
and several of them have spec-confirmed, fixed-width binary layouts with no
lossy text formatting in the way. `ALLDATA.KWI` (main map data) and the
`IDX/` search-index chain are both real parsers with real findings, but
neither has an inverse/writer yet — out of scope for this pass, see "Not
attempted yet" below.

### Methodology

New module `parser/kiwiw/misc_writer.py` provides one `write_*` function per
`parse_*` function in `parser/kiwiw/misc.py` — each takes the dataclass (or
dict, for the plain-text files) that the parser produces and re-emits bytes.
New harness `parser/roundtrip_misc.py` reads each target file from the real
mounted disc (`/run/media/codyh/464210-8480` by default, override with
`--root`), parses it, re-serializes it, and byte-diffs the result against
the original — reporting either `PASS` (exact match) or `FAIL` with the
first differing offset and a short hex window of expected-vs-actual bytes.
A matching regression test, `parser/tests/test_roundtrip_misc.py`, follows
the existing `test_mesh.py` convention (skips cleanly if the disc isn't
mounted, runs standalone with plain `python3` — no pytest dependency is
installed in this environment).

### Results

Run against the real mounted disc:

```
PASS  PCT2MNG.KWI: byte-identical (174 bytes)
PASS  COVERAGE.BIN: byte-identical (21 bytes)
PASS  DN/CLUSTER.DAT: byte-identical (272 bytes)
PASS  COUNTRY.KWI: byte-identical (113 bytes)
FAIL  SPEC.KWI: original 34 bytes, rebuilt 35 bytes
FAIL  METADATA.KWI: original 164 bytes, rebuilt 166 bytes
PASS  VERSION.TXT: byte-identical (19 bytes)

5/7 files byte-identical
```

**5 of 7 targeted files are genuinely byte-identical round-trips** — a real,
diffable win, not a plausible-looking approximation:

- **`PCT2MNG.KWI`** (174 bytes, the image-file-pair manifest) — fully
  spec-confirmed fixed-width binary records
  (`[group_id:u32][role:u16][reserved:u32][variant:u16][filename:12B]`);
  round-trips exactly.
- **`COVERAGE.BIN`** (21 bytes) — `[u16][u16][u8 len][path]`; exact.
- **`DN/CLUSTER.DAT`** (272 bytes) — 14 header words + 61 key/value pairs,
  all captured as plain integers with nothing discarded; exact.
- **`COUNTRY.KWI`** (113 bytes) — interesting case: this file's *trailing*
  block (a repeating TLV-like pattern, `01 2d 00` "no translation"
  placeholders and `00 05 AUSTRALIA 00` name records) is explicitly flagged
  in `docs/phases/01-format-analysis.md` as "not spec-confirmed... offered
  as a hypothesis only." It round-trips exactly anyway, because
  `parse_country_kwi` was already careful to store that unconfirmed tail
  **verbatim** (`CountryFile.raw_tail`) rather than force it through a lossy
  reinterpretation — the writer reattaches `raw_tail` unchanged rather than
  regenerating it from the (lossier) `name_records` field. This is a useful
  lesson for the rest of Phase 2: a parser that preserves "I don't fully
  understand this part" as raw bytes, instead of round-tripping it through
  a partial model, is much easier to invert exactly.
- **`VERSION.TXT`** (19 bytes) — single `KEY=value;` statement, no
  whitespace irregularities to lose; exact.

**2 documented, honest failures — not silently declared "close enough":**

- **`SPEC.KWI`** and **`METADATA.KWI`** fail by 1-2 bytes each. Root cause:
  `parse_bnf_metadata` (in `kiwiw/misc.py`, Phase 1 code, intentionally
  *not* modified in this pass since it's shared/validated elsewhere) splits
  the file's `KEY ::= value ;` statements into a plain `dict[str, str]`,
  stripping the surrounding whitespace. The real files have *irregular*
  whitespace that the dict can't remember: `METADATA.KWI` has a stray
  leading space before `CHCD` that `LANG` doesn't have
  (`"...Finish,Australian English ; CHCD ::=ISO 8859-1 ;..."`), and every
  statement has a space before its `;` but no consistent spacing around
  `::=`. `write_bnf_metadata` emits a canonical, consistently-spaced form
  instead, which is provably different byte-for-byte (confirmed by the
  harness — see the FAIL lines above showing the exact offset and hex
  bytes). This is flagged as a real gap, not fudged: if a byte-identical
  round-trip of these two files is wanted, `parse_bnf_metadata`'s
  intermediate representation needs to capture either the raw per-statement
  text or an explicit whitespace-formatting model, and this pass
  deliberately did not touch that shared Phase 1 module to keep scope
  disciplined.

### What this proves, and what it doesn't

**Proves:** for files with a fully-understood, fixed-width (or
verbatim-preserved-unknown-tail) binary structure, the "parse then
serialize" round-trip genuinely works byte-for-byte on real disc data, not
just in the abstract — this is the concrete evidence Phase 2 exists to
produce. It also surfaced a real, generalizable finding (preserve unconfirmed
regions verbatim rather than reinterpreting them) that should inform how any
future Phase 2 work on `ALLDATA.KWI`/`IDX/*` handles their own remaining
uncertain fields (e.g. `ALLDATA.KWI`'s Additional Data / Data Extended
region-list bytes that `parcel.py` currently skips past without decoding,
per Phase 1's findings — those are exactly the kind of thing that should be
captured as raw bytes if a writer is ever built for them).

**Doesn't prove:** nothing about `ALLDATA.KWI` (main map data — roads,
background, names) or any of the `IDX/*.IDX` search-index files. Those are
the two largest and most format-critical parts of the disc, and neither has
a writer yet. They're also each substantially harder than the files
targeted here:

- `ALLDATA.KWI`'s container/mesh layer (volume header, LMR/BSMR/BMT tables)
  is "high confidence" per Phase 1, but road-type codes are only ~50%
  identified, background/parcel-local coordinate decoding is only "medium
  confidence" (inferred, not spec-confirmed), several record kinds are
  explicitly skipped-past/undecoded (Name Data Frame string types 0/2/3/7,
  Additional Data records, Data Extended region bytes), and — per the
  2026-08-25 decision log entry — `mesh.py`'s parcel-selection/iteration-order
  bug means parcel *addressing* itself isn't fully verified yet. A writer
  for this file needs those gaps closed (or, per the lesson above, the
  undecoded parts preserved verbatim) before it could plausibly round-trip.
- The `IDX/*.IDX` search-index chain (`search_frame.py`/`index_data.py`) is
  now solved for *reading* real street/POI data end-to-end, but a writer
  would additionally need to regenerate `DCTF` definition frames, `STFG`
  presence bitmaps, and the SWS-halved additional-address indirection
  tables self-consistently — untried, and a substantially bigger lift than
  anything attempted in this pass.
- `LOADING.KWI`'s ~31MB module-code payload, the `*256*`/`VAR256D`/
  `KGRPDAT`/`DICVCE56` image/voice files, and `COVERAGE/AUC.BMP` were all
  flagged in Phase 1 as "copy through unchanged" candidates for Phase 4 —
  no writer was attempted for them here since the plan is to pass their
  bytes through untouched rather than regenerate them, so a round-trip
  writer has no purpose for these.

### What remains before Phase 2 can be considered complete

1. Fix (or explicitly scope out) the `SPEC.KWI`/`METADATA.KWI` whitespace
   loss — either by capturing raw per-statement text in
   `parse_bnf_metadata`'s intermediate representation, or by documenting
   that these two files will always be regenerated fresh (not byte-matched)
   in Phase 4, in which case exact round-trip of the *original's* quirky
   whitespace stops mattering.
2. Attempt a writer for at least one non-trivial `ALLDATA.KWI` structural
   layer (e.g. the volume header + LMR/BSMR tables, which Phase 1 called
   "high confidence") before attempting full parcel/road/background/name
   round-trip, given how much of that file's decode is still
   medium-confidence or explicitly unimplemented.
3. Attempt a writer for the simplest `IDX/*.IDX` structure once the above
   main-map work de-risks the general "write what you've verbatim-preserved"
   approach — likely the `DCTF` definition frame or a single fixed-shape
   record type, not the full self-describing chain.
4. Only after real (not just plausible) round-trip success on a
   representative main-map and index-chain sample should an actual disc
   image be reassembled and burned for in-vehicle testing, per the original
   phase goal.

## Not started yet (unchanged from before this pass)

Full `ALLDATA.KWI` and `IDX/*.IDX` round-trip, disc reassembly, and
in-vehicle testing of a regenerated-but-unchanged disc.
