# Maps host OOM — 2026-10-06 ~00:19 Brisbane

Evidence package for plan 25 (OOM memory RCA). **No master code fix landed. HOLD not cleared. Do not resume heavy encode/K1 from this note.**

Timezone: Australia/Brisbane (UTC+10). Journal converted as 00:19 Brisbane = 14:19 UTC on 2026-10-05.

Machine: `codyh-ubuntu` (`machineId` 090ebdb6-1309-4527-9c34-1135deb7968b).

Commands used (host unless noted): `journalctl -k`, `dmesg`, `ps`, `sqlite3 ~/.local/share/opencode/opencode.db`, reads under `~/workspace/open-pajero-maps*` and `output/scratch-14/`.

---

## 1. Kernel OOM facts

| Fact | Value |
|------|--------|
| Time | **2026-10-06 00:19:10–11 Brisbane** |
| Invoker | `dockerd invoked oom-killer` (global OOM, not a memcg-limited kill of the python) |
| Victim | **`cursor` pid=2626982**, `oom_score_adj=300` |
| Killer line | `Out of memory: Killed process 2626982 (cursor) … anon-rss:691560kB … oom_score_adj:300` |

Quotes:

```
Oct 06 00:19:10 … dockerd invoked oom-killer: …
Oct 06 00:19:11 … [2881900] … 2405197  1692622  1692568 … 100 python
Oct 06 00:19:11 … [2881899] … bash
Oct 06 00:19:11 … [2881901] … tail
Oct 06 00:19:11 … oom-kill:… task=cursor,pid=2626982 …
Oct 06 00:19:11 … Out of memory: Killed process 2626982 (cursor) …
```

Mem-Info at kill (Node 0): `active_anon≈11.6GiB` + `inactive_anon≈14.7GiB` pages pressure; `shmem≈6.7GiB`; `all_unreclaimable? yes`; swap total 8GiB.

### Top RSS at OOM (pages×4KiB)

| pid | name | RSS ≈ | notes |
|-----|------|-------|--------|
| **2881900** | **python** | **≈6612 MiB** (1692622 pages) | largest resident; matches Cody ~6.5GiB |
| 3598773 | firefox | ≈835 MiB | |
| 2626982 | cursor | ≈684 MiB | **killed** (high `oom_score_adj`) |
| 2830082 / 2824887 | opencode | ≈531 / 514 MiB | |
| 152740 | claude | ≈378 MiB | Claude RC present — left alone |

Pipeline neighbors of the big python: **2881899 bash → 2881900 python → 2881901 tail** ⇒ process was a `python … \| tail` (or equivalent) shell pipeline. Exact argv **not** in `/proc` (dead), no coredump, no audit `execve` recovered.

---

## 2. Timeline (plan 14 Phase 2 + neighbors)

| Brisbane | Event |
|----------|--------|
| 00:10:01–00:15:58 | OpenCode **2-01** `ses_ef39991ccffe…` — worktree `open-pajero-maps-14-completeness` |
| **00:11:16** | Wrote + ran `flock output/.heavy.lock … python -B output/scratch-14/cell_local/proto.py 2>&1 \| tail -40` — **completed** (proto_res.json) |
| **00:14:29–00:14:35** | `flock output/.heavy.lock … python -B docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py 2>&1 \| tail -60` — **completed**; proofs/summary/TSVs written (~00:14:32 proofs) |
| 00:15:32–00:15:58 | 2-01 commit + session close (Flash 2-01 log closed **00:15:58**) |
| **00:16:34** | Flash **2-02** pid file; OpenCode 2-02 `ses_ef3938c55ffe…` (~00:16:36), opencode pid **2874846** |
| **~00:16:50** | **python 2881900** starts (PID after 2874846, before cron-ish 2882167) |
| 00:16:36–00:17:02 | 2-02 log: **only small CSV/JSON heredocs + explore**; then `external_directory` reject on main checkout |
| **00:19:10** | OOM; cursor killed; python 2881900 still at ≈6.5GiB in task dump |
| ~00:21+ | Flash 2-02b / later master docs — light; not the OOM |
| Concurrent | Plan 17 dump_join docs; plan 18 name-anchor; silver-chronicle; Claude RC |

---

## 3. Cmdline attribution for pid 2881900

### Confirmed

- **RSS ≈ 6612 MiB anon**, name `python` (venv-style binary name in oom dump).
- **Shell pipeline** with `tail` sibling — same *shape* as Maps Flash `python … 2>&1 | tail -N` invocations.
- **Start ≈ 00:16:50**, in the **plan-14 Phase 2 / 2-02 OpenCode window**, worktree class `open-pajero-maps-14-completeness`.
- **Not** the same process as `cell_local_2-01.py` or `proto.py` (those finished under flock in the 2-01 log before 00:16).

### Not recovered

- Exact argv / cwd / open paths for 2881900 (`/proc` gone; no coredump; no audit execve).
- 2-02 Flash/opencode bash parts do **not** log a command that by itself explains 6.5GiB (only small TSV/JSON heredocs).

### Ruled out as the 00:19 resident

| Candidate | Why not 2881900 |
|-----------|------------------|
| `cell_local_2-01.py` | Flock run **00:14:29**, finished by **00:14:35**; proofs ≈00:14:32; 2-01 log closed 00:15:58. Different, earlier PID generation. |
| `proto.py` | Completed ~00:11 in 2-01 log. |
| ~00:23 master doc lands | After OOM; light. |

### Job-class (for plan 25)

**Plan-14 completeness OpenCode path** (Phase 2 Flash on `open-pajero-maps-14-completeness`), during unit **2-02** wall-clock, with incomplete cmdline. Peak during large-leaf / disc / spool decode remains **plausible for that class** (R+G `ALLDATA.KWI` ~1.5–1.6GiB each; spool `level_0.data` ~4.2GiB on disk) but **not proven** as the 00:19 process’s load set.

Note for Execute (do not over-weight): SpoolReader uses **pread** (not full mmap of level_0); LeafIndex uses **bounded LRU** (`LEAF_CACHE_SIZE=64`). Unbounded anonymous growth would need another path (e.g. full-file `read()`, accumulating decoded parcels, encode/bench helpers, or a command never flushed to the 2-02 log because the session died in OOM).

Concurrent host noise (not primary class): other OpenCode/pytest/agent work the same minute; cursor lost the OOM lottery via `oom_score_adj=300` while python adj=100 kept the 6.5GiB resident.

---

## 4. What cell_local / 2-01 *did* load (completed job)

Logged heavy cmds (both **completed** under flock):

```text
flock output/.heavy.lock \
  /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B \
  output/scratch-14/cell_local/proto.py 2>&1 | tail -40

flock output/.heavy.lock \
  /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B \
  docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py 2>&1 | tail -60
```

Inputs (from script + `summary.json`):

- R: `/run/media/codyh/464210-8480/ALLDATA.KWI` (~1.5GiB)
- G: `output/scratch-14/G_new/ALLDATA.KWI` (sha `4ed9cd80…`, ~1.6GiB)
- Spool: `output/extract_timing/spool` (level_0.data ~4.2GiB on disk; cell reads via pread)
- Seeds: 343 `R_polygon_count>0` rows from `completeness_evidence.tsv`
- Workers: **none** (`-j` not used); single process
- Caps: **flock held**; not a K1≤-j6 / encode≤-j4 violation

---

## 5. Misuse vs expected

| Question | Answer |
|----------|--------|
| Exact 2881900 misuse proven? | **No** — cmdline incomplete. |
| cell_local_2-01 misuse vs caps? | **No clear cap violation** (flock used, no `-j` overshoot). Finished minutes before OOM. |
| 2-02 logged cmds unbounded dump load? | **Not in the log** — heredocs only. |
| Classification | **Incomplete cmdline attribution**; **job-class = plan-14 completeness OpenCode path** under Phase 2 pressure + concurrent agents. Treat as **host exceeded under Maps completeness Flash**, not as a proven K1/encode `-j` breach. |

---

## 6. What was fixed / what Execute (plan 25) must change

- **This investigation:** **no master code fix** (not a one-line flock/docs triviality with proven offending argv).
- **Plan 25 Phase 2 — recommended class:** **small harness** (bounded inventory + reproduce under accounting), aimed at:
  1. Catching the next `python\|tail` Flash invocation with **cgroup/`memory.peak` + cmdline capture** (so argv is not lost).
  2. Hold-lift criteria that require: identified cmdline **or** harness proof that completeness triage paths stay under a stated ceiling with R+G+spool present.
  3. Optional inventory of completeness triage scripts’ peak (cell_local-class decode) vs any full-file `read()` of `ALLDATA.KWI` elsewhere — **measurement first**, algorithmic fix only if harness shows a clear unbounded path.
- **Do not** restart plan-14 P2/P3 heavy encode/K1 from this RCA alone.

---

## 7. Safe to resume Execute / clear HOLD?

| Item | Status |
|------|--------|
| Root-cause write-up | **This file** (cmdline incomplete; job-class stated) |
| Safe to clear HOLD? | **No** |
| Safe to resume heavy encode/K1? | **No** until plan 25 Phase 2 harness + hold-lift criteria say so |
| Claude remote-control maps session | **Left alone** |

---

## 8. Evidence index

| Artifact | Path |
|----------|------|
| Kernel slice | host `~/workspace/oom-kernel-2026-10-06.txt` (from `journalctl -k --since '2026-10-05 14:19:10 UTC' --until '…14:19:12'`) |
| Flash 2-01/2-02 | `output/scratch-14/CHM-14-p2-flash-2-0{1,2,2b}.log` (+ `.prompt.md`, `.pid`) |
| cell_local script | `…/04-c-core-orchestration/triage/cell_local_2-01.py` |
| cell_local summary | `output/scratch-14/cell_local/summary.json` |
| OpenCode sessions | `ses_ef39991ccffe…` (2-01), `ses_ef3938c55ffe…` (2-02) in `~/.local/share/opencode/opencode.db` |
| Caps doc | `docs/plans/05-heavy-job-memory.md` |

