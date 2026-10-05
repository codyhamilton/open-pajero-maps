# SADSR SRMX: the generator's 0x3f00 reference-disc claim is false

Pre-edit evidence was checked against commit
`58bdbfd0dfc120ab46dbf2fa54b066b452a61f7c`. R denotes the reference
disc; G denotes the generator. This resolves the documented conflict as a
generator defect; it does not repair the generator.

## Verified reference pattern

The committed `docs/schema/index-idx.md:85` STFG row is **verified**:

> Presence bitmap over later fields in definition order, LSB-first, byte 0 first

Its evidence records:

> SADSR201 SRMX 7f00 (38,119 of 38,120)

The **verified** SADSR SRMX family row at `docs/schema/index-idx.md:97`
lists:

> BFRL NFRL FGFZ STFG STID NXKD NXFN NXST NXCT KYCH NAME (+RPAT RPNK RPNF RPNS RPNC in 202); 38,120 in 201

and records:

> STFG in 202 is 7f00 for all 2,827

Those rows cite `parser/tests/test_roundtrip_idx.py` and
`parser/tests/test_roundtrip_idx_full.py`. Their committed census is the
reference evidence used here; no new disc census was performed. The one
SADSR201 exception is not classified by this note, and no claim is made
that every SRMX record must use the same mask.

## Reader interpretation

`parser/kiwiw/search_frame.py:314-325` documents unconditional fields through
STFG, then gating in definition order, LSB-first and byte 0 first:

> SADSR alphabetical record (``STFG=7f 00`` -> the 7 fields STID..NAME present, rest absent)

`parse_matching_record` implements that rule using `divmod(bit_index, 8)`
and `(stfg_bits[byte_i] >> bit_i) & 1` before reading each gated field.
The verified SRMX definition therefore maps the first seven bits as follows:

| Bit | Field | `7f 00` | `3f 00` |
|---|---|---|---|
| 0 | STID | present | present |
| 1 | NXKD | present | present |
| 2 | NXFN | present | present |
| 3 | NXST | present | present |
| 4 | NXCT | present | present |
| 5 | KYCH | present | present |
| 6 | NAME | present | absent |

Hex masks here retain the documented byte order: `0x7f00` means bytes
`7f 00`, not a little-endian integer. `0x7f` has seven set bits; `0x3f`
has six. NAME is a separate gated field from KYCH.

## False generator claim and inconsistent legacy gloss

Before editing, `docs/schema/flags.md:148` marked the SADSR SRMX street
STFG value **unknown**, with the conflict recorded but unresolved.

`parser/osm_to_address_index.py:466-467`, in `street_to_srmx_dict`, claims:

> This matches the real disc's ``STFG = 0x3F 0x00`` pattern for streets that carry only the primary search fields.

The helper actually emits bytes `3f 00`, includes STID through KYCH, and
omits NAME. The quoted claim cannot justify that output against the verified
R census and reader: R's documented `7f 00` includes NAME. Resolution:
**G's claim is wrong; R's `0x7f00` + NAME interpretation stands**. The
generator output remains a known defect pending Phase 2.

`parser/kiwiw/index_data.py:294-297` also originally glossed `7f 00` as:

> 7 fields present: STID, NXKD, NXFN, NXST, NXCT, KYCH -- NAME absent

That lists only six fields and contradicts the seven-bit presence mask and
the verified definition. Its documentation now lists NAME as the seventh
present field. This is a documentation-only correction; decoder behavior
is unchanged.

The schema row is promoted to **verified**, with the conflict explicitly
resolved as a generator defect and this note as its evidence. No generator
behavior, Phase 2 test expectations, disc bytes, disc SHA, or later phase
completion is changed by this work.
