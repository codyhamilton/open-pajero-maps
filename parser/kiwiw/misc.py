"""Decoders for the small metadata/coverage/loading/image-manifest files.

Covers sub-task 3 of Phase 1 (see docs/phases/01-format-analysis.md):
COUNTRY.KWI, SPEC.KWI, METADATA.KWI, COVERAGE.BIN, DN/CLUSTER.DAT,
VERSION.TXT, COVERAGE/AUC.BMP, PCT2MNG.KWI, and the LOADING.KWI top-level
header (Ch. 30).

Confidence levels are called out per-function in docstrings and in
docs/phases/01-format-analysis.md — this module mixes spec-confirmed parsing
(PCT2MNG.KWI, the LOADING.KWI system/module header, DN/CLUSTER.DAT's header
word) with byte-pattern-matched-but-not-spec-confirmed parsing (COUNTRY.KWI's
per-country binary records). Nothing here is a guess dressed up as fact
without a docstring saying so.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# SPEC.KWI / METADATA.KWI -- plain BNF-style ASCII metadata (Ch. 13).
# Both files are just `KEY::=value1, value2 ;` text. No binary framing at
# all -- confirmed by direct inspection, matches Ch.13's stated BNF grammar.
# ---------------------------------------------------------------------------

def parse_bnf_metadata(raw: bytes) -> dict[str, str]:
    """Parse a KIWI Ch.13-style `KEY ::= value ; KEY2 ::= value2 ;` blob.

    Used for both SPEC.KWI (e.g. ``SUPERMETA::=AFAU:2.64, AGAU:2.64 ;``) and
    METADATA.KWI (``LANG::=...; CHCD::=ISO 8859-1; COOR::=WGS84;``).
    Confirmed by direct inspection against Ch.13's stated BNF grammar.
    """
    text = raw.decode("ascii", errors="replace")
    out: dict[str, str] = {}
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if not stmt or "::=" not in stmt:
            continue
        key, val = stmt.split("::=", 1)
        out[key.strip()] = val.strip()
    return out


# ---------------------------------------------------------------------------
# COUNTRY.KWI
# ---------------------------------------------------------------------------

@dataclass
class CountryFile:
    version_or_count: int          # byte 0 -- meaning unconfirmed, plausibly a record/format tag
    num_language_codes: int        # byte 1 -- CONFIRMED: equals count of languages in METADATA.KWI (13 on this disc)
    language_codes: list[str]      # variable-length codes, e.g. ["us","eng","ger",...,"au"]
    iso_country_code: str          # e.g. "aus" -- CONFIRMED ISO 3166-1 alpha-3 style
    country_id: int                # single byte following the ISO code (0x12 on this disc) -- meaning unconfirmed
    name_records: list[str]        # ASCII country-name strings found in the trailing binary block (e.g. "AUSTRALIA" x2)
    raw_tail: bytes                # the trailing tag/value block, undecoded confidently -- see notes


def parse_country_kwi(raw: bytes) -> CountryFile:
    """Parse COUNTRY.KWI.

    CONFIRMED (by direct byte inspection, cross-checked against
    METADATA.KWI's language list -- see docs/phases/01-format-analysis.md):
      - byte[1] is a count of language codes that follow, delimited by a
        literal ``#`` character. On this disc: 0x0d (13), matching the 13
        languages enumerated in METADATA.KWI's LANG field exactly, with each
        KIWI-format code below corresponding 1:1, in order, to a language in
        that list:
            us, eng, ger, fre, spa, ita, dut, swe, dan, por, nor, fin  (first block, no separators, 35 bytes)
            #
            au                                                        (second block, after a second '#')
      - Following the language-code section: a single-byte-or-more field,
        then the ISO-3166-1-alpha-3-style country code "aus", NUL terminated.

    NOT SPEC-CONFIRMED (Ch.13's archived text explicitly carves country
    codes out of the ISO-managed character set prerequisites and does not
    give a byte-level grammar for a per-country binary record like this one
    in the chapters we have -- this is reverse-engineered from the single
    disc we have, i.e. n=1 sample):
      - The trailing block (after "aus\\x00") is a repeating pattern that
        looks like TLV records: `<tag:1><payload>` where tag 0x01 has a
        fixed 1-byte payload (always seen as 0x2d, ASCII '-', suggestive of
        an "untranslated/placeholder" marker for 10 language slots) and tag
        0x00 with a following length byte of 0x05 precedes a 9-byte ASCII
        country name ("AUSTRALIA", appearing twice: once early, once at the
        very end). This is offered as a plausible hypothesis only.
    """
    if len(raw) < 3:
        raise ValueError("COUNTRY.KWI too short")

    version_or_count = raw[0]
    num_codes = raw[1]
    if raw[2] != 0x23:  # '#'
        raise ValueError("expected '#' delimiter at offset 2")

    # First code block: read ASCII until the next '#'.
    end1 = raw.index(0x23, 3)
    block1 = raw[3:end1].decode("ascii")

    # Second code block: ASCII until the country-id byte / NUL-terminated
    # ISO code. Empirically this is exactly 2 bytes on the one disc we have
    # ("au"), followed by a 1-byte country_id, then the NUL-terminated ISO
    # country code.
    after_hash = end1 + 1
    # Find the NUL-terminated ISO code: scan forward for a lowercase-ascii
    # run followed by NUL, skipping the fixed 2-char block1 continuation.
    # On this disc: b'au' + 0x12 + b'aus' + 0x00
    block2 = raw[after_hash:after_hash + 2].decode("ascii")
    country_id = raw[after_hash + 2]
    iso_start = after_hash + 3
    iso_end = raw.index(0x00, iso_start)
    iso_country_code = raw[iso_start:iso_end].decode("ascii")

    language_codes = _split_known_language_codes(block1) + [block2]

    tail = raw[iso_end + 1:]
    name_records = []
    i = 0
    while i < len(tail):
        # tag 0x01 -> 1-byte payload (commonly '-' placeholder)
        # tag 0x00 followed by length byte 0x05 -> ASCII name record whose
        # actual byte length is NOT reliably 5 (seen: 9-byte "AUSTRALIA"
        # following a "0x05" byte) -- so we detect it by scanning for the
        # next NUL/next-record boundary instead of trusting the length byte
        # literally. This is the least confident part of the parse.
        if tail[i] == 0x00 and i + 1 < len(tail) and tail[i + 1] == 0x00:
            i += 2
            continue
        if tail[i] == 0x01 and i + 1 < len(tail):
            i += 2
            continue
        if tail[i] == 0x05:
            # scan ahead for an ASCII run
            j = i + 1
            start = j
            while j < len(tail) and 0x41 <= tail[j] <= 0x5A:
                j += 1
            if j > start:
                name_records.append(tail[start:j].decode("ascii"))
            i = j
            continue
        i += 1

    return CountryFile(
        version_or_count=version_or_count,
        num_language_codes=num_codes,
        language_codes=language_codes,
        iso_country_code=iso_country_code,
        country_id=country_id,
        name_records=name_records,
        raw_tail=tail,
    )


# Known 2-3 char KIWI language codes, longest first, used to greedily split
# the un-delimited first code block. Derived from matching this disc's
# METADATA.KWI language list; CONFIRMED to reconstruct the exact byte string
# on this disc but the general list (for discs with other language sets) is
# a guess based on obvious abbreviation patterns.
_KNOWN_LANG_CODES = [
    "eng", "ger", "fre", "spa", "ita", "dut", "swe", "dan", "por", "nor",
    "fin", "us", "au",
]


def _split_known_language_codes(blob: str) -> list[str]:
    codes = []
    i = 0
    while i < len(blob):
        for code in sorted(_KNOWN_LANG_CODES, key=len, reverse=True):
            if blob.startswith(code, i):
                codes.append(code)
                i += len(code)
                break
        else:
            raise ValueError(f"unrecognized language code at {i!r} in {blob!r}")
    return codes


# ---------------------------------------------------------------------------
# COVERAGE.BIN
# ---------------------------------------------------------------------------

@dataclass
class CoverageBin:
    count: int          # bytes[0:2] BE -- plausibly "number of coverage entries" (=1 here)
    unknown: int        # bytes[2:4] BE -- meaning unconfirmed (0x0012 = 18 on this disc)
    path: str           # DOS-style backslash path to the coverage bitmap, length-prefixed


def parse_coverage_bin(raw: bytes) -> CoverageBin:
    """Parse COVERAGE.BIN.

    CONFIRMED: bytes[4] is a 1-byte length prefix whose value (0x10 = 16)
    exactly matches the length of the path string that follows
    ("COVERAGE\\AUC.BMP"), so the [len][path] framing is solid. The meaning
    of the two leading 16-bit fields (0x0001, 0x0012) is NOT confirmed --
    plausible guesses noted in the field docstrings above.
    """
    count, unknown, plen = struct.unpack_from(">HHB", raw, 0)
    path = raw[5:5 + plen].decode("ascii")
    return CoverageBin(count=count, unknown=unknown, path=path)


# ---------------------------------------------------------------------------
# DN/CLUSTER.DAT
# ---------------------------------------------------------------------------

@dataclass
class ClusterDat:
    header_words: tuple[int, ...]      # the 14 leading 16-bit BE words
    disc_stamp: bytes                  # header_words[2:8] as bytes -- CONFIRMED to recur verbatim as a header prefix in KGRA256/KPCT256/KPCT2DT/KGRPDAT/DICVCE56/VAR256D
    num_pairs: int                     # CONFIRMED: header_words[13] == number of following 16-bit words / 2
    pairs: list[tuple[int, int]]       # (key, value) pairs


def parse_cluster_dat(raw: bytes) -> ClusterDat:
    """Parse DN/CLUSTER.DAT.

    CONFIRMED (verified arithmetically against this file's exact size):
      - The file is 14 big-endian 16-bit header words (28 bytes) followed by
        a flat array of (key, value) 16-bit pairs.
      - header_words[13] (== 122 on this disc) equals the count of 16-bit
        words remaining after the header (61 pairs * 2 = 122), i.e. it's a
        "words following" / record-count field.
      - header_words[2:8] (12 bytes: 0f 67 88 00 3c 47 22 00 03 00 07 22) is
        byte-identical to the leading 12 bytes of KGRA256.KWI, KPCT256.KWI,
        KPCT2DT.KWI, KGRPDAT.KWI, DICVCE56.KWI, and (at a 4-byte offset)
        VAR256D.KWI. This strongly suggests a disc-build/edition stamp
        embedded across many auxiliary files' headers, not specific to
        CLUSTER.DAT. Not spec-confirmed (no field name from the archived Ch.
        2-4/30 text matches this), but the cross-file byte match is solid
        evidence, not a guess.
      - header_words[0] and header_words[11] are both 14 (0x0e) -- possibly
        the same field repeated in two nested sub-headers, or coincidence.
        Not confirmed.
      - The (key, value) pairs form 3 contiguous runs of keys (134-146,
        166-191, 250-271 on this disc) each mapped to a value that looks
        like a compacted/shuffled small-integer index (values span roughly
        3-58, no run in key order). Read as a sparse-ID -> dense-index
        remapping table (consistent with Phase 0's "cluster index"
        hypothesis for DN/CLUSTER.DAT), but the exact semantics of "key" and
        "value" (which one is the cluster ID, which is the remapped index)
        are inferred, not spec-confirmed.
    """
    n = len(raw) // 2
    words = struct.unpack(">" + "H" * n, raw[: n * 2])
    header = words[:14]
    body = words[14:]
    pairs = list(zip(body[0::2], body[1::2]))
    return ClusterDat(
        header_words=header,
        disc_stamp=raw[4:16],
        num_pairs=len(pairs),
        pairs=pairs,
    )


DISC_STAMP_12B = bytes.fromhex("0f678800 3c472200 03000722".replace(" ", ""))
"""The 12-byte cross-file stamp described in `ClusterDat.disc_stamp`, as a
module-level constant for callers who want to check other files against it
without re-parsing CLUSTER.DAT. CONFIDENCE: confirmed present verbatim in
KGRA256.KWI/KPCT256.KWI/KPCT2DT.KWI/KGRPDAT.KWI/DICVCE56.KWI (at file offset
0) and VAR256D.KWI (at file offset 4) on this disc; semantics unconfirmed."""


# ---------------------------------------------------------------------------
# VERSION.TXT
# ---------------------------------------------------------------------------

def parse_version_txt(raw: bytes) -> dict[str, str]:
    """VERSION.TXT is plain `KEY=value;` text, e.g. `COMMENT=2007 ver.1;`.
    CONFIRMED trivially -- it's already human-readable ASCII."""
    text = raw.decode("ascii")
    out = {}
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if "=" in stmt:
            k, v = stmt.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------------------
# COVERAGE/AUC.BMP
# ---------------------------------------------------------------------------

@dataclass
class BmpInfo:
    width: int
    height: int
    bpp: int
    compression: int
    file_size_field: int
    pixel_data_offset: int


def parse_bmp_header(raw: bytes) -> BmpInfo:
    """Verify AUC.BMP is a standard Windows BMP (BITMAPFILEHEADER +
    BITMAPINFOHEADER). CONFIRMED on this disc: magic 'BM', file-size field
    matches actual file size (30648), BITMAPINFOHEADER (40-byte DIB header),
    176x168, 8 bits/pixel (palette-indexed), uncompressed. This file needs
    no special KIWI-specific handling -- any standard BMP reader/writer
    round-trips it.
    """
    if raw[:2] != b"BM":
        raise ValueError("not a BMP file")
    file_size, _res1, _res2, offset = struct.unpack_from("<IHHI", raw, 2)
    dib_size = struct.unpack_from("<I", raw, 14)[0]
    if dib_size < 40:
        raise ValueError(f"unexpected/legacy DIB header size {dib_size}")
    w, h = struct.unpack_from("<ii", raw, 18)
    _planes, bpp = struct.unpack_from("<HH", raw, 26)
    compression = struct.unpack_from("<I", raw, 30)[0]
    return BmpInfo(
        width=w, height=h, bpp=bpp, compression=compression,
        file_size_field=file_size, pixel_data_offset=offset,
    )


# ---------------------------------------------------------------------------
# PCT2MNG.KWI -- image-file-pair manifest
# ---------------------------------------------------------------------------

@dataclass
class ImageManifestEntry:
    group_id: int      # ties related files together, e.g. all files backing one "resource family"
    role: int           # 0 = primary/"D" data file, 2 = "K" key/index file (observed values)
    variant: int        # trailing 2-byte field, meaning only partially understood (see notes)
    filename: str


@dataclass
class ImageManifest:
    num_groups: int
    filename_field_width: int
    num_records: int
    entries: list[ImageManifestEntry]


def parse_pct2mng(raw: bytes) -> ImageManifest:
    """Parse PCT2MNG.KWI -- a manifest listing every image/tile data file on
    the disc and how the "K"-prefixed index files pair up with their "D"
    data files.

    CONFIRMED (fully self-consistent, byte-exact, cross-checked against the
    actual filenames present on the disc):
      - 6-byte header: [num_groups:u16][filename_field_width:u16=12][num_records:u16=7]
      - Then num_records x 24-byte records:
          [group_id:u32][role:u16][reserved:u32=0][variant:u16][filename:12 bytes, NUL-padded ASCII]
      - group_id ties files into families:
          1    -> PCT2DAT.KWI (role 0), KPCT2DT.KWI (role 2)
          0x0a -> GRA256D.KWI (role 0), KGRA256.KWI (role 2), VAR256D.KWI (role 1)
          0x0b -> PCT256D.KWI (role 0), KPCT256.KWI (role 2)
      - role 0 consistently marks the "D" (data) file of a pair, role 2
        consistently marks the "K" (key/index) file -- this directly
        confirms Phase 0's "K-prefixed files are index tables pointing into
        the D data files" hypothesis, for this file family at least.
      - VAR256D.KWI's role is 1 and it shares GRA256D's group id but has no
        "K" index partner of its own -- read as a same-family variant
        dataset, not spec-confirmed as to what "variant" 1 means exactly.
    """
    num_groups, field_width, num_records = struct.unpack_from(">HHH", raw, 0)
    entries = []
    off = 6
    for _ in range(num_records):
        group_id, role, _reserved, variant = struct.unpack_from(">IHIH", raw, off)
        name = raw[off + 12: off + 24].split(b"\x00", 1)[0].decode("ascii")
        entries.append(ImageManifestEntry(group_id=group_id, role=role, variant=variant, filename=name))
        off += 24
    return ImageManifest(
        num_groups=num_groups,
        filename_field_width=field_width,
        num_records=num_records,
        entries=entries,
    )


# ---------------------------------------------------------------------------
# LOADING.KWI -- top-level Loading Module Management Frame header (Ch. 30)
# ---------------------------------------------------------------------------

@dataclass
class LoadingModuleHeader:
    num_systems: int                 # CONFIRMED matches Ch.30.1/30.2 field layout
    systems: list["SystemInfo"]


@dataclass
class SystemInfo:
    manufacturer_id: str    # 12-byte field, e.g. "DENSO"
    num_modules: int
    module_id_offset: int    # byte offset in the file where this system's module identification info begins


def parse_loading_header(raw: bytes) -> LoadingModuleHeader:
    """Parse just the fixed-format top of LOADING.KWI: the Loading Module
    Management Frame's system-count + System Identification Information
    records (Ch. 30.1/30.2). Does NOT parse the actual module code blobs
    that follow (~31MB on this disc) -- those are opaque firmware/resource
    payloads for the head unit, not something this project needs to
    regenerate from OSM data.

    CONFIRMED byte-for-byte against the archived Ch.30 field tables:
      - offset 0, 2 bytes: Number of Accommodated Systems (n). On this disc: 1.
      - offset 2, 2 bytes: reserved (0).
      - offset 4: Sequence of System Identification Information, each a
        16-byte record: [Manufacturer Identifier: 12 bytes ASCII, NUL-padded]
        [Number of Accommodated Modules: u16][reserved: u16].
        On this disc: one system, MID="DENSO", 1 module.
      - Immediately after: Module Identification Information begins (seen
        as ASCII "KH07" on this disc), followed by Module Management
        Information and then the actual Module Code (the bulk of the file).
        The exact byte layout of Module Identification/Management
        Information beyond the "KH07"/"1000"-looking strings we can read is
        NOT decoded here -- Ch.30's later subsections would need to be
        pulled to go further, and it wasn't judged worth it: this is a
        head-unit firmware/resource blob unrelated to map content.
    """
    num_systems, _reserved = struct.unpack_from(">HH", raw, 0)
    systems = []
    off = 4
    for _ in range(num_systems):
        mid = raw[off:off + 12].split(b"\x00", 1)[0].decode("ascii", errors="replace")
        num_modules, _reserved2 = struct.unpack_from(">HH", raw, off + 12)
        systems.append(SystemInfo(manufacturer_id=mid, num_modules=num_modules, module_id_offset=off + 16))
        off += 16
    return LoadingModuleHeader(num_systems=num_systems, systems=systems)
