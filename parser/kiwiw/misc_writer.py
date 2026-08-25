"""Serializers (inverse of `kiwiw.misc`'s parsers) for the small metadata/
coverage/loading/image-manifest files.

Phase 2 (round-trip writer prototype, see docs/phases/02-roundtrip.md): each
`write_*` function here is the exact inverse of the matching `parse_*`
function in `kiwiw.misc` -- given the dataclass/dict that function produces
when reading a real file, re-emit the original bytes.

Confidence / round-trip status per file (see docs/phases/02-roundtrip.md for
the full writeup and actual byte-diff results):

- `write_pct2mng`, `write_coverage_bin`, `write_cluster_dat`,
  `write_country_kwi`, `write_bnf_metadata`: the corresponding parser
  captures every input byte losslessly (either as fully-decoded fixed-width
  fields, or, for COUNTRY.KWI's not-spec-confirmed tail, as a verbatim
  `raw_tail` blob, or, for SPEC.KWI/METADATA.KWI, as verbatim raw
  per-statement text via `BnfMetadata.raw_statements`) so these are exact
  inverses.
- `write_version_txt`: the *parser* it inverts (`parse_version_txt`)
  discards whitespace formatting and statement order when it builds a
  plain `dict[str, str]` -- so a writer driven only by that dict cannot in
  general reconstruct the original bytes exactly, though it happens to for
  the one single-statement `VERSION.TXT` on this disc. See
  docs/phases/02-roundtrip.md.
"""

from __future__ import annotations

import struct

from .misc import (
    BnfMetadata,
    ClusterDat,
    CountryFile,
    CoverageBin,
    ImageManifest,
)


# ---------------------------------------------------------------------------
# PCT2MNG.KWI
# ---------------------------------------------------------------------------

def write_pct2mng(manifest: ImageManifest) -> bytes:
    """Inverse of `kiwiw.misc.parse_pct2mng`.

    Re-emits the 6-byte header and each 24-byte record
    `[group_id:u32][role:u16][reserved:u32=0][variant:u16][filename:12B]`.
    The `reserved` field isn't retained on `ImageManifestEntry` (it was
    always observed as 0), so this always writes 0 for it -- exact for any
    file where that held, which is the only file this has been tested
    against.
    """
    out = bytearray()
    out += struct.pack(">HHH", manifest.num_groups, manifest.filename_field_width, manifest.num_records)
    for e in manifest.entries:
        name_bytes = e.filename.encode("ascii")
        if len(name_bytes) > 12:
            raise ValueError(f"filename {e.filename!r} too long for 12-byte field")
        name_field = name_bytes + b"\x00" * (12 - len(name_bytes))
        out += struct.pack(">IHIH", e.group_id, e.role, 0, e.variant)
        out += name_field
    return bytes(out)


# ---------------------------------------------------------------------------
# COVERAGE.BIN
# ---------------------------------------------------------------------------

def write_coverage_bin(cov: CoverageBin) -> bytes:
    """Inverse of `kiwiw.misc.parse_coverage_bin`."""
    path_bytes = cov.path.encode("ascii")
    return struct.pack(">HHB", cov.count, cov.unknown, len(path_bytes)) + path_bytes


# ---------------------------------------------------------------------------
# DN/CLUSTER.DAT
# ---------------------------------------------------------------------------

def write_cluster_dat(cd: ClusterDat) -> bytes:
    """Inverse of `kiwiw.misc.parse_cluster_dat`.

    `header_words` already includes the disc-stamp bytes (words 2-7), so
    this doesn't need `disc_stamp` separately -- it's derived redundancy on
    the dataclass, not additional information.
    """
    words = list(cd.header_words)
    for key, value in cd.pairs:
        words.append(key)
        words.append(value)
    return struct.pack(">" + "H" * len(words), *words)


# ---------------------------------------------------------------------------
# COUNTRY.KWI
# ---------------------------------------------------------------------------

def write_country_kwi(cf: CountryFile) -> bytes:
    """Inverse of `kiwiw.misc.parse_country_kwi`.

    The head fields (version/count byte, language codes, country id/ISO
    code) are fully captured by the dataclass and reconstructed here
    exactly per the confirmed grammar
    (`[ver][num]#<codes-but-last>#<last-code>[country_id]<iso>\\x00`).
    The trailing not-spec-confirmed block is *not* re-derived from
    `name_records` (which is lossy -- it drops the placeholder-record
    structure) -- it's reattached verbatim from `raw_tail`, which the
    parser already stores byte-for-byte. This is why COUNTRY.KWI round-trips
    exactly despite its tail grammar being unconfirmed: the parser never
    actually threw those bytes away.
    """
    if not cf.language_codes:
        raise ValueError("no language codes to serialize")
    *head_codes, last_code = cf.language_codes
    block1 = "".join(head_codes)
    out = bytearray()
    out += bytes([cf.version_or_count, cf.num_language_codes])
    out += b"#"
    out += block1.encode("ascii")
    out += b"#"
    out += last_code.encode("ascii")
    out += bytes([cf.country_id])
    out += cf.iso_country_code.encode("ascii")
    out += b"\x00"
    out += cf.raw_tail
    return bytes(out)


# ---------------------------------------------------------------------------
# SPEC.KWI / METADATA.KWI
# ---------------------------------------------------------------------------

def write_bnf_metadata(meta: BnfMetadata) -> bytes:
    """Exact inverse of `kiwiw.misc.parse_bnf_metadata`.

    `BnfMetadata.raw_statements` is exactly `text.split(";")` from the
    parser, so re-joining it with `;` reproduces the original text (and
    therefore bytes, since these files are plain ASCII) byte-for-byte,
    whitespace quirks and all -- no canonicalization/reformatting is done
    here. See docs/phases/02-roundtrip.md for the resolved-whitespace-loss
    writeup (this used to emit a canonical reformatted near-miss; now it
    round-trips exactly on both SPEC.KWI and METADATA.KWI).
    """
    return ";".join(meta.raw_statements).encode("ascii")


# ---------------------------------------------------------------------------
# VERSION.TXT -- documented lossy near-miss
# ---------------------------------------------------------------------------

def write_version_txt(fields: dict[str, str]) -> bytes:
    """Best-effort inverse of `kiwiw.misc.parse_version_txt`. `VERSION.TXT`
    happens to round-trip exactly on this disc (single statement, no
    whitespace quirks to lose), but statement order and any formatting
    quirks beyond `KEY=value;` are not recoverable from the plain dict this
    inverts, unlike `write_bnf_metadata` above.
    """
    return "".join(f"{k}={v};" for k, v in fields.items()).encode("ascii")
