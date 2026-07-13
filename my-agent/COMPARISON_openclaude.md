# Pulse Agent vs. OpenClaude (Gitlawb/openclaude) — Engineering Gap Analysis

## Important context, read first

`Gitlawb/openclaude` is **not an independently-engineered competitor**. It is
a fork of Anthropic's actual Claude Code source code, which leaked publicly
on March 31, 2026 via a packaging mistake (a source map shipped to npm
pointed to a public, unauthenticated Cloudflare R2 bucket containing the
full ~512,000-line TypeScript source). Anthropic confirmed this was human
error, not a breach — no user data or model weights were exposed, only the
harness source. This is the second time this exact class of leak has
happened to Claude Code (first was Feb 2025).

**What this means for the comparison below:** most of what OpenClaude "has"
is Anthropic's own multi-year, professionally-staffed engineering — not
something the OpenClaude maintainers built from scratch. Their actual
original contribution is narrower: a provider-abstraction shim so the
leaked harness can call OpenAI/Gemini/Ollama/DeepSeek/etc. instead of only
Anthropic's API, plus incremental features added since (repo map, agent
routing, step limits, packaging/deployment hardening).

This document only draws on **publicly reported facts** (press coverage of
the leak, OpenClaude's own README/docs) — not the leaked source itself,
which is not something to build from or copy, regardless of what license
OpenClaude's own modifications claim.

---

## Side-by-side

| Dimension | OpenClaude (via leaked Claude Code + their shim) | Pulse Agent |
|---|---|---|
| Origin of core harness | Anthropic's professional engineering (leaked, not licensed) | Built here, incrementally, this whole conversation |
| Lines/files (harness) | ~512,000 lines / 1,906 files (reported) | Orders of magnitude smaller — a few thousand lines across ~20 focused modules |
| Commit history | 1,007 commits (mostly on top of an already-mature base) | 7 commits (each one a real, tested feature) |
| Community scale | 29.8k stars, 8.9k forks, active Discord | None yet — not published |
| Provider support | 15+ backends via a shim over the SAME underlying harness | 4 real providers wired directly into a Router with verified failover |
| Repo map | Yes — tree-sitter + PageRank, `/repomap`, token-budgeted | **Not built yet** (real, open gap) |
| Surgical file edits | Yes (`Edit` tool, inherited from Anthropic's own `str_replace_based_edit_tool`) | **Yes — `apply_edit`**, same `old_string`/`new_string` exact-match design, built and tested independently this session |
| Streaming tool output | Yes (inherited) | **Yes** — `run_command`'s `on_line` streaming, verified via real timestamps |
| IDE integration | VS Code extension (inherited + their own Control Center/theme layer) | **Yes** — real VS Code extension with corrected `postMessage`/`acquireVsCodeApi` architecture, live-tested via Node.js integration tests |
| Confirmation/safety gate | Inherited from Anthropic (permission modes: ask/plan/acceptEdits/bypass) | **Yes** — `confirm_bridge.py`, proven live to be a genuinely *blocking* gate (a real `rm -rf` paused until externally approved), not just documented behavior |
| Sub-agents / background sessions | Yes (`--bg`, `openclaude ps/logs/kill`, per-agent model routing) | Partial — `start_background_process`/`stop_background_process` (simpler, single-process-tracking, no persistent daemon or per-mission model routing) |
| Mission/task decomposition | `maxSteps` cap + forced summary per sub-agent | **Different, arguably more deliberate**: full mission checkpointing (`missions.py`) with isolated memory per mission and explicit handoff summaries — built specifically because letting one conversation grow unbounded silently drops history |
| MCP support | Yes (inherited) | **Yes** — filesystem + fetch servers, verified clean shutdown, safety-wrapped writes |
| Semantic code search | Not documented as a built-in feature | **Yes** — `rag_search` (ChromaDB), verified finding code by concept not keyword |
| AST-based code transforms | Not documented | **Yes** — `ast_transform_var_to_const`, `ast_add_jsdoc`, verified against real Node execution |
| Accessibility-aware browser tools | Not documented | **Yes** — `get_accessibility_snapshot`, real ARIA tree |
| Version control tools | Inherited bash + git, no structured wrapper documented | **Yes** — structured `git_*` tools with secret-leak protection verified stricter than a naive diff |
| Packaging/install | Mature npm package, `>=Node 22`, AUR package, Android/Termux guide | Not packaged for distribution yet |
| Terminal UI | Custom React-based terminal renderer (Ink), reported in leak coverage | None — Pulse Agent has no terminal UI beyond `main.py`'s plain REPL |

---

## The honest engineering gap, narrowed to what's real

Most of the table above is **not** a fair "they engineered X, you didn't" —
it's "Anthropic engineered X over years with a full team, and it leaked."
The genuinely comparable, buildable gaps — things a small team actually
chose to add on top of the inherited base, using known public techniques —
are:

1. **Repo map** (tree-sitter + PageRank, token-budgeted). This is real,
   valuable, and the ONE item here with a fully open, non-proprietary
   reference implementation (Aider, Apache-licensed, predates both Claude
   Code and OpenClaude's repo-map feature). **Not yet built in Pulse
   Agent.** This is the most legitimate, safely-reproducible gap on the
   list.
2. **Per-agent/per-mission model routing** — routing different missions or
   sub-tasks to different providers/models by role (cheap model for
   exploration, strong model for planning). Pulse Agent's Router already
   does provider-level failover, but not intentional per-task model
   *selection* by role.
3. **A `maxSteps`-style forced-summary cap**, distinct from
   `MAX_TOOL_ITERATIONS` (which just stops): forcing the model to
   summarize progress/next-steps when a step budget is hit, similar in
   spirit to Pulse Agent's own mission checkpoints but triggerable
   mid-mission on a smaller budget, not just at natural mission boundaries.
4. **A published, installable package** — OpenClaude ships via npm with a
   real version history; Pulse Agent has never been packaged for anyone
   outside this workspace to install.

Everything else in the table that looks like a "gap" is really "you're
comparing a few thousand lines built collaboratively over one conversation,
verified line-by-line, against Anthropic's multi-year commercial product
that leaked." That's not a fair engineering comparison, and treating it as
one would be the same mistake as the earlier "Claude Code is better in 8
ways" document that got corrected for conflating model quality with
engineering.

---

## Addendum: three more gaps, sourced from OFFICIAL Anthropic docs (not the leak)

The three items below are genuinely safe to build from directly — they're
published, current-as-of-2026 product documentation at `code.claude.com`,
`platform.claude.com`, and the (legitimately open-source, Anthropic-owned)
`anthropics/claude-code` GitHub repo's `plugins/` directory. None of this
required touching the leaked source; it's all normal public docs.

### A. Permission modes (`default`/`acceptEdits`/`plan`/`auto`/`dontAsk`/`bypassPermissions`)

Officially documented at `code.claude.com/docs/en/permission-modes`. Six
modes, not the binary "confirm or don't" Pulse Agent has today:

| Mode | Runs without asking | Best for |
|---|---|---|
| `default` (aka "Manual") | Reads only | Getting started, sensitive work |
| `plan` | Reads only, proposes without editing | Explore before changing |
| `acceptEdits` | Reads + file edits + common filesystem cmds | Iterating on reviewed code |
| `auto` | Everything, with a background safety classifier | Long tasks, less prompt fatigue |
| `dontAsk` | Only pre-approved tools; denies everything else outright | Locked-down CI/scripts |
| `bypassPermissions` | Everything, including protected paths | Isolated containers/VMs only |

Pulse Agent has the rough equivalent of `default` (ask before
destructive/sensitive) and, via `main.py --dry-run`, something close to
`dontAsk` (auto-decline instead of prompting). It has no `plan`, `auto`,
or `acceptEdits` mode, and no per-mode "protected path" distinction
(currently sensitive-path blocking is unconditional regardless of mode,
which is actually stricter than Claude Code's own `bypassPermissions` --
worth keeping, not a gap).

**Buildability: high.** This is almost entirely a refactor of the existing
`confirm` callback plumbing (`_needs_confirmation`, `_default_confirm`,
`confirm_bridge.py`) into a named-mode dispatcher, not new tool mechanics.

### B. Agent Skills (`SKILL.md` + progressive disclosure)

Officially documented at `anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills`
and `platform.claude.com/docs/en/build-with-claude/skills-guide`. A Skill
is a folder with a `SKILL.md` (YAML frontmatter: `name` + `description`,
required) plus optional `scripts/`, `references/`, `assets/`. Key design:
**progressive disclosure**, three loading layers:
1. Metadata (name + description) -- always loaded into the system prompt
   for every installed skill, cheap enough to have dozens installed
2. The full `SKILL.md` body -- loaded only when the description matches
   the current task
3. Bundled reference files/scripts -- loaded only if `SKILL.md` itself
   references them

This is a genuinely different mechanism from a "tool call": a Skill
doesn't execute and return a result, it injects instructions into context
and modifies what the agent does next (can also restrict allowed
tools/model for the duration). Skills are meant to be shareable,
versioned, composable (a single task can trigger multiple skills, e.g.
"analyze data" -> data-analysis skill + "make a deck" -> pptx skill).

**Pulse Agent status:** no equivalent. The single `SYSTEM_PROMPT` is
static and total; there's no discoverable, on-demand-loaded library of
task-specific procedures.

**Buildability: medium-high.** Needs: (1) a `skills/*/SKILL.md` loader
that parses YAML frontmatter, (2) injecting just name+description of
every installed skill into `SYSTEM_PROMPT` at startup (cheap), (3) a tool
the model calls to "load" a skill's full body into context on demand
(e.g. `load_skill(name)` returning the `SKILL.md` body + pointers to any
bundled files, which the model can then `read_file`). No exotic
mechanics -- this composes cleanly with existing `read_file`/tool-call
infrastructure.

### C. Plugins (bundles of commands/agents/skills/hooks/MCP servers)

Officially documented at `code.claude.com/docs/claude-code/plugins` and
`anthropics/claude-code/plugins/README.md` (Anthropic's own public
plugins repo -- genuinely open, not leaked). A plugin is a directory with
a `.claude-plugin/plugin.json` manifest that can bundle: slash commands,
custom agents, skills, hooks (lifecycle callbacks like `SessionStart`),
and MCP server configs -- installed as one unit from a "marketplace"
(just a git repo with a `.claude-plugin/marketplace.json` catalog file).
Real examples from Anthropic's own official marketplace: LSP plugins per
language (auto diagnostics + code navigation after every edit -- Pulse
Agent already has rough LSP equivalents via `tools_lsp.py`, just not
packaged/shareable), a PR code-review plugin (5 parallel specialized
agents), a git commit-workflow plugin.

**Pulse Agent status:** no equivalent packaging/distribution unit at all
-- every capability (git tools, LSP, RAG, AST, MCP) is hardcoded into
`tools.py`'s registration blocks, not something a user could
install/share/version independently.

**Buildability: medium.** This is the most infrastructure-heavy of the
three -- needs a manifest format, a loader that merges a plugin's
commands/agents/skills/MCP-configs into the running agent, and (later,
not urgent) a marketplace-fetch mechanism. Realistically builds ON TOP of
custom agent definitions (Tier 1 #4) and skills (this addendum, item B)
existing first -- a plugin bundling agents+skills needs both primitives
to already work before "bundle and install them together" is meaningful.

### Updated recommended build order

1. ~~Sub-agents (Tier 1 #2)~~ -- **DONE.** `subagents.py` +
   `agent.py`'s `tool_functions`/`tool_specs`/`system_prompt`/
   `persist_memory` parameters. `dispatch_agent` tool with
   `general-purpose`/`explore`/`plan` types, REAL structural tool-registry
   restriction (not prompt-level), `MAX_SUBAGENT_DEPTH`/`SubagentBudget`
   rate-limit safety given this project's free-tier provider stack.
   Verified 3 ways (unit/no-LLM, live single-call, full live parent-to-
   subagent chain) -- see README.md's "Sub-agents" section for the full
   verification writeup, including a real cross-check of a sub-agent's
   answer against the actual codebase (zero hallucination).
2. ~~Permission modes (Addendum A)~~ -- **DONE.** `permissions.py`:
   6 modes (`default`/`plan`/`accept_edits`/`auto`/`dont_ask`/`bypass`),
   all built on the existing `_needs_confirmation()` gate and the
   `tool_functions`/`tool_specs` registry-restriction mechanism from
   sub-agents (zero new safety mechanics) -- caught and fixed a real
   design bug pre-review (a `confirm()`-only `dont_ask` implementation
   would have silently allowed every unflagged tool through). Zero extra
   LLM calls per loop, per explicit instruction. Verified 16 unit
   scenarios + 3 live-LLM scenarios, including a real `.env`
   before/after diff proving `bypass` mode never touches the
   unconditional secret-path block. See README.md for the full writeup.
3. ~~Skills (Addendum B)~~ -- **DONE.** `skills.py`: 3-layer progressive
   disclosure (metadata always in system prompt, body loaded via
   `load_skill(name)`, supporting files never auto-loaded) per Anthropic's
   OFFICIAL spec -- corrected a proposal on 3 points before building
   (the real `allowed-tools` vs `disallowed-tools` semantics, found via 2
   real Anthropic GitHub bug reports + their official docs; a real
   frontmatter-parsing crash bug that would have taken down the whole
   skills registry from one malformed file; and a deliberate scope
   decision to defer mid-task hard tool enforcement to `dispatch_agent`,
   which already restricts at spawn time, rather than adding loop-mutable
   state to `run_agent`'s already-hardened ReAct loop). Verified 24 unit
   scenarios + 2 live-LLM scenarios reproducing the original proposal's
   own validation scenario, including 2 real test-design mistakes found
   and fixed live (an ambiguous task that never says "React", and
   asserting on the model's chat summary instead of the real file it
   wrote). See README.md for the full writeup.
3.5. ~~Custom project rules~~ -- **DONE (added between Skills and Repo
   map).** `rules.py`: always-loaded root `AGENTS.md` (a genuinely open,
   cross-tool standard) + `.agent_rules/*.md`, verified against BOTH
   Cursor's (`.cursor/rules/*.mdc`, `globs:`) and Claude Code's
   (`CLAUDE.md`+`.claude/rules/*.md`, `paths:`) real, current docs. Found
   and fixed a real bug in Python's OWN stdlib before shipping:
   `pathlib.PurePosixPath.match()` doesn't implement correct globstar
   (`**`) semantics -- `glob.translate` does, verified against 8 cases.
   Path-scoped rules reuse the exact injection mechanism already proven
   in the batching nudge (append to tool-result content mid-task, not a
   new mechanism). Reuses `skills.py`'s frontmatter parser via a new
   shared `parse_frontmatter()` rather than duplicating it. Verified 22
   unit + 5 wiring + 2 live-LLM scenarios, including a real live run
   where the model self-corrected a file it had just written after a
   path-scoped rule fired mid-task. See README.md for the full writeup.
4. ~~Repo map (Tier 1 #1)~~ -- **DONE.** `repo_map.py`: PageRank over the
   real import graph (Aider's algorithm, Apache-2.0, independently-open),
   `repo_map_query` tool. Found and fixed 3 real bugs in the original
   proposal before building (a tree-sitter verification snippet that
   fails immediately against the actually-installed 0.26.0, a JS
   require()-detection query matching every function call not just
   require(), and a false "networkx already installed" claim -- it's
   sandbox coincidence, not a real dependency, documented in
   `REPO_MAP_NETWORKX_UPGRADE.md`), plus 3 more found by the test suite
   itself (aliased Python imports, relative Python imports, and a
   node_modules exclusion gap for directories with no matching
   `.gitignore` rule). Hand-rolled PageRank verified numerically against
   `networkx`'s real output to 5-6 decimal places. Verified 22 unit
   scenarios + 2 live-LLM scenarios against this project's own real
   codebase -- a real model chose to call `repo_map_query` unprompted for
   an overview-style task and correctly named the real, relevant files.
   See README.md for the full writeup.
5. ~~Custom agent definitions (Tier 1 #4)~~ -- **DONE.** `custom_agents.py`:
   `.agent_agents/*.md` (YAML frontmatter + Markdown body, modeled on
   Claude Code's real, currently-documented `.claude/agents/*.md` shape),
   single-parent inheritance (`extends:`) with cycle detection, wired into
   `subagents.dispatch_agent(agent_name=...)`. A proposal for this feature
   left 2 design questions genuinely ambiguous, resolved per this
   project's own "build the cheap thing first" rule rather than guessed:
   (a) no `model:` field in v1 -- `llm_client.chat_completion` hardcodes
   `model=first_model` with no per-call override hook, and adding one
   would either bypass the Router's rate-limit-cooldown safety net for
   that call or change the one code path every LLM call in the project
   goes through, for a feature with no proven need yet; a `model:` field
   present in a file is a warning, not a hard error; (b) `skills:` is
   metadata-only, never force-preloaded, matching skills.py's own
   already-shipped design exactly. A 3rd decision made explicit rather
   than left implicit: `tools:` composes with `mode:` via INTERSECTION,
   never union (a named agent's tool list can only narrow what its mode
   already restricted, never re-grant something the mode removed) --
   verified with a real test asserting `write_file`/`run_command` stay
   excluded even when a `tools:` list names them, because `mode: plan`
   already removed them. A real circular-import hazard was found and
   confirmed live before shipping: a module-level `import permissions`
   inside `subagents.py` deadlocks at import time (permissions.py itself
   does `from subagents import READ_ONLY_TOOL_NAMES` at ITS OWN module
   level) -- fixed by keeping that import lazy, the same established
   pattern every other optional module in this project already uses. A
   real regression was caught and fixed during this feature's own build:
   an earlier draft resolved `agent_name` (which can raise for an unknown
   name/broken `extends`/inheritance cycle) AFTER the sub-agent budget had
   already been acquired, silently wasting a budget slot on a call that
   could never actually dispatch -- fixed by validating both
   `subagent_type` and `agent_name` before either the depth check or the
   budget, restoring the exact same "validate first, spend nothing on a
   rejected call" contract the pre-existing `subagent_type` path already
   had (and that the existing test suite's own
   `test_unknown_subagent_type_rejected_before_any_llm_call` caught when
   it briefly broke). 18 unit tests + 2 live-LLM scenarios: a real
   `security-auditor` agent (extends `base-coder`, `mode: plan`,
   read-only `tools:`) dispatched directly against a file with genuine,
   deliberately-introduced vulnerabilities (hardcoded secret + SQL
   injection) correctly found and explained both, proposed fixes without
   applying them, and left the audited file byte-for-byte unchanged
   (verified by hash, not just "no write call was logged"); a second live
   test gave the real top-level agent a task requiring it to discover the
   custom agent itself via `list_custom_agents` and choose to dispatch it
   by name -- it did, unprompted, and its own final summary correctly
   named the agent it used and the real findings. See README.md for the
   full writeup.
6. ~~Plugins (Addendum C)~~ -- **DONE.** `plugins.py`: `.agent_plugins/
   <name>/.agent_plugin/plugin.json` manifest (only `name` required, per
   the real spec) + component folders at the plugin root (`skills/`,
   `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`), plus a real
   `.agent_marketplace.json` catalog with actual remote fetch (GitHub/git,
   via GitPython -- already a real dependency, no new library). Framed by
   this doc's own earlier note as "a packaging layer over everything
   above, not a new capability by itself" -- verified that framing is
   accurate rather than assumed: checked Claude Code's OWN current docs
   and found "custom commands have been merged into skills" (a
   `commands/deploy.md` and `skills/deploy/SKILL.md` are literally the
   same mechanism) -- so plugin commands are loaded through skills.py's
   existing parser, not a second one. The one genuinely missing
   capability that check surfaced: a human at the REPL had no way to
   force a specific skill/command to run without waiting for the LLM to
   decide to call `load_skill` itself -- added real, direct `/name [args]`
   invocation to `main.py`. Hooks are a deliberately narrow, REAL subset
   (`SessionStart`/`PreToolUse`/`PostToolUse`/`Stop`), not the full
   ~30-event Claude Code catalog -- checked `agent.py`'s actual structure
   first and only implemented the 4 events that map onto extension points
   already proven live (the existing confirm() gate for PreToolUse, the
   exact tool-result-content injection point the batching nudge/rules
   already use for PostToolUse, run_agent's own real entry/exit for
   SessionStart/Stop); `Stop`/`SessionStart` are explicitly observational-
   only (append a note), never real loop-continuation, since Claude
   Code's own real `Stop` hook can force the agent to keep going and
   building that here would mean re-entering an already-hardened ReAct
   loop for a feature framed as packaging, not new capability. Verified
   MCP servers register through `mcp_client.py`'s ALREADY-GENERIC
   `connect_server` -- no new MCP plumbing needed. A real bug was found
   and fixed via this project's own committed example plugin
   (`.agent_plugins/git-safety/`): a command file can have real
   frontmatter (description, etc.) but no `name:` field at all (the
   filename is always authoritative for a command's name, confirmed from
   research) -- a first draft only handled the "no frontmatter at all"
   case and rejected this real, valid shape as malformed. 23 unit tests +
   1 live test (a REAL `git clone` of Anthropic's own public
   `anthropics/skills` repo, loading 17 real skills with zero warnings)
   + a real end-to-end REPL run (`/react-component build a ... component`
   → real file written → self-verified) via the actual `main.py` process,
   not a harness. See README.md for the full writeup.
7. ~~Plan mode (Tier 1 #3, now subsumed by Addendum A's `plan` mode) and
   session resume UX (Tier 1 #5)~~ -- **DONE.** This project's real
   durable state for a long task was already `missions.py` (a compact
   checkpoint -- summary/next-step/key-files -- not a raw replayed
   transcript, deliberately different from Claude Code's own full-
   transcript `.jsonl` session files, per `missions.py`'s own module
   docstring). Added the CLI surface real Claude Code exposes for this:
   `--resume <id>`/`-r` (scope the whole REPL to a named mission,
   loading its checkpoint), `--continue`/`-c` (resume the MOST RECENTLY
   UPDATED mission without needing to know its id -- reuses
   `missions.list_missions()`'s existing most-recent-first sort, not a
   second one), `--list-missions` (print and exit, no LLM call), and
   `--print`/`-p` + `--output-format json` (non-interactive one-shot
   mode for scripts/CI, reusing the SAME `run_agent`/`run_mission`/
   `run_agent_with_mode`/`run_mission_with_mode` call paths the
   interactive loop uses -- not a second, parallel execution path that
   could silently drift). A real gap was found and closed while wiring
   `--resume`+`--permission-mode` together: `agent.run_mission` had NO
   `system_prompt`/`tool_functions`/`tool_specs` parameters at all
   (confirmed by checking the real signature before assuming it would
   just work) -- so combining a mode with a resumed mission would have
   silently ignored the mode entirely. Fixed by extending `run_mission`
   to mirror `run_agent`'s own parameters and adding
   `permissions.run_mission_with_mode` as the exact mission-scoped
   mirror of the already-existing `run_agent_with_mode` (same
   `PermissionEngine`, never a second parallel mode implementation). A
   real test-design bug (mocked `sys.exit` not actually stopping
   execution, causing a redundant second exit call) was caught and fixed
   by a test written specifically to expose it -- the same class of bug
   `_parse_permission_mode`'s own test suite already caught once before.
   14 unit tests + multiple REAL, live end-to-end runs (not mocked): a
   real `--print` one-shot mission run, a real `--continue` correctly
   resuming the most-recently-updated mission and correctly recalling
   what happened in the prior run via its checkpoint, `--output-format
   json` producing real parseable JSON, and `--resume ... --permission-
   mode plan` genuinely refusing to write a file (the model itself
   explained it was in plan mode) -- verified by confirming the file was
   never created on disk, not just by trusting the model's own claim.
   See README.md for the full writeup.

