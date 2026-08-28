# Phase 2 — Writer prototype: round-trip the existing disc

## Goal
Prove format understanding by re-serializing the parsed intermediate representation
back into byte-identical (or documented-diff-only) files, then burning and testing
that regenerated-but-unchanged disc in the vehicle.

## Status: small files 7/7 byte-identical; ALLDATA.KWI container/mesh layer 3/3 byte-identical; IDX search-index structural writer 232/232 checks byte-identical; parcel content writer 8/8 checks byte-identical; ALLDATA.KWI whole-file allocation layer 87/87 in-place + 84/84 de novo (2026-08-28)

Four things have landed since this doc's first section was written, all
further down: the `SPEC.KWI`/`METADATA.KWI` whitespace fix (small files now
7/7), a writer for `ALLDATA.KWI`'s volume-header/LMR/BSMR/BMT layer
(3/3 regions, 25,184 bytes, byte-identical — see "ALLDATA.KWI container
/mesh layer: byte-identical"), a writer for parcel *content* itself: the
Ch. 6 Parcel Management Record a Block Management Table entry addresses,
and the Ch. 7 Map Frame (header + mfde table + road/background/name
sub-frames) a leaf entry of that record points at (see "Parcel content
writer: 8/8 checks byte-identical"), and — the allocation/layout gap all
three of those left explicitly open — a whole-block-set assembler that
decides *where* each structure goes in a from-scratch build and rewrites
its cross-reference pointers accordingly (level 8, all 6 real block sets:
87/87 in-place byte-identical, 84/84 de novo re-parse-consistent; level 6,
block set 0, 227 leaf parcels: 231/231 in-place, 228/228 de novo — see
"Whole-file `ALLDATA.KWI` assembly: allocation/layout layer" below).
Whole-disc reassembly and in-vehicle testing remain outstanding regardless
(see "Not started yet").

## Status: 7/7 small metadata files byte-identical (2026-08-25 update — see below)

The "5/7, 2 documented failures" writeup below is the honest original
result from this phase's first pass. It is superseded, not deleted: a
follow-up pass the same day fixed the `SPEC.KWI`/`METADATA.KWI` whitespace
loss by changing `parse_bnf_metadata`'s intermediate representation (see
"Update: SPEC.KWI/METADATA.KWI whitespace loss fixed" further down). The
original section is left intact below for the record.

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

## ALLDATA.KWI container/mesh layer: byte-identical (2026-08-25)

Second Phase 2 pass, taking item 2 of the "what remains" list below: a
writer for one non-trivial `ALLDATA.KWI` structural layer — the volume
header and the LMR/BSMR/BMT block tables Phase 1 called "high confidence" —
*without* attempting parcel content (roads, background geometry, names),
which stays deferred.

New code: `parser/kiwiw/volume_writer.py` (inverse of `parser/kiwiw/volume.py`),
parse-side additions in `volume.py`/`model.py`/`bitutils.py` described
below, harness `parser/roundtrip_alldata_header.py`, regression test
`parser/tests/test_roundtrip_alldata_header.py`.

### Result

Run against the real mounted disc (`/run/media/codyh/464210-8480`):

```
PASS  Data Volume (Ch. 5.1): byte-identical (2048 bytes at file offset 0)
      coverage: 354/2048 bytes (17.3%) rebuilt from decoded fields, 1694 carried verbatim (27 of those non-zero)
PASS  Management Header Table (Ch. 5.2): byte-identical (2048 bytes at file offset 2048)
      coverage: 2034/2048 bytes (99.3%) rebuilt from decoded fields, 14 carried verbatim (0 of those non-zero)
      13 of 113 management header records point at real data (highest index 34)
PASS  Parcel-related Data Management Record: PDMDH + LMR + BSMR + BMT (Ch. 6): byte-identical (21088 bytes at file offset 6144)
      coverage: 21066/21088 bytes (99.9%) rebuilt from decoded fields, 22 carried verbatim (0 of those non-zero)
      7 levels, 601 block sets, 165 block management tables / 2307 block entries

3/3 ALLDATA.KWI header/table regions byte-identical
```

**All three regions (25,184 bytes total) round-trip byte-identically.**
Phase 1's "high confidence" call on this layer is confirmed — but only
after three concrete corrections/extensions that a read-only parser had no
reason to notice (below). The write direction is what forced them out.

### How the harness avoids fooling itself

- **Poison fill.** Every buffer `volume_writer` builds starts filled with
  `0xA5`, not zeros, and each field is written explicitly. A region the
  model forgets therefore shows up as a diff instead of accidentally
  matching a zero-filled original. Verified: deleting one Block Management
  Table from the parsed structure leaves 20 `0xA5` bytes and fails the
  diff.
- **Negative controls.** Perturbing single decoded values (`sector_size`,
  a maker-ID date, one management-header filename, one BMT entry size, one
  LMR frame-index-table entry) each produce a FAIL, so the passes are not
  an artifact of the harness comparing something to itself.
- **Nothing raw is smuggled in.** The writer takes only the parsed
  intermediate representation; the raw disc bytes are never passed to it.
  The verbatim regions it does re-emit are carried *through* the IR as
  explicitly named hex fields (see below), each counted in the coverage
  line above.
- **Offsets are re-derived, not copied.** LMRs are placed after the 30-byte
  PDMDH header, the BSMR table at the offset the parse computed, and each
  BMT at its own block set's `bmt_offset` — so a byte-identical result also
  proves those offsets are mutually consistent, and confirms the SWS/`D`
  halved-storage convention on every one of them (`bitutils.unsws()`, new,
  raises on an odd value rather than silently writing wrong bytes).

### What the write direction turned up

1. **The Level Management Record is 170 bytes on this disc, and the extra
   128 bytes are now decoded.** `volume.py` (following `kiwiread.c`)
   modelled a 40-byte LMR plus an optional 2-byte extended-info word, and
   simply strode over the rest using the PDMDH's `lmr_size`. The remainder
   is three `u16` index tables — one entry per road, background and name
   sub-frame — sized exactly by the frame counts in that extended word
   (16 road / 32 background / 16 name here):
   `42 + 2*(16+32+16) = 170 = lmr_size`, with zero bytes left over, for all
   7 levels. Now parsed into `LevelMgmtRecord.road_frame_table` /
   `.background_frame_table` / `.name_frame_table`; anything a future disc
   leaves over is kept in `.raw_tail_hex` rather than guessed at.
2. **The Management Header Table is one 2048-byte table, and this disc uses
   the maker-original area as more of the same records.** Ch. 5.2
   (`spec/format_english/pdf/0500122e.pdf`, p. 5-7) defines the table as 33
   18-byte records followed by a single 1454-byte "record 34 (maker
   original: RESERVED)". Both `kiwiread.c` and our `parse_mhr_table()` read
   exactly 34 × 18 bytes and stop — one record short of a *real, in-use*
   entry: index 34 is `COUNTRY.KWI`. Modelling the whole table as
   113 × 18 bytes + a 14-byte remainder covers 99.3% of it with decoded
   fields and round-trips exactly (new `parse_management_header_table()`).
   The old `parse_mhr_table()` is left untouched, since `disc.py` and the
   validated parcel path depend on it and records 0..33 decode identically.
3. **The whole Ch. 6 management record is accounted for, byte for byte**:
   30-byte PDMDH header + 7 × 170 LMR + 601 × 10 BSMR + 165 Block
   Management Tables tiling offsets 7230..21072 with **zero gaps or
   overlaps**, + 16 zero bytes of padding to the logical-sector boundary.
   The PDMDH's field 1 (SWS-halved, 21072) is the record size *excluding*
   that padding. Each BMT's entry count derived from `bmt_size` also equals
   the entry count the owning level's LMR implies
   (`(1+n_blocks_lat)*(1+n_blocks_lng)`) for all 165 tables —
   `parse_pdmdh_full()` raises if that ever disagrees. This is
   independent structural corroboration of the block/parcel addressing that
   `mesh.py`'s recently fixed parcel lookup relies on.

### What is still carried verbatim (and why that is honest, not hidden)

Per the `COUNTRY.KWI` lesson, regions that are not understood are stored as
raw hex in the IR and written back unchanged, never regenerated from a
partial interpretation. The harness counts them and reports how many are
non-zero:

- **Data Volume, 1694 of 2048 bytes verbatim, only 27 non-zero.** The zero
  ones are the spec's RESERVED areas (14 B at offset 478, 1300 B at 748)
  and the 256-byte Level Management Information area (Ch. 5.1.1) — which is
  **entirely zero on this disc, so its structure remains untested**. The 27
  non-zero bytes are inside the maker-defined halves of the three MID:C
  identification fields, which the spec explicitly leaves to the
  manufacturer; note the "Data author identification" field is *binary*,
  not text, so Phase 1's `VolumeHeader.data_author_id` string
  (`'\x0fa<'`) is a truncation and could not have been used to rebuild it.
  Everything the spec actually defines here — the three 12-byte Maker
  Identifications (office lat/lon, floor, date), all four Data Contents
  words, format/data/media version and disk title, the coverage PIDs
  including their exponent bytes, sector sizes, background defaults — is
  decoded and rebuilt from typed fields.
- **Management Header Table, 14 bytes verbatim** (all zero): the remainder
  the 18-byte record grid cannot cover.
- **PDMDH record, 22 bytes verbatim** (all zero): 6 undecoded header bytes
  at offset 2..8 and the 16 padding bytes.

### Explicitly not attempted in this pass

- File offsets 4096..6144 — the 2048-byte management frame that management
  header record 29 points at. It is a real, non-zero frame but belongs to a
  different chapter's layer, not to the volume/LMR/BSMR/BMT layer targeted
  here.
- Parcel content: road, background and name frames, plus the parcel
  management records the BMT entries point at. Unchanged from the
  assessment below — that layer still carries ~50%-identified road-type
  codes, medium-confidence parcel-local coordinate decoding, and several
  record kinds that `parcel.py`/`name.py` skip past rather than decode.

### Concrete next steps for the deeper layers

1. **Parcel management records** (what BMT `dsa` fields point at, and what
   `mesh.py` walks) are the natural next rung: small, fixed-shape
   `[type][mapinfo array of dsa+size]` records with the same divided
   /integrated-parcel recursion `mesh.py` already handles. Writing them
   would extend the proven layer one level deeper without touching content
   decoding at all, and would validate the sub-parcel `[D]`-encoded
   in-buffer offsets.
2. **Map Frame header + Main Map Data Frame Entry table** (`parcel.py`'s
   first 36 bytes + region list + mfde table) next: still pure structure —
   offsets and sizes — but it is the boundary where a writer starts having
   to lay content out rather than transcribe it. Round-tripping just the
   header/mfde table of a real parcel (leaving the sub-frame payloads as
   opaque byte blobs) is a cheap, high-value checkpoint, and it directly
   exercises the sub-frame index tables newly decoded in finding 1 above.
3. **Only then** attempt a road/background/name frame writer, one frame
   kind at a time, and take the `raw_tail_hex` approach for every record
   kind still undecoded (Name Data Frame string types 0/2/3/7, Additional
   Data records, Data Extended region-list bytes) so that a partial model
   cannot silently corrupt bytes it does not understand.
4. Consider switching `disc.py` to `parse_management_header_table()` so the
   read path sees all in-use management records (it currently stops at 34
   and misses the `COUNTRY.KWI` entry). Deferred here to avoid touching the
   validated parcel path in the same pass as a writer.

### What remains before Phase 2 can be considered complete

1. Fix (or explicitly scope out) the `SPEC.KWI`/`METADATA.KWI` whitespace
   loss — either by capturing raw per-statement text in
   `parse_bnf_metadata`'s intermediate representation, or by documenting
   that these two files will always be regenerated fresh (not byte-matched)
   in Phase 4, in which case exact round-trip of the *original's* quirky
   whitespace stops mattering.
2. ~~Attempt a writer for at least one non-trivial `ALLDATA.KWI` structural
   layer (e.g. the volume header + LMR/BSMR tables, which Phase 1 called
   "high confidence") before attempting full parcel/road/background/name
   round-trip, given how much of that file's decode is still
   medium-confidence or explicitly unimplemented.~~ **Done** — see
   "ALLDATA.KWI container/mesh layer: byte-identical" above; 3/3 regions
   (Data Volume, Management Header Table, PDMDH+LMR+BSMR+BMT) are
   byte-identical. Parcel content remains untouched, with a staged plan for
   it in that section's "next steps".
3. ~~Attempt a writer for the simplest `IDX/*.IDX` structure once the above
   main-map work de-risks the general "write what you've verbatim-preserved"
   approach — likely the `DCTF` definition frame or a single fixed-shape
   record type, not the full self-describing chain.~~ **Done, at the
   structural-piece level** — see "`IDX/*.IDX` search-index structural
   writer: 232/232 checks byte-identical" below: the full self-describing
   chain (definition frames, matching records of every kind, DFSR headers,
   Detailed Search Info Records, additional-address entries) round-trips
   exactly against real bytes, well beyond "just the DCTF frame." Whole-file
   reassembly (re-deriving *where* each piece lives in a from-scratch file)
   remains outstanding — see that section's "explicitly NOT attempted."
4. Only after real (not just plausible) round-trip success on a
   representative main-map and index-chain sample should an actual disc
   image be reassembled and burned for in-vehicle testing, per the original
   phase goal.

## `IDX/*.IDX` search-index structural writer: 232/232 checks byte-identical (2026-08-28)

Third Phase 2 pass, resolving "what remains" item 3 below (partially --
see "explicitly not attempted" at the end of this section for the honest
scope boundary). Target: the `IDX/*.IDX` search-index chain
(`kiwiw/search_frame.py`), whose read side was already solved end-to-end as
of 2026-08-25 (see `docs/00-overview.md`'s decision log,
"Address/POI search chain SOLVED end-to-end").

New code: `parser/kiwiw/index_writer.py` (inverse of `kiwiw/search_frame.py`),
harness `parser/roundtrip_idx.py`, regression tests
`parser/tests/test_roundtrip_idx.py`. `search_frame.py`/`index_data.py`
themselves were not modified -- all new logic lives in `index_writer.py`.

### Result

Run against the real mounted disc (`/run/media/codyh/464210-8480`):

```
232/232 checks passed
```

covering, per `parser/roundtrip_idx.py`'s output:

- **DFSR search-frame headers**: SADSR201.IDX's top-level header and its
  nested address-range (SRT1) header, both byte-identical.
- **92-byte Detailed Search Info Records** (`SRMX` street search, `SRHA`
  city selection, `SRT1` address range, and POISR201.IDX's POI record):
  4/4 byte-identical.
- **SWS-halved "Additional \*\*\*Address" indirection-table entries**: 6/6
  byte-identical, across both files and both the top-level and nested
  frames -- this is the exact field that "bit us badly" on the read side
  (see module docstrings in `index_data.py`/`search_frame.py`); getting the
  halving direction right on write was the one place most likely to repeat
  that mistake, and it didn't.
- **`DCTF` Matching Data Definition Frames**: 3/3 byte-identical (street
  records' 15-field frame, address-range records' 13-field frame, POI
  records' 19-field frame).
- **Matching Data Records -- the generic, highest-leverage piece**:
  - **All 38,120 Street Name Search records in SADSR201.IDX** (full scan,
    not a sample) round-trip byte-identical.
  - Address-range records for **~85 sampled streets plus the three named
    anchor streets** (GADEN ROAD: 1 record, GINGIN BROOK ROAD: 6 records,
    GINGIN ROAD: 25 records) -- every one byte-identical.
  - **2,000 sampled POI records in POISR201.IDX**, plus **all 3** records
    matching **BURSWOOD CAR RENTALS** -- every one byte-identical.
- **Negative controls** (all confirmed to actually change the output,
  i.e. the passes above are not the harness comparing bytes to itself):
  perturbing a street record's `STID`, perturbing a street record's `KYCH`
  name, and perturbing one `FieldDef.count` in a definition frame each
  produce different bytes than the unperturbed rebuild.

### Design: one generic record writer, reused for every frame kind

The read side's key insight -- every index file is self-describing via its
`DCTF` definition frame plus each record's own `STFG` presence bitmap -- is
exactly what makes the writer cheap: `index_writer.write_matching_record()`
takes the dict `search_frame.parse_matching_record()` produces plus the
frame's `FieldDef` list and re-emits the record, with **no per-frame-kind
special-casing**. The same function, unmodified, produced byte-identical
output for street records (`STFG=7f 00`), address-range records
(`STFG=07`), and POI records (`STFG` varying per record, including the
degenerate representative rows). This directly confirms the read side's
"no hardcoded offsets" design inverts as cleanly as it decodes.

Two format details the write direction had to get exactly right that a
read-only parser could take for granted:

1. **Nibble-packed `UH` fields** (`NXKD`/`NXFN`, `RPNK`/`RPNF`) must be
   written back in adjacent pairs sharing one byte. A small `_BitWriter`
   (mirroring `search_frame._BitReader`) raises loudly if a nibble is left
   unpaired when a byte-aligned field is written or the record ends,
   rather than silently dropping it.
2. **Trailing pad-to-even-length byte.** Every real record sampled (street
   and address-range alike) has a gap between the end of its last decoded
   field and its declared length (`NFRL`, doubled) of either 0 or exactly
   one zero byte -- CONFIRMED empirically across the whole 38,120-record
   street scan plus every sampled address-range record. The writer applies
   this as a flat rule ("pad to even length") rather than trusting the
   stored `NFRL` value to derive padding length, and it held with zero
   exceptions.

### The SWS-halved indirection entry, the read side's known trap

`index_writer.write_frame_ref_entry()` is the inverse of
`search_frame._resolve_frame_ref()` / `index_data._resolve_additional_address()`
-- the little `[4B halved absolute file offset][2B halved name length]
[name]` struct that a previous read-side pass got backwards (using the
offset raw instead of halved) and lost three investigation passes to. The
writer halves the real offset back down (`file_offset // 2`) and raises if
given an odd offset, mirroring `bitutils.unsws()`'s discipline. All 6 real
entries tested (both files, both nesting levels) round-trip exactly.

One branch is flagged rather than silently trusted: the function pads an
odd-length filename with one NUL to keep the halved length field integral.
Every filename actually observed on this disc (`IDX/SADSR201.IDX`,
`IDX/POISR201.IDX`) is 16 ASCII bytes, already even -- so that padding
branch has **never been exercised against a real byte** and is documented
as UNVALIDATED in the docstring, not claimed as confirmed.

### The Detailed Search Info Record: explicit fields + verbatim gaps

`DetailedSearchInfoRaw` captures the 92-byte record as raw stored field
values at every offset the read side's `parse_detailed_search_info()`
decodes (record-relative sws32-encoded pointers, not resolved through the
indirection above) plus two small gaps that are read but never decoded --
12 bytes at record offset 4, and 12 bytes at offset 48 -- carried as
verbatim hex, per the `COUNTRY.KWI` lesson from the earlier round-trip
pass: don't force an unread/unmapped region through a lossy
reinterpretation, replay it exactly. All 4 real records tested (SRMX, SRHA,
and the nested SRT1, plus POISR201.IDX's own SRMX) round-trip exactly,
which also confirms the offset map (`category_definition_raw` at +16,
`matching_data_definition_raw` at +60, etc.) is correct -- a wrong offset
would have silently shifted a decoded value into a "gap" and failed the
byte-diff rather than being hidden by symmetrically re-deriving the same
wrong value.

### Explicitly NOT attempted

**Full-file reassembly of a whole `SADSR*.IDX`/`POISR*.IDX` from scratch.**
Every check in this pass validates one structural piece (a definition
frame, a matching record, a DFSR header, a Detailed Search Info Record, an
additional-address entry) against real bytes **at that piece's own byte
range in the existing file** -- i.e. it proves "given where this thing
already lives in the file, here are its exact bytes," not "here is where
this thing should live in a from-scratch build." Nothing here re-derives:

- where in the file each `DCTF` definition frame, matching-data frame, or
  category table should itself be placed;
- how the disc allocates/orders the additional-address indirection tables
  relative to the records that point at them;
- the category definition/data frames (`category_definition`/
  `category_data` in `DetailedSearchInfoRaw`) -- these are resolved and
  round-tripped as opaque pointer values, but their pointed-at *content*
  (the category table itself) was never parsed or written.

This is the disc's file-layout allocation strategy -- a materially bigger,
separate problem from decoding the self-describing record format, and is
left open here exactly the way `ALLDATA.KWI`'s parcel content was left open
after the container/mesh-layer pass (see that section above). `ARCD`/`CTGY`
*values* remain located-but-not-mapped-to-names, unchanged from the read
side's confidence grading -- since the generic record writer passes them
through as opaque integers rather than reinterpreting them, this doesn't
block round-tripping, only semantic understanding of what a given category
code means.

### What this changes in "what remains"

Item 3 of the original "what remains before Phase 2 can be considered
complete" list (below) is **partially done**: a writer for the
self-describing frame machinery, matching records, DFSR headers, Detailed
Search Info Records, and additional-address entries is built and validated
byte-for-byte against real SADSR201.IDX/POISR201.IDX data, including the
specific anchor records named in the original ask (GADEN ROAD / GINGIN
BROOK ROAD / GINGIN ROAD streets, BURSWOOD CAR RENTALS POI) plus a broad
sample (all 38,120 street records, ~85+ sampled streets' address ranges,
2,000 POI records). What remains outstanding for that item is whole-file
reassembly (see "explicitly NOT attempted" above), which was out of scope
for this pass and is a separate, larger undertaking. Item 4 (disc
reassembly/in-vehicle testing) is unaffected and still outstanding.

## Parcel content writer: 8/8 checks byte-identical (2026-08-28)

Fourth Phase 2 pass, resolving "what remains" items 2-3 above (the
Parcel Management Record layer and the Map Frame + road/background/name
content layer). Target: `parser/kiwiw/parcel_writer.py` (new),
`parser/roundtrip_parcel_content.py` (new harness), and
`parser/tests/test_roundtrip_parcel_content.py` (new pytest wrapper).

### Result

For all 4 real, known-good test coordinates reused from `test_mesh.py`
(Melbourne Docklands, Sydney Harbour, Sydney/Camellia-Granville, Perth
CBD — spanning 3 different Australian cities), both the Block's Parcel
Management Record and the leaf parcel's full Map Frame (header + mfde
table + road + background + name content) round-trip byte-identical:

```
-- Melbourne (Docklands) (-37.813629, 144.963058), block dsa=1115153 size=779 --
  PASS  block record: byte-identical (24928 bytes)
  PASS  parcel @ sector 27441950: byte-identical (28160 bytes, 238 road links, 23 bg shapes, 82 names)
-- Sydney Harbour (-33.86882, 151.20929), block dsa=1603084 size=776 --
  PASS  block record: byte-identical (24832 bytes)
  PASS  parcel @ sector 40009749: byte-identical (51808 bytes, 344 road links, 35 bg shapes, 193 names)
-- Sydney (Camellia/Granville) (-33.8148, 151.0011), block dsa=1603084 size=776 --
  PASS  block record: byte-identical (24832 bytes)
  PASS  parcel @ sector 40112702: byte-identical (81920 bytes, 587 road links, 31 bg shapes, 282 names)
-- Perth CBD (-31.95312, 115.86719), block dsa=1353743 size=770 --
  PASS  block record: byte-identical (24640 bytes)
  PASS  parcel @ sector 44232977: byte-identical (55552 bytes, 361 road links, 122 bg shapes, 241 names)

8/8 parcel-content round-trip checks byte-identical (0 skipped)
```

`parser/tests/test_roundtrip_parcel_content.py` also includes four
negative-control tests (perturb one byte inside a
`ParcelMgmtRecord.tail_raw`, a `RoadLink.raw_bytes`, a
`NameRecord.raw_bytes`, and a `MapFrame.tail_raw`, and confirm the
round-trip check correctly fails) — all 4 pass, confirming these fields
are actually load-bearing in the writer rather than dead weight.

### Findings, with confidence levels

1. **Parcel Management Record `routeoff` field (high confidence, spec-named).**
   The 2-byte gap between a Parcel Management Record's type word and its
   mapinfo array (previously an unexplained `header_gap_raw`) is
   `kiwiread.c`'s own `struct parman_t.routeoff` field: a [D]-encoded
   offset into a route-guidance parcel management list. Its target
   content is out of this task's scope (route-planning layer), but the
   field itself is now named and its bytes are preserved verbatim either
   way.
2. **Block-buffer trailing bytes (`ParcelMgmtRecord.tail_raw`) — medium
   confidence, plausible but not spec-confirmed.** A Block Management
   Table entry's declared size is consistently larger (8.3–12.5 KB more,
   across all 4 test points: 24928/24832/24832/24640 bytes vs. what the
   record tree itself reaches) than everything the recursive
   `ParcelMgmtRecord` structure reaches. Cross-checked against
   `kiwiread.c`'s `showbmt()`: the reference tool's own traversal never
   reads past the same point either. Read as reserved/leftover disc space
   (plausibly a mastering artifact) rather than an undecoded structure,
   but this is an inference from "no known reader reaches it," not a
   spec citation — a real structure here can't be ruled out. Preserved
   byte-for-byte regardless.
3. **Name Data Record length is `na`-derived, not `string_type`-derived
   (high confidence, spec-documented).** The `na` field (offset 0, bits
   0:11, [SWS]-encoded) is `kiwiread.c`'s own commented "Size of Minimum
   Graphics Record" — it gives a Name Data Record's total byte length
   directly, for every `string_type`. The previously-observed mystery
   `string_type=0` records on every real parcel were a decode-alignment
   bug, not a real record kind: the old per-type manual length
   computation for `string_type=4` (Linear-B) was 2 bytes short,
   cascading misalignment into every subsequent record in that list.
   Fixed by making record-boundary derivation `na`-based unconditionally;
   verified end-to-end on a 76-record real name-data-list (Melbourne)
   with zero anomalies. A side effect: an unrecognized `string_type` no
   longer aborts decoding of the rest of the list (record boundaries are
   now known regardless of whether the type's content is understood).
4. **Main Map Data Frame Entry (mfde) table length is self-describing, not
   derivable from any single LMR field — medium confidence, empirically
   derived, not spec-confirmed.** Neither `n_basic_map` (always 3 on this
   disc), nor `n_basic_map + n_ext_map` (3+9=12), nor all four LMR
   "numbers" nibbles combined (14) account for the table's true length.
   Empirically, on every one of the 4 tested real parcels the table runs
   to **exactly 20 entries**, ending precisely where the road sub-frame's
   own content begins with no gap. `kiwiread.c`'s `showmap()` never reads
   past index `n_basic_map` in its own loop, so it offers no ground truth
   on the true length either. Fixed by deriving the table length directly
   from the data: `(min in-buffer offset among indices 0-2 − de_off) // 6`,
   falling back to `n_basic_map + n_ext_map` only if none of road/
   background/name has an in-buffer offset (this fallback path is
   **untested on real data** — all 4 test parcels took the primary path).
   Whether 20 is a true disc-wide constant or coincidental across just
   these 4 points (all level 0, all `n_basic_map=3`/`n_ext_map=9`) is not
   confirmed.
5. **mfde entries beyond index 2 — two kinds, distinguished by whether
   their offset resolves in-buffer.** In-buffer ones are captured raw as
   "Extended Data Frame" content (`MapFrame.ext_frame_raw`); ones whose
   `sws()`-decoded offset is far larger than the buffer (looking like an
   absolute disc sector address rather than an in-buffer `[D]` offset)
   are preserved as table entries only, with no content dereferenced.
   Read as route-guidance-related content belonging to the sibling
   route-planning layer (out of this task's scope per the forbidden-files
   boundary) — this is an inference from the numeric magnitude of the
   values and the scope boundary, **not a confirmed cross-reference**
   against route-planning code.
6. **Road Data Frame "Display Flag" (high confidence, spec-documented).**
   A 2-byte field `kiwiread.c`'s `dumproad()` reads (`dispflag`)
   immediately before each display class's polyline list, previously
   skipped by `road.py`. Fixed via `RoadFrame.display_class_flags`.
7. **Road Data Frame "Additional Data Management Records" content (high
   confidence, content presence confirmed on real data, semantics not
   decoded).** The offset/size table (7.2.1) was already captured; the
   content those offsets point at (trailing the last polyline, up to the
   road frame's own end) was not. Fixed via `RoadFrame.additional_data_raw`
   — captured and round-tripped verbatim, meaning not interpreted.
8. **Map Frame buffer trailing bytes (`MapFrame.tail_raw`) — medium
   confidence, same caveat as finding 2.** Analogous leftover region (6-16
   bytes observed, some ASCII-looking fragments like "...REET"/"...RANT")
   beyond everything the Map Frame's own structure reaches. Same
   "no known reader reaches it" inference as the block-buffer tail; not
   spec-confirmed as a mastering artifact vs. an unrecognized structure.

### Coverage and honest gaps

All 4 test points are level 0 (`n_basic_map=3`, `n_ext_map=9` on every one
of the 7 levels checked; `n_basic_route` nonzero only on levels 0/2, never
exercised by decoding). Not yet validated:
- the mfde-table-length fallback path (no test point needed it);
- whether the 20-entry table length holds on parcels with a different
  `n_basic_map`/`n_ext_map` combination (none observed on this disc so
  far, but not exhaustively surveyed);
- levels other than 0.

### What this changes in "what remains"

Items 2 and 3 of the original "what remains" list (Map Frame header/mfde
table, then road/background/name frame writers) are now **done** at the
level tested (4 real parcels, both structural layers). Item 4 (disc
reassembly, in-vehicle testing) is unaffected and still the only thing
outstanding for Phase 2's stated goal.

## Whole-file `ALLDATA.KWI` assembly: allocation/layout layer (2026-08-28)

Fifth Phase 2 pass, resolving the remaining gap the "IDX structural
writer" and "Parcel content writer" sections above both flagged
explicitly: every prior `ALLDATA.KWI` writer (`volume_writer.py`,
`parcel_writer.py`) only ever proves "given where a structure already
lives in the real file, here are its exact bytes" — none of them decide
*where* a structure should go in a from-scratch build, or rewrite the
cross-reference pointers that follow from a new placement. This pass adds
that missing layer.

New code: `parser/kiwiw/alldata_writer.py` (new module — composes, does
not modify, `volume_writer.py`/`parcel_writer.py`), harness
`parser/roundtrip_alldata_full.py`, regression tests
`parser/tests/test_roundtrip_alldata_full.py`. No existing file was
modified in this pass (confirmed via `git status` before/after: only this
pass's three new files are untracked; `kiwiw/index_writer.py` and
`kiwiw/search_frame.py` show as modified in the working tree, but that is
a different, concurrently-running task's change, not this one's — this
pass never opened either file).

### Scope: whole block sets, not hand-picked coordinates

Unlike `roundtrip_parcel_content.py` (4 hand-picked coordinates),
`load_region()` walks **every real (non-empty) Block Management Table
entry** of one or more requested block sets at a given level, and **every
leaf parcel each block's Parcel Management Record tree reaches**
(including divided/integrated `pardiv1..3` recursion), decoding full Map
Frame + road/background/name content for each. Two regions were exercised
against the real mounted disc (`/run/media/codyh/464210-8480`):

- **Level 8, all 6 real block sets** (indices 0,1,2,4,5,6 — the only ones
  with data at this level): 6 blocks, 78 leaf parcels, 2,330,016 bytes of
  de novo output.
- **Level 6, block set 0** (1 block, 227 leaf parcels): a single larger
  block set, chosen per the "ideally more" guidance, to check the
  allocation logic on a region an order of magnitude bigger than the
  level-8 default.

### Two allocation modes, two different claims

1. **In-place** (`assemble_inplace()`): re-serialize the header layer plus
   every loaded block and every loaded leaf Map Frame at the **exact
   original file offset**, then byte-diff against the real file there.
   This is the "replicate the original's exact layout choices" half of
   the task — a pass proves the allocation *rule* is understood, not
   merely that the byte encoding is (which the prior two sections already
   established).
2. **De novo** (`assemble_denovo()`): pack the *same* loaded content into
   a brand-new, freshly chosen, contiguous buffer — the genuinely new
   problem, since every writer up to this point only ever wrote a
   structure back to the offset it was read from. Every cross-reference
   that addresses a relocated structure is recomputed and rewritten:
   - the Management Header Table's own entry 0 `dsa` (which addresses the
     PDMDH blob);
   - each relocated block's `BmtEntry.dsa` inside the PDMDH's Block
     Management Table;
   - each relocated leaf's `ParcelMapInfoEntry.dsa` inside its owning
     block's Parcel Management Record tree.
   Validated by **re-parsing the de novo buffer with the unmodified
   read-side parser** (`volume.parse_volume_header`,
   `parse_management_header_table`, `parse_pdmdh_full`,
   `parcel_mgmt.parse_parcel_mgmt_record`, `parcel.decode_parcel`) and
   confirming every relocated pointer resolves to the right new offset
   and decodes to the same semantic content (tail_raw, mfde table, road
   links, background shapes, name records) as the original decode. **This
   is explicitly NOT a byte-identity claim against the real file** — the
   layout is deliberately different (see "PDMDH gap" below) — it is a
   self-consistency claim only.

### Results

```
$ python3 roundtrip_alldata_full.py --level 8 --blocksets 0 1 2 4 5 6
Loaded 6 block(s), 78 leaf parcel(s).
In-place: 87/87 regions byte-identical.
De novo: 84/84 relocated structures re-parse consistently.
OVERALL: PASS
```

(87 = 3 header/PDMDH regions + 6 blocks + 78 leaves; 84 = 6 blocks + 78
leaves, header/PDMDH regions aren't part of the "relocated structure"
count since only the leaf/block *pointers* into them are what moved.)

The larger level-6/block-set-0 region (1 block, 227 leaves, checked via
the standalone smoke test that preceded this section, not committed as a
separate harness invocation) produced the same result at scale: **231/231
in-place byte-identical, 228/228 de novo reparse-consistent** — the
allocation logic held with zero exceptions at roughly 3x the content
volume of the default region.

`parser/tests/test_roundtrip_alldata_full.py` runs the level-8/all-6-
block-sets region as its default (fast enough for routine regression use)
and includes two negative controls: perturbing a `RoadLink.raw_bytes`
inside the loaded region breaks the in-place byte-identity check;
perturbing a block's `ParcelMgmtRecord.tail_raw` breaks the de novo
re-parse's content-equality check. Both confirmed to actually fail before
being asserted as passing.

### The allocation rule found, and its confidence level

**HIGH confidence — sector/logical-sector alignment (directly derived,
not inferred).** `encode_sector_addr()` is the exact algebraic inverse of
`volume.getsector()`: any byte offset can be expressed as a KIWI-W sector
address only if it is a multiple of `logical_sz` (32 bytes on this disc)
and its remainder within a `sector_sz`-sized (2048-byte) sector fits the
address format's 6 low bits (i.e. `remainder // logical_sz <= 63`, which
holds automatically since `2048 / 32 == 64`). `assemble_denovo()` packs
every structure back-to-back at whatever multiple of `logical_sz` the
previous structure's length lands on — content lengths on this disc
(block/leaf sizes, all multiples of `logical_sz` themselves, since
`BmtEntry.size`/`ParcelMapInfoEntry.size` are stored in logical-sector
units) keep every subsequent offset aligned with no extra padding logic
needed in the tested regions. This rule is proven, not guessed: every
resulting sector address round-trips through the real, unmodified
`getsector()` in the re-parse check above.

**MEDIUM confidence — the real disc already packs a block set's blocks
contiguously, in block-management-table (i.e. block-index) order.**
Direct inspection of the loaded level-8 region's real file offsets:

```
entry_index  original_offset  length
0            27456            224
0            27680            320
0            28000            224
0            28224            224
0            28448            224
0            28672            224
```

Each block's real offset is exactly the previous block's offset plus its
length — genuinely contiguous, in the same order the Block Management
Tables are walked (block set 0, 1, 2, 4, 5, 6). This is an empirical
observation from one region, not exhaustively checked across all 601
block sets / 7 levels, but it is consistent with `assemble_denovo()`'s
choice to pack blocks back-to-back in load order — i.e. the de novo mode
happens to mirror a real pattern here, though this was not required for
the de novo mode's own self-consistency proof (which holds regardless of
placement order).

**WEAK / not established — leaf (Map Frame) placement order across the
whole disc.** The same region's leaf parcels' real offsets are
increasing but *not* tightly contiguous (e.g. block 0's first ten leaves'
real offsets: 26607840, 26609440, 26620896, 26622496, 26712736, 26714336,
27197184, 27198784, 27287872, 27310784 — gaps of anywhere from 1,600 to
~480,000 bytes between consecutive leaves, presumably other levels'/other
block sets' content interleaved between them). No rule for *why* the real
mastering tool left those particular gaps, or what fills them, was
derived or tested — `assemble_denovo()` does not attempt to reproduce
this; it packs leaves back-to-back with no gaps, which is a valid,
self-consistent choice but not a claim about matching the original
mastering tool's true leaf-placement algorithm.

**Traversal order (HIGH confidence, directly reused from proven code).**
Block-set/block/parcel indexing is exactly the row-major
(lat-outer, lon-inner) grid confirmed in `mesh.py`'s `locate_parcel()`
(itself cross-validated against `kiwiread.c` — see
docs/01-format-analysis.md's "Parcel-index bug" entry). This pass's
`_block_base_bounds()`/`_narrow_bounds()` in `alldata_writer.py` are a
structural (array-index-driven) generalization of that same math — not a
new hypothesis — enumerating bounds for *every* leaf in a block rather
than following one query coordinate's single path. Cross-checked
implicitly: every leaf's `bounds` computed this way was used to construct
a valid `MeshLocation` that `parcel.decode_parcel()` accepted and
round-tripped, for all 78 (level 8) and 227 (level 6) leaves tested.

### What is byte-identical vs. self-consistent-only

- **Byte-identical against the real disc**: the in-place mode's 87
  regions (level 8) / 231 regions (level 6) — Data Volume, Management
  Header Table, PDMDH+LMR+BSMR+BMT, every loaded block's Parcel Management
  Record buffer, and every loaded leaf's full Map Frame (header + region
  list + mfde table + road/background/name sub-frames), each diffed byte-
  for-byte at its real file offset.
- **Self-consistent only (re-parse verified, NOT byte-diffed against any
  real file)**: the de novo mode's entire freshly-packed buffer. No claim
  is made that this buffer matches, or was intended to match, any real
  byte range on the disc — its purpose is to prove the pointer-rewriting
  logic is internally coherent (every relocated `dsa` resolves through the
  unmodified read-side parser to the structure that was actually placed
  there, decoding to the same content as the original).

### Regions still copied verbatim / explicitly out of scope

- **File offsets 4096..6144** (the "other management frame" management
  header record 29 points at, flagged as out of scope in "ALLDATA.KWI
  container/mesh layer: byte-identical" above): `assemble_denovo()` does
  not reproduce this gap at all — it places the PDMDH blob directly after
  the Management Header Table (at offset 4096, not the real disc's 6144),
  since recreating that separate frame's content is outside this pass's
  scope. This is a deliberate, documented divergence between "in-place"
  (which is byte-identical at the real 6144 offset) and "de novo" (which
  places PDMDH at 4096 instead) — not an oversight.
- **The route-planning layer's placement**: `MapFrame.mfde_raw` entries at
  index >= 3 whose offset resolves *outside* the leaf's own buffer
  (observed to look like absolute disc sector addresses — plausibly
  route-guidance content, a sibling layer explicitly out of scope for
  this task) are carried through as opaque table entries only, exactly as
  `parcel_writer.write_map_frame()` already did; this pass does not decide
  where route-planning content itself should live in a from-scratch file.
- **Vendor Extended Data Frame content** (`ext_frame_raw`, in-buffer mfde
  entries beyond index 2): passed through verbatim via the already-proven
  `parcel_writer.write_map_frame()` path, unchanged by this pass.
- **Category/index-chain allocation** (`IDX/*.IDX` whole-file reassembly):
  explicitly out of scope for this pass (a separate, parallel task's
  territory — see "Explicitly not attempted" under the IDX section
  above), and this pass did not touch any IDX-related file.

### What remains before Phase 2 can be considered complete

Disc reassembly and in-vehicle testing (the original phase goal) are
still outstanding, and now additionally require: (a) deciding what to do
about the still-unreproduced 4096..6144 management frame in a real
whole-file build (either derive/decode it, or accept a hybrid layout that
keeps the original disc's own offset for it), and (b) extending this
pass's whole-block-set coverage to the larger levels (0, 2, 4) that carry
the bulk of the disc's real content, which this pass deliberately did not
attempt (see "Scope" above — level 8/6 were chosen as tractable
proof-of-concept regions, not as the largest available).

## Not started yet (unchanged from before this pass)

Whole-file reassembly of `IDX/*.IDX` files (as opposed to the
structural-piece-level writer above), disc reassembly, and in-vehicle
testing of a regenerated-but-unchanged disc. Full `ALLDATA.KWI`
parcel-content round-trip (the item this line used to flag as
not-started) is now done — see "Parcel content writer: 8/8 checks
byte-identical" above — though only at the coverage described in that
section's "Coverage and honest gaps." Whole-file `ALLDATA.KWI` assembly
(deciding *where* a structure goes in a from-scratch build, as opposed to
reproducing/encoding it at a known offset) is now also done at the
allocation-rule level — see "Whole-file `ALLDATA.KWI` assembly:
allocation/layout layer" above — though only for levels 6 and 8, not the
larger levels 0/2/4 that hold most of the disc's real content.

## Update: SPEC.KWI/METADATA.KWI whitespace loss fixed (2026-08-25)

Resolves "what remains" item 1 above. **7/7 targeted files now round-trip
byte-identical.**

### The real whitespace pattern

Direct hex/text inspection of both files on the mounted disc
(`/run/media/codyh/464210-8480`):

```
SPEC.KWI (34 bytes):
SUPERMETA::=AFAU:2.64, AGAU:2.64 ;

METADATA.KWI (164 bytes):
LANG::=US English,...,Australian English ; CHCD ::=ISO 8859-1 ; COOR::=WGS84 ;
```

Splitting each file's text on `;` cleanly separates it into per-statement
chunks whose *exact* surrounding whitespace differs statement-to-statement
with no discoverable general rule:
- `SPEC.KWI`: one statement, no space before `::=`, one space before `;`.
- `METADATA.KWI`: `LANG` has no leading space and no space before `::=`;
  `CHCD` has both a leading space *and* a space before `::=`; `COOR` has a
  leading space but no space before `::=`. Every statement has exactly one
  space before its `;`.

There is no consistent formatting rule to encode as a small parameter set
(e.g. "always one space before `;`" almost holds but the `::=`/leading-space
inconsistency doesn't reduce to anything simpler than "keep the literal
text"). Critically, in both files `raw.decode("ascii").split(";")` applied
to the original bytes, then rejoined with `";".join(...)`, reproduces the
original bytes exactly — including the trailing empty chunk after the
file's final `;` — because that's definitionally how `str.split`/`str.join`
compose. So preserving the *raw split chunks*, not a reformatted
approximation, is sufficient and requires no whitespace model at all.

### Representation chosen

`parse_bnf_metadata` in `parser/kiwiw/misc.py` now returns a `BnfMetadata`
dataclass instead of a plain `dict[str, str]`:

```python
@dataclass
class BnfMetadata:
    raw_statements: list[str]      # text.split(";") result, completely unmodified
    fields: dict[str, str]         # convenience lookup: stripped key -> stripped value
```

`raw_statements` is `text.split(";")` untouched (including the trailing
empty string after the final `;`); `fields` is the same stripped-key/value
dict the old return type was, built from the same statements, kept as a
`.fields` attribute for any code that only wants "give me the value of
`COOR`" without caring about formatting. This was chosen over an explicit
whitespace/formatting model (e.g. per-field leading-space/space-before-`::=`
flags) because the raw-text approach needs no model of *what* varies —
it can't miss a whitespace quirk future discs might have that this one
disc's fields don't happen to exercise, since it never tries to categorize
the whitespace in the first place, it just remembers the literal bytes.

`write_bnf_metadata` (`parser/kiwiw/misc_writer.py`) is now a single line:
`";".join(meta.raw_statements).encode("ascii")` — an exact inverse, not a
best-effort canonical reformatting.

### Callers checked

Grepped the whole tree for `parse_bnf_metadata`/`write_bnf_metadata`/
`BnfMetadata` before changing the return shape. Only two call sites exist,
both already owned by this same round-trip work and both updated/verified
in this pass:
- `parser/roundtrip_misc.py` — passes the parser's return value straight
  through to the writer opaquely; needed no code change since it never
  inspects the intermediate value's shape.
- `parser/tests/test_roundtrip_misc.py` — previously asserted the
  known-lossy failure (`test_spec_kwi_known_lossy`, `assert raw != rebuilt`)
  with a comment explicitly anticipating this fix
  ("update this test... the known whitespace-loss gap seems fixed").
  Replaced with `test_spec_kwi_byte_identical` and a new
  `test_metadata_kwi_byte_identical`, both asserting `raw == rebuilt`.

`VERSION.TXT`'s `parse_version_txt`/`write_version_txt` were deliberately
left untouched (out of scope, already passing, single-statement file with
no whitespace quirks to lose on this disc) — still works via the plain
`dict[str, str]` it already returned.

### Final round-trip results

```
PASS  PCT2MNG.KWI: byte-identical (174 bytes)
PASS  COVERAGE.BIN: byte-identical (21 bytes)
PASS  DN/CLUSTER.DAT: byte-identical (272 bytes)
PASS  COUNTRY.KWI: byte-identical (113 bytes)
PASS  SPEC.KWI: byte-identical (34 bytes)
PASS  METADATA.KWI: byte-identical (164 bytes)
PASS  VERSION.TXT: byte-identical (19 bytes)

7/7 files byte-identical
```

`parser/tests/test_roundtrip_misc.py` and `parser/tests/test_mesh.py` both
still pass in full (no regressions from the `mesh.py` parcel-index fix
either, which predates this change).

### What this changes in "what remains"

Item 1 of the original "what remains before Phase 2 can be considered
complete" list is now done. Items 2-4 (an `ALLDATA.KWI` structural-layer
writer, an `IDX/*.IDX` writer, and eventual disc reassembly/in-vehicle
testing) are unaffected and still outstanding — this was a small, fully
self-contained fix scoped to the two BNF-metadata files only.

*(Later the same day: item 2 is now also done — see "ALLDATA.KWI
container/mesh layer: byte-identical" above. Items 3 and 4 remain
outstanding.)*

## Whole-file `IDX/*.IDX` assembly (2026-08-28)

This is the counterpart, for the `IDX/*.IDX` search-index chain, of the
"Whole-file `ALLDATA.KWI` assembly" pass above: the "`IDX/*.IDX` search-index
structural writer" section earlier in this document validated every
structural piece (`DCTF` definition frames, Detailed Search Info Records,
"Additional ***Address" indirection entries, matching-data records) against
real bytes **at that piece's own byte range in the existing file** -- it
never re-derived *where in the file* each piece should itself be placed.
This pass closes that gap for `IDX/SADSR201.IDX`, using
`parser/roundtrip_idx_full.py` and `parser/tests/test_roundtrip_idx_full.py`.

### Two bugs found and fixed (both invisible to the previous per-piece checks)

Both were found because a whole-file assembler needs a structural piece's
*exact total byte span* (to place the next piece right after it), not just
a byte-range comparison against a known-good prefix -- which is all the
previous checks ever did.

1. **`DCTF` definition frame field count was off by one** (read side:
   `kiwiw/search_frame.py::parse_definition_frame`; write side:
   `kiwiw/index_writer.py::write_definition_frame`). The declaration
   entry's `n_items` field is the exact number of field entries that
   follow, **not** "including the header itself". The old code
   (`range(1, n_items)`) silently dropped the last field of every
   definition frame on this disc. Confirmed against all 7 real `DCTF`
   frames in SADSR201.IDX: `off + 16*(n_items+1)` (the corrected
   end-of-frame offset) lands exactly on the next structure's own already
   -resolved anchor offset, with zero exceptions. This was invisible before
   because (a) every earlier check compared only a byte *prefix*, never
   the frame's true end, and (b) the dropped field's `STFG` presence bit is
   always 0 on every real record on this disc, so no previously-decoded
   record value was ever wrong. The street matching-data-definition frame
   really has 16 fields (`...RPNS, RPNC`), not 15; the address-range frame
   really has 14 (`...STYP, GDXY`), not 13; every category-definition frame
   really has 8 (`...NEXT, NTSZ`), not 7. Confidence: **HIGH** (exact,
   zero-exception fit across all 7 instances).

2. **A definition-frame field entry's "additional" (and "element type")
   slot was parsed with `.strip("\x00 ")`** (`kiwiw/search_frame.py::parse_definition_frame`),
   which destructively removes *leading* NUL bytes as well as trailing
   ones. `write_field_def` only ever pads on the right, so this was a
   silent, asymmetric round-trip bug for any field whose "additional" slot
   is not really an ASCII tag but a raw big-endian integer that happens to
   decode as mostly-NUL ASCII -- e.g. the category-definition frame's
   `DCSF` entry, whose real "additional" bytes are `0x00000003` (an
   integer, not the text "\x03"). The old code stripped the leading NULs
   down to `'\x03'`, and `write_field_def` re-padded it on the wrong side,
   producing `0x03000000` instead of `0x00000003`. Fixed by changing
   `.strip(...)` to `.rstrip(...)` (right-strip only). This was never
   caught before because no earlier test round-trip-compared a
   `category_definition` frame's *full* rebuilt bytes against the real
   file -- only the street `matching_data_definition` frame was checked,
   whose fields don't hit this case. Confidence: **HIGH** (direct byte
   diff, single clean fix, re-verified against the whole existing suite).

Both fixes were re-verified against the full existing regression baseline
before proceeding: `roundtrip_idx.py` still reports 232/232, and
`parser/tests/test_roundtrip_idx.py` still reports 9/9 (with the street
definition frame now correctly reporting 16 fields instead of 15).

### Allocation rule discovered

Every reachable byte of `IDX/SADSR201.IDX`, from offset 0 through
15,375,908 (99.92% of the 15,387,684-byte file), is explained by a single,
**zero-gap, zero-padding sequential-packing rule**, applied recursively to
every `DFSR` frame (the top-level frame and every `next_level` nested frame
alike):

1. the 16-byte `DFSR` header;
2. every Detailed Search Info Record's fixed-`rec_size` slot (`rec_size` is
   itself read from the frame's own header -- it is **not** a global
   constant: SADSR201.IDX's top-level and nested SRMX/SRHA frames use 440,
   but the "ADDRESS RANGE" SRT1 frame uses 376), in record order, packed
   with no gap after the header;
3. for each record, **in record order**: its `category_definition` DCTF
   frame, `matching_data_definition` DCTF frame, `category_data` blob, and
   `matching_data_frame` matching-record chain -- whichever of these four
   are present (`None` fields are simply skipped) -- each packed with zero
   gap after the previous one;
4. for each record, **in REVERSE record order**, recurse into its
   `next_level` nested frame (steps 1-4 again) -- unless that exact
   original file offset has already been placed by an earlier record's
   `next_level` (see the shared-target case below).

This was confirmed by recomputing every byte boundary, by hand, for all 4
reachable Detailed Search Info Records (top-level SRMX @16, top-level SRHA
@456, the SRMX record nested under SRHA's `next_level` @1,576,934, and the
SRT1 address-range record @5,047,012) and finding **zero** unexplained
gaps anywhere in the entire reachable tree -- e.g. `SRMX`'s
`category_definition` (896) + its size (144) lands exactly on
`matching_data_definition` (1040); that + its size (272) lands exactly on
`category_data` (1312); that + `category_data_size` (233,060) lands
exactly on `matching_data_frame` (234,372); that + `matching_data_frame_size`
(1,283,208) lands exactly on `SRHA`'s `category_definition` (1,517,580) --
i.e. the *next record's* local-fields block, confirming step 3 really is
"per record in order", not "all records' one field-kind, then the next
kind".

**Shared next_level target** (confirms and refines step 4): both the
top-level SRMX record and the SRMX record nested under SRHA point their
`next_level` at the exact same original file offset, 5,046,996 (the
"ADDRESS RANGE" SRT1 frame) -- this content is genuinely shared, not
duplicated. The observed order for a 2-record top-level frame is: both
records' local-fields blocks (in record order), then SRHA's `next_level`
subtree recursed fully (which itself recurses into the shared SRT1 target,
since SRHA's nested SRMX record reaches it first), then -- when the outer
loop reaches SRMX's own `next_level` -- the target is already placed, so
nothing more is emitted. This exact rule (packing + forward-order locals +
reverse-order `next_level` recursion + dedup-by-original-offset) accounts
for the entire reachable tree with no exceptions found.

**Confidence: HIGH** for the zero-gap packing rule and the forward-order
local-fields rule (exact, zero-exception fit across the whole reachable
tree, three different frame shapes, three different `rec_size` values).
**WEAK** for the *specific claim* that `next_level` recursion order is
reversed relative to record order -- this is witnessed only once (a single
2-record sibling group), so it is not independently confirmed across
multiple sibling groups. The implementation in `roundtrip_idx_full.py`
therefore documents this as "the order observed and replayed", not as a
generally-proven allocator rule -- see the two allocation modes below.

### Two required proofs, both implemented and passing

`parser/roundtrip_idx_full.py` implements two allocation modes over the
same recursively-parsed intermediate representation:

- **`mode="replicate"`**: an allocator *constrained* to use the exact order
  above (derived from, and specific to, the real disc's own layout) --
  proves understanding of the real allocation rule by producing
  **byte-identical** output.
- **`mode="fromscratch"`**: a deliberately *different*, still-internally-consistent
  order (each record's `next_level` is recursed into immediately, in
  forward record order, rather than deferred to a second reverse-order
  pass) -- proves this is a genuine from-scratch reallocation, not a replay
  of recorded offsets, via **self-consistency after re-parse** (the
  from-scratch buffer decodes to the same intermediate representation as
  the original, even though every absolute offset in it differs).

Both took the parsed IR only, never handed a writer raw disc bytes to copy
through as its "product" without explanation (see "Not modelled" below for
the narrow, explicitly-flagged exceptions), and poison-filled (`0xA5`)
every output buffer before writing any chunk into it.

```
$ python3 roundtrip_idx_full.py
replicate mode: 15387684 bytes (real file 15387684 bytes)
  matching_data_frame @234372: verified (1283208 bytes)
  matching_data_frame @1526372: verbatim (UnicodeEncodeError: 'ascii' codec can't encode characters in position 0-2: ordinal not in range(128))
  matching_data_frame @2117136: verified (2929860 bytes)
  matching_data_frame @5047628: verified (10328280 bytes)
PASS: whole-file reassembly is BYTE-IDENTICAL to the real SADSR201.IDX
fromscratch mode: 15375908 bytes (not expected to match real layout)
PASS: fromscratch buffer's layout is provably different from the real file's (genuine reallocation)
PASS: fromscratch buffer re-parses to a decode-EQUIVALENT tree (self-consistency via re-parse)
```

`parser/tests/test_roundtrip_idx_full.py` (5 tests, all passing) wraps
both proofs plus two negative controls -- one perturbing a real street
record's field before reassembly and confirming `compare_decoded_trees`
actually detects the resulting decode mismatch (proving the comparison is
discriminating, not vacuous), and one corrupting a single byte of the
replicate-mode output and confirming the byte-identical assertion actually
fails (proving that check isn't vacuous either).

### A third bug found: one matching-record population never previously exercised

Building the whole-file assembler required, for the first time, decoding
and rebuilding **every** matching-record population reachable in the tree
-- not just the ones earlier tests happened to sample. Three of the four
populations decode-and-rebuild byte-identical across their **full**
population (not sampled):

- the top-level street name search records (offset 234,372, 38,120
  records -- already known-good from the earlier "IDX/*.IDX search-index
  structural writer" pass);
- the nested "city selection" -> street search records (offset 2,117,136,
  87,533 records -- **newly fully verified by this pass**, not previously
  exercised by any test);
- the "ADDRESS RANGE" records under SRT1 (offset 5,047,628, 344,276
  records -- **newly fully verified by this pass** at 100% of population;
  the earlier structural-writer pass had only spot-checked 3 named anchor
  streets' address ranges, not the full population).

The fourth population -- SRHA's own "city name" matching records (offset
1,526,372, 1,285 records, the literal list of city/town names presented
before street selection) -- **fails to decode correctly** with a
pre-existing bug in `parse_matching_record`/`iter_matching_records`: the
`NAME` field's decoded value overruns into subsequent records' bytes
entirely (verified: `_consumed` bytes exceed the record's own `_nfrl`
length by more than 100 bytes on the very first record). This schema was
never exercised by any earlier test (SADSR201.IDX's only previously-tested
matching-record populations were the street frame, POI records, and 3
sampled address ranges). The root cause was not tracked down further within
this pass's time budget -- `roundtrip_idx_full.py`'s `_matching_frame_bytes`
detects this case (either an outright decode exception or a byte mismatch
against the real file) and falls back to copying that one population's
136-KB span **verbatim** from the real file, clearly flagged in its
`report` output (`"verbatim"` vs `"verified"`) rather than silently
succeeding or crashing the whole assembler. This is an **honest known gap**,
not a silent one -- it is why the byte-identical replicate-mode proof above
explicitly checks that at least 3 populations were reconstructed
record-by-record (not just copied), so the byte-identical claim isn't
trivially satisfied by copying everything.

### Not modelled / explicitly out of scope (verbatim, per this project's established discipline)

- Each Detailed Search Info Record's bytes from `+92` to `+rec_size` (the
  "tail", which holds the up-to-5 embedded "Additional ***Address"
  indirection entries) are copied **verbatim** from the original record,
  not reconstructed field-by-field -- with one narrow, fully-explained
  exception: the 4-byte absolute-file-offset word *inside* an indirection
  entry is patched to the new location of the content it points at (its
  *locator*, a record-relative `sws32` offset, is unaffected by relocating
  the record and is left untouched). This is the same "preserve what isn't
  understood as raw bytes" discipline already used for
  `DetailedSearchInfoRaw`'s two 12-byte undecoded gap fields, just applied
  to the larger, still-undecoded tail region beyond the known 92-byte
  prefix.
- `category_data` blob content is relocated as an opaque byte range,
  never decoded -- consistent with this project's established
  `ARCD`/`CTGY` category-table scope boundary.
- SRHA's "city name" matching-record population (see bug #3 above) is
  copied verbatim rather than reconstructed from IR.
- The trailing 11,776-byte region of SADSR201.IDX (offset 15,375,908 to
  EOF) remains **unresolved**. It begins with a well-formed `DFSR` header
  (count=1, `rec_size`=440, `first_offset`=16) followed by a Detailed
  Search Info Record declared `SRAL` -- a declaration never seen anywhere
  else in this investigation -- but it is not reachable from any
  `next_level` pointer anywhere in the tree: all 4 reachable Detailed
  Search Info Records' `next_level` fields were checked directly (SRT1 has
  none; the other 3 all resolve into the already-walked tree, one of them
  twice, to the shared SRT1 target). The two 12-byte undecoded "gap"
  fields in every Detailed Search Info Record's 92-byte prefix (offsets
  4-16 and 48-60) were checked byte-by-byte, for all 4 reachable records,
  as a candidate record-relative or absolute pointer to this offset; none
  resolved to it -- one gap instead contains what reads as a short ASCII
  tag (e.g. `KBA2`/`KBST`), not a pointer. This region is copied
  **verbatim** by `assemble(..., include_trailing_tail=True)` in
  `"replicate"` mode (which is why the whole-file byte-identical proof
  above covers the full 15,387,684-byte file, not just the 15,375,908-byte
  reachable tree) -- but it is not reconstructed from IR, and its true
  structure and purpose are undocumented. This is the same status as
  before this pass; no progress was made resolving it.

### `IDX/POISR201.IDX`: attempted, not completed

The task's secondary target was attempted but not completed within this
pass's time budget. `POISR201.IDX` has a materially different top-level
shape from `SADSR201.IDX` -- more sibling frames/populations at the top
level (5 matching-record populations were found reachable, versus
SADSR201.IDX's 4), and running the same `"replicate"`-mode assembler
against it produces a first byte diff at offset 771 -- **before** any
matching-frame content, meaning the DSIR/DCTF local-fields ordering itself
does not follow the exact SADSR201.IDX pattern for this file (this was not
investigated further). Of its 5 matching-record populations, only 1
decode-and-rebuilds cleanly; the other 4 hit pre-existing decode bugs
never previously exercised, including at least one `ValueError: odd number
of nibble fields written before a byte-aligned field` (a POI-specific
nibble-field-pairing case not present in any SADSR201.IDX population).
None of this was investigated further -- it is recorded here as an honest
"not done", not a hidden gap. `docs/00-overview.md`'s "what remains" list
should treat `POISR201.IDX` whole-file assembly as still fully outstanding.

### Regression check

The full existing suite was re-run after this pass's two `search_frame.py`
/ `index_writer.py` fixes, with no regressions: `parser/roundtrip_misc.py`
(7/7), `roundtrip_alldata_header.py` (3/3 + documented not-attempted
regions unchanged), `roundtrip_idx.py` (232/232), `roundtrip_parcel_content.py`
(8/8), and every file under `parser/tests/` (`test_mesh.py`,
`test_roundtrip_alldata_full.py`, `test_roundtrip_alldata_header.py`,
`test_roundtrip_idx.py` [9/9], `test_roundtrip_misc.py`,
`test_roundtrip_parcel_content.py`, `test_route_planning.py`,
`test_boundary_links.py`, `test_contraction.py`) plus the new
`test_roundtrip_idx_full.py` (5/5).
