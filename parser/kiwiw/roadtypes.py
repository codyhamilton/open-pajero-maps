"""Type-code lookup tables.

Two independent sets of codes appear in the main map data frame:

1. `MULTILINK_ROAD_TYPES`: the 4-bit "Road Type code" field in a road
   multilink's attribute word (7.2.2.1.1, bits 12:15). kiwiread.c only
   assigns rendering colors to codes 0,3,4,5,6,7 (see `dumproad()`); it
   never names them. **Confidence: low/guessed** -- derived only from
   kiwiread.c's render-color comments ("highway", "main district road",
   "prefectural road", "general road (trunk)"), which read like informal
   notes, not spec text. We could not confirm these against the spec: the
   Ch. 7.A "Road Type" appendix section (`spec/format_english/pdf/07A1122e.pdf`,
   section 7.A.1) has a header but **no extracted table content** -- either
   the table is an embedded image `pdftotext` can't read, or this revision
   of the archived spec genuinely ships that table empty (7.A.2/7.A.3 are
   explicitly marked "(added in future)"; 7.A.1 has no such marker but also
   has no visible content). Treat these labels as placeholders pending
   either a better spec extraction (try `pdftoppm`/OCR on that page) or
   corroboration against real disc data (e.g. do type-6 roads cluster on
   freeways visually).
2. `BACKGROUND_TYPE_CODES`: the 16-bit "Type Code" field on background
   shapes (7.3.2.2.1) and name records' Attribute 2 field (7.4.1). These
   *are* the `types[]` table from kiwiread.c, which reads like a direct
   transcription of a spec code table (values like 0x131/0x132/0x134 for
   "address level 1/2/4" match Ch. 7 background-frame address-boundary
   semantics exactly) -- **confidence: medium-high**, but not independently
   cross-checked against a Ch. 7.3 code-table PDF page in this pass.
"""
from __future__ import annotations

MULTILINK_ROAD_TYPES = {
    0: "highway (expressway)",
    3: "main district road",
    4: "prefectural road",
    5: "general road (trunk)",
    6: "general road (unclassified, guessed)",
    7: "narrow/local road (guessed, kiwiread renders as thin blue)",
}


def road_type_label(code: int) -> str:
    return MULTILINK_ROAD_TYPES.get(code, f"unknown road type {code}")


BACKGROUND_TYPE_CODES = {
    0x101: "unknown 101",
    0x102: "unknown 102",
    0x103: "unknown 103",
    0x104: "unknown 104",
    0x105: "unknown 105",
    0x106: "unknown 106",
    0x121: "water system (shore line, ocean, bay, sea, creek)",
    0x122: "water system (lake, marsh, pond)",
    0x123: "water system (river)",
    0x124: "water system (canal, irrigation canal)",
    0x128: "island",
    0x131: "address level 1 (country)",
    0x132: "address level 2 (state)",
    0x134: "address level 4 (municipality)",
    0x140: "urban district",
    0x141: "green belt, park",
    0x142: "factory, factory site",
    0x1FE: "information highway symbol",
    0x201: "other transport 1",
    0x210: "road type 0",
    0x211: "road type 1",
    0x212: "road type 2",
    0x213: "road type 3",
    0x214: "road type 4",
    0x215: "road type 5",
    0x216: "road type 6",
    0x217: "road type 7",
    0x218: "road type 8",
    0x21B: "road type 11",
    0x21C: "road type 12",
    0x21D: "road type 13",
    0x242: "very high speed railway, JR line [main line]",
    0x280: "other airport",
    0x408: "cemetery",
    0x43C: "national defense facility, base",
    0x464: "university, college",
    0x480: "hospital",
    0x520: "other sports facility",
    0x566: "historic spot, scenic spot, natural monument",
    0x620: "other shopping facility",
    0x6180: "golf course",
}


def background_type_label(code: int) -> str:
    return BACKGROUND_TYPE_CODES.get(code, f"unknown type 0x{code:x}")
