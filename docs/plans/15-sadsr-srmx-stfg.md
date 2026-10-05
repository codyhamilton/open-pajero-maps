# SADSR SRMX STFG vs R

The SADSR SRMX street STFG unknown was closed as a generator defect. Reference
evidence on master already showed R's dominant pattern is `0x7f00` with NAME
present; G had emitted `0x3f00` under a false "matches the real disc" claim.
Phase 1 proved the claim false and promoted the schema row. Phase 2 made G
emit `0x7f00` with a NAME field. The row left the unknown census.

## Intent

User request, verbatim:

> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Maps Manager asked Design for the next design after plan 14, runnable without the missing completeness disc/dumps. Close one concrete schema unknown: SADSR SRMX street STFG, where G writes `0x3f00` (NAME absent) under a false "matches the real disc" claim while committed R evidence is `0x7f00` (bits 0–6 including NAME). Land each phase on master. No feature branch. No pull request. Do not reseat 170, 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not invent Phase 3 close.

## Why This Existed

`docs/schema/flags.md` still listed SADSR SRMX street STFG as **unknown**
while committed surfaces already disagreed: verified `index-idx.md` census
(SADSR201 SRMX `7f00` on 38,119 of 38,120; SADSR202 all 2,827 `7f00`) and
`search_frame.py`'s `7f 00` → STID..NAME reading versus
`street_to_srmx_dict` emitting `0x3f00` with a docstring claiming disc match,
and a test locking `STFG[0] == 0x3F`. This was a processing defect (G omits a
field R carries), not an OSM shortfall, and did not need the missing
completeness disc that blocks plan 14.

## What Was Built

**Changed:** `docs/schema/flags.md`, regenerated `docs/schema/UNKNOWNS.md`,
comment-only honesty in `parser/kiwiw/index_data.py`,
`parser/osm_to_address_index.py` (`street_to_srmx_dict`), and
`parser/tests/test_address_extractor.py`. Design: `58bdbfd`. Phase 1:
`b46132f` / close `b61b8b1`. Phase 2: `56a5462` / close `22bafef`.

### Phase 1 — Prove G's `0x3f00` claim false

An evidence package (now summarised in this record) cited the verified
index-idx census, the reader's seven-field `7f 00` gating, the false
"matches the real disc" sentence, and the inconsistent `index_data.py`
"NAME absent" gloss of a seven-bit mask. The flags.md row moved from
**unknown** to **verified**, conflict resolved-as-defect (G wrong; R
`0x7f00`+NAME stands). `lint_schema.py --write` dropped the row from
UNKNOWNS (unknowns 94→93). `index_data.py` documentation now lists NAME as
the seventh present field for `7f 00`; decoder behaviour unchanged.
Encoder emission stayed at `0x3f00` until Phase 2.

### Phase 2 — G emits `0x7f00` with NAME

`street_to_srmx_dict` sets STFG bits 0–6 (`7f 00`) and `"NAME": street.name`
(Assumption 2: same string as KYCH). The false `0x3F00` docstring was
replaced with the R-aligned rationale. Tests expect `0x7F`/`0x00` and NAME
presence; a synthetic write/parse smoke (16-field SRMX FieldDefs, no disc)
round-trips one record with bit 6 set. Schema Evidence/Code cite those tests.
No ALLDATA encode; Plan 04 Phase 3 not closed; 170 / 3-16 / 3-17 not reseated.

Bit layout retained for the dominant mask:

| Bit | Field | `7f 00` | former G `3f 00` |
|---|---|---|---|
| 0–5 | STID…KYCH | present | present |
| 6 | NAME | present | absent |

## Deviations

1. Phase 1 worker landed then rebased onto an advancing origin (plan 14
   Assumption 1); paths were disjoint. Workflow `artifact_feedback` was
   unreachable; blank `design_id` left intentional.
2. Phase 2 worker rebased onto origin after plan 16 Phase 1 advanced during
   the run (paths disjoint aside from unrelated plan-16 files).
3. Synthetic STFG FieldDef uses real on-disc type `NORM UB count=2`, not
   `BF` — a BF-typed STFG crashes `parse_matching_record` bitmap setup.
4. Read-only R probe found NAME bit set but NAME value empty on sampled
   SADSR street records (see Follow-ups). Binding Assumption 2 was retained;
   value was not silently changed.
5. Close-out of the plan folder was deferred from the Phase 2 close commit
   and performed in this record commit.

## Review

No `REVIEW.md` was written. Phase outcomes were recorded in unit handoff
reports and the IMPLEMENTATION ledger. Self-recorded verification found the
signed outcomes met within the stated deviations. This is not an independent
review.

## QA

Phase 1: `test_address_extractor.py` `-k 'srmx_dict_has_required_keys or
stfg_bits_correct_for_srmx'` → **2 passed** (generator still at `3f 00`);
`git diff --check` passed; schema lint regeneration succeeded despite 142
pre-existing missing-path errors unchanged before/after.

Phase 2: `-k 'srmx or stfg_bits'` → **4 passed**; full
`test_address_extractor.py` → **33 passed**; `test_roundtrip_idx.py` with
disc present → **9 passed**. UNKNOWNS not stale. No ALLDATA/disc sha change.

## Residual Risks

NAME content is not byte-exact to R (empty on sampled SADSR street records
while G writes `street.name`). The single SADSR201 SRMX exception whose STFG
is not `7f00` (1 of 38,120, observed as `ff0f`) remains unclassified. Schema
lint still reports 142 pre-existing missing-path errors. WP3 / other IDX
families were not opened. Plan 14 completeness remains blocked on disc.

## Follow-ups

- R probe: NAME bit set but NAME empty on SADSR201 — code kept
  `NAME=street.name` per DESIGN; Open Q1 may adjust value only.
- The single SADSR201 non-`7f00` SRMX row (Open Q2) stays out of scope unless
  a committed identity appears.
- Plan 04 Phase 3 and plan 14 disc-gated completeness work remain separate.
