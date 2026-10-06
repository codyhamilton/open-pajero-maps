Verdict: PASS_WITH_FOLLOWUPS

Reviewer: Claude CLI seat (clean context; Codex weekly-limited), plan 41 Phase 2 at `ec90121`. Light only: no builds, no lock.

Verified:
- **Trigger list.** `TRIGGER_PATTERNS` and the WORKFLOW.md bullets match DESIGN Contract 1 exactly: `kiwiw/*.c|*.h`, `cenc.py`, `build_alldata.py`, `alldata_writer.py`, `disc.py`, goldens.
- **Exit codes.** 0 when the trigger does not fire or all gates are present. 1 when a gate is missing. 2 on a bad rev, a missing impl file, or missing args.
- **`--impl-rev`.** Reads the file through `git show REV:path`, so it works for closed plans whose folder is gone.
- **Tests.** `test_close_gates.py` + `test_perf_inventory.py` gave **13 passed**, matching IMPLEMENTATION.
- **Worked examples reproduced:**
  - plan 34 `9fb00da..4ab27e8`: trigger on `parser/build_alldata.py`, missing a/b/c, exit 1;
  - plan 37 `517781e..5facd75`: not triggered, exit 0;
  - plan 41 `6e12b36..ec90121`: not triggered, exit 0.
- **Classification.** The workflow plugin on box is at `ace7370`; DESIGN cites `6dd6b9d3`. Its close-out and execute skills still contain no suite rule. The trigger surfaces and the `.venv-rp` / `parser/tests` command are specific to this repo, so "repo rule, not plugin rule" holds.

## Findings

1. **Medium: gate (a) accepts a restricted run (the plan 34 failure mode) and a stale or non-commit sha.**
   - **Evidence.** These probes all report `present: True`:
     - `Close gate (a) full suite: 53 passed, 1317 deselected at abc1234`
     - `... pytest parser/tests/test_x.py -> 53 passed at abc1234`
     - `... 1370 passed on 20261006`: the date matches `SHA`, because digits are hex.
   - **Second gap.** The sha is never resolved. A gate line quoted at an earlier phase's close also satisfies a later phase that touches the encoder.
   - **Fix, in `check_text` / `run`:**
     - Add `deselected` to the reject set: `FAILED = re.compile(r'\b([1-9]\d*) (failed|errors?|deselected)\b')`.
     - In `run`, resolve the matched sha with `git rev-parse --verify <sha>^{commit}`.
     - Require `git merge-base --is-ancestor <base> <sha>` and `git merge-base --is-ancestor <sha> <head>`. Report `stale` if the sha predates the last trigger-surface commit in `base..head` (`git log -1 --format=%H base..head -- <trigger paths>`).
     - Add tests for the `deselected` probe and the `stale` probe.

2. **Medium: gate (c) accepts a failing sha gate.**
   - **Evidence.** `Close gate (c) sha gate: AU 4e6b0de7 FAIL, Perth 04be2f6e MISMATCH` reports `present: True`. Gate (a) rejects failures; (c) does not.
   - **Fix.** For k == 'c', mark the gate not present when the line matches `re.compile(r'\b(FAIL\w*|MISMATCH|differ\w*)\b', re.I)`. Add a parametrized test.

3. **Low: gate (b) is too loose on its values.**
   - **Evidence.** These report `present: True`:
     - `median 58 s ... at -j4 (spread TBD) vs baseline TBD`
     - `median 58.2 s of 1 at -j4 ...`
   - **Fix.** In the (b) regex, require `\bspread\s*\d` and `\bbaseline\s*\d`. Require `\bof\s*3\b`, or `of\s*[3-9]`, since Assumption 2 allows more runs.

4. **Low: some regex choices are too strict for reasonable phrasing.**
   - **Evidence.** These report `False`:
     - `58.2 sec` (`s\b`);
     - `encode wall at -j4: median ...` (field order is fixed);
     - `au … perth …` (gate c is case-sensitive);
     - a red-then-green history. `rx.search` takes the first (failing) (a) line, so a later green line is ignored.
   - **Fix.**
     - (b): `s(?:ec)?\b`.
     - Let (b) match `-j\s?4` anywhere on the line. Use per-field lookaheads, `^\W*Close gate \(b\)(?=[^\n]*-j\s?4\b)(?=[^\n]*\bmedian\b…)…`, rather than fixed order.
     - (c): add `re.I`.
     - Iterate with `finditer` and judge the **last** matching (a)/(b)/(c) line, which is the one current at close.

5. **Low: Phase 2 outcome 3 ("41 → pass") is only partly met. The IMPLEMENTATION states its future as fact.**
   - **Evidence.**
     - The 41 row is a *not-triggered* pass (docs/tools diff).
     - IMPLEMENTATION says the triggered pass example "is its Phase 1 close … and it quotes all three gates". But P1 touches `_cenc.c` only if a fix lands. With no fix, P1 is also not triggered, and no triggered-pass example on real history ever exists.
     - Deferral to P1 is otherwise honest, and DESIGN Contract 4 sets P1 as the first use.
   - **Fix.**
     - Reword the row to "41 P2: not triggered (exit 0); triggered pass: **open, recorded at P1 close**".
     - Add to the P1 outcome checklist: P1 quotes gates (a)–(c) and runs `close_gates.py --base 6e12b36 --impl-rev <P1 close>` whether or not a fix lands. If nothing triggers, it records that no triggered-pass example exists yet.

6. **Low: the WORKFLOW rule does not make running the checker mandatory, which weakens the R-G8-5 discharge.**
   - **Evidence.** The "Checker" bullet describes the tool but never requires it at close. There is no CI wiring (a non-goal), so nothing makes a plan run it.
   - **Fix.** Add to the WORKFLOW.md "Required before the phase-closing commit" bullet: "and `close_gates.py` exits 0 for the plan, with its JSON `pass` quoted in IMPLEMENTATION."
   - **Assessment.** With that sentence (and finding 1's `deselected` reject), the R-G8-5 discharge is justified: repo rule, checker, and the plugin variant routed. It is acceptable as discharged now with this follow-up.

Not findings:
- `git diff base..head` with two dots is fine on master-direct linear history.
- fnmatch `*` crosses `/`, so nested `kiwiw/` sources also trigger. That is harmless.
- The `perf_inventory.json` entry is correct (`orchestration`, phase null).
