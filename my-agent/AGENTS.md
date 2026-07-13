# Pulse Agent

A from-scratch coding agent: a ReAct loop (`agent.py`) driving a large
tool registry (`tools.py` + optional modules) via a multi-provider LLM
router (`llm_client.py`, LiteLLM-backed: Groq/Gemini/Cerebras/OpenRouter
with automatic failover). Runs locally via `main.py`; also exposes a
stdio JSON bridge (`bridge_server.py`) for a VS Code extension
(`vscode-extension/`).

This file follows the AGENTS.md open standard (agents.md) -- plain
markdown, no required frontmatter, read natively by any AGENTS.md-aware
tool. Pulse Agent's own `rules.py` also loads this file into every task's
system prompt as an always-on project rule (see "Custom Project Rules" in
README.md) -- so this file governs both external tools working on this
codebase AND Pulse Agent working on itself.

## Setup commands

- Install Python deps: `pip install -r requirements.txt`
- Install Playwright's browser binary (needed for browser tools):
  `python3 -m playwright install chromium && sudo python3 -m playwright install-deps chromium`
- Install optional MCP/LSP tooling (only if using those features):
  `sudo npm install -g typescript-language-server typescript`
- Set at least one provider API key in `.env` (see `.env.example`):
  `GROQ_API_KEY`, `GOOGLE_API_KEY`, `CEREBRAS_API_KEY`, or `OPENROUTER_API_KEY`

## Run commands

- Interactive REPL: `python main.py`
- Dry-run (never executes flagged actions): `python main.py --dry-run`
- With a permission mode: `python main.py --permission-mode plan` (also:
  `accept_edits`, `auto`, `dont_ask`, `bypass` -- see `permissions.py`)

## Test commands

- Every feature has a corresponding test file in `test/` -- run any of
  them directly: `PYTHONPATH=. python3 test/<name>_test.py`
- Tests are split into three tiers by design (see README.md for the full
  rationale behind this split):
  1. `*_test.py` -- unit-level, no real LLM call, fast, safe to run often.
  2. `*_wiring_test.py` -- integration through the real dispatch chain,
     LLM calls fully mocked, isolates wiring bugs from LLM
     non-determinism.
  3. `*_live_test.py` -- real LLM calls against real provider API keys,
     slower (can take several minutes), the authoritative end-to-end
     proof for any given feature.
- `test/` is a PERMANENT directory -- never delete its contents. Only
  `test/scratch/` is disposable scratch space.

## Code style / conventions

- Every optional feature module (`git_tools.py`, `rag_indexer.py`,
  `ast_tools.py`, `subagents.py`, `skills.py`, `rules.py`, ...) follows
  the SAME registration pattern: expose `TOOL_FUNCTIONS`/`TOOL_SPECS` dicts
  plus an `<X>_AVAILABLE` boolean flag; `tools.py` imports each in a
  `try/except` block at its own end and only registers the tools if the
  flag is `True`. Never hard-require an optional dependency at the top of
  `tools.py` itself.
- Any module that needs `tools.py`'s own helpers (`WORKDIR`, `_resolve`,
  `is_sensitive_path`, etc.) imports `tools` LAZILY -- inside a
  `_get_tools()` function, on first actual call -- never at module level.
  `tools.py` imports these optional modules at its own end, so a
  module-level `import tools` in one of them creates a real circular
  import that silently leaves the whole feature disabled with no visible
  error (this has been a real, repeatedly-found bug class in this
  project -- see README.md's git/RAG sections for the original
  discovery).
- Never trust a design/proposal's code as correct without verifying it
  against the actually-installed library/runtime -- this project has
  found and fixed real bugs (fabricated APIs, stdlib gotchas like
  `pathlib.match()`'s incorrect globstar semantics, off-by-one
  frontmatter parsers) by testing directly rather than reviewing by eye.
- Secret/credential paths (`.env`, private keys, git/AWS/SSH credentials)
  are hard-blocked by `tools.is_sensitive_path()` -- the single canonical
  check, reused everywhere (never re-implemented per-module). No
  permission mode or confirmation override can bypass this.
- Destructive/irreversible shell commands are flagged by
  `tools.is_destructive_command()` -- also the single canonical check.
- When adding a new write-like tool, register it in
  `agent._WRITE_FILE_TOOL_NAMES` / `_APPLY_EDIT_TOOL_NAMES` and
  `cache.MUTATING_TOOLS` so the confirmation gate and cache invalidation
  both see it -- these are NOT inferred automatically by tool name.

## Verification discipline (read before claiming something works)

- A claim of "tested" must mean the LITERAL scenario was run, not a
  generic substitute -- this project was directly challenged on this
  once (see README.md's "Honest gap-check" section) and the right
  response was to actually go verify, not explain why a substitute was
  reasonable.
- Verify the REAL ARTIFACT (a file's actual content on disk, a real
  screenshot, a real `.env` diff), never the model's own natural-language
  summary of what it did -- this project has caught its own test bugs
  this way more than once (see README.md's Skills and Rules sections).
- For anything LLM-facing, prefer a live test with a real provider API
  call over a mocked one wherever practical; use mocked/wiring tests to
  isolate a specific mechanism from LLM non-determinism, not as a
  substitute for the live proof.

## Sandbox / environment notes

- Pip packages, npm globals, and Playwright browser binaries do NOT
  persist across sessions in this project's usual sandboxed environment --
  expect to re-run the setup commands above at the start of a fresh
  session before assuming any optional feature is available.
- `.git/config` does not persist either -- re-run
  `git config user.email/user.name` and `git remote add origin ...` each
  fresh session before committing.

## Key files (start here)

- `agent.py` -- the ReAct loop, system prompt, confirmation gate, batching
  nudge, path-scoped rule injection.
- `tools.py` -- the core tool registry + safety guardrails
  (`is_sensitive_path`, `is_destructive_command`).
- `permissions.py` -- named permission modes on top of the confirmation gate.
- `subagents.py` -- `dispatch_agent`, restricted sub-loop delegation.
- `skills.py` / `rules.py` -- Agent Skills and custom project rules.
- `README.md` -- the full changelog/design-rationale doc; every feature's
  "what broke and how it was fixed" story lives there.
- `COMPARISON_openclaude.md` -- the competitive capability roadmap this
  project is being built against.
