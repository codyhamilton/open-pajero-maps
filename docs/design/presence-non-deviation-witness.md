# Presence non-deviation witness

The contract for closing a G-versus-DVD deviation as **proven
non-deviation** on the grounds that both discs lack a feature type in a
cell.

1. **No default verdict.** A row is `proven-non-deviation` only with its own
   committed byte or decode witness. The witness must show that the
   demanded type is absent in that cell on the G disc in force and on R.
   Without such a witness the row stays `conflict-open`. A counterfactual
   (for example, "a repaired source would emit one piece") is evidence, not
   a mandate to edit the source.
2. **What counts as absence.** Absence means a demanded-type count of 0 over
   class-2 polygons with at least 3 coordinates, in every indexed frame
   covering the cell. Each frame must be decoded from retained bytes (hex
   and SHA-256) by two independent decoders that agree.
3. **R slot status.** A slot proves absence only when the hardened plan-29
   reader resolves it (`resolved` with decoded frames, or `empty_slot` from
   a raw `FFFFFFFF` sentinel). A `lookup_failed`, a decode error or a
   missing probe is never absence.
4. **Extent.** An R frame whose extent strictly contains the G cell (an L0
   sparse tile) is valid. A zero count over the larger extent implies zero
   in the cell. An R extent that does not cover the cell is not a witness.
5. **No invented presence.** A source repair must not make G emit a type in
   a cell where R has none. Such a repair creates a new G≠R deviation and
   needs an explicit, evidenced ruling.
6. **Disc identity.** Each witness names the full disc SHA-256. G discs are
   stream-hashed by the probe. R may be cited from a prior stream hash only
   when it is corroborated; new tools should stream-hash R as well.

Reference implementation and evidence:
`docs/plans/04-c-core-orchestration/triage/o04_seven/` (plan 33 record:
`docs/plans/33-o04-spool-successor-seven.md`).
