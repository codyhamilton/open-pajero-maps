# L0 outside-mask empty-shell parity (plan 34)

Lasting tools and evidence from
[plan 34](../../../34-l0-empty-slot-frame-parity.md). The emission rule is in
[docs/design/out-of-span-name-guard.md](../../../../design/out-of-span-name-guard.md)
§ Final outside-mask empty-shell omission.

- `successor_oracle_4e6b0de7.json`: the record for the oracle disc in force
  (`4e6b0de7…`, successor of `2ee3456a…`), with its classified diff scope and
  sha256-pinned evidence.
- `disposition.json` / `.tsv`: per-cell cause and verdict (all three fix-landed).
- `phase2_cause.md`: root cause and emission rule (R basis, falsifier).
- `frame_witness.py`: bounded G/R frame and block witnesses (`commands.md`, Phase 1).
- `phase2_gates.py`: snapshot, classified all-level `diff`, `r-check`,
  `check-witness` and `sha` (`phase2_commands.md`). `snapshot` also pins the
  oracle disc in force when it is present.
- `witnesses/`: Phase 1 byte witnesses (predecessor pins) and
  `g_successor_4e6b0de7.json` (block 0 on the new disc).
- `phase2/`: measured gate outputs and run summaries for the successor.
