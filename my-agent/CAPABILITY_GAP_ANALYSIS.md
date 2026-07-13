# Full Capability Inventory: OpenClaude vs. Pulse Agent

Sourced from OpenClaude's own public documentation (README, `docs/`,
DeepWiki's indexed structure overview) and independent, widely-published
explainers of Claude Code's `Task`/sub-agent tool (a documented, public
API surface — not something extracted from the leaked source itself).
Every row is something you can verify yourself at the cited URL.

Sectioned by what it actually takes to close each gap.

---

## Tier 1 — Real gaps, clean-room buildable, no leak dependency

These are the honest, closeable gaps. Each has a public spec or is a
well-known open pattern (Aider, general agent-orchestration literature) —
nothing here requires touching Anthropic's leaked source.

### 1. Repo map (codebase intelligence)
**What OpenClaude's docs say it does** (`docs/repo-map.md`):
- Enumerates files via `git ls-files --cached --others --exclude-standard`
  (falls back to a directory walk outside git)
- Parses each file with tree-sitter -> function/class/type/interface
  definitions + cross-file references
- Builds a directed reference graph, edges weighted by
  `reference_count * IDF(symbol_name)` (common names like `get`/`set`
  contribute less)
- Ranks files with PageRank -- files imported by many others rank highest
- Renders top-down: file paths + signatures only (not implementations),
  stopping at a token budget
- Disk-cached, keyed by `(path, mtime, size)` -- only changed files re-parsed
- Supports TS/JS/Python only, ~20-30s cold build on 2000+ files, <100ms warm
- A `/repomap` command with `--tokens`, `--focus <path>`, `--focus-symbols
  <name>`, `--stats`, `--invalidate`
- Also exposed as a callable `RepoMap` tool the model can invoke mid-session
  with its own `focus_files`/`focus_symbols` args for a bigger ad-hoc budget

**Pulse Agent status:** not built. `rag_search` (ChromaDB semantic search)
solves a different problem (finding code by natural-language concept) --
it has no structural/import-graph awareness and isn't auto-injected into
context at session start.

**Buildability:** High. Pulse Agent already has `tree-sitter` +
`tree-sitter-python`/`tree-sitter-javascript` installed and working
(`ast_tools.py`) -- the parsing half of this is a known-working dependency
already. The graph+PageRank half needs `networkx` (or a small
hand-rolled PageRank, it's ~20 lines of linear algebra) -- Aider's own
implementation (`aider/repomap.py`, Apache-2.0, fully public) is the
correct reference to build from, not OpenClaude's docs-only description.

---

### 2. Sub-agents (nested task delegation with a scoped tool budget)
**What's publicly documented about Claude Code's `Task` tool** (via
DeepWiki's public architecture index, and multiple independent explainers
citing the tool's own JSON schema, which is standard practice to publish
since it's sent to the model as part of normal tool-calling):
- A tool (`Task`) whose schema takes `description`, `prompt`,
  `subagent_type`, optional `model` (sonnet/opus/haiku), optional `resume`
  (continue a prior sub-agent transcript), optional `run_in_background`
- Built-in agent types: `general-purpose` (full tools, inherits context),
  `Explore` (read-only, fast, cheap model by default), `Plan` (architect,
  proposes a plan, doesn't edit)
- Custom agents defined as Markdown + YAML frontmatter
  (`.claude/agents/*.md`), with a `tools:` allowlist that is a HARD
  constraint (a reviewer agent scoped to `Read, Grep, Glob` structurally
  cannot call `Write`, not just prompted not to)
- Subagents cannot spawn further subagents (bounded nesting depth)
- Returns exactly ONE final message back to the parent -- the parent never
  sees the sub-agent's intermediate tool calls, only its summary
- Real, cited cost trade-off: multi-agent workflows use "roughly 4-7x more
  tokens than single-agent sessions" (per Anthropic's own published
  guidance, cited in multiple explainers)

**Pulse Agent status:** No equivalent at all. `missions.py` decomposes a
LONG task into SEQUENTIAL missions with checkpoint handoff -- fundamentally
different from spawning a PARALLEL/NESTED sub-task with a restricted tool
set and getting one summary back. `start_background_process` runs a raw
shell command in the background, not another instance of the agent itself.

**Buildability:** High, and this is the single biggest structural gap.
Nothing here is provider-specific or leak-derived -- it's a tool-calling
pattern (a tool named e.g. `dispatch_agent` whose handler recursively
calls `run_agent()` with a restricted `TOOL_FUNCTIONS` subset and a fresh,
isolated message history) that fits directly into the existing
`TOOL_FUNCTIONS`/`TOOL_SPECS` registration pattern already used for every
other tool in this project.

---

### 3. Plan mode (propose-then-approve, distinct from per-action confirm)
**What's documented:** a `Plan` subagent type / a `plan` permission mode
that produces a step-by-step implementation plan and explicitly does NOT
call any mutating tool until the user approves the whole plan -- contrasted
with Pulse Agent's current per-action confirmation (approve/deny each
write/command as it comes up).

**Pulse Agent status:** No equivalent. `confirm_bridge.py` gates individual
destructive actions one at a time; there's no "show me the whole plan
first, then let me approve/reject it as a unit" mode.

**Buildability:** Medium -- mostly a system-prompt + a new `confirm=`
policy variant (accumulate proposed actions instead of executing them,
present as a batch, then either execute all with the EXISTING confirm
gate suppressed since it was pre-approved, or discard all). No new tool
mechanics, mostly orchestration around what already exists
(`_dispatch_tool_call`, `_needs_confirmation`).

---

### 4. Custom agent definitions (Markdown + YAML frontmatter)
**What's documented:** user-authored `.md` files with a `tools:` allowlist,
`model:`, `permissionMode:`, and a system-prompt body -- loaded at project
or user scope, invocable by name.

**Pulse Agent status:** None. One fixed `SYSTEM_PROMPT` for every task.

**Buildability:** Medium -- needs a loader (`agents/*.md` -> parsed
frontmatter + body), and ties naturally into sub-agents (gap #2): a
sub-agent's `subagent_type` would resolve to one of these definitions.
Building #2 and #4 together is more efficient than either alone.

---

### 5. Session resume by ID / non-interactive scriptable mode
**What's documented:** `--resume <id>`, `--continue`, `--fork-session`
(branches history into a new session ID); a `--print`/headless mode with
structured JSON output for CI/scripting; a background-session CLI
(`--bg`, `ps`, `logs`, `kill`) explicitly documented as local child
processes, NOT a daemon.

**Pulse Agent status:** Partial. `missions.py` already gives durable,
resumable state (`load_progress`/`save_progress`) keyed by `mission_id` --
conceptually equivalent to session resume, just not exposed as a
`--resume <id>` CLI flag with a "list my sessions" command.
`start_background_process`/`stop_background_process` already cover the
"don't run a daemon, track local child processes" design goal.

**Buildability:** High, and cheap -- this is mostly CLI/UX plumbing on top
of state (`missions.list_missions()`-style listing) that already exists.

---

## Tier 2 — Real features, but overlapping with what Pulse Agent already
## has via a different, arguably more deliberate design

- **Per-agent/per-task model routing** (`agentModels`/`agentRouting` in
  OpenClaude) -- Pulse Agent's Router already does provider-level failover
  automatically; intentional per-role model *selection* (cheap model for
  "Explore," strong model for "Plan") is a real, missing refinement, but
  it's an enhancement to an existing, tested system, not a net-new one.
- **`maxSteps` forced-summary cap per sub-agent** -- overlaps with mission
  checkpointing's existing "compact handoff summary" mechanism; the
  difference is granularity (per-sub-agent-call vs. per-mission).

## Tier 3 — Not worth chasing (product surface, not core agent capability)

- Custom Ink-based terminal renderer -- UI polish, not agent capability.
- 15+ provider integrations -- you have 4 real, verified ones; more
  providers is marginal engineering, not a capability gap.
- npm/AUR/Android packaging maturity -- real, but it's distribution work,
  tracked separately (see prior conversation turn).
- Headless gRPC server -- a specific IPC transport choice; Pulse Agent's
  `bridge_server.py` (newline-delimited JSON over stdio) solves the same
  "let another process drive the agent" problem with less complexity for
  a VS Code extension's specific needs. Only worth revisiting if a
  non-Node consumer (Python service, another IDE) needs to drive the
  agent and stdio-JSON turns out to be insufficient.

---

## Recommended build order (this doc's own conclusion)

1. **Sub-agents** (Tier 1 #2) -- the single largest structural capability
   gap, and it composes with almost everything else (custom agents,
   per-role model routing, plan mode all build ON TOP of having a
   sub-agent dispatch mechanism at all).
2. **Repo map** (Tier 1 #1) -- second-largest, and already has the hard
   dependency (tree-sitter) installed and working in this project.
3. **Custom agent definitions** (Tier 1 #4) -- natural follow-on to #1.
4. **Plan mode** (Tier 1 #3) and **session resume UX** (Tier 1 #5) --
   smaller, mostly orchestration/CLI work on existing infrastructure.
