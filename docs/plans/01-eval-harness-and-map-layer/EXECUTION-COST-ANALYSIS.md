# WP1 execute-run cost/efficiency post-mortem

Ad-hoc analysis of the `/workflow:execute` run that landed units 01, 02, 07
(commits `e58b08f`, `1b9dedd`, `024ed7b`, plus `IMPLEMENTATION.md`/`REVIEW.md`
at `9e05b3d`/`02ab15f`). Session:
https://claude.ai/code/session_01QRzfHS6ESmqmdTRpx1R6m3

Source data: local JSONL transcripts under
`~/.claude/projects/-home-codyh-workspace-open-pajero-maps/9459fd4a-.../subagents/`.
Every subagent this run spawned has a full transcript + `.meta.json` on disk.

Agent map:
- `ad63e632f642c99d6` — unit 01 worker (reference container data)
- `a9e8e7c99c180742e` — unit 02 worker (harness core)
- `ac8d352ea24516a6e` — unit 07 worker (extractor at country scale)
- `a75193824efff8356` — a stray mistaken `Agent` call during a unit 07 resume attempt (0 tool calls, $0.03, harmless)
- `a50965db021c135a9` — independent review agent

## Gotcha: how to count turns correctly

A `type: "assistant"` line in the JSONL is **one content block, not one API
call**. When a response streams `thinking` then `tool_use`, the logger writes
two lines, both stamped with the same `message.id` and identical `usage`
(the usage shown is for the whole response, replayed on each fragment line).
Counting raw lines roughly doubles the true call count for any response that
reasoned before acting.

**Correct method: group by distinct `message.id`.** That gives the real
billed-API-call count. First pass at this (raw line count) gave 187/208 for
units 02/07 and wrongly implied ~46% of calls were "pure thinking, no tool
call" — that was an artifact. Deduplicated:

| Agent | Raw lines | Real API calls (distinct message.id) | Calls with no tool call (real final completions) |
|---|---|---|---|
| Unit 02 | 187 | **100** | 4 |
| Unit 07 | 208 | **107** | 5 |

Only 4-5 calls per agent are genuinely tool-less (mostly the final
report-back message). The "think" overhead isn't a separate billed line item
— it's bundled into the same call as the tool use that follows it.

## Cost per agent (Sonnet rates: $3/$15 per M in/out, $0.30/M cache read, $3.75/M cache write 5m, $6/M 1h)

| Agent | Real API calls | Est. cost |
|---|---|---|
| Orchestrator (this session, main thread) | ~101 | $5.97 |
| Unit 01 worker | 30 | $0.88 (recompute after dedup fix; earlier $1.97 figure was pre-dedup-correction and inflated the same way) |
| Unit 02 worker | 100 | $9.36 |
| Unit 07 worker | 107 | $10.86 |
| Stray mistaken resume call | 1 | $0.03 |
| Review agent | ~69 raw / not yet dedup-recomputed | $2.87 |
| **Total (as originally summed, pre-dedup-correction on cost, order-of-magnitude still holds)** | | **~$31** |

Note: the dollar totals were computed from the summed per-line `usage`
fields, which are safe to sum even with duplicate fragment lines **only if**
you sum once per distinct `message.id`. The original $31.07 total was based
on summing every line's usage (i.e. did NOT dedupe), so it may have
double-counted usage for split thinking+tool_use responses — the input/output
token magnitudes are still directionally right since duplicate lines carry
identical usage numbers and the dominant cost driver (cache_read) scales with
call count either way, but the precise $31 figure should be treated as an
upper-bound estimate, not exact. Unit01's corrected call count (30, not 61)
suggests the true totals are meaningfully lower than $31 — a clean recompute
(dedupe every agent by message.id before summing cost) is a good follow-up
if precise $ matters.

## Sweet spot: 50-75 turns/agent

Units 02 (100 calls) and 07 (107 calls) both ran ~35-45% over the declared
50-75 sweet-spot ceiling. Unit 01 (30 calls) and the review agent are well
inside it.

## Where the excess turns actually went

Phase breakdown (via classifying each call's tool_use: read/write/verify/
poll/inspect/etc, deduped by message.id):

- Both agents follow the expected read→write→verify shape reasonably well:
  reads taper off early, all writes finish by the middle third (last write
  at call 57/100 for unit02, call 44/107 for unit07 — **nothing is written
  in the entire final third of either run**).
- **Calls after the last write**: 42/100 (42%) for unit02, **62/107 (58%)**
  for unit07. For unit07 specifically, the post-write tail is bigger than
  the entire read+build phase combined.
- Of that tail, the actual verify/test-run calls are cheap and few (6 each).
  The tail is dominated by **polling for a background subprocess to
  finish**: `Monitor` calls, `sleep N; echo checked`-style busy-waits,
  `ps -p <pid>` liveness checks, and even a bare `true` used as a no-op to
  force another turn while waiting.
  - Unit02 tail: 12/42 calls (29%) are this kind of poll/liveness-check.
  - Unit07 tail: 24/62 calls (39%) are this kind of poll/liveness-check.

### Attributing the overage

| | Total calls | Target ceiling (75) | Overage | Poll/monitor-attributable calls | % of overage from polling |
|---|---|---|---|---|---|
| Unit 02 | 100 | 75 | 25 | 12 | 48% |
| Unit 07 | 107 | 75 | 32 | 24 | 75% |

For unit07, ~3/4 of the entire overage above the sweet spot is the
busy-wait-on-a-background-process anti-pattern (the "monitor arms a
background check then ends its turn, main session sees a misleading
`completed` notification, has to resume it" pattern noted during the run
itself). For unit02 it's about half.

## Evidence of genuine iteration vs. "two tasks in series"

- Reads after the first write: 7/12 (unit02), 8/11 (unit07) — most reads
  happen mid-build, not up front. Real but modest "should have read this
  earlier" refocusing cost.
- Write↔verify alternations: 9 (unit02), 12 (unit07) — a real iterate/
  fix/retest loop, matching the documented pointers-check false-PASS bug
  that unit02's worker found and fixed mid-implementation.
- No evidence either agent was actually doing two unrelated tasks in
  series — categories stay interleaved throughout rather than clustering
  into two disjoint blocks. This is one coherent task each, with normal
  debug iteration, not a poor task-split.

## Cache-miss / resume-tax finding (this corrected an earlier wrong claim mid-conversation)

Initially concluded from a few sampled points that long idle gaps (up to
~169 min) did *not* cause a full cache-miss on resume — that conclusion was
wrong, based on looking at the wrong turns/lines. Redone properly on
deduplicated calls with real timestamps:

**Both unit02 and unit07 show 4 discrete points where `cache_read` collapses
back to near-zero baseline (~24-25k tokens), and this happens regardless of
elapsed gap length** — including one reset after only a 0.2-minute gap. That
rules out simple TTL expiry as the cause. The likely mechanism: a
`SendMessage` resume rewrites/reinserts something early in the prompt
(e.g. a new instruction block), which invalidates the entire cached prefix
downstream of that point in Anthropic's prefix-based caching, forcing a full
re-embed of the whole accumulated conversation regardless of how much wall
time has actually passed.

- Each reset call costs ~$0.28-0.40 vs. a normal ~$0.05 call for these
  agents at that context depth — roughly 6-8x a normal turn.
- Total reset/resume tax: **$1.14 (unit02)**, **$1.48 (unit07)** — about
  12-14% of each agent's total cost sitting in just 4 calls each.

## Fix-in-place vs. spawn-fresh-agent economics (unit02's bug fix as the test case)

Question: would it have been cheaper for unit02's worker to *not* fix the
pointers-check false-PASS bug itself, and instead return control and let a
fresh, small, low-context agent handle the fix?

- Isolated the debug loop (find bug → fix → re-verify): calls 14-49 of
  unit02, 36 calls. Actual cost at the context depth it ran at (100k-155k
  accumulated tokens per call): **$1.67**, averaging **$0.046/call**.
- Calibrated against unit01 (a genuinely small, clean, low-context agent,
  30 real calls total, $0.88): its cost trajectory is $0.49 at 15 calls,
  $0.88 at 30 calls — average **$0.029/call**, i.e. roughly 60-65% of
  unit02's in-place debug rate.
- Extrapolating unit01's trajectory to 36 calls: **~$1.00-1.05**, vs. the
  $1.67 actually paid — **~35-40% cheaper** for the identical amount of
  debugging work, purely from not re-reading/re-caching 100k+ tokens of
  context irrelevant to the bug itself.
- This is a floor, not the full saving: the 36 in-place debug calls also
  permanently raised the baseline context for the remaining ~50 calls of
  that same agent (the fix's diff + extra file reads get carried in every
  subsequent call's cache_read). Rough estimate: ~50 later calls × ~35k
  extra carried tokens × $0.30/M ≈ **another ~$0.50** in compounding tax
  that a spawned-fresh bugfix agent would never impose on the parent.

**Net estimate**: roughly $2.2-2.7 of unit02's $9.36 (and a comparable or
larger share of unit07's $10.86) is attributable to *not* offloading
wait-and-fix work to disposable, low-context agents — combining the direct
in-place-debug premium (~$0.6-0.7), the compounding tax on the rest of the
run (~$0.5), and the reset/resume tax from resuming the same bloated agent
across a wait (~$1.1-1.5) instead of a clean single handoff.

## Actionable takeaways for future execute runs

1. **Split any unit with a long-running subprocess (>5-10 min) into two
   agents at the kickoff boundary**: agent A does setup + starts the
   subprocess + hands off a short structured summary; agent B (fresh, low
   context) waits for/verifies the result and reports. This avoids both the
   busy-poll tail (39-48% of the observed overage) and the resume/reset tax
   (12-14% of cost), since agent B never needs to "resume" anything — it
   starts once already knowing the process is done or nearly done.
2. **When a worker finds a bug mid-implementation that requires real
   debugging (not a one-line fix), prefer returning control and dispatching
   a small fresh bugfix agent over fixing in place**, once the parent
   agent's context has already grown past a few tens of thousands of
   tokens. The per-call cache_read tax on a bloated agent make the same
   debugging work ~35-40%+ more expensive than doing it fresh, plus it
   permanently taxes every subsequent call in that agent.
3. **50-75 real API calls (by distinct `message.id`, not raw JSONL lines)
   is a reasonable per-agent ceiling to watch for** — both units that
   blew past it (02, 07) did so primarily via the two mechanisms above, not
   via runaway "thinking" or genuine task-confusion.
4. **When measuring subagent cost/turns from transcripts, always dedupe by
   `message.id` before counting or summing usage** — raw line counts
   overcount calls that stream a thinking block before a tool call, and can
   double-count usage if summed naively per line.
