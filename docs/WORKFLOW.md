## Workflow plugin

This repo uses [workflow-plugin](https://github.com/codyhamilton/workflow-plugin) for design → per-phase execute → review → close-out.

- **Skills (core only, no lab):** bootstrap before the first phase, then `python3 <path-to-workflow-plugin>/tools/driver/check_skills.py` (exit 0). Cursor cloud: environment setup runs `tools/cloud-env/bootstrap-workflow-skills.sh` (or `docs/lab/bootstrap/cursor-cloud-setup.sh`); daily rebuild refreshes master (no session hook). Claude Code on the web: copy `docs/lab/bootstrap/session-start.sh` to `.claude/hooks/session-start.sh` and merge `docs/lab/bootstrap/claude-settings-fragment.json` into `.claude/settings.json`. Gitignore `<repo>/.cursor/skills/workflow/` if the Cursor path is used.
- **Phase loop (bot or human):** check skills → read-only status → one phase → assert → repeat until `done` or `unsuccessful`.
  - Skills: `python3 <path-to-workflow-plugin>/tools/driver/check_skills.py`
  - Status: `python3 <path-to-workflow-plugin>/tools/driver/status.py docs/plans/<NN>-<slug>/`
  - One phase: `python3 <path-to-workflow-plugin>/tools/driver/run.py <plan-folder> --once`
  - Assert: `python3 <path-to-workflow-plugin>/tools/driver/assert_phase.py --state <compact-state.json>` (see `tools/driver/README.md`)
- **Markers:** `Workflow-Plan:` on the PR; `Workflow-Phase: <slug>:<n>` / `<slug>:done` on closing commits (`skills/execute/SKILL.md`).
- **Status lives in the PR/issue tracker**, not in plan folder names.

Grok Bot does not auto-discover plugin skills. On Cursor cloud they have to be in the image before the process starts. On Claude Code remote the SessionStart hook installs them and reloads. Then call the driver CLIs.

**OpenCode + DeepSeek Flash:** skills-only install (`./install.sh --opencode-skills`); no driver provider. Flash is encouraged for brief/unit work when rationing capacity; [`GUIDANCE-flash-review-gate.md`](https://github.com/codyhamilton/workflow-plugin/blob/master/docs/lab/GUIDANCE-flash-review-gate.md) bounds sign-off only (Sonnet 5.5 on Flash work, hold for Claude or Grok — no Flash auto close-out or `Workflow-Phase:`).

### Cursor cloud bootstrap (Maps agents)

Cloud VMs do **not** inherit the marketplace plugin. Every Cursor cloud agent env/setup for this repo must run:

```bash
export WORKFLOW_WORKSPACE="${WORKFLOW_WORKSPACE:-/workspace}" && curl -fsSL https://raw.githubusercontent.com/codyhamilton/workflow-plugin/master/tools/cloud-env/bootstrap-workflow-skills.sh | bash
```

Then `python3 …/tools/driver/check_skills.py` must exit 0 (six core skills under `.cursor/skills/workflow/`).

Local Claude Code / OpenCode on this host keep using the installed plugin / skill symlinks; they do not need this curl path.
