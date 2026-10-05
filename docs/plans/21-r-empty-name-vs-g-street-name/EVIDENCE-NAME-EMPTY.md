# Evidence — R-dominant empty SRMX NAME (no new disc bytes)

Offline promotion of plan 15 residual / historical Phase 2 probe for plan 21.

| Claim | Source | Note |
| --- | --- | --- |
| STFG presence `0x7f00` (bit 6 = NAME present) on dominant SADSR201/202 SRMX | `docs/schema/index-idx.md`; plan 15 close | Unchanged by this plan |
| NAME **content** empty on sampled / dominant SADSR street records with bit set | `docs/plans/15-sadsr-srmx-stfg.md` Residual / Follow-ups | Committed residual |
| Historical SADSR201 probe: **0 / 38,120** non-empty NAME; STFG `7f00` on 38,119 and `ff0f` on 1; first records of SADSR202–207 also `NAME == ""` | Plan 15 Phase 2 unit report at git `56a5462` (collapsed at close; cited in plan 21 DESIGN) | Not re-measured here; no new IDX dump |
| G now emits `STFG=0x7f00`, `KYCH=street.name`, `NAME=""` | `parser/osm_to_address_index.py` `street_to_srmx_dict` | Plan 21 Phase 1 |

No remount required for acceptance. Do not invent disc hex.
