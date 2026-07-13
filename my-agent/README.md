# my-agent

A tiny, self-contained coding agent loop.

```
my-agent/
├── main.py         # interactive loop: you type → agent thinks → acts
├── tools.py        # tool functions the agent can call (read_file, write_file, run_command)
├── agent.py        # ReAct loop + system prompt (talks to llm_client, not any single provider)
├── llm_client.py   # LiteLLM-based multi-provider LLM access, with automatic failover
├── memory.py       # helper functions to load/save memory.json
└── memory.json     # persisted conversation history + notes
```

## Setup

```bash
cd my-agent
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and fill in whichever free-tier provider keys you have
(any subset, at least one required):

```
GROQ_API_KEY=...         # https://console.groq.com/keys
GOOGLE_API_KEY=...       # https://aistudio.google.com/apikey
CEREBRAS_API_KEY=...     # https://cloud.cerebras.ai
OPENROUTER_API_KEY=...   # https://openrouter.ai/keys
```

`llm_client.py` auto-loads `.env` on startup (via `python-dotenv`) and only
registers providers whose key is actually set, so you don't need all four —
one is enough to get started.

**`.env` is git-ignored** — never commit it or paste real key values into
chat/docs/issues. If a key is ever exposed that way, treat it as
compromised and regenerate it immediately from the provider's dashboard.
You can also skip `.env` entirely and `export` the same variables directly
in your shell instead; both work, and real shell exports always take
precedence over `.env` values.

## Run

```bash
python main.py
```

Then just type requests, e.g.:

```
you> read main.py and tell me what it does
you> write a hello.py that prints "hi"
you> run hello.py and show me the output
```

Special commands inside the loop:
- `/reset` — clear persisted memory
- `/memory` — print current memory.json contents
- `/exit` — quit

## Multi-provider LLM layer (llm_client.py)

Instead of hardcoding one LLM provider, `agent.py` calls into
`llm_client.chat_completion()`, which is backed by a
[LiteLLM](https://docs.litellm.ai) `Router` spanning every free-tier
provider you've configured a key for: **Groq → NVIDIA NIM → Gemini →
Cerebras → OpenRouter**. If one provider is rate-limited or down
mid-conversation, the Router automatically retries on the next one — the
ReAct loop itself never needs to know which provider actually answered.

```python
from litellm import Router

router = Router(
    model_list=[
        {"model_name": "code-agent", "litellm_params": {"model": "groq/llama-3.3-70b-versatile", "api_key": ...}},
        {"model_name": "code-agent", "litellm_params": {"model": "nvidia_nim/z-ai/glm-5.2", "api_key": ...}},
        {"model_name": "code-agent", "litellm_params": {"model": "gemini/gemini-2.5-flash", "api_key": ...}},
        {"model_name": "code-agent", "litellm_params": {"model": "cerebras/gpt-oss-120b", "api_key": ...}},
        {"model_name": "code-agent", "litellm_params": {"model": "openrouter/openai/gpt-oss-120b:free", "api_key": ...}},
    ],
    num_retries=2,
    allowed_fails=1,
    cooldown_time=30,
    routing_strategy="simple-shuffle",
)
```

`llm_client.py` also exposes a simpler `ask_llm(prompt, model=...)` helper
for one-off scripts/experiments (Phase 1 style) with its own manual
fallback chain, independent of the Router — see the `FALLBACK_CHAIN` list
at the top of the file if you want to reorder providers or swap models.

> **Model choice note:** only models that support tool/function calling are
> used here (`llama-3.3-70b-versatile`, `z-ai/glm-5.2` on NVIDIA NIM,
> `gemini-2.5-flash`, `gpt-oss-120b` on both Cerebras and OpenRouter),
> since the agent's ReAct loop depends on tool calls to read/write files
> and run commands. Smaller/older free models often can't call tools
> reliably.

### NVIDIA NIM (`z-ai/glm-5.2`) — added mid-session, verified before wiring in

A user pasted a working code snippet using
[NVIDIA's build.nvidia.com](https://build.nvidia.com) hosted API (OpenAI
SDK, `base_url="https://integrate.api.nvidia.com/v1"`, model
`z-ai/glm-5.2`) along with fresh Groq/Google keys. Per this project's
"never trust a proposal, verify against the real thing" discipline, before
touching `llm_client.py`:

- **Confirmed live** the raw `openai` SDK snippet actually works (real
  `chat.completions.create` call succeeded) and that the model supports
  real OpenAI-style tool-calling (a `get_weather` tool round trip returned
  a genuine `tool_calls` response, not just plain text) — the agent's
  ReAct loop is useless against a model that can't call tools.
- **Real bug avoided, not assumed**: NVIDIA's own docs/code snippets tell
  you to set `NVIDIA_API_KEY`, but litellm's `nvidia_nim/` provider prefix
  actually reads `NVIDIA_NIM_API_KEY` when no explicit `api_key` kwarg is
  passed — confirmed directly against litellm 1.91.0's installed source
  (`get_llm_provider_logic.py`) AND with a real live call using only the
  env var, no explicit key argument.
- **Confirmed live** that `litellm.completion(model="nvidia_nim/z-ai/glm-5.2", ...)`
  needs no `api_base` override — litellm resolves the real
  `https://integrate.api.nvidia.com/v1` endpoint internally for this
  provider prefix, same as Groq/Gemini/OpenRouter don't need one either
  (only Cerebras does, for an unrelated reason already documented above).
- Researched GLM-5.2 itself before treating it as worth adding at all: an
  independently-published review confirms it benchmarks near Claude Opus
  4.8 on SWE-Bench Pro with full function-calling support — genuinely
  relevant to this project's "capability parity with Claude Code" goal,
  not just "one more free model."
- **User's explicit placement decision**, asked directly rather than
  guessed: NVIDIA NIM goes **second** in the fallback chain (right after
  Groq), not first — GLM-5.2's real-world latency/rate-limit behavior
  under sustained agentic use hasn't been proven the way Groq's has been
  across this whole project (a single test call took ~5-8s vs Groq's
  usual sub-1s), so it doesn't get first priority despite being the
  strongest model in the chain.
- **Real fallback verified, not just "both providers work independently"**:
  mocked `litellm.completion` (the function `Router.completion` calls per
  deployment attempt — an earlier draft of this test mistakenly mocked
  `Router.completion` itself, which IS the retry/fallback logic under
  test, so the mocked failure short-circuited before ever exercising real
  fallback) to always fail every `groq` model call. Confirmed the Router
  genuinely retried groq 3 times then called `nvidia_nim/z-ai/glm-5.2`
  next, and got a real answer back. Full regression test:
  `test/nvidia_nim_provider_test.py`.
- Ran the full existing regression suite afterward (10 test files) — zero
  regressions from adding a 5th model to the `model_list`.

## How it works — the ReAct loop

`agent.py` implements the classic **Thought → Action → Observation** loop
that drives coding agents like Claude Code:

```python
while not task_complete:
    response = llm.chat(messages)          # Thought: model decides what to do
    if response.tool_calls:
        for call in response.tool_calls:
            result = execute_tool(call)    # Action: run read_file/write_file/run_command
            messages.append(result)        # Observation: feed result back to the LLM
        # loop again — model reacts to what it just observed
    else:
        task_complete = True               # model gave a final answer, no more tools needed
```

Concretely:

1. `main.py` reads your input and calls `agent.run_agent(user_input)`.
2. `agent.py` sends the conversation (system prompt + memory history + your
   message) to the LLM along with the tool specs from `tools.py`.
3. If the model requests a tool call (e.g. `read_file`), `agent.py` executes
   it via `tools.py` and appends the result back into `messages` as an
   observation.
4. This repeats (up to `MAX_TOOL_ITERATIONS` as a safety cap) until the model
   responds with no tool calls — a final plain-text answer — which is
   printed and saved to `memory.json`.

By default (`verbose=True`), `main.py` prints each step live as it happens:

```
you> read main.py and tell me what it does
[Thought] I need to see the file first.
[Action] read_file({"path": "main.py"})
[Observation] """ main.py ------- ... """
[Thought] Now I have enough context to answer.

agent> main.py is the interactive REPL that ...
```

## Safety guardrails

- **Secrets are hard-blocked, unconditionally.** `read_file`, `write_file`,
  and `run_command` all refuse to touch `.env`, private keys (`.pem`,
  `.key`), git/AWS/SSH credentials, etc. — no confirmation prompt can
  override this, since the whole point is to stop that content from ever
  entering the LLM's context (which gets sent over the network to
  whichever provider answers that turn). See `tools.is_sensitive_path` /
  `tools.references_sensitive_path`.
- **Destructive shell commands require confirmation.** Patterns like
  `rm -rf`, `git reset --hard`, force-push, `DROP TABLE`, `sudo`, etc. (see
  `tools.is_destructive_command`) pause the loop and ask a human to approve
  before running. In `main.py` this is an interactive `y/N` prompt; the
  underlying `confirm(name, args, reason) -> bool` callback in
  `agent.run_agent()` can be swapped out for automated tests, CI, or a UI.
- **`--dry-run` mode**: `python main.py --dry-run` auto-declines every
  flagged action instead of prompting — the agent will tell you what it
  *would* have run, without actually running it. Useful the first time you
  point it at a real codebase.

## Parallel tool execution

When a single LLM turn requests multiple **independent, read-only** tool
calls (`read_file`/`list_files`/`grep_files` — see `cache.CACHEABLE_TOOLS`),
`agent.py` runs them concurrently in a thread pool instead of one at a time.
`write_file`/`run_command`, and anything that needs a confirm() prompt (see
Safety guardrails above), always run sequentially and in order, since they
can have side effects or real dependencies on each other.

**Be precise about what this does and doesn't save:** this reduces
wall-clock *latency per task* when the model batches calls into one turn —
confirmed live at ~1–1.4s for a 3-file read that took ~64s across 4
sequential turns when the model didn't batch. It does **not** reduce the
*number* of LLM calls the model chooses to make — that depends on how the
model decides to structure the task and isn't fully controllable via
prompting (in testing, the model sometimes batched reads into one turn on
its own for an ambiguous prompt, and sometimes didn't; an explicit
instruction to batch made it reliable). For tasks with genuine sequential
dependencies (read → decide → write → verify), there's nothing to
parallelize and this has no effect, which is expected and correct.

## Context window / large-output protection

`read_file`, `run_command`, and `grep_files` all cap how much text they can
return in a single tool result (`tools.MAX_READ_FILE_CHARS` = 40,000 chars
for read_file, `tools.MAX_TOOL_OUTPUT_CHARS` = 4,000 for the other two).
Oversized output is cut on a line boundary with a note like
`"... [truncated: showing 949 of 60000 lines, 2656686 more chars. Use
grep_files to search for specific functions/sections instead]"`, so the
model knows to search for a specific part rather than assume it saw the
whole file.

**Why this exists:** confirmed live that a single unbounded `read_file()` on
a large (~2.7MB / ~670k-token) file crashed the whole agent with an
unhandled `BadRequestError` ("Please reduce the length of the messages or
completion") — `run_command`/`grep_files` were already capped, but
`read_file` wasn't. Retested after the fix on the same file: the agent
truncated gracefully, adapted by using `grep_files` and then
`run_command("grep -c ...")` to get an exact count via shell instead of
reading the whole file, and answered correctly (30,000 functions,
independently verified).

As a second line of defense, `agent.py` also catches
`litellm.ContextWindowExceededError` around the LLM call itself — if
conversation history *still* grows too large across many turns on a long
task (a different failure mode than one oversized tool result), the agent
stops gracefully with an explanation instead of crashing with a raw
stack trace, and suggests breaking the task into smaller pieces or running
`/reset`.

## Overwrite protection: diffs, confirmation, and undo

`write_file` overwriting an EXISTING file with genuinely different content
now requires human confirmation, showing a real unified diff of exactly
what would change (see `tools.diff_for_write`). Creating a brand-new file,
or "writing" identical content, proceeds without friction — the goal is to
gate the case that can actually lose real work, not to nag on every write.

Separately and *unconditionally* — regardless of how the write was
approved — every overwrite of an existing file is first backed up to
`.agent_backups/` (see `checkpoint.py`). This is deterministic, not
something the LLM controls or can skip: even a mistaken "yes" to the
confirmation prompt is recoverable. Use the `undo_last_edit(path)` tool (or
call it directly from Python) to restore a file to its content from just
before its most recent write. The backup index is persisted to
`.agent_backups/index.json` and reloaded on every run, so undo keeps
working even after the process restarts or crashes — verified live: a
write followed by a simulated crash (killing the Python process entirely)
still restored correctly from a fresh process afterward.

This deliberately does **not** try to be git. If your project is already a
git repo, real git integration (diffs via `git diff`, checkpoints as real
commits) would be a stronger foundation for a later iteration — this is the
minimal, dependency-free layer that makes `write_file` safe to use today
regardless of whether a repo exists.

**Note on `grep_files` and secrets:** while building this, found and fixed
a related gap — `grep_files` had no `is_sensitive_path` check at all, so a
match landing inside `.env` (e.g. searching for a common word that also
appears in a key's name) would return the literal secret value as part of
the match line, bypassing the hard block that `read_file`/`write_file`
already had. `grep_files` now excludes sensitive files from the search
entirely (`--exclude`/`--exclude-dir` at the grep level, plus a second
defensive filter on the output) — confirmed with several adversarial
search patterns that it no longer leaks real key material.

## Provider failover: a real bug found by simulating an actual IDE workload

Testing a realistic multi-turn "build a website" scenario (index.html +
styles.css + script.js, then adding a features section, then a contact
form — three sequential tasks, the kind of work an IDE agent is actually
used for) surfaced a genuine bug in the multi-provider Router setup, not a
hypothetical one: it crashed on the very first task.

**Root cause:** all four providers (Groq, Gemini, Cerebras, OpenRouter)
shared a single Router `model_name` ("code-agent"). In LiteLLM, "retries"
(same deployment, tried again) and "fallback to a different deployment" are
distinct mechanisms — sharing one model_name across providers does NOT
guarantee that exhausting retries on a failing provider moves on to a
different one. Reproduced this directly with a mocked "Groq always returns
a malformed tool-call" scenario: the Router retried Groq twice and gave up
without ever trying Gemini/Cerebras/OpenRouter, even though they were
configured and healthy.

**Fix:** each provider now gets its own Router `model_name`
(`groq-agent`, `gemini-agent`, `cerebras-agent`, `openrouter-agent`) with an
explicit `fallbacks=` chain wired between them, so exhausting retries on
one guarantees the next attempt is a genuinely different provider. Verified
with the same mocked scenario: call sequence now shows Groq retried once,
then Gemini actually invoked and answering successfully. Also verified a
deeper case (only the 3rd provider in the chain works) and the "everything
fails" case (raises cleanly instead of hanging).

**Re-ran the full 3-task website scenario after the fix: zero crashes.**
Inspected the actual generated files afterward (not just "did it crash") —
correct HTML structure with nav/hero/features/contact form, real CSS
including the requested grid layout for feature cards, and JS with the
exact validation logic requested (checks all three fields are non-empty
before allowing submit). This is the first real evidence in this project
that a sustained, multi-turn build task can complete without a provider
API quirk unhandled-crashing the whole session.

## Long tasks: missions instead of one giant conversation

Directly tested the "50-turn session, then a crash/restart" scenario and
found the real bug: `memory.py`'s `MAX_HISTORY_TURNS = 20` silently and
permanently drops old turns once a single conversation exceeds it —
confirmed by appending 50 turns, then reloading from a fresh process:
turns 0–29 were gone, only 30–49 survived. Persistence itself worked fine
(the data that WAS kept did survive the restart); the cap on any single
conversation was the actual problem.

Rather than fix this by raising the cap (which just delays hitting the
LLM's own context window instead) or by adding SQLite + FTS5 + LLM-driven
context compression (a much larger rewrite, unproven to be needed, and
still fundamentally about sustaining one ever-growing conversation), this
takes a different approach: **`missions.py`** breaks a large task into
several short, fresh-context missions that hand off to each other through
a small, explicit checkpoint file instead of a shared transcript.

```python
from agent import run_mission

# Mission 1 (any process)
run_mission("Design the database schema.", mission_id="my-app")
# -> saves .agent_missions/my-app/progress.{json,md}: summary, next step, key files

# Mission 2 (a LATER, possibly fresh process/session) automatically resumes:
run_mission("Now build the backend API.", mission_id="my-app")
# -> its prompt is prefixed with mission 1's checkpoint, so it has the
#    context it needs without replaying mission 1's full transcript
```

Each mission gets its **own** memory file
(`.agent_missions/<mission_id>/memory.json`), completely isolated from
other missions and from the global `memory.json` `main.py` uses — so no
single mission's history needs to approach `MAX_HISTORY_TURNS` in the first
place, by design, rather than by compressing around a cap after the fact.
After every mission task, the agent asks the model for a short (2-4
sentence) summary + explicit next step + key file list, and that's what
gets checkpointed — not the raw conversation.

**Verified end-to-end, live, across two genuinely separate processes:**
mission 1 created `index.html`/`styles.css` for a landing page (verified
via real `cat` execution) and saved a checkpoint; a completely fresh
process then ran mission 2 against the same `mission_id`, correctly printed
`[Mission] Resuming 'landing-page' from checkpoint saved at ...`, read the
existing `index.html`, added the requested paragraph, and re-verified it —
all without ever having seen mission 1's conversation, only its checkpoint.
Confirmed independently on disk: the file genuinely contained the new
content, and the mission's own memory.json held only 2 turns.

This does **not** add cross-session full-text search (FTS5) — if that
becomes a real, separately-justified need (e.g. "what did we decide about
auth three missions ago"), it's still a reasonable feature to add later,
but it isn't required to solve "a long build eventually loses context."

## MCP tools: inheriting the ecosystem instead of writing every parser

`mcp_client.py` + `tools.py` connect to two external MCP (Model Context
Protocol) servers and expose their tools alongside the native ones:
`fetch_fetch` (arbitrary HTTP requests, via `mcp-server-fetch`) and
`filesystem_read_file`/`list_directory`/`search_files`/etc. (via
`@modelcontextprotocol/server-filesystem`, scoped to this project's
`test/` directory).

**Setup**, beyond `pip install -r requirements.txt`:
```bash
pip install mcp mcp-server-fetch
# @modelcontextprotocol/server-filesystem runs via `npx -y ...` automatically,
# no separate install needed (confirmed: npx fetches and runs it on demand).
```

**Corrected two real bugs in the original design sketch, confirmed by
direct testing before writing the real integration:**
1. `ClientSession(...)` isn't `await`-able directly — both it and
   `stdio_client(...)` are async context managers (`async with`).
2. The fetch server's tool is literally named `fetch`, not `fetch_get`.

**Bridged a structural mismatch the sketch didn't address**: MCP sessions
are inherently async (persistent subprocess + stdio connection), but this
project's entire tool dispatch is synchronous. Rather than `asyncio.run()`
per call (which breaks inside an already-running loop and can't keep a
server connection alive across calls), one persistent background event
loop thread runs for the process lifetime; synchronous callers submit
coroutines to it via `run_coroutine_threadsafe` and block on the result —
so server connections stay alive across multiple tool calls instead of
respawning a Node process every time.

**Closed a real safety gap the sketch didn't address**: the MCP filesystem
server's own `write_file`/`edit_file` would bypass this project's entire
existing safety net (diff-before-overwrite confirmation, automatic
backup, `undo_last_edit`) if registered as raw pass-throughs — they write
through a completely separate code path. `filesystem_write_file` is
instead intercepted and routed through this project's own `write_file()`
underneath, so an MCP-driven write gets identical protection to a native
one. **Found and fixed a real bug in this wiring**: `agent.py`'s
`_needs_confirmation` only checked for the literal name `"write_file"`,
so the wrapped MCP tool initially bypassed confirmation entirely despite
being routed through the same function — confirmed directly (denying
confirmation didn't stop the write), fixed by adding
`filesystem_write_file` to the set of tool names that trigger the
diff/confirmation check.

**A second real bug, found via the live validation test, not inspection**:
asked the agent to fetch weather and save it via MCP — on its first
attempt it wrote the literal placeholder string `<fetch_fetch_result>` to
the file instead of the actual fetched text, a new variant of the
"placeholder instead of real content" hallucination documented earlier
for file-edit diffs, this time applied to a tool call's output instead of
a file's prior content. The existing checkpoint/backup system correctly
captured this bad state; the agent then self-corrected on read-back. Fixed
the root cause by generalizing the system prompt's anti-placeholder rule
to explicitly cover both cases (referencing prior file content vs.
referencing an earlier tool result) — re-ran the identical test afterward
and it wrote the correct real content on the first attempt.

**Validated with the exact "fetch + save + verify" test, live**: the agent
called `fetch_fetch` for San Francisco's weather, `filesystem_write_file`
to save it, and the native `read_file` to verify — all three succeeded
with zero custom HTTP or file-write code in the agent itself. Independently
re-verified: the real file on disk contains the correct weather text, and
confirmed via `pgrep` immediately after process exit (and again 2 seconds
later) that no `mcp-server-fetch` or filesystem-server subprocess was left
running — the daemon-thread + `atexit` shutdown genuinely cleans up.

## LSP tools: semantic refactoring, not grep-and-replace

`tools_lsp.py` adds three tools backed by REAL language servers (`pylsp`
for Python, `typescript-language-server` for JS/TS) via `pylspclient` —
proper import/scope resolution, not text matching:

- **`lsp_find_references(file_path, symbol_name)`** — every real usage of a
  symbol across the project, following actual imports (won't conflate two
  unrelated identically-named variables in different scopes the way grep can).
- **`lsp_preview_rename(file_path, symbol_name, new_name)`** — previews a
  semantic rename across every affected file. Returns the **complete new
  content** of each file, not a diff, specifically so the agent's only job
  is to pass that exact text to `write_file` — no reconstruction, no risk
  of the placeholder-comment hallucination documented above. Never writes
  anything itself; the actual edit still goes through `write_file`, so it
  gets the existing diff-confirmation/backup/undo safety net for free.
- **`lsp_get_diagnostics(file_path)`** — real compiler/language-server
  errors and warnings (e.g. a broken import after a rename).

**Setup**, beyond `pip install -r requirements.txt`:
```bash
pip install python-lsp-server                              # Python support
sudo npm install -g typescript-language-server typescript   # JS/TS support
```

**Built on `pylspclient`, not hand-rolled JSON-RPC.** A naive
Content-Length-header parser is exactly the kind of "looks simple, subtly
wrong" code this project has been bitten by before (see the provider-schema
and truncation bugs earlier) — `pylspclient` already handles header framing,
threading, and request/response correlation correctly.

**Two real bugs found and fixed while building this, both confirmed by
direct testing before assuming the naive approach would work:**

1. **`checkJs` gap**: confirmed `typescript-language-server` reports **zero
   diagnostics** for plain `.js` files with no `jsconfig.json` (or one
   without `"checkJs": true`) — including a genuinely broken import of a
   function that no longer exists. `lsp_get_diagnostics` now explicitly
   warns when this applies, so "no diagnostics" can never be silently
   mistaken for "verified clean" — the system prompt also tells the agent
   to fall back to actually running the code in that case.
2. **Process hang on exit**: `pylspclient`'s `LspEndpoint` is a
   non-daemon `threading.Thread` running a blocking read loop — confirmed
   directly that a script which successfully got its result and printed it
   would still hang indefinitely afterward, because the interpreter waits
   for all non-daemon threads before exiting. Fixed by marking the thread
   a daemon so it can never block process exit, while `atexit` still
   attempts a clean shutdown first on normal exit.

**Validated with the exact "rename across files" test**: asked the agent
to rename `calculateAge` to `getUserAge` in `test/linkedin_profile/utils.js`,
used across `profile.js` and `analytics.js`. It correctly called
`lsp_find_references` (found 5 real references across all 3 files with
correct line:character positions), `lsp_preview_rename` (3 files, exact
change counts), applied each file's exact returned content via `write_file`,
then ran `lsp_get_diagnostics` per file and correctly distinguished
unrelated pre-existing lint hints from actual import errors (there were
none). Independently verified after the fact: **grepped for the old name
across all files (zero matches — fully renamed)**, and **actually executed
the refactored code with `node`** — both files ran cleanly with correct
output, real proof the rename didn't just look right but works.

## Browser tools: visual verification, not just "the file wrote fine"

`tools_browser.py` adds three tools (only registered if Playwright + a
working headless Chromium are actually usable — see setup below):

- **`screenshot_url(url, output_path)`** — screenshot a live http(s) URL.
- **`test_local_html(file_path, output_path)`** — serve the file's directory
  over a REAL local HTTP server (never `file://` — many pages behave
  differently or break under `file://`, especially anything using
  `fetch`/relative asset paths) and screenshot the rendered result.
- **`evaluate_js(file_path, script)`** — load a local file the same way and
  run a JS expression against it (e.g. `document.querySelectorAll('.card').length`)
  for a precise check instead of eyeballing a screenshot.

All three capture browser console errors/warnings and uncaught JS
exceptions during page load and report them as part of the tool result —
directly answering "no errors in browser console" as something the agent
can actually check, not just assume.

**Setup is two steps beyond `pip install -r requirements.txt`** — confirmed
by direct testing that skipping either one causes a real, specific failure:
```bash
playwright install chromium
sudo playwright install-deps chromium   # Linux: OS-level shared libs Chromium needs
```
Without the second command, headless Chromium fails to even launch with
`error while loading shared libraries: libnspr4.so: cannot open shared
object file` — reproduced directly in this sandbox before installing the
OS deps. If Playwright/Chromium/its OS deps aren't available, `tools.py`
simply doesn't register these tools (`tools.BROWSER_TOOLS_AVAILABLE`),
rather than exposing tools that would always fail.

**Validated with the exact "LinkedIn profile" test**: asked the agent to
build a professional profile site in `test/linkedin_profile/` (header,
profile, experience, skills sections, linked stylesheet, responsive) and
verify it with `test_local_html`. Independently re-verified afterward,
not just trusting the agent's self-report:
- `index.html` has real semantic structure: 1 `<header>`, 1 `<main>`,
  3 `<section>`, 1 `<footer>`.
- `style.css` exists, is linked via `<link>`, zero inline `style=`
  attributes.
- The screenshot is a genuine render, not a placeholder: sampled a pixel
  from the header at `(100, 30)` and got `(10, 102, 194)` — an exact match
  for the CSS's `#0a66c2` LinkedIn-blue background, plus 670 distinct
  colors in the image (not blank/solid).
- Zero console errors/warnings reported.

Also separately tested the console-error detection path with a page that
deliberately calls `console.error()` and throws an uncaught exception —
both were correctly captured and surfaced in the tool's result, and the
existing path-traversal/sensitive-path guardrails from `tools.py` are
inherited automatically (verified: `.env` and `../../etc/passwd` are both
correctly refused by the browser tools too).

## Cross-session memory: what actually persists, and the bug that was fixed

Contrary to a design proposal that assumed session state was being lost on
restart (which would have called for a SQLite/FTS5/compression rewrite),
testing showed **cross-process persistence already worked correctly**:
`memory.py` writes every completed turn to `memory.json`, and a brand-new
Python process reading it back recalls prior context fine — verified live
across two fully separate process runs.

The REAL gap: if `run_agent()`'s ReAct loop crashed partway through a task
(observed live and often during testing: provider rate limits, transient
network errors, schema mismatches) the loop would raise before ever
reaching `memory.append_turn()` at the bottom — so the entire turn,
including any tool calls that had *already run for real* (files written,
commands executed), vanished from `memory.json` as if nothing happened.
Reproduced directly: a simulated crash after a real `write_file` call left
the file genuinely changed on disk, but `memory.json` had no record of the
attempt at all.

Fixed with a `try/except` around the loop body: on any unhandled exception,
whatever's known so far is recorded to memory (with an explicit
`[INTERRUPTED before completion: ...]` marker warning that tool calls may
already have taken real effect) *before* the exception is re-raised — the
crash is never swallowed, `main.py`'s outer `except` still reports it, but
the next session now has an honest record instead of a false-clean slate.

This was intentionally NOT solved with a database rewrite, multi-session
hierarchy, or LLM-driven summarization pipeline — none of that was needed
for the actual, reproduced bug, and adding it would mean a new dependency
(`tiktoken`), extra LLM calls burning free-tier quota to compress context we
don't have evidence of accumulating, and a much larger surface area to keep
correct. `memory.py`'s existing `MAX_HISTORY_TURNS = 20` cap already bounds
`memory.json`'s growth; if a genuine need for semantic search over past
sessions or long-running single-session compression ever shows up in
practice, that's a good candidate for a future, separately-scoped feature.

## Notes

- `tools.py` restricts `read_file`/`write_file` to the current working
  directory (no path traversal outside it) and truncates `run_command`
  output to keep things safe and manageable.
- `memory.json` keeps the last 20 turns plus any free-form notes; delete it
  or run `/reset` to start fresh.

## Gap-closing pass: Router timeout, orphaned process cleanup, mobile CSS fix

Three gaps flagged during the 3-mission stress test were closed and each was
independently, live-verified against real subprocesses/LLM providers/browser
rendering (not just unit-tested with mocks) -- see `test/` for all logs and
screenshots referenced below.

### 1. LiteLLM Router had no overall timeout (`llm_client.py`)

**Bug:** a provider (Groq) got put into a 2185-second (36+ minute) cooldown
by the Router during the stress test, and because the Router has no overall
wall-clock deadline of its own, one `chat_completion()` call silently
blocked the whole ReAct loop for ~40 minutes.

**A proposed fix was rejected on fact-check** before implementing: it
assumed `RouterRateLimitError.cooldown_list` was a list of
`{"model_name":..., "cooldown_time":...}` dicts you could inspect and
selectively evict providers from. Read the actual installed litellm source
(`litellm/router_utils/handle_error.py`, `litellm/types/router.py`) and
confirmed `cooldown_list` is really just a flat list of deployment-ID
strings with no per-entry cooldown time attached -- the proposed
`item.get(...)` calls would have crashed with `AttributeError` the first
time they ran. There is no supported, version-stable way to introspect
"how long is provider X's cooldown" from outside the Router.

**Actual fix:** `chat_completion()` now runs the real Router call in a
background thread and enforces a hard wall-clock deadline (default 90s,
`timeout_seconds=None` to disable) via `queue.Queue.get(timeout=...)` --
raises a new `llm_client.LLMTimeoutError` instead of hanging, regardless of
what's happening inside Router's internal retry/fallback machinery. Does
NOT kill the background thread (Python can't safely do that) -- it just
stops the caller from waiting past the deadline. `agent.py`'s ReAct loop
catches `LLMTimeoutError` and reports a clear, honest message instead of
hanging or crashing with a raw exception.

Verified: `test/llm_timeout_test.py` (mocks a stuck `router.completion`,
confirms the exception fires at the deadline, not the full hang duration;
also confirms a fast call and `timeout_seconds=None` still work normally)
and `test/agent_timeout_integration_test.py` (confirms `run_agent()` itself
surfaces the timeout as a graceful reply). Also re-ran a real, live
`chat_completion()` call against actual providers afterward to confirm the
new wrapper doesn't break normal, fast responses.

### 2. Orphaned background processes (new `process_manager.py`)

**Bug:** a Flask dev server started via `run_command`'s shell `&`
backgrounding survived past the mission that started it at least twice
during the stress test, needing a manual `pkill`.

**A proposed fix was corrected before implementing:** it suggested adding
`background`/`mission_id` parameters to `run_command` itself. Checked
`run_command`'s actual `TOOL_SPECS` entry (the JSON schema sent to the LLM)
and confirmed it has no such parameters -- the model can only pass
arguments that exist in that schema, so a hidden flag it can never set
would never fire in practice. It also only tracked processes by
`mission_id`, but plain `run_agent()` calls outside a mission can start
servers too.

**Actual fix:** a new, separate tool trio the LLM can call explicitly --
`start_background_process(cmd, name)` (uses `subprocess.Popen` directly,
`start_new_session=True`, returns a real PID/handle immediately, unlike
shell `&` which gives the caller nothing to track), `stop_background_process
(handle)` (SIGTERM, wait, SIGKILL if still alive, signals the whole process
group), and `list_background_processes()`. Registry persists to
`.agent_processes.json` (git-ignored, like `.agent_backups/`/
`.agent_missions/`). `agent.py`'s `run_mission()` now cleans up any
still-tracked processes automatically when a mission ends (the real
"mission exit" boundary the original bug report was about), and `main.py`
registers `atexit.register(process_manager.cleanup_all)` plus calls
`cleanup_orphans_from_previous_run()` at REPL startup to catch anything left
over from a session that crashed/was SIGKILLed before it could clean up.

**A real bug in this fix's own first draft was caught by testing before
shipping:** an initial version ran `cleanup_orphans_from_previous_run()` and
registered `atexit.register(cleanup_all)` unconditionally at *module import
time*. Reproduced directly that this actively broke the feature: starting a
server in one short-lived process, then merely *re-importing* the module in
a separate later process (the normal pattern here -- start a server in one
tool call, curl/screenshot it in later, separate tool calls), triggered the
first process's own atexit and killed the server before anything could use
it. Fixed by moving both hooks out of module-import time and into explicit
caller-chosen boundaries (mission end / REPL start) instead.

Also caught and fixed along the way: `os.kill(pid, 0)` returns success (no
exception) for a *zombie* process still sitting in the process table
un-reaped -- confirmed directly that after SIGTERM-ing a child we're the
direct parent of, `ps` showed `<defunct>`/`STAT=Z` while a naive liveness
check still reported it alive, which would have made `stop()` wait out its
full grace period and then SIGKILL a process that had already exited.
Fixed by reaping via `os.waitpid(pid, os.WNOHANG)` as part of the liveness
check.

Verified: `test/process_manager_test.py` runs 5 scenarios against real
subprocesses (start+track, stop+confirm dead via both `os.kill` and an
independent `ps` check, `cleanup_all()` on multiple processes, and orphan
cleanup from a simulated crashed run) -- all passing. Then verified live,
end-to-end, through the real ReAct loop with a real LLM call: asked the
agent to start the actual `test/finance_dashboard/app.py` Flask server via
`start_background_process`, curl a real endpoint (`/api/balance`, got back
genuine JSON), and stop it -- confirmed the real PID died (`ps -p <pid>`
empty) and no process was leaked (`test/gap2_live_test_run.log`).

**Bonus bug found and fixed while running this live test:** the ReAct loop
crashed with an unhandled `IndexError: list index out of range` on
`response.choices[0]` when a provider/fallback path returned a response
with an *empty* `choices` list (no exception raised, so the existing
`except litellm.ContextWindowExceededError` guard didn't catch it). Fixed
with an explicit `if not response.choices` check that reports a clear,
graceful message instead of crashing the mission.

### 3. Mobile overflow bug (`test/finance_dashboard/style.css`)

**Bug:** the transactions table had no wrap/scroll handling, so at a real
375px mobile viewport the page overflowed horizontally.

**Verified numerically, both before and after, by actually rendering the
page** (not by reasoning about the CSS) via a raw Playwright script at
375px width, reading `document.documentElement.scrollWidth`:
- Before the fix: `scrollWidth = 391px` at a 375px viewport -- confirms the
  originally-reported ~16px overflow exactly.
- After the fix: `scrollWidth = 375px` -- zero overflow.

**Fix:** `overflow-x: auto` on `.transactions` (the existing `<section>`
that already wraps the `<table>` -- no new wrapper div needed, unlike an
earlier proposal that referenced a `.transactions-container` class that
doesn't exist in the actual HTML) plus `min-width: 500px` on the table
itself so columns scroll instead of illegibly squishing.

Also re-verified at 1280px desktop width afterward
(`test/finance_dashboard/desktop_1280_regression_check.png`) to confirm no
regression -- `test_local_html`'s built-in overflow check reported none at
either width.

## Git integration (new `git_tools.py`)

**What it replaces:** raw `run_command("git ...")` calls, which bypass this
project's entire existing safety net -- no sensitive-path checking on what
gets committed, no diff preview before it happens.

**A proposed design was fact-checked before implementing and had two real
gaps, reproduced directly against a throwaway repo before writing any
fix:**
1. Its `get_uncommitted_changes()` only scanned `repo.untracked_files` for
   secrets. Reproduced: a `.env` that was already TRACKED (e.g. committed
   by mistake earlier) and then merely MODIFIED never appears in
   `untracked_files` at all -- a check that only looks there misses it
   completely.
2. Its diff preview was built only from `repo.index.diff(None)`. Reproduced:
   a brand-new untracked file produces an EMPTY diff from that call --
   `git diff` shows nothing for untracked files at all -- so a diff preview
   built only that way silently omits new secret files from what's shown.

**Fix:** every git_* tool now derives its "what's changed" list from the
UNION of `repo.untracked_files` and `repo.index.diff(None)`/`diff("HEAD")`,
and checks EVERY path in that union through `tools.is_sensitive_path()` --
the same, already-tested guardrail every other tool (`read_file`,
`write_file`, `run_command`, `grep_files`) uses, instead of a second,
narrower keyword list that can drift out of sync with the real one.
`git_commit` refuses outright (no override) if any changed path is
sensitive. `git_diff` was ALSO caught leaking by this module's own test
suite during development: an early draft appended a "[N sensitive paths
excluded]" note but still ran `git diff` unfiltered underneath it, so the
actual secret VALUE (e.g. `.env`'s real old/new contents) was still present
in the returned text -- a note next to a leak is still a leak. Fixed by
passing an explicit pathspec (`git diff -- <only the non-sensitive paths>`)
so sensitive content is never fetched from git in the first place, not
filtered after the fact.

`git_init` is a deliberately separate, explicit tool -- never invoked
automatically as a side effect of any other git_* call, since silently
turning a plain directory into a git repo is not something any tool should
do without being asked. `git_create_branch` refuses on a dirty working tree
(uncommitted changes would otherwise silently follow onto the new branch).

**Sandbox note:** `/home/user/my-agent` is not itself a git repository (no
`.git/` directory) -- this was deliberately never changed while building
and testing this feature. All development and testing happened against a
disposable repo under `test/git_tools_sandbox_workdir/` (created fresh by
the test script each run) or a temporary sandboxed `tools.WORKDIR` pointed
at a throwaway directory, specifically so nothing here could ever touch
real project state without an explicit, separate decision to run
`git_init` on the real project.

Verified: `test/git_tools_test.py` runs 7 scenarios against a real,
throwaway git repo -- including both bug repros above as explicit
regression tests (`test_real_bug_repro_modified_tracked_env_file_is_still_
caught`, `test_real_bug_repro_untracked_secret_file_shown_in_diff_and_
blocked`) that assert the actual secret VALUE never appears in `git_diff`'s
output, not just that a warning is printed. Then verified live through the
real ReAct loop with a real LLM call (`test/git_live_test_run.log`):
pointed the agent's sandbox root at a throwaway repo with a `.env`, asked
it to init/status/commit, and confirmed the tool genuinely refused to
commit while `.env` was present, and that `run_command("rm .env")` was
ALSO independently refused (defense in depth: the sensitive-command
detector already used by `run_command` blocks it too), reproducing
exactly the intended layered protection.

**Bonus bug found and fixed during this live test:** some providers emit
the literal JSON string `"null"` as a zero-argument tool call's arguments
instead of `"{}"` (git_status/git_init are among the first common
zero-arg tools in this project, which is why this surfaced now). `json.
loads(arguments_json or "{}")` doesn't catch this -- the non-empty string
`"null"` already satisfies the `or`, so `json.loads` receives `"null"` and
returns Python `None`, and `TOOL_FUNCTIONS[name](**None)` then raises a
`TypeError`. It was already caught by `_dispatch_tool_call`'s existing
`except TypeError` (so it surfaced as a normal, recoverable tool-error
message rather than crashing the process), but the model then had to waste
a retry figuring out the right shape. Fixed by explicitly treating a parsed
`None` the same as an empty `{}`. Covered by
`test/null_args_dispatch_test.py`.

## Git repo prep + RAG (semantic code search)

**Git repo initialized.** `/home/user/my-agent` was not a git repository
before this (confirmed: `git status` failed with "not a git repository").
Initialized via this project's own `git_init` tool (never done silently as
a side effect of anything else), fixed a real false-positive bug that
surfaced immediately (below), then committed via `git_commit` -- verified
independently afterward with `git show`/`git ls-tree` that no real API key
fragments or `.env` content appear anywhere in the commit, only the blank
`.env.example` template. Remote `origin` points at the user-provided GitHub
repo; pushing was left to the user (no GitHub credentials exist in this
sandbox to push with, and pushing wasn't asked for).

**Real false-positive bug found and fixed:** running `git_status` against
this project's OWN real files immediately flagged `.env.example` (a
deliberately blank, safe-to-commit template documented in this README) as
a sensitive path -- purely because `.env` is a substring of `.env.example`.
Fixed in `tools.is_sensitive_path()` (not just in git_tools, since every
other tool -- `read_file`, `write_file`, `run_command`, `grep_files` --
shares this same check) with a narrowly-scoped exemption: only paths that
start with `.env` AND end in a conventional template suffix
(`.example`/`.sample`/`.template`/`.dist`) are exempted, and only from the
`.env` token specifically -- a file like `id_rsa.example` is still treated
with suspicion, and `.env.example.pem` is still caught by the `.pem`
suffix check. Covered by `test/sensitive_path_test.py` (4 scenarios: the
exemption itself, real `.env` variants still caught, other sensitive
tokens unaffected, and the narrow-exemption edge case).

**RAG / semantic code search (new `rag_indexer.py`).** Complements
`grep_files` (exact text) and `lsp_find_references` (exact symbol) with
concept-level search -- "find where we handle X" queries that don't share
exact wording with the code.

Cost decision, fact-checked before building: the originally proposed stack
(`sentence-transformers`) needs `torch`, whose Linux wheel is **507MB** --
confirmed directly that downloading it filled this sandbox's entire 996MB
`/tmp` tmpfs and failed with `OSError: No space left on device`. Used
ChromaDB's own **default embedding function** instead: a small ONNX
`all-MiniLM-L6-v2` model (~79MB, downloaded once to
`~/.cache/chroma/onnx_models/`, confirmed directly), run via `onnxruntime`
(already a chromadb dependency -- no separate, heavier install). See
`RAG_UPGRADE_PATH.md` for a full, fact-checked guide (with confirmed-real
API snippets, not invented ones) to upgrading to a stronger local model,
a code-specific embedding model, or a hosted embedding API later, if this
project's codebase ever grows enough to need it.

**Chunking**, unlike a proposed design that blindly split every file into
30-line windows or blank-line breaks (which routinely cuts a function
signature from its body), chunks along actual function/class boundaries
for Python and JS/TS (regex-based, not a full parser) and only falls back
to fixed-size windows for unrecognized file types. **Real bug found and
fixed by this module's own test suite during development:** a Flask route
like `@app.route('/api/balance')` followed by `def api_balance():` got
split with the decorator attached to the END of the PREVIOUS chunk and the
function starting its own chunk with no decorator -- so a search for the
literal route string would miss the function it belongs to. Fixed by
walking backward from each function/class boundary to also swallow any
contiguous decorator lines immediately preceding it. Verified with a
direct regression test (`test_decorator_stays_attached_to_function`) plus
a line-range-reconstruction test that confirms no content is lost, gapped,
or duplicated across chunk boundaries.

**A separate, more serious bug was found (and is the same bug in
`git_tools.py`, fixed the same way): a genuine circular import.** Both
`git_tools.py` and `rag_indexer.py` need `tools.WORKDIR`/
`tools.is_sensitive_path`, while `tools.py` itself imports `git_tools`/
`rag_indexer` at its own end (to register their functions as agent tools).
A module-level `import tools as _tools` in either of those two files
creates a real import cycle: reproduced directly that if ANYTHING imports
`git_tools.py` (or `rag_indexer.py`) BEFORE `tools.py` has ever been
imported in that process, `tools.py`'s own `from git_tools import
GIT_AVAILABLE, ...` hits a partially-initialized module mid-load and
raises an `ImportError` -- which `tools.py`'s broad `except Exception`
swallows SILENTLY, permanently leaving `GIT_AVAILABLE`/`RAG_AVAILABLE`
`False` for the rest of that process with **no visible error at all**.
This is exactly the shape of bug that's hardest to catch by inspection --
it only reproduces depending on import order, and the failure is silent by
design (the whole point of the try/except pattern used throughout this
project for optional tool availability). Found by an incidental but
realistic test pattern: isolating `rag_indexer.INDEX_DIR` to a throwaway
path for a test (`import rag_indexer; rag_indexer.INDEX_DIR = ...`) before
importing `agent`. Fixed in both files by deferring the `tools` import to
first actual use (`_get_tools()`, called lazily inside each function
instead of at module level) -- by the time any function actually runs,
both modules have finished loading regardless of which one started first.
Reproduced the exact failure AND confirmed the fix resolves it in both
import orders as a direct test, independent of the existing test suites
(which happened to always import `tools`/`agent` first and so never
exercised the broken order).

Verified end-to-end: `test/rag_indexer_test.py` (4 scenarios: decorator
attachment, no-content-lost via line-range reconstruction, sensitive-file
exclusion, and live index+search against the real
`test/finance_dashboard/` code) plus a live run through the real ReAct
loop with a real LLM call (`test/rag_live_test_run.log`) that was
explicitly instructed to avoid the literal word "bitcoin" in its search
query -- `rag_search` still correctly ranked the actual
`/api/bitcoin_price` CoinGecko-fetching endpoint as the top semantic match,
proving this is genuine concept-level matching, not disguised keyword
search.

## AST / Tree-sitter surgical code transforms (new `ast_tools.py`)

Goes beyond `tools_lsp.py`'s rename/reference tools with custom, rule-based
transforms: "convert every safely-convertible `var` to `const`" and "find
functions missing a JSDoc comment", for JavaScript. Currently JS-only;
`tree-sitter-python` is installed and available if a Python-specific
transform is ever needed, but nothing uses it yet.

**Four real bugs were found and fixed in a proposed design, each confirmed
by running code against the actually-installed tree-sitter 0.26.0 /
tree-sitter-javascript 0.25.0 BEFORE writing any transform logic — this
project's established pattern of fact-checking proposals against reality
instead of trusting them:**

1. `Language.query(...)` doesn't exist -- confirmed `AttributeError`. Real
   API: `Query(language, pattern)` then `QueryCursor(query).matches(node)`.
2. `"(var_declaration) @var"` isn't a valid node type -- confirmed
   `tree_sitter.QueryError: Invalid node type`. Walked a real parse tree
   directly and found the actual type: `variable_declaration` for `var`
   (`let`/`const` use a different type, `lexical_declaration`).
3. Matches aren't positional tuples indexable like `match[0][0]` -- each
   match is really `(match_index, {capture_name: [nodes]})`, a dict keyed
   by capture NAME, confirmed directly.
4. **The serious one:** reassignment detection only checked
   `assignment_expression` (`x = 2`), missing that `x += 1` and `x++`/`x--`
   are DIFFERENT node types (`augmented_assignment_expression` and
   `update_expression` respectively, confirmed by parsing both directly).
   Proven concretely: reproduced the unfixed logic converting a `var` that
   gets `++`-incremented later into `const`, then ACTUALLY RAN the result
   via `node` and got the exact predicted crash --
   `TypeError: Assignment to constant variable`. This means the unfixed
   version wouldn't just be "occasionally wrong" -- it would ship a tool
   that reliably breaks the code it claims to make safer. Fixed by
   checking all three mutation node types before allowing a `var` to
   convert.

Like `git_tools.py`/`rag_indexer.py`, `ast_transform_var_to_const`/
`ast_add_jsdoc`/`ast_find_untyped_functions` never write anything
themselves -- they return the full transformed file content as a PREVIEW
(same pattern as `lsp_preview_rename`), and the agent must call
`write_file` itself with that exact content to apply it. Unlike those two
modules, `ast_tools.py` doesn't import `tools` at all (not even lazily) --
it's pure string-in, string-out, so it never had their circular-import
risk in the first place; the tool wrapper functions (which DO need
`tools._resolve`/`is_sensitive_path`/file I/O) live directly in `tools.py`.

Verified: `test/ast_tools_test.py` runs 8 scenarios, including two that
ACTUALLY EXECUTE the transformed JavaScript via `node` (not just string
assertions) -- confirming the var/const split is correct for plain
assignment, `+=`, AND `++`/`--` all at once, and that inserted JSDoc
comments don't break parseability. Then verified live through the real
ReAct loop with a real LLM call (`test/ast_live_test_run.log`): the agent
previewed the transform, applied it via `write_file`, ran the result via
`node` (exit code 0, correct output `115.5`), then independently
re-verified by running the final file myself outside the agent entirely.

## Accessibility snapshots, advisory UI hints, and a real webview confirmation bridge

### 1. `get_accessibility_snapshot` (new, in `tools_browser.py`)

**Real bug found and fixed before writing any code:** a proposed
implementation called `page.accessibility.snapshot()`. Confirmed directly
against the actually-installed Playwright (1.61.0) that this API **does
not exist** -- `AttributeError: 'Page' object has no attribute
'accessibility'`. That whole `Accessibility` class was removed from
Playwright years ago. The real, current replacement is
`Locator.aria_snapshot(depth=...)`, which also returns an
already-formatted, readable string (headings, roles, nesting as YAML-like
text) rather than a raw nested dict requiring a hand-written recursive
tree-printer -- so the real implementation is simpler than the original
proposal, not just corrected.

Supports both a local file (served via the same real local HTTP server as
`test_local_html`/`evaluate_js`, never `file://`) and a live URL, with a
mutual-exclusivity guard, the standard `is_sensitive_path` check, and
output truncation via the existing `tools.MAX_TOOL_OUTPUT_CHARS`/
`_truncate` helpers (reusing established infrastructure instead of an
unbounded string builder). Verified with 5 tests
(`test/accessibility_snapshot_test.py`): real output against
`test/finance_dashboard/index.html` matches actual page content
(headings, table structure), a real live URL works, the sensitive-path
guard blocks `.env`, and no browser process leaks after the call.

### 2. `render_ui`/`clear_ui` -- advisory UI hints ONLY (new `a2ui.py`)

Writes a JSON manifest (`.agent_ui/current_manifest.json` + an
append-only `.jsonl` history) that a future webview/extension host can
read to show progress, diff previews, tool-result summaries, or chat-style
messages. Purely advisory -- these are ordinary LLM-callable tools with no
power to pause anything.

**A serious safety gap was found and deliberately NOT built, rather than
"fixed":** a proposed design included a `CONFIRM_DIALOG` template as part
of this same advisory tool -- the idea being the agent calls `render_ui`
to "show" a confirmation card. Checked this against how `agent.py`'s REAL
confirmation gate actually works (`_needs_confirmation` /
`_dispatch_tool_call`'s synchronous `confirm(name, args, reason, diff) ->
bool` callback, which BLOCKS before running a flagged tool) and found
zero connection between the two: `render_ui` is just another tool the
model calls voluntarily. Nothing would stop a model from calling
`render_ui(template="CONFIRM_DIALOG")` for show and then separately
calling `run_command` right after -- the "confirmation" would be pure
decoration with no actual power to block anything, which is worse than no
confirmation UI at all (it *looks* safe while providing none of the
protection). `a2ui.py`'s `render()` explicitly REJECTS `CONFIRM_DIALOG`
with an error pointing at the real mechanism instead.

### 3. `confirm_bridge.py` -- the REAL, blocking webview confirmation gate

A drop-in replacement for `agent.py`'s `_default_confirm` (identical
`(name, args, reason, diff) -> bool` signature), meant to be passed as the
actual `confirm=` argument to `run_agent()`/`run_mission()`. Writes a
pending-request file and blocks (via polling, from the same OS process as
the agent -- not from inside a sandboxed webview, see below) until an
external responder (a future extension host, or a human) writes a
response file, with a 5-minute timeout that **fails closed** (denies) if
nothing responds -- matching `_default_confirm`'s own "EOF/interrupt ->
deny" policy. Never includes raw file content in the request (only the
diff, which is what's actually needed to approve/deny), and cleans up
request/response files after use.

Verified two ways:
- `test/confirm_bridge_test.py` (7 assertions): proves the call is
  **genuinely blocked** (a real background thread stays alive until
  answered, confirmed via `Thread.is_alive()`, not just a fixed sleep),
  that approve/deny correctly return `True`/`False`, that an unanswered
  request times out and fails closed, that a malformed response file
  doesn't accidentally parse as approval, and that raw file content never
  leaks into the request file.
- `test/a2ui_live_test.py` -- the real proof, live through the actual
  ReAct loop with a real LLM call: wired `confirm_bridge.webview_confirm`
  as `run_agent`'s actual `confirm=` parameter, asked the agent to run a
  real destructive `rm -rf` on a throwaway test directory, and confirmed
  independently (both via a background responder thread's own assertions
  AND by checking the directory's existence myself afterward) that the
  directory was NOT deleted until the external responder saw the genuine
  pending request and explicitly approved it. Also confirmed live that
  `render_ui(template="CONFIRM_DIALOG")` is rejected by the real running
  agent, not just in a unit test.

### Corrected assumptions about VS Code webview integration

The original design assumed a webview could `fetch()` a local file path
directly and that `window.parent.postMessage(...)` was the right way to
send actions back. Neither is true: VS Code webviews run in a sandboxed
iframe with no filesystem access -- only resources explicitly passed
through `webview.asWebviewUri()` (declared in `localResourceRoots`) are
reachable, and the correct way to send messages FROM a webview is the
handle returned by `acquireVsCodeApi()`, not `window.parent`. The right
architecture (not yet built -- `a2ui.py`/`confirm_bridge.py` only write
the files) is: the EXTENSION HOST (a normal, non-sandboxed Node.js
process) watches `.agent_ui/` for changes and pushes updates into the
webview via `webview.postMessage()`, and receives actions back via
`webview.onDidReceiveMessage`. `confirm_bridge.py`'s own Python-side
polling is unrelated to this limitation and is fine specifically because
it runs in the same unsandboxed OS process as the agent, not inside a
webview's renderer.

## Phase 3: the actual VS Code extension (new `vscode-extension/`, `bridge_server.py`)

Builds the real extension-host <-> webview bridge previously only
described, using the corrected APIs (`acquireVsCodeApi()`,
`webview.postMessage()`/`onDidReceiveMessage`, `webview.asWebviewUri()` +
`localResourceRoots`) instead of the original proposal's `fetch()` of a
local path and `window.parent.postMessage()`, neither of which work in a
sandboxed webview.

**`bridge_server.py`** (new) is the process the extension spawns and talks
to over stdin/stdout, one JSON object per line. Deliberately NOT built as
an ACP JSON-RPC 2.0 server -- that protocol's exact wire format was never
fact-checked in this project, so the bridge only uses infrastructure that
has already been written and independently tested: `agent.run_agent()`/
`run_mission()`, `confirm_bridge.webview_confirm()` (already proven to be
a REAL blocking gate, not decoration -- see the previous section), and
`design/tool_labels.js`'s already-verified tool-name-hiding map. If/when
ACP's real spec gets verified, this can be reframed as an ACP server
without touching the underlying agent-calling logic.

**A real, load-bearing prompt bug was found and fixed while testing this
end-to-end, not caught by any earlier unit test:** the system prompt told
the model, in the general "ambiguous or risky" guidance, to "ask the user
for clarification" for destructive commands -- which some providers
interpreted as "reply in chat asking permission" INSTEAD OF calling
`run_command` and letting the real, already-tested confirmation gate
intercept it. Reproduced directly, twice, via `test/bridge_server_test.py`
failing because a `confirm_request` was never pushed -- the model had
simply never called the tool, so `agent.py`'s own gate never even saw the
request. This is a categorically different failure than anything unit
tests catch, since `confirm_bridge`/`_needs_confirmation` themselves were
completely correct -- the bug was the MODEL choosing not to invoke them.
Fixed by rewriting that guidance to explicitly separate "ambiguous intent"
(still worth asking about) from "destructive commands" (call the tool
directly; the system's own mechanical gate handles confirmation, asking
in chat instead defeats it) -- see `agent.py`'s `SYSTEM_PROMPT`. Even with
the fix, this remains inherently probabilistic across 4 different LLM
providers with different instruction-following characteristics -- the
underlying gate (`confirm_bridge.py`) still fails closed regardless of
what the model does, so a model asking redundantly in chat is a UX
inefficiency, not a safety hole.

Verified three ways, each exercising a different real transport:
- `test/bridge_server_test.py` -- spawns `bridge_server.py` as a real
  Python subprocess, talks to it over real stdio, confirms `ready`/`run`/
  `result`/`confirm_request`/`confirm_response` all work, including the
  destructive-command gate genuinely pausing until answered.
- `test/extension_bridge_integration_test.js` -- the same scenario, but
  driven from real Node.js `child_process`/`readline` (the exact APIs
  `extension.ts`'s `startBridge()` uses), without needing a full VS Code
  test harness (not installable in this sandbox) -- proves the message
  shapes `extension.ts` expects to parse actually match what
  `bridge_server.py` really emits.
- `npx tsc -p ./` compiles `vscode-extension/` with zero type errors.

**What's deliberately not done yet:** actually loading the extension
inside a running VS Code instance (`vscode-test`/Extension Development
Host) -- not installable/runnable in this headless sandbox. The
Node.js-side integration test is the closest verification achievable
here; a real load-test in an actual VS Code window is the one remaining
step before calling this production-ready.

## `apply_edit` -- surgical file edits alongside `write_file`

New tool (`tools.apply_edit`), modeled on the same `old_string`/`new_string`
exact-match-and-replace primitive Anthropic's own `str_replace_based_edit_tool`
uses -- fails closed (no write at all) if `old_string` is missing or
appears more than once in the file, instead of guessing where to apply a
change or clobbering a file that changed since it was last read.
Complements, not replaces, `write_file` -- new files and large rewrites
still go through `write_file`; small, targeted changes to existing files
should use `apply_edit`.

**Two real bugs were found and fixed before this shipped, neither present
in the originally proposed design:**

1. **`diff_for_edit()` had no `is_sensitive_path` check.** The proposal's
   preview function only checked the file existed and the match was
   unique -- confirmed directly that this means it would have happily
   returned a real, readable diff of a sensitive file's contents (e.g.
   `.env`) as a confirmation preview, even though `apply_edit()` itself
   separately refused to write it. A preview is still a read; it needs the
   same guardrail every other read path (`read_file`, `grep_files`) already
   has. Fixed by adding the check as the very first line of
   `diff_for_edit()`. Covered by `test_diff_for_edit_refuses_sensitive_path`.
2. **`apply_edit` was never added to `cache.MUTATING_TOOLS`.** The proposal
   never touched `cache.py` at all. Confirmed directly (before the fix)
   that `"apply_edit" in MUTATING_TOOLS` was `False` even after `apply_edit`
   was registered as a real tool -- meaning a `read_file` result cached
   earlier in a task would keep being served as "current" after
   `apply_edit` silently changed that file on disk, reproducing the exact
   stale-cache failure mode `cache.py`'s own module docstring warns about
   for any mutating tool left out of that set. Fixed by adding it
   alongside `write_file`/`run_command`. Verified with a real
   stale-vs-fresh read test (`test_cache_actually_invalidates_after_apply_edit`),
   not just a set-membership check.

`agent.py`'s confirmation gate (`_needs_confirmation`) got its own
`apply_edit`-specific branch (using `diff_for_edit`, not shoehorned into
the `write_file`-shaped `_WRITE_FILE_TOOL_NAMES` path, since `apply_edit`'s
arguments -- `old_string`/`new_string` -- don't match `write_file`'s
`content` argument `diff_for_write` expects). `undo_last_edit` needed no
changes at all: `apply_edit` reuses the exact same
`checkpoint_mgr.checkpoint_before_write()` call `write_file` does, so a
change made via either tool is undoable identically -- verified directly
by editing a file with `apply_edit` then calling `undo_last_edit` and
confirming the original content came back byte-for-byte.

Verified: `test/apply_edit_test.py` runs 9 scenarios (unique replacement,
missing old_string, ambiguous old_string with disambiguating context
shown, sensitive-path refusal for both the tool and its preview,
confirmation-gate wiring, and the two cache bugs above). Then verified
live through the real ReAct loop with a real LLM call: asked the agent to
fix a function using `apply_edit` specifically, and confirmed it read the
file first, used a correctly-unique `old_string`, left the unrelated
`format_currency` function completely untouched, and re-read the file
afterward to verify its own change -- matching the exact pass condition
originally specified for this feature.

## Streaming `run_command` output

`tools.run_command()` gained an optional `on_line(line: str) -> None`
callback, threaded through `agent._dispatch_tool_call` -> `_run_tool_calls`
-> `run_agent`/`run_mission` -> `bridge_server.py` -> the VS Code webview,
so a long command (`npm install`, `pytest`) shows live, line-by-line
output instead of a frozen screen for the whole duration. Purely additive:
`on_line=None` (the default, and the ONLY path the LLM's own tool call can
ever take, since `on_line` isn't a `TOOL_SPECS` parameter) reproduces the
exact prior blocking behavior -- confirmed directly that the model can
never set it.

**Two real bugs were found and fixed before this shipped, neither present
in the originally proposed design:**

1. **The proposed `fcntl`+`select` non-blocking-read pattern was fragile
   and unnecessary.** Used a plain background thread doing blocking
   `readline()` calls into a list instead (the same pattern
   `bridge_server.py`'s own stdout reader already uses successfully) --
   simpler, portable, and avoids partial-line/`BlockingIOError` edge cases
   that come with manual `fcntl` flag manipulation on a text-mode pipe.
2. **The real, serious one: killing just the shell process on timeout
   does not close the output pipe if the shell's own child is still
   running.** Confirmed directly: for `sleep 5` launched via `shell=True`,
   calling `proc.kill()` on the shell alone left the reader thread's
   `readline()` blocked for ~4.7 extra seconds waiting on `sleep` itself
   to exit on its own -- turning a requested 1-second timeout into an
   actual ~5-second stall (reproduced exactly: first test run measured
   3.00s instead of ~1s). Fixed with the same `start_new_session=True` +
   `os.killpg(..., SIGKILL)` process-group-kill pattern `process_manager.py`
   already uses for background processes -- confirmed this closes the pipe
   in under 1ms instead of ~4.7s, and the timeout test now measures ~1.00s
   as expected.

The originally proposed design also assumed the webview polls
`.agent_ui/current_manifest.json` for `PROGRESS_BAR` a2ui events -- neither
is accurate against this project's actual, already-built architecture:
the webview polling model was explicitly replaced by `bridge_server.py`'s
push-based `postMessage` bridge in the previous phase, and `"PROGRESS_BAR"`
was never a valid `a2ui` template (the real one is `"PROGRESS"`, and even
that's for occasional advisory summaries, not a firehose of per-line
command output). Implemented instead as a new `command_output` message
type in `bridge_server.py`'s existing stdout wire protocol, rendered by
`vscode-extension/media/main.js` as a live-scrolling pane attached to the
in-progress `run_command` action card -- reusing the real, already-tested
push architecture rather than a design that was already known not to work.

Verified: `test/run_command_streaming_test.py` (6 scenarios: default
behavior unchanged, lines genuinely arrive incrementally -- measured via
real timestamps spread across the command's runtime, not just correctness
of final output -- a broken `on_line` callback never kills the command it's
watching, timeout still works with partial output reported, sensitive-
command blocking unaffected, and the LLM's tool schema has no `on_line`
parameter). `test/agent_streaming_wiring_test.py` (3 scenarios proving the
parameter reaches `tools.run_command()` through the real `agent.py`
dispatch chain, not just in isolation). `test/bridge_streaming_test.py` --
the real, live proof, run against an actual `bridge_server.py` subprocess
with a real LLM call: reproduced the EXACT originally-requested validation
scenario (`for i in 1 2 3 4 5; do echo step $i; sleep 0.5; done`) and
confirmed via real wall-clock timestamps that `step 1`...`step 5` arrived
as five separate `command_output` events spread over ~2.1 seconds, not
delivered in a single batch at the end.

## Sub-agents (`subagents.py`) -- built for competitive capability parity, clean-room

Adds a `dispatch_agent` tool letting the main agent delegate a self-contained
sub-task to a SEPARATE, isolated ReAct loop with its own restricted tool set
and its own fresh conversation, returning exactly ONE final summary string
back to the parent -- not the sub-agent's intermediate tool calls. Modeled on
the publicly-documented shape of Claude Code's own `Task` tool (schema:
`prompt`/`subagent_type`/`description` -- verified against independently-
published explainers that quote the tool's own JSON schema, standard practice
since it's sent to the model as part of ordinary function-calling, NOT
extracted from any leaked source -- see `COMPARISON_openclaude.md` for the
full legal/IP context established this session) and OpenClaude's own public
`maxSteps`-cap concept, but built clean-room against this project's own
already-tested `agent.py` plumbing.

Three sub-agent types, each mapping to a REAL, structurally-restricted tool
registry (not a prompt-level instruction):
- `general-purpose`: full tool access (same as the parent), minus the
  ability to spawn a further nested sub-agent once at the depth ceiling.
- `explore`: read-only research (`read_file`, `list_files`, `grep_files`,
  `lsp_find_references`, `lsp_get_diagnostics`, `rag_search`,
  `get_accessibility_snapshot`, `git_status`/`git_diff`/`git_log`,
  `web_search`, the read-only `filesystem_*`/`fetch_fetch` MCP tools) --
  `write_file`/`apply_edit`/`run_command`/etc. are absent from its registry.
- `plan`: same read-only tool set as `explore`, intended for proposing an
  implementation plan without making changes.

**The actual enforcement mechanism (not just a design description):**
`agent._dispatch_tool_call()` gained a `tool_functions` parameter that, when
given, REPLACES the module-level `TOOL_FUNCTIONS` registry used to look up
`name`. A restricted sub-agent is handed a dict that structurally does not
contain `"write_file"` as a key at all -- if its own LLM call still emits a
`write_file` tool_call, the lookup fails and returns
`"ERROR: unknown tool 'write_file'"`, the exact same failure mode as a
genuinely nonexistent tool name. `agent.run_agent()` also gained matching
`tool_specs`/`system_prompt`/`persist_memory` parameters (all default to
`None`/`True`, reproducing prior behavior exactly when omitted) so a
sub-agent's own model is never even told a disallowed tool exists, gets a
narrower prompt describing only its real tools, and never reads or writes
the parent's `memory.json` (a fresh, throwaway in-memory conversation only).

**Rate-limit/cost safety (the free-tier providers in this project's Router
have already been observed hitting multi-minute cooldowns under load -- see
the `LLMTimeoutError`/`_run_with_deadline` fix above):** each `dispatch_agent`
call is a COMPLETE separate multi-turn loop, not one extra LLM call --
Anthropic's own published guidance says multi-agent workflows use roughly
4-7x the tokens of a single-agent session. Two hard, independently-tested
limits guard against a runaway chain:
1. `MAX_SUBAGENT_DEPTH` (default 1): a sub-agent's own restricted registry
   does not even contain `dispatch_agent` once nesting would exceed this --
   it cannot spawn a further sub-agent, matching Claude Code's own
   documented bounded-nesting behavior.
2. `SubagentBudget` (default 4 per top-level task): a small thread-safe
   counter shared across every `dispatch_agent` call within one
   `run_agent()`/`run_mission()` call (threaded through via the same
   Python-only-injection pattern already used for `run_command`'s `on_line`
   callback -- `_confirm`/`_subagent_depth`/`_subagent_budget` are NOT in
   `dispatch_agent`'s LLM-visible `TOOL_SPECS` schema, confirmed by a direct
   test). Exceeding the budget returns a clear `ERROR` string instead of
   silently starting another full ReAct loop.

Verified three ways, escalating from unit-level to fully live:
- `test/subagents_test.py` (7 scenarios, no LLM): the `explore` registry
  structurally excludes every write/destructive tool (checked as dict KEYS,
  not behavior); `general-purpose` keeps full access but loses
  `dispatch_agent` at the depth ceiling; an unknown `subagent_type` and a
  depth-ceiling violation are both rejected BEFORE touching the shared
  budget; a REAL `SubagentBudget` object (not mocked) genuinely blocks a
  3rd dispatch once exhausted, proven via its actual `try_acquire()` method
  across real sequential calls; the LLM-visible schema exposes only
  `prompt`/`subagent_type`/`description`; `agent._dispatch_tool_call`'s new
  `tool_functions` parameter genuinely restricts what's callable, tested
  with a synthetic fake registry to isolate the wiring from subagents.py's
  own logic.
- `test/subagents_live_test.py` (2 scenarios, REAL LLM call, no mocking):
  an `explore` sub-agent was explicitly instructed to overwrite a real file
  on disk -- confirmed byte-for-byte unchanged afterward (the model itself
  self-reported "outside of my capabilities as a read-only sub-agent," but
  the test's actual pass condition is the file's real content, not the
  model's self-report); a `general-purpose` sub-agent was explicitly
  instructed to nest a further sub-agent -- it correctly reported having no
  `dispatch_agent` tool available and did the read itself instead.
- `test/subagents_parent_integration_test.py` (1 scenario, full real chain,
  REAL LLM calls at both levels): a genuine top-level `agent.run_agent()`
  call was given a task worth delegating (not forced to use the tool) --
  the parent model chose on its own to call `dispatch_agent(subagent_type=
  "explore")` to find every Flask route in `test/finance_dashboard/app.py`;
  the sub-agent's real result (`/`, `/<path:filename>`, `/api/balance`,
  `/api/history`, `/api/bitcoin_price`) was cross-checked directly against
  `grep -n "@app.route" test/finance_dashboard/app.py` and matched exactly,
  with zero hallucination; the parent's own action log never shows the
  sub-agent's internal `read_file` call (proving true isolation -- the
  parent only ever sees the sub-agent's single tagged summary string).

**What this is NOT (scope discipline, matching the user's own stated
priority: capability parity, not model/cost/funding parity):** no per-agent
model routing (`agentModels`/`agentRouting` from OpenClaude's own README --
this project's Router already fails over across providers uniformly, and
routing a *specific* sub-agent type to a *specific* provider is a separate,
not-yet-requested feature), no `resume`/`run_in_background` support (Claude
Code's own `Task` schema has these; this project's sub-agents are
deliberately synchronous/blocking for now, matching this project's existing
`run_agent()` design rather than adding an async execution model
speculatively), no custom agent definitions loaded from `.claude/agents/`-
style markdown files yet (that's the NEXT agreed roadmap item in
`COMPARISON_openclaude.md`, which composes with -- but is separate from --
this sub-agent dispatch mechanism).

## Permission modes (`permissions.py`) -- reuses existing confirmation gate, zero new mechanics

Adds six named permission MODES (`default`/`plan`/`accept_edits`/`auto`/
`dont_ask`/`bypass`) as a thin policy layer on top of `agent.py`'s existing,
already-tested `_needs_confirmation()`/`confirm()` gate -- built per explicit
instruction to derive tool categories from already-existing code
(`cache.CACHEABLE_TOOLS`, `tools.is_destructive_command`, `tools.is_sensitive_path`,
and last session's `subagents.READ_ONLY_TOOL_NAMES`), never a new hand-typed
list, and to spend zero extra LLM calls per tool call. Modeled on Anthropic's
currently-published permission-mode docs (`code.claude.com/docs/en/permission-modes`,
verified this session, not extracted from any leaked source).

**A real design bug caught and fixed BEFORE this was shown for review:** a
first draft tried to implement `dont_ask`'s "deny anything not explicitly
allowed" entirely inside the `confirm()` callback. That's structurally wrong
in this codebase: `agent._dispatch_tool_call` only ever calls `confirm()` for
a call `_needs_confirmation` has ALREADY flagged (a destructive command, or a
write/edit with a real diff) -- a plain, unflagged call like `read_file` or
even `write_file` creating a brand-new file never reaches `confirm()` at all.
A `confirm()`-only gate would therefore have silently ALLOWED every unflagged
tool straight through in `dont_ask` mode -- the opposite of its documented
behavior, and a real safety regression if it had shipped. Fixed by using the
only mechanism in this codebase that can deny BY TOOL IDENTITY rather than by
flagged-riskiness: the same `tool_functions`/`tool_specs` registry-restriction
mechanism `agent.run_agent()` already gained last session for sub-agents.
`plan` and `dont_ask` both restrict the registry so disallowed tools are
structurally absent as dict keys; `default`/`accept_edits`/`auto`/`bypass`
leave the registry untouched and only vary what `confirm()` decides.

**Mode behavior, all built on already-tested primitives, not new checks:**
- `default` -- byte-for-byte identical to prior behavior; `confirm_fn` is
  just `agent._default_confirm` (or a caller's own callable) unchanged.
- `plan` -- registry-restricted to the canonical read-only tool catalog
  (`subagents.READ_ONLY_TOOL_NAMES` unioned with `cache.CACHEABLE_TOOLS`,
  the exact set already live-tested against a real LLM escape attempt for
  sub-agents last session). `write_file`/`apply_edit`/`run_command`/etc.
  don't exist for the model to call -- nothing to "confirm."
- `accept_edits` -- an ordinary write/edit (`_needs_confirmation` already
  returned a real `diff`, meaning "safely-previewable content change, not a
  sensitive path or destructive command") proceeds without asking; a write
  to a sensitive path or a destructive `run_command` (both always return
  `diff=None`) still falls through to the human confirmation exactly like
  `default` -- this precisely reuses `_needs_confirmation`'s own existing
  `(reason, diff)` distinction rather than introducing a second signal.
- `auto` -- same write/edit relaxation as `accept_edits`. **Deliberate
  deviation from Anthropic's own docs** (their `auto` runs a background
  LLM-based safety classifier): per this session's explicit instruction,
  reuses the free, already-tested `is_destructive_command`/`is_sensitive_path`
  regex/path checks instead of spending an extra completion call per tool
  call on this project's rate-limit-prone free-tier providers. A destructive
  command is, by construction, the only reason a `run_command` call would
  ever reach the confirmation layer at all -- `auto` does not relax that
  further; there is no code path in this mode that auto-allows a destructive
  command or a sensitive-path access.
- `dont_ask` -- registry-restricted to the same canonical read-only catalog
  (`ALLOWED_IN_DONT_ASK`); anything else is absent from the registry, so a
  call to it fails with `"ERROR: unknown tool"` -- proven directly in the
  test suite by passing a `confirm` callable that raises an `AssertionError`
  if ever invoked at all, confirming the denial never even reaches that layer
  (matches Anthropic's own documented "no `canUseTool` callback invoked").
- `bypass` -- `confirm_fn` always returns `True` (skips the prompt only).
  Does **not** touch `tools.is_sensitive_path`'s unconditional hard block
  inside `read_file`/`write_file`/`run_command` themselves -- proven by
  calling the REAL `write_file()`/`read_file()` against the project's real,
  live `.env` file under bypass mode and confirming both are still refused,
  with the real `.env` file diffed byte-for-byte unchanged on disk afterward.

Verified two ways, matching the sub-agents precedent:
- `test/permissions_test.py` (16 scenarios, no LLM): `default` mode is
  provably unchanged; `plan` mode's registry excludes every write tool AND
  `agent._dispatch_tool_call` genuinely can't reach `write_file` through it
  (checked against disk -- the target file was never created); `accept_edits`
  auto-approves an ordinary write with a diff but still gates a destructive
  command and a sensitive-path write (diff=None in both cases, correctly not
  auto-approved); `auto` never relaxes a destructive command further;
  `dont_ask`'s registry contains only the allow-listed 18 tools, a disallowed
  tool is denied via the registry alone with `confirm()` never invoked
  (proven via a raising callable), and an allow-listed tool still genuinely
  executes; `bypass` skips the prompt but the REAL `write_file()`/`read_file()`
  against the REAL `.env` are still hard-refused, confirmed via a real
  before/after diff of `.env`'s actual content; every mode produces a valid
  system-prompt suffix; `run_agent_with_mode` correctly wires a restricted
  registry and system prompt through to `agent.run_agent` (verified via
  monkeypatching `agent.run_agent` and inspecting the exact kwargs it
  received).
- `test/permissions_live_test.py` (3 scenarios, REAL LLM calls, no mocking):
  a `plan`-mode agent was asked to make a real file change -- it correctly
  produced a text PLAN instead (explicitly noting "an agent with write
  permission" would need to execute the write), and the real target file
  was confirmed byte-for-byte unchanged on disk afterward; an `accept_edits`-
  mode agent was given a `base_confirm` that raises an `AssertionError` if
  ever called, and successfully appended a real line to a real file with
  zero prompts (verified via the file's real before/after content, and the
  test process not crashing from the raising confirm); a `dont_ask`-mode
  agent was asked to run a real shell command and explicitly said "I'm
  unable to execute shell commands in this environment" instead of
  fabricating output (the test asserts on an explicit admission phrase,
  not the absence of the command's literal text, since the model
  legitimately quotes the requested command while explaining it can't run
  it -- one real test-assertion bug, caught immediately: an initial version
  used a straight-apostrophe check against a real model response containing
  a smart/curly apostrophe (U+2019) and failed on a correct model response,
  fixed by normalizing quote characters and checking for an explicit
  admission phrase instead).

**What this is NOT** (scope discipline, matching sub-agents' own precedent):
no LLM-based safety classifier for `auto` mode (explicit instruction this
session: zero extra API calls per loop); no persistent, cross-session mode
setting (`~/.claude/settings.json`-style `defaultMode` config is a plausible
future addition, not built here -- `run_agent_with_mode` is a per-call
wrapper only); no `--permission-mode` CLI flag wired into `main.py` yet
(the wrapper function exists and is fully tested; wiring it into the
interactive REPL/bridge_server.py is a follow-up, not blocking this review).

## Wiring permission modes into `main.py`'s CLI (`--permission-mode`)

Added `--permission-mode <name>` to `main.py`'s interactive REPL, exposing
`permissions.run_agent_with_mode()` (built and fully tested in the prior
step, but not previously reachable from the CLI). Usage:

```
python main.py                                  # unchanged: default behavior, no permissions.py involved at all
python main.py --permission-mode plan           # read-only: propose, never execute
python main.py --permission-mode accept_edits   # ordinary file writes/edits proceed without asking
python main.py --permission-mode auto           # same as accept_edits (see permissions.py for why this
                                                 # project's "auto" deliberately doesn't run an LLM classifier)
python main.py --permission-mode dont_ask       # locked-down: only read-only tools are even callable
python main.py --permission-mode bypass         # skips confirmation prompts only -- NOT the unconditional
                                                 # secret-path block inside the tools themselves
```

**The backward-compatibility guarantee this was built around:** when
`--permission-mode` is omitted entirely, `main()` takes the *exact* prior
code path -- a plain `run_agent(user_input, verbose=True, confirm=confirm)`
call, never touching `permissions.py` at all. This was a deliberate design
choice, not an oversight: `PermissionEngine.system_prompt_suffix()` appends
a short note to the system prompt for EVERY mode, including `default` --
if `main.py` always routed through `run_agent_with_mode(mode=DEFAULT)`
regardless of whether the flag was passed, the model would see a subtly
different system prompt than before permission modes existed, even though
`default`'s actual `confirm()` behavior is identical. `_parse_permission_mode`
returns Python `None` (not `PermissionMode.DEFAULT`) specifically to
distinguish "flag not given at all" from "flag given, value is default" --
`main()` branches on that `None` to choose between the two call paths,
keeping the no-flag case provably, not just functionally, unchanged.

**A real bug caught by my own test, not found by inspection:** the first
draft of `_parse_permission_mode`'s error paths called `sys.exit(1)` for a
missing/invalid value but had no `return` after it. In real use this is
harmless (`sys.exit()` raises `SystemExit`, which always stops execution
before the next line runs) -- but a test that mocks `sys.exit` to make it
inspectable (rather than actually killing the test process) exposed that
execution would otherwise fall through to `argv[idx + 1]` and crash with an
`IndexError` instead of exiting cleanly. Fixed by adding an explicit
(defensively unreachable in real use, but now correct regardless)
`return None` after each `sys.exit(1)` call.

**`--dry-run` + `--permission-mode` interaction, surfaced explicitly rather
than left as a silent surprise:** `bypass` mode's `confirm_fn` never
consults `base_confirm` at all (see permissions.py), so combining
`--dry-run --permission-mode bypass` would otherwise silently make
`--dry-run` a complete no-op -- everything actually executes. Similarly,
`accept_edits`/`auto` auto-approve ordinary file writes without consulting
`base_confirm`, so those specific writes happen for real even under
`--dry-run` (only genuinely destructive commands and sensitive-path
attempts still go through `--dry-run`'s decline-and-report path in those
two modes). `main.py` now prints an explicit `⚠️` warning to stderr the
moment these combinations are detected at startup, rather than letting a
user assume `--dry-run`'s protection is unconditional across every mode.
No warning is printed for `default`/`plan`/`dont_ask`, since none of those
reduce `--dry-run`'s protection (`plan`/`dont_ask`'s restricted registries
never even contain `write_file`/`run_command` for `--dry-run` to need to
protect against in the first place).

Verified two ways:
- `test/main_permission_mode_cli_test.py` (9 scenarios, no LLM, no real
  REPL loop): confirms `_parse_permission_mode([])` returns `None` (not
  `PermissionMode.DEFAULT`); every valid mode value parses to the correct
  enum member; a missing value after the flag exits(1) with a clear error
  instead of crashing (this is the test that caught the `IndexError` bug
  above); an unknown mode value exits(1) listing the valid ones; the
  `--dry-run` interaction warning fires for exactly `bypass`/`accept_edits`/
  `auto` and stays silent for `default`/`plan`/`dont_ask`; `main()` is
  proven (by patching both `agent.run_agent` and `permissions.run_agent_with_mode`
  and asserting exactly one was called) to take the untouched prior call
  path with no flag, and to route through `run_agent_with_mode` with the
  correct mode when the flag is given; `--dry-run`'s confirm callable is
  confirmed to still be threaded through as `base_confirm` even when
  combined with a mode.
- Real subprocess runs of the actual `main.py` CLI (not mocked): startup +
  `/exit` succeeds cleanly for `--permission-mode plan` (banner shows
  `🔐 Permission mode: plan`, exit code 0) and for no flags at all (exit
  code 0, unchanged banner); `--permission-mode bogus-mode` and
  `--permission-mode` with no following value both exit with code 1 and a
  clear, correctly-formatted error message listing valid values.

All 12 pre-existing test files (permissions, sub-agents, streaming, apply_edit,
AST, git, sensitive-path, process-manager, LLM-timeout) still pass unchanged.

## Honest gap-check: "did u test?? 4 of this" -- a real accountability episode

After presenting permission modes as fully verified, a direct challenge
revealed the earlier claim was **partially true**: the live test suite
covered the same *mechanisms* a competitor's proposal specified (Tests 1-3)
but not the *exact literal scenarios* (specific files, specific commands),
and Test 4 (a full React furniture site, plan-to-output) had been silently
skipped entirely, never flagged. This section documents what was actually
verified afterward, including a real bug found along the way -- kept here
deliberately as a record of the accountability process, not just the
end result.

### A real, pre-existing bug found via the exact-scenario re-test

`tools.is_destructive_command()`'s `rm` pattern only matched an `-rf`/`-fr`
style flag combination (`r"\brm\s+-[a-z]*r[a-z]*f"`). Confirmed directly:
`is_destructive_command("rm old_auth.py")` (a plain `rm`, no flags -- the
proposal's own literal Test 2 command) returned `False`, and
`agent._needs_confirmation("run_command", {"cmd": "rm old_auth.py"})`
returned `None` -- meaning this command would run **completely unprompted
in every permission mode, including `default`**, not just `accept_edits`.
This predates permission modes entirely; it surfaced specifically because
the exact-scenario test insisted on the proposal's literal command instead
of a generic substitute like `rm -rf /tmp/x`. Fixed by widening the
pattern to `r"\brm\s+"` (any `rm` invocation) -- `run_command` has no
checkpoint/undo mechanism the way `write_file`/`apply_edit` do (see
checkpoint.py), so any file deletion via `rm` is irreversible through this
tool and warrants confirmation, not just the recursive-force-flag case.
Verified no regression: word-boundary `\b` means "term"/"germ"/"confirm"/
"affirm"/"perform" are correctly NOT matched; all 14 existing test files
(including `test/confirm_bridge_test.py`, which has its own hardcoded
`rm -rf` test command) still pass unchanged.

### Tests 1-3, re-verified against the EXACT literal scenarios (not generic substitutes)

`test/permissions_exact_scenarios_test.py` (4 scenarios, real LLM calls):

- **Test 1** (`plan` mode + the real `test/calculator.py`, with its
  actual pre-existing tax-doubling bug): the proposal expected a hard
  `"ERROR: Tool 'apply_edit' is not allowed in plan mode"` observation.
  This project's actual mechanism is structural registry restriction
  (`apply_edit`/`write_file` are absent from plan mode's schema, not
  present-but-denied), so that literal string never appears by design --
  verified the functionally equivalent, correct outcome instead: the real
  file is provably byte-for-byte unchanged, and the model proposes a fix
  in text instead of executing it.
- **Test 2** (`accept_edits` mode, the exact `auth.py` JWT refactor +
  `rm old_auth.py` scenario): confirmed live, in one real multi-step run --
  `apply_edit` on `auth.py` (JWT refactor) proceeded with **zero**
  confirmation prompts (verified: no `write_file`/`apply_edit` call ever
  reached the `confirm()` callable), while `run_command("rm
  test/scratch/old_auth.py")` correctly hit the gate, was recorded via
  `confirm()`, and -- once denied -- `old_auth.py` was confirmed to still
  exist on disk (the denial genuinely blocked the delete, not just
  reported as denied while secretly still running).
- **Test 3** (`dont_ask` mode, the exact `npm install` command): the model
  explicitly said "I don't have a tool for executing shell commands," with
  an added check (found necessary during this session) that it doesn't
  fabricate realistic-looking npm output ("added N packages", "up to date
  in") instead of admitting the limitation.

### Test 4: built for real, a real bug found, a real self-fix by the agent -- fully live, nothing scripted

A minimal Vite+React scaffold (`test/furniture_site/`, committed as a
permanent fixture like `test/finance_dashboard/`) was created directly
(not agent-driven, to avoid this sandbox's tight ~1.5GB free RAM being
risked on an agent-orchestrated `npm install` loop -- `npm install` itself
took 11s and posed no actual resource problem once scoped this way).

The agent, running under `permissions.run_agent_with_mode(mode=ACCEPT_EDITS)`
with **no code-writing help from the human operator**, was given a plan-
to-output task: build a minimalist furniture landing page (nav, hero,
4-item product grid, footer). It wrote `App.jsx` and `App.css` with **zero
confirmation prompts** (accept_edits working as designed), and the result
compiled cleanly (`npm run build`: 16 modules, 0 errors).

**A real, independently-caught bug**, not the agent's own self-report: a
screenshot via `tools_browser.screenshot_url` (this project's own tool,
not manual inspection) showed the page rendering completely unstyled --
raw bullet-point nav, no grid, no cards. Root cause, confirmed by reading
the actual generated source: the new `App.jsx` never contained `import
'./App.css'` (the original scaffold's `App.jsx` had this import; the
agent's rewrite silently dropped it). The agent's own `read_file`-based
self-verification never caught this, because text-based read-back cannot
detect a missing import's VISUAL consequence -- only actually rendering
the page can, which the task didn't originally direct it to do.

**Self-fix, run twice, both fully live and both being an honest account of
what actually happened, not a retry-until-success narrative:**
- Attempt 1 (15-iteration budget): the agent correctly reached for real
  browser tools (`test_local_html`, `evaluate_js`, reading the actual
  compiled CSS bundle) and was genuinely converging on the right
  diagnosis, but ran out of budget mid-investigation -- never reached the
  fix. Reported as a real, useful finding (agent thoroughness vs. step
  budget is a real tradeoff), not silently re-run until it happened to
  pass.
- Attempt 2 (25-iteration budget): found and fixed the exact root cause
  via `apply_edit` (added the missing import, again with **zero**
  confirmation prompt), then used `run_command` itself (unprompted --
  `npm install`/`npm run build` aren't destructive) to rebuild, producing
  a 17-module build with the CSS bundle correctly growing from 1.78kB to
  3.51kB (proof the furniture styles are now actually bundled, not just a
  successful-looking compile).

An independent screenshot (taken directly via `tools_browser.screenshot_url`
against the rebuilt site, NOT trusting the agent's own incomplete final
log -- the agent's process actually hit its wall-clock timeout right after
the rebuild, before printing a final summary) confirmed the fix: a real,
correctly-styled landing page with a horizontal nav bar, centered hero
with an accent-colored CTA button, a 4-card product grid with gray
placeholder boxes, and a minimal footer -- matching the original spec.

**What this episode demonstrates beyond the specific bugs found:** the
project's standing "never trust a proposal's code as correct, verify
everything directly" discipline applies equally to this project's OWN
prior claims of "verified" -- a claim of testing is not the same as having
tested the literal thing asked for, and the right response to being
challenged on that is to actually go find out, not to explain why the
substitute was reasonable.

## Skills (`skills.py`) -- Anthropic's official spec, fact-checked before building

Adds Agent Skills: reusable, on-demand instruction bundles the model loads
mid-task via a real `load_skill(name)` tool call, per Anthropic's
OFFICIALLY PUBLISHED spec (`code.claude.com/docs/en/skills`,
`agentskills.io` -- verified this session, not extracted from any leaked
source, per the standing legal/IP policy in `COMPARISON_openclaude.md`).

**A proposal's design was corrected on THREE separate points before any
code was written, each verified against real sources rather than assumed:**

1. **The `tools:` hint's real semantics were the opposite of what both the
   proposal and several real Anthropic GitHub bug reports assumed.**
   Searching Anthropic's own bug tracker surfaced two genuine, still-open
   issues (`anthropics/claude-code#18837`, `#37683`) where users configured
   `allowed-tools: Read, Glob, Grep` expecting it to BLOCK `Edit`/`Write`,
   and found Claude used them anyway. Reading Anthropic's own official docs
   (not the bug reports) resolved why: `allowed-tools` **pre-approves**
   listed tools to skip a confirmation prompt and explicitly "does not
   restrict which tools are available" -- the real restriction field is a
   DIFFERENT one, `disallowed-tools`. Building "advisory-only tools hints"
   (the proposal's stated default) would have accidentally matched
   Anthropic's real, documented behavior for the wrong reason (never having
   read the real spec) rather than for the right one.
2. **Even knowing the real spec, `disallowed-tools`'s real MID-TASK
   enforcement was deliberately NOT built in v1** -- found a genuine
   architectural cost first: `agent.run_agent()`'s `active_tool_functions`/
   `active_tool_specs` are computed ONCE before the ReAct loop starts and
   never touched again inside it (confirmed by reading the actual code,
   not assumed) -- real enforcement would require turning these into
   loop-mutable state updated when `load_skill` is dispatched, a
   non-trivial change to a loop already carefully hardened across several
   recent features (streaming, the batching nudge, sub-agent depth/
   budget). The cheaper, ALREADY-BUILT alternative for a task that
   genuinely needs enforcement: dispatch the skill as a sub-agent
   (`subagents.py`'s `dispatch_agent`, which restricts tools at SPAWN
   time, no mid-loop mutation needed) -- e.g. `dispatch_agent(
   subagent_type="explore", prompt=<skill body> + <task>)`. `tools_hint`
   is therefore advisory text only in `load_skill`'s output for v1,
   explicitly labeled as such -- matching this project's own
   build-cheap-first, measure-then-escalate practice from the
   batching-nudge decision, not a shortcut taken silently.
3. **A real bug found and fixed before shipping, not caught by review**:
   a naive `text.split("---", 2)` frontmatter parser (matching a pattern
   several real skill-tooling projects actually use, confirmed by reading
   their source) raises an unhandled `ValueError` on unpacking if a
   `SKILL.md` is missing its closing `---` delimiter -- confirmed directly
   (`"---\nname: x\nno closing delimiter".split("---", 2)` returns only 2
   parts). Combined with a `scan_skills()` loop that has no per-skill
   exception handling, ONE malformed `SKILL.md` (a plausible typo in a
   hand-written file) would crash the WHOLE skills registry, silently
   taking down every OTHER valid skill too -- the exact "one bad input
   kills everything" bug class this project has already been bitten by
   and fixed before (the null-args `TypeError` bug, the RAG/git circular-
   import silent-failure bug). Fixed with a regex-based parser
   (`_FRONTMATTER_RE`, non-greedy + DOTALL) that fails predictably with a
   catchable error instead of an unhandled exception, PLUS a per-skill
   `try/except` in `scan_skills()` so one broken skill never prevents any
   other valid skill from loading.

**Three-layer progressive disclosure, per the official spec:**
1. **Metadata** (name + description) -- computed FRESH on every
   `run_agent()` call (not baked into the module-level `SYSTEM_PROMPT`
   once at import time -- a real, deliberate distinction: unlike every
   other optional-feature flag in `SYSTEM_PROMPT`, which only depends on
   whether a PACKAGE is installed and is fixed for the whole process,
   skills are user-authored FILES that can be added/edited on disk between
   two `run_agent()` calls within the same process -- a metadata block
   computed once at import time would silently go stale).
2. **Body** -- loaded only when the model calls `load_skill(name)`.
3. **Supporting files** (templates/, references/) -- NEVER auto-loaded;
   `load_skill`'s output only mentions their relative paths and tells the
   model to `read_file` them if the skill's own instructions reference one
   -- confirmed directly that a template file's actual CONTENT never
   appears in `load_skill`'s output, only its path.

**Naming**: `.agent_skills/` for consistency with `.agent_backups/`/
`.agent_missions/`, but semantically DIFFERENT from both -- those are
pure runtime state (regenerated, gitignored); skills are USER-AUTHORED
CONTENT meant to be committed and shared, closer to `test/finance_dashboard/`
than a runtime cache. Not added to `.gitignore`.

**Verified two ways, escalating to fully live -- including two real
mistakes in the FIRST live test attempts, caught and fixed, not hidden:**

- `test/skills_test.py` (24 scenarios, no LLM): frontmatter parsing
  (normal case, a body containing a literal `---` horizontal rule
  correctly preserved, a missing closing delimiter raising a clear error,
  malformed YAML, missing required `name`/`description` fields, both
  string and YAML-list forms of `disallowed-tools`/`allowed-tools`);
  `scan_skills`'s core fix directly proven (one malformed skill alongside
  two valid ones -- both valid skills still load, the broken one reports
  a real error instead of silence); `get_metadata_block` never lists a
  broken skill; `render_loaded_skill` includes the body, mentions
  supporting files by path, and PROVABLY never auto-loads a supporting
  file's actual content (a unique marker string placed in a template file
  is confirmed absent from the rendered output); tool registration and
  schema-shape checks. One real bug caught by this test suite itself: an
  earlier version of `render_loaded_skill` crashed with `Path.relative_to`
  raising `ValueError` for a non-absolute `skill.root` (harmless in real
  use, where `scan_skills` always builds absolute paths from
  `tools.WORKDIR`, but still fragile code) -- fixed with a fallback.
- `test/skills_live_test.py` (2 scenarios, REAL LLM calls, no mocking) --
  reproducing the original proposal's own validation scenario as literally
  as possible, with two real, disclosed corrections made ALONG THE WAY
  after live runs exposed them (not before, and not hidden after the
  fact):
  1. The proposal's own literal task text ("Build a login form component",
     no mention of React) was tried FIRST, verbatim -- a real live run
     showed the model reasonably building a plain HTML/CSS form instead,
     never calling `load_skill` at all. This is NOT a skills.py bug (Test
     1 independently confirms the metadata block reaches the system
     prompt correctly) -- it's a genuine ambiguity in that literal task
     text, which never actually says "in React." Documented plainly
     rather than silently reworded away; the task text was then
     deliberately disambiguated ("...React component with TypeScript") to
     isolate the mechanism under test from this separate, real, and still
     openly-acknowledged limitation (a skill's one-line catalog
     description isn't a strong enough signal to make the model infer an
     unstated framework from a generic request).
  2. An earlier version of the test asserted on the model's final CHAT
     REPLY text for whether the generated code matched the skill's rules
     (TypeScript interface, both exports). A live run showed the model
     writing a fully correct file to disk (confirmed by hand against the
     real `write_file` log entry) but then summarizing it in PROSE in its
     final answer without repeating the literal code -- causing the
     assertion to fail against an actually-correct result. Fixed by
     parsing the real `write_file` Action from the run's own event log to
     find whatever path the model actually chose (not assumed to be a
     fixed filename -- confirmed live across multiple runs that the model
     chose different paths/directories each time, e.g. `LoginForm.tsx` at
     the root vs. `components/LoginForm.tsx`) and asserting against the
     REAL FILE CONTENT on disk -- the same "verify the real artifact, not
     a report about the artifact" principle applied everywhere else in
     this project (screenshots over descriptions, real `.env` diffs over
     self-reported bypass claims).
  Final, corrected result, live: the model called `load_skill(
  "react-component")` before writing any code (confirmed via the real
  event log), and the resulting real file
  (e.g. `components/LoginForm.tsx`) contained every one of the original
  proposal's 4 pass conditions: a functional component with hooks (no
  class), a TypeScript `interface LoginFormProps`, Tailwind
  `className="..."` utility classes throughout (zero inline styles), and
  BOTH `export default LoginForm;` and `export { LoginForm };`.

All 15 pre-existing test files (permissions, sub-agents, streaming,
batching nudge, apply_edit, AST, git, sensitive-path, process-manager,
LLM-timeout) still pass unchanged.


## Batching nudge (`agent.py`) -- closing a real gap found via the episode above, not a hypothetical one

The furniture-site self-fix runs above (both without this fix) made 4
CONSECUTIVE, fully independent `read_file` calls (`App.jsx`, `App.css`,
`main.jsx`, `index.css`) as 4 SEPARATE LLM turns, even though this project
already has everything needed to avoid that: `agent._is_batchable()` +
`_run_tool_calls()`'s `ThreadPoolExecutor` already run several independent
read-only calls CONCURRENTLY when the model requests them in the SAME
turn, and the system prompt's own `"Efficiency:"` section already
instructs exactly this ("reading 3 unrelated files... request them as
multiple tool calls in the SAME turn"). The machinery was correct; it was
advisory text the model simply didn't follow in that real run. This adds
a CORRECTIVE OBSERVATION that fires the moment the wasteful pattern is
actually detected -- not a new tool, not a new message role, not a
stronger up-front instruction (that was already tried, in the existing
system prompt, and didn't work for this case).

**Detection logic, reusing existing eligibility checks rather than
inventing a second notion of "independent":**
- `_solo_batchable_call_info(tool_calls)`: returns `(tool_name, args)` for
  a turn's lone call ONLY if that call individually passes the EXACT SAME
  `_is_batchable()` check the real concurrent-execution path uses --
  guarantees "the nudge says these could batch" and "the engine would
  actually run them concurrently if batched" can never disagree. Returns
  `None` for a turn with more than one call (that's the GOOD, already-
  batched behavior this nudge exists to encourage -- nothing to correct).
- `_should_nudge_to_batch(prev, curr)`: `True` only if both the previous
  and current turn were solo batchable calls, EXCLUDING two deliberate
  false-positive risks found by inspecting the real transcript this fix is
  based on: (1) two consecutive `list_files` calls are NOT flagged, since
  a parent-directory listing followed by a subdirectory listing is a
  plausible, genuinely SEQUENTIAL discovery pattern (confirmed in the same
  transcript: `list_files("test/furniture_site")` ->
  `list_files(".../src")` -> `list_files(".../dist")`) -- flagging this as
  a missed batch would be actively wrong advice; (2) an exact repeat of
  the same `(tool, args)` is not flagged either, since `cache.py`'s
  `ToolCache` already serves that from cache -- there's nothing to batch.
- The nudge text is appended to the CONTENT of the existing tool-result
  message for the current turn's lone call -- NOT a new message or role.
  This deliberately reuses the exact wire shape `_sanitize_tool_calls`
  already keeps minimal for cross-provider portability (see that
  function's own docstring: a real, previously-found bug where Cerebras
  strictly validates incoming messages and rejects unrecognized fields
  when the Router fails over to it mid-conversation) -- a plain string
  append can never trigger that class of bug on any provider.

**Verified two ways:**
- `test/batching_nudge_test.py` (13 scenarios, no LLM): `_solo_batchable_call_info`
  correctly returns `None` for an already-batched multi-call turn, a solo
  `write_file` (not eligible for batching at all), and a solo destructive
  `run_command` (must stay sequential for confirmation); correctly
  extracts `(name, args)` for a real solo read; doesn't crash on malformed
  JSON. `_should_nudge_to_batch` fires for the EXACT real missed-batch
  pattern from the transcript (`App.jsx` -> `App.css`), does not fire on
  the first call of a task (nothing to compare), correctly excludes the
  `list_files`/`list_files` pair and an exact repeat, and correctly fires
  for a mixed `read_file` -> `grep_files` pair (not `read_file`-specific).
  A full wiring test confirms the nudge text appears in the SECOND of two
  consecutive independent solo reads' tool-result content, never the
  first (there's nothing to compare against yet on the first).
- **Live, head-to-head comparison against the EXACT same broken state**
  (the furniture site's `App.jsx` was reverted to the missing-import bug,
  rebuilt to the identical 16-module/1.78kB-CSS broken state, then the
  IDENTICAL fix task re-run under the IDENTICAL `accept_edits` mode and
  25-iteration budget used in the pre-fix live test above):

  | Run | LLM turns to complete | Reached the fix? | Fully finished? |
  |---|---|---|---|
  | Without the nudge (attempt 1, 15-budget) | 13 (exhausted budget) | No | No |
  | Without the nudge (attempt 2, 25-budget) | 15+ (killed by 700s wall-clock timeout) | Yes | No -- never printed a final summary |
  | **With the nudge (25-budget)** | **8** | Yes | **Yes -- completed with a correct final summary** |

  The nudge fired 3 times in the successful run (visible in the log as
  `[Note]` entries) and never misfired on a `list_files`->`read_file`
  transition (a genuinely dependent pair). The model did not literally
  start requesting multiple tool calls per turn mid-task (a text nudge
  can't force that), but total turn count dropped by roughly 40-45%
  versus the no-nudge runs, and -- the more important result -- this run
  actually FINISHED, which neither prior attempt did. The final result
  was independently re-verified: `App.jsx` correctly contains
  `import "./App.css"`, the rebuilt CSS bundle grew from 1.78kB to 3.51kB
  (matching the earlier successful fix's numbers exactly), and a
  screenshot of the rebuilt site is pixel-identical to the earlier
  successful fix's screenshot. Full transcript preserved at
  `test/batching_nudge_live_comparison_run.log`.

**Decision per the agreed criterion going in:** the nudge measurably
worked (turn count dropped, and the run completed where two prior runs
didn't) -- so per the agreed plan, `read_files(paths: list[str])` (a
plural read tool that would remove the need for the model to remember to
batch at all) is NOT being built now. It remains a reasonable escalation
if a FUTURE measurement shows the nudge's effect fading (e.g. a different
task shape where the model doesn't respond to the corrective text), but
building it now would be solving a problem this specific, measured test
just showed doesn't currently require it.

## Custom Project Rules (`rules.py`) -- verified against BOTH Cursor and Claude Code's real, current docs

Adds user-authored, version-controlled standing instructions, following
the real conventions of both major AI coding tools (researched fresh this
session, not assumed): Cursor's `.cursor/rules/*.mdc` (`description`/
`globs`/`alwaysApply` frontmatter) and Claude Code's `CLAUDE.md` +
`.claude/rules/*.md` (`paths:` frontmatter for path-scoped rules, per
`code.claude.com/docs/en/memory`). Also supports `AGENTS.md` at the
project root -- a genuinely open, cross-tool standard (originated by
OpenAI, donated to the Linux Foundation's Agentic AI Foundation, read
natively by 20+ tools including Claude Code as a documented fallback and
Cursor) -- confirmed no naming collision with anything already in this
project before adding it.

**Two kinds of rules, matching the real, verified behavior of both tools:**
1. **Always-loaded**: `AGENTS.md` at the project root, plus any
   `.agent_rules/*.md` file with NO `paths:`/`globs:` frontmatter (or no
   frontmatter at all -- a rule file can be plain text/markdown with zero
   YAML, exactly like a real `.cursorrules` or `CLAUDE.md`). Computed
   FRESH on every `run_agent()` call and appended to the system prompt --
   the same deliberate "not baked into the module-level `SYSTEM_PROMPT`
   once at import time" design already used for skills' metadata block,
   for the identical reason: these are user-authored FILES that can
   change on disk between calls within the same process.
2. **Path-scoped**: a rule file WITH `paths:` (or Cursor's `globs:`)
   frontmatter is NOT loaded upfront. It's injected as a corrective
   observation the FIRST time (per task) a matching file is actually read
   or written -- reusing the EXACT injection mechanism already proven live
   in the batching nudge above (append to the tool-result CONTENT, never a
   new message role). This matches Claude Code's/Cursor's real, documented
   behavior (a path-scoped rule only "activates" when the agent actually
   touches a matching file) and is architecturally identical to the
   batching nudge's own "detect a real-time condition mid-loop, inject
   into the next tool result" pattern -- built as a natural extension of
   already-proven code, not a new mechanism invented from scratch.

**A real bug found in Python's own standard library before this shipped,
not in a proposal this time:** `pathlib.PurePosixPath.match()` does NOT
implement correct globstar (`**`) semantics. Confirmed directly:
`PurePosixPath("src/api/foo.ts").match("src/api/**/*.ts")` returns
`False`, even though EVERY real documentation example for both Cursor and
Claude Code uses exactly this pattern shape expecting it to match a file
**directly** inside `src/api/`, not just nested ones (real glob semantics:
`**` matches zero or more directories). Confirmed the correct primitive
instead: `glob.translate(pattern, recursive=True, include_hidden=True)`
(Python 3.13+, present in this environment) -- translates a glob pattern
into a real regex with correct globstar semantics, verified directly
against 8 test cases (exact matches, direct-child matches, nested matches,
non-matches) with `glob.translate` matching expected behavior in every
case while `pathlib.match()` failed the direct-child case. This class of
bug is worse than a crash: it fails "successfully" (returns a plausible-
looking `False`) and a path-scoped rule would have silently never fired
for the most common case (a file directly in the scoped directory)
without anyone noticing.

**Reuses, not duplicates, skills.py's own machinery**, per explicit
instruction this session: `skills.py`'s frontmatter/body-splitting regex
was extracted into a new shared `parse_frontmatter()` function that both
modules call, rather than `rules.py` reimplementing the same
`---`-delimited YAML parsing a second time (verified the extraction
didn't change `skills.py`'s existing behavior -- all 24 pre-existing
skills tests still pass unchanged after the refactor). `rules.py` also
reuses `agent.py`'s own canonical `_WRITE_FILE_TOOL_NAMES`/
`_APPLY_EDIT_TOOL_NAMES` sets (the same ones `_needs_confirmation` already
uses) to know which tools touch a file, rather than declaring a second,
parallel list that could drift out of sync.

**A `list_rules` tool** (not a `load_rule` tool, deliberately -- rules are
never explicitly invoked by the model the way skills are; they're either
always-on or triggered automatically by file access) lets the model or a
human debugging why a rule isn't firing see every discovered rule
(always-loaded or path-scoped), including parse errors for any rule file
that failed to load, mirroring `skills.py`'s own `list_skills` tool.

**Verified three ways, escalating to fully live:**
- `test/rules_test.py` (22 scenarios, no LLM): frontmatter-optional
  parsing (a rule with zero YAML is valid, unlike a skill which requires
  `name`+`description`); both `paths:` (Claude Code) and `globs:`
  (Cursor) frontmatter field names accepted; a YAML list of patterns
  normalized correctly; malformed-but-present frontmatter still raises a
  clear error (distinct from "no frontmatter at all," which is valid);
  **the critical globstar test directly proving the real pathlib bug is
  fixed** (`src/api/**/*.ts` correctly matches a file directly in
  `src/api/`, not just nested ones); non-matching paths correctly don't
  match; multiple patterns joined with `|` match via alternation; a
  malformed glob pattern fails safe (never matches) instead of crashing;
  per-rule scan isolation (one broken rule file doesn't take down the
  others, the same real bug class `skills.py`'s `scan_skills` was built
  to avoid); recursive subdirectory discovery (matching Claude Code's own
  documented behavior); `get_always_loaded_block` correctly excludes
  path-scoped rules; a real `AGENTS.md` at the actual project root is
  correctly included.
- `test/rules_wiring_test.py` (5 scenarios, fully mocked LLM, no real API
  calls -- isolates the WIRING bug class from LLM non-determinism): a
  path-scoped rule fires and its exact body appears in the tool-result
  content for a matching `read_file` call; a rule correctly does NOT fire
  for a non-matching file extension in the same directory; a rule fires
  **exactly once per task** even when 2 different matching files are
  touched (verified by counting literal occurrences of a unique marker
  string in the full conversation, not just checking "at least once");
  an always-loaded rule appears in the system prompt from the very first
  turn.
- `test/rules_live_test.py` (2 scenarios, REAL LLM calls, no mocking):
  (1) an always-loaded rule ("use pytest, not unittest") measurably
  changed a real model's output for a task that never mentioned pytest at
  all -- verified the real reply contains `def test_` / `import pytest`
  and NOT `unittest.TestCase`; (2) a path-scoped rule genuinely fired in
  real time (visible as a `[Note]` event in the live log) the moment the
  model's `write_file` call touched a matching path under
  `test/scratch/`, and -- this is the strongest result -- **the model
  self-corrected**: its first write didn't have the required marker
  comment (it hadn't seen the rule yet), the rule fired immediately after
  that write, and the model's VERY NEXT action was `read_file` followed by
  a second `write_file` adding the exact required
  `# SCRATCH FILE - not part of the permanent codebase` comment as the
  first line -- confirmed against the real file content on disk (not the
  model's chat summary, learning directly from the earlier `skills_live_test.py`
  mistake this session already found and fixed), then further verified by
  watching the model actually execute the corrected script via
  `run_command` and confirm its real output.

All 17 pre-existing test files (permissions, sub-agents, streaming,
batching nudge, skills, apply_edit, AST, git, sensitive-path,
process-manager, LLM-timeout) still pass unchanged.

## Repo Map (`repo_map.py`) -- PageRank over the real import graph, every claim fact-checked before building

A ranked map of the codebase's most structurally important files
(definitions + real import graph), following the algorithm made popular
by Aider (`Aider-AI/aider/blob/main/aider/repomap.py`, Apache-2.0,
independently-open -- safe to build from per this project's standing
leak-avoidance policy) and described, without implementation, in
OpenClaude's own public `docs/repo-map.md`. A `repo_map_query` tool lets
the model get an overview of "what exists and how it connects" before
diving into `list_files`/`read_file` calls one at a time.

**Every non-trivial claim in the original proposal was run against this
project's actually-installed libraries before any code was written --
three real bugs found this way, not caught by review:**

1. **The proposal's own tree-sitter verification snippet fails
   immediately.** `parser.set_language(tspython.language())` -- confirmed
   directly: `AttributeError: 'tree_sitter.Parser' object has no
   attribute 'set_language'` in the actually-installed tree-sitter 0.26.0.
   The real, already-proven pattern (this project fact-checked this exact
   API months earlier building `ast_tools.py`) is
   `Parser(Language(grammar.language()))` -- language passed directly to
   the constructor -- plus `QueryCursor(query).matches(node)`, since
   `Query` objects have no `.captures`/`.matches()` of their own either
   (also reconfirmed directly, matching `ast_tools.py`'s own earlier
   finding).
2. **A real, serious bug in the proposed JS `require()` detection query**:
   `(call_expression function: (identifier) @require)` matches EVERY
   function call in a file, not just `require(...)` calls -- confirmed
   directly against real code (`console.log(...)`, `calculateTotal(1,2)`,
   `someOtherFunction()` all got captured as "require" alongside the one
   real `require("./helpers")` call, 3 false positives for 1 true
   positive). This would have corrupted the import graph with dozens of
   fabricated dependency edges per real file. Fixed with a
   `(#eq? @fn "require")` predicate -- the same exact predicate pattern
   already proven working in `ast_tools.py`'s own function-name matching.
3. **`networkx` was claimed "already installed via some dependency" --
   confirmed FALSE as stated.** It's present in this sandbox purely by
   coincidence, transitively pulled in by `scikit-image` (unrelated to
   this project, not itself required by anything in `requirements.txt`).
   Unlike `PyYAML` (genuinely required by `chromadb`, a real project
   dependency, verified separately when building `skills.py`), relying on
   `networkx` here would mean relying on sandbox coincidence. Per explicit
   decision: built a small (~50 line), hand-rolled PageRank instead,
   VERIFIED NUMERICALLY correct against `networkx`'s own real
   `nx.pagerank()` output (used here only as verification ground truth,
   not a runtime dependency) -- matched to 5-6 decimal places on both a
   normal multi-file import graph and one containing an isolated node
   (a file with zero imports/importers), the latter surfacing a real gap
   during verification (edges alone can never reveal an isolated file --
   the full node set must be passed in explicitly). The documented future
   upgrade path to `networkx` (for a much larger codebase or more
   sophisticated graph algorithms) is written up in
   `REPO_MAP_NETWORKX_UPGRADE.md`, per explicit instruction to preserve
   this reasoning rather than silently build on an accidental dependency.

**Two more real bugs found by this module's own test suite** (not caught
during the initial fact-check, found while writing
`test/repo_map_test.py`):
- `import utils as u` wraps the module name inside an `aliased_import`
  node -- the original Python import query only matched
  `name: (dotted_name)` directly on `import_statement`, silently missing
  every aliased import. Confirmed by walking the real parse tree; fixed
  with a second query line reaching into the `aliased_import` wrapper.
- `from . import helpers` / `from ..pkg import thing` wrap the source in a
  `relative_import` node, not a plain `dotted_name` -- the original query
  only matched `module_name: (dotted_name)`, silently missing every
  relative import. Fixed by matching `import_from_statement`'s `name:`
  field specifically when `module_name` is a `relative_import` (the real,
  resolvable target for a relative import is the imported symbol name,
  e.g. "helpers", not the bare "." prefix) -- confirmed this correctly
  does NOT also over-match `from auth import login, logout`'s `name:`
  fields (those remain genuinely just symbol names, not files; `auth`
  itself is still separately captured via the plain-dotted-name case).

**A design gap found the same way** (`test_list_project_files_falls_back_for_non_git_directory`):
file enumeration originally trusted `git ls-files --exclude-standard`
alone to exclude noise directories like `node_modules` -- but a directory
with no `.gitignore` rule covering `node_modules` specifically (confirmed
directly: this project's own ROOT `.gitignore` doesn't mention
`node_modules` at all -- that exclusion for `test/furniture_site/` comes
from Vite's own NESTED `.gitignore` inside that specific subdirectory)
would return `node_modules` contents completely unfiltered. Fixed with a
defensive `_SKIP_DIRS` re-filter applied regardless of git's own
`.gitignore` handling -- matching this project's own established pattern
(`tools.grep_files` applies the identical "exclude via flag, then
defensively re-filter" approach for sensitive paths, never trusting the
flag alone).

**Verified against this project's own real, live codebase, not just
synthetic fixtures:** a cold scan of this project's 74 real `.py`/`.js`
files completes in ~0.35s; a warm (cached) re-scan completes in ~0.006s
(confirmed the cache -- keyed by path+mtime+size, matching OpenClaude's
own documented cache-invalidation approach -- genuinely skips
re-parsing, proven by monkeypatching the extractor to raise on any real
call and confirming a warm scan never triggers it); the full
`get_repo_map()` pipeline (scan + PageRank + format) completes in ~0.03s
warm. The real, unweighted PageRank ranking correctly surfaces `tools.py`
(imported by nearly every module in this project) at #1, with `agent.py`/
`permissions.py`/`cache.py`/`subagents.py` immediately behind it --
matching this project's actual, known real structure, not asserted in
isolation. Cross-checked the extracted import graph directly against
`agent.py`'s real `import`/`from` lines by hand: every real import
(`tools`, `process_manager`, `cache`, `llm_client`, `memory`, `missions`)
was captured as a graph edge, with zero false positives.

**Verified two ways, escalating to fully live:**
- `test/repo_map_test.py` (22 scenarios, mostly no LLM -- pure static
  analysis + graph ranking is deterministic and doesn't need one):
  Python extraction (functions/classes, both import forms, relative
  imports, syntax-error tolerance), JS extraction (functions/classes, ES
  module imports, **the critical require()-predicate test proving the
  real bug fix holds**, syntax-error tolerance), file enumeration (real
  git repo, non-git fallback with defensive `_SKIP_DIRS` filtering),
  import-graph resolution (same-directory Python import, JS relative
  import, and critically -- an import of a real external package like
  `numpy` correctly produces NO fabricated edge, since a missing edge is
  fine but a wrong one corrupts the whole ranking), **the two PageRank-
  vs-networkx numerical cross-checks**, query-boost ranking, token-budget
  formatting (always includes at least the top file even under a tight
  budget; shows definition NAMES only, never full implementation bodies),
  cache hit/invalidation (both proven with real file mtime/size changes,
  not just logic assertions), and the full pipeline against this
  project's own real codebase.
- `test/repo_map_live_test.py` (2 scenarios, REAL LLM calls, no mocking):
  a direct query for "permission mode confirmation gate" against this
  project's real codebase correctly surfaces the real `permissions.py`
  in the top 10 ranked files; a real model, given an "I'm new to this
  codebase, get an overview" task, CHOSE on its own to call
  `repo_map_query` (never forced to) before answering, and its final
  answer correctly named `tools.py`/`permissions.py`/`agent.py` as the
  core files for permission-mode/confirmation-gate logic, with an
  accurate description of each file's actual real role -- independently
  confirmed correct by cross-referencing against this project's own
  actual implementation history.

All 18 pre-existing test files (permissions, sub-agents, streaming,
batching nudge, skills, rules, apply_edit, AST, git, sensitive-path,
process-manager, LLM-timeout) still pass unchanged.

## Custom Agent Definitions (`custom_agents.py`) -- composition + inheritance, 2 real design gaps resolved, 1 real regression caught

A user proposal for this feature (`.agent_agents/*.md`, YAML frontmatter +
Markdown body, `extends:` for single-parent inheritance) was solid on the
file format but explicitly flagged two open design questions and one
verification request before any code was written -- handled per this
project's standing "never trust a proposal's code as correct, verify
against the real thing first" discipline:

- **Verification question answered by checking the real code, not
  assuming**: does `subagents.py`'s `dispatch_agent` already accept a
  `mode` parameter (from the earlier permission-modes work)? Checked
  directly against the real signature: **no** -- `subagents.py` doesn't
  even `import permissions` today. Permission modes and sub-agent dispatch
  were two genuinely independent systems before this feature connected
  them for the first time.
- **`model:` field -- dropped for v1.** Checked `llm_client.chat_completion`
  directly: it hardcodes `model=first_model` (the Router's first
  configured deployment) at its own call site, with no existing parameter
  to route a single call to a specific deployment. Honoring an arbitrary
  `model:` string would mean either bypassing the Router's rate-limit-
  cooldown safety net for that call, or adding a new pass-through
  parameter into the one code path every LLM call in the project goes
  through, for a feature nobody has a proven need for yet. A `model:`
  field present in a real file is surfaced as a one-time warning
  (`unknown_fields`), never a hard error and never silently dropped
  without a trace -- the rest of the agent still loads and works. Also
  confirmed live, as a demonstration of why hardcoding a model ID per
  agent file is fragile: the user's own example value
  (`gemini-2.0-flash-exp`) was deprecated and shut down June 1, 2026.
- **`skills:` -- metadata-only, never force-preloaded.** Matches
  `skills.py`'s own already-shipped, explicitly-decided design exactly
  (Layer 1 metadata always shown, Layer 2 body loaded only via a real
  `load_skill` call) -- a named agent's `skills:` list becomes the same
  "Available Skills" block filtered to just those names, so the sub-agent
  still has to actively call `load_skill` itself, exactly like the main
  agent does today.
- **A 3rd gap the proposal left implicit, resolved explicitly**: what
  happens when an agent sets BOTH `mode: plan` (which already structurally
  restricts to read-only tools) AND `tools: [write_file]`? Decided:
  **intersection, never union** -- `tools:` can only narrow what a mode
  already restricted, never re-grant something the mode removed. Verified
  with a real test: an agent with `mode: plan` + `tools: [read_file,
  write_file, run_command]` resolves to ONLY `read_file` in its final
  registry -- `write_file`/`run_command` never leak through despite being
  explicitly named in `tools:`.
- **A real circular-import hazard, confirmed live before shipping, not
  assumed**: `permissions.py` already does `from subagents import
  READ_ONLY_TOOL_NAMES` at its own module level. A draft that added a
  module-level `import permissions` inside `subagents.py` was actually run
  and confirmed to deadlock at import time with a real traceback
  (`ImportError: cannot import name 'READ_ONLY_TOOL_NAMES' from
  'subagents'` -- `subagents.py` was still only half-initialized when
  `permissions.py` tried to pull the name back out of it). Fixed by
  keeping the `import permissions` lazy, inside the function that needs
  it -- the same established pattern every other optional module in this
  project (`skills.py`, `rules.py`, `git_tools.py`, `rag_indexer.py`)
  already uses for exactly this class of bug.
- **A real regression caught by the pre-existing test suite while adding
  this feature**: an early draft of `dispatch_agent` resolved `agent_name`
  (which can raise `ValueError` for an unknown name, a broken `extends`
  link, or an inheritance cycle) only AFTER `budget.try_acquire()` had
  already run -- silently wasting a sub-agent budget slot on a call that
  could never actually dispatch anything. Caught immediately because it
  broke `test/subagents_test.py`'s own pre-existing
  `test_unknown_subagent_type_rejected_before_any_llm_call` (a full
  regression sweep is run after every change in this project, not just
  the new feature's own tests) -- fixed by validating both
  `subagent_type` and `agent_name` up front, before either the depth
  check or the budget, restoring the exact contract the original
  `subagent_type` path already had.

### Composition rules (once the two open questions above were resolved)

| Field | Inheritance rule |
|---|---|
| `name`/`description` | Always the child's own -- never inherited |
| `skills` | Union, deduplicated, across the whole chain |
| `tools` | Replace -- nearest ancestor that specifies one wins; composes with `mode` via intersection (see above) |
| `mode` | Replace -- nearest ancestor that specifies one wins |
| `max_iterations` | Replace -- nearest ancestor that specifies one wins |
| `body` | Prepend -- child's own body first, then a `---` separator, then the parent's (already-resolved) body |

Single-parent inheritance only (`extends: <name>`, not multiple
inheritance) -- cycle detection is a linear visited-name walk that raises
with the actual chain shown (e.g. `a -> b -> a`), not just "cycle
detected." One malformed `.md` file never crashes the whole registry
(same per-item try/except isolation as `skills.py`/`rules.py`), and a
duplicate `name:` across two files is reported as an error, never a
silent overwrite.

### Live verification

Two real example files were committed: `.agent_agents/base-coder.md`
(a shared base, `mode: accept_edits`, full read/write/run tools) and
`.agent_agents/security-auditor.md` (extends `base-coder`, overrides
`mode: plan` and narrows `tools:` to read-only, lists the real
`react-component` skill).

- **Direct dispatch**: `dispatch_agent(agent_name="security-auditor", ...)`
  against a real file with a deliberately-introduced hardcoded secret and
  a string-concatenated SQL query correctly found and explained BOTH
  vulnerabilities (not just "some issue exists"), proposed parameterized-
  query fixes, and -- verified by MD5 hash before/after, not just "no
  write_file call appeared in the log" -- never modified the audited file,
  because `mode: plan` intersected with its own `tools:` structurally
  removed `write_file`/`apply_edit`/`run_command` from its registry.
- **Full end-to-end, through the real parent ReAct loop**: given a task
  that only mentioned wanting a security review, a real model chose,
  UNPROMPTED, to call `list_custom_agents`, saw `security-auditor`, and
  dispatched it BY NAME -- nothing forced this path; a plain
  `subagent_type="explore"` call would have worked too. The sub-agent's
  report went further than the direct-dispatch run, correctly noting that
  the hardcoded secret "bypasses `tools.is_sensitive_path()`'s protection
  entirely" (a real, accurate cross-reference to this project's own
  actual guardrail) and referencing the real `scratch-python-style`
  project rule that fired mid-task on the same file. The parent's own
  final summary correctly named the agent it used and repeated the real
  findings, and the audited file was independently re-verified unchanged
  by hash after this run too.

Full test suites: `test/custom_agents_test.py` (18 unit-level scenarios:
parsing, missing-field rejection, malformed-frontmatter rejection, the
`model:`-is-a-warning decision, per-file isolation, duplicate-name
detection, all 5 composition rules, 3-level skills union, cycle
detection, broken-`extends` detection, unknown-agent-name handling, the
tools/mode intersection rule, depth-limit enforcement for named agents,
clean ERROR strings with no raw tracebacks, backward-compatibility of the
pre-existing `subagent_type` path, the circular-import hazard confirmed
absent, and tool registration) and `test/custom_agents_live_test.py` (the
2 real-LLM scenarios described above). Full regression sweep across all
13 pre-existing test files run afterward -- zero unresolved regressions
(one real one was found and fixed during this feature's own build, as
described above).

## Plugins (`plugins.py`) -- a real packaging layer, verified against Claude Code's CURRENT docs, not assumed

Before writing any code, researched Claude Code's actual, currently-documented
plugin format (`code.claude.com/docs/en/plugins`, `plugins-reference`,
`plugin-marketplaces` -- official docs -- plus several independently-published,
current explainers; never `Gitlawb/openclaude`'s leaked `src/`). The real
format: a plugin is a directory with `.claude-plugin/plugin.json` (only `name`
is required) + component folders at the plugin **root**, not inside the
manifest directory (the docs' own most-common-mistake warning); a marketplace
is a separate `marketplace.json` catalog listing plugins and where to fetch
them (local path, GitHub, git URL, npm).

This project mirrors that shape with its own `.agent_*` naming convention:
`.agent_plugins/<name>/.agent_plugin/plugin.json` + `skills/`, `commands/`,
`agents/`, `hooks/hooks.json`, `.mcp.json` at the plugin root, plus a real
`.agent_marketplace.json` catalog.

### A real finding that changed the whole design: commands already exist

Checking Claude Code's OWN current docs before building a "commands" system
turned up: **"Custom commands have been merged into skills. A file at
`.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md`
both create `/deploy` and work the same way."** This project already has a
complete skills implementation (`skills.py`) — so a plugin's `commands/*.md`
files are loaded through the **exact same** `skills.parse_skill_text`/
`scan_skills` machinery, not a second parallel prompt-template parser.

The one genuinely missing capability that check surfaced: checking `main.py`'s
real REPL loop confirmed a human typing at the prompt had **no way to force**
a specific skill/command to run — only the LLM itself could decide to call the
`load_skill` tool. Added real, direct `/name [args]` invocation to `main.py`
(`_try_expand_slash_invocation`), reusing `skills.py`'s existing parse/render
functions, not a new parser. Built-ins (`/exit`, `/quit`, `/reset`, `/memory`)
are checked first and can never be shadowed; the project's own `.agent_skills/`
takes precedence over any plugin's skill/command of the same name (verified
with a real test).

### A real bug found via a headerless command file

A command file can be **plain prompt text with no frontmatter at all** (a real,
documented shape) — synthesized into valid frontmatter from the filename
before parsing. A **second, subtler real shape** was found only by actually
loading this project's own committed example plugin
(`.agent_plugins/git-safety/commands/changelog.md`): a command file can have
**real frontmatter** (`description:`, etc.) but **no `name:` field at all** —
a command's name is *always* the filename, never taken from its own
frontmatter (confirmed from research), unlike a skill. A first draft only
handled the "no frontmatter at all" case and rejected this real, valid file as
malformed — caught by loading the real example, not assumed to work; fixed by
parsing whatever frontmatter exists and overriding just the `name` field
before final parsing.

### Hooks: a narrow, real subset — not the full ~30-event catalog

Claude Code's own documented hook catalog has ~30 events, most with no analog
anywhere in this project's actual architecture (`WorktreeCreate`,
`TeammateIdle`, `Elicitation`, `ConfigChange`, ...). Building handlers for
events that can never fire here would be dead code. Checked `agent.py`'s real
structure first and implemented exactly the 4 events that map onto **already-
existing, already-proven extension points**:

- **`PreToolUse`**: plugs into the real confirm-gate call site in
  `agent._dispatch_tool_call`, checked *before* this project's own
  `_needs_confirmation` — a hook can block a call this project's own
  destructive/sensitive checks would never have flagged at all.
- **`PostToolUse`**: reuses the *exact* "append to the tool-result message
  content" injection point the batching nudge and path-scoped project rules
  already use — not a new mechanism.
- **`SessionStart`** / **`Stop`**: `run_agent()`'s own real entry/exit.

**A real scope decision, stated explicitly rather than left implicit**: Claude
Code's actual `Stop` hook can force the agent to keep going (its
`decision: "block"` re-enters the loop). Implementing genuine loop-continuation
here would mean converting an already-returned final reply back into a fake
tool result and re-entering a ReAct loop this project has deliberately
hardened across several recent features — real risk for a feature explicitly
framed as "a packaging layer, not a new capability." This project's
`Stop`/`SessionStart` hooks are **observational/advisory only**: a
`{"context": "..."}` response is appended as a visible note, but the run
always actually ends — never silently claims a capability it doesn't have.

Hook commands use a real, portable JSON-in/JSON-out contract (one JSON object
on stdin: `{tool_name, tool_args, ...}`; an optional JSON object on stdout to
make a decision) — **fail-open by construction**: a hook that times out,
errors, or prints unparseable output is treated as "no opinion, allow" and
simply skipped, never allowed to block a real call or crash the run. A broken
third-party hook script must never be able to brick the whole agent.

### MCP servers and remote fetch reuse existing infrastructure

A plugin's `.mcp.json` (`mcpServers: {name: {command, args, env}}`, the real
documented shape) registers through `mcp_client.py`'s **already-generic**
`connect_server(name, command, args)` — confirmed directly this function
isn't hardcoded to just the filesystem/fetch servers `connect_all_sync`
happens to call it with; zero new MCP plumbing needed. Remote marketplace
sources (`github`/git URL) are fetched via **GitPython** — already a real,
tested dependency via `git_tools.py`, not a new library. `${CLAUDE_PLUGIN_ROOT}`
and `${CLAUDE_PROJECT_DIR}` placeholder expansion uses the *exact same*
placeholder names Claude Code's own docs use, so a plugin authored against
the real docs works here unmodified for that one mechanic.

### Live verification, not just unit tests

- **Real remote fetch**: a real `.agent_marketplace.json` pointing at
  Anthropic's own public `anthropics/skills` GitHub repo was actually cloned
  (via `git.Repo.clone_from`, no mock) and loaded — **17 real skills** parsed
  with zero warnings through this project's own `skills.py`, plus a re-install
  confirming the cache-then-pull path (not a re-clone) also works for real.
- **Real hook execution**: this project's own committed example plugin
  (`.agent_plugins/git-safety/`) ships a real `PreToolUse` hook script that
  blocks `git push --force` to `main`/`master` specifically — verified it
  actually blocks the dangerous command and allows a feature-branch force-push
  and an ordinary push, via real subprocess execution with real JSON stdin/
  stdout, not a mocked call.
- **Real ReAct-loop wiring**: using the same mocked-LLM harness already
  proven in `test/batching_nudge_test.py` (no real API call, no
  non-determinism), confirmed a `PreToolUse` hook genuinely blocks a tool
  call **inside `agent.run_agent()`'s real loop** (not just in
  `plugins.run_hooks()` isolation), and a `PostToolUse` hook's note appears
  in the real tool-result content.
- **Real end-to-end REPL run**: `python main.py`, typed `/react-component
  build a tiny badge component`, `/exit` — the skill expanded into a real
  task, the agent wrote a real `.tsx` file, self-verified it by reading it
  back, and `/exit` cleanly printed `bye!` — the actual `main.py` process,
  not a test harness calling internals directly.

`.agent_plugins/git-safety/` ships as a real, permanent example (not a scratch
fixture): a `commit-message` skill, a `/changelog` command, and the real
force-push guardrail hook described above. Full test suites:
`test/plugins_test.py` (23 scenarios), `test/plugins_live_test.py` (the real
GitHub clone), `test/main_slash_invocation_test.py` (8 scenarios covering
built-in precedence, real committed skills, plugin skills/commands, and the
project-vs-plugin name-collision precedence rule). Full regression sweep
across all 13 pre-existing test files afterward — zero regressions.

## Session Resume UX (`--resume`/`-r`, `--continue`/`-c`, `--list-missions`, `--print`/`-p`) — a CLI layer over durable state that already existed

This project's real durable state for a long task was already `missions.py`
(built earlier this session): a compact **checkpoint** — summary, next step,
key files — not a raw replayed transcript, deliberately different from Claude
Code's own full-`.jsonl`-transcript session files. What was missing was the
CLI surface real Claude Code exposes to actually use it day to day: `-r`/`-c`
to resume, `--list` to see what's there, `-p`/`--output-format json` for
scripts. Researched Claude Code's actual current flags before building
anything (`-c`/`--continue` = most recent session in this directory,
`-r`/`--resume [id]` = a specific session or an interactive picker, `--print`
+ `--output-format json` for non-interactive scripting) and mapped each onto
this project's own checkpoint-based model rather than trying to fake a
full-transcript replay it was never designed to do.

### A real gap found and closed: `run_mission` couldn't compose with permission modes at all

Checked `agent.run_mission`'s real signature before assuming `--resume`
combined with `--permission-mode` would just work — it didn't: `run_mission`
had **no** `system_prompt`/`tool_functions`/`tool_specs` parameters at all,
unlike `run_agent`, which already has all three (added for sub-agents).
Combining a mode with a resumed mission would have silently ignored the mode
entirely. Fixed by extending `run_mission` to mirror `run_agent`'s own
parameters exactly, and adding `permissions.run_mission_with_mode` as the
mission-scoped mirror of the already-existing `run_agent_with_mode` — same
`PermissionEngine`, never a second, parallel implementation of mode policy.

### What was built

- **`--resume <id>` / `-r <id>`** — scopes the whole interactive REPL session
  to a named mission, loading its saved checkpoint (if any) as context for
  every turn, and saving a fresh checkpoint after each one. Starting a
  mission id that's never been used before is not an error (prints a clear
  "starting new mission" message, matching `missions.load_progress`'s own
  "`None` means first-ever run" semantics).
- **`--continue` / `-c`** — resumes the **most recently updated** mission
  without needing to know its id. Reuses `missions.list_missions()`'s
  existing most-recent-first sort rather than re-deriving it. Exits with a
  clear error if no mission has ever been saved — there is nothing to
  continue, and silently falling back to a fresh session would contradict
  what the flag is asking for.
- **`--list-missions`** — prints every saved mission (id, last updated,
  summary) and exits. No LLM call, no REPL — a pure read of already-saved
  state, matching real Claude Code's own `--list`.
- **`--print <prompt>` / `-p <prompt>`** — non-interactive one-shot mode for
  scripts/CI: runs exactly one prompt to completion and exits, reusing the
  *exact same* `run_agent`/`run_mission`/`run_agent_with_mode`/
  `run_mission_with_mode` call paths the interactive loop uses — not a
  second, parallel execution path that could silently drift out of sync.
  Composes with `--resume`/`--continue` and `--permission-mode`.
- **`--output-format json`** — a single machine-readable JSON object on
  stdout (`{"result": ..., "mission_id": ...}`) instead of plain text.
  Deliberately a small, real subset of Claude Code's own documented JSON
  result shape (which also tracks cost/duration/turn-count fields this
  project doesn't currently record anywhere) — not fabricated just to look
  more complete than it is.
- `--resume`/`-r` and `--continue`/`-c` are mutually exclusive (rejected with
  a clear error, never silently picking one), matching this project's
  standing "never silently guess" posture already established for
  `--permission-mode`'s own error handling.

### A real test-design bug caught by a test written to expose it

An early draft had a **redundant** `if mission_id is None: sys.exit(1)` check
after `_extract_flag_value` (which already exits with a clear message when a
flag has no value) — harmless in real use (`sys.exit` actually stops the
process), but a test mocking `sys.exit` to make it inspectable exposed the
fallthrough: the mocked call let execution continue into the second,
redundant exit call. The same class of bug `_parse_permission_mode`'s own
test suite already caught once before this session. Fixed by removing the
dead, unreachable-in-real-execution check.

### Live verification, not just unit tests

- **A real `--print` one-shot mission run**: `python main.py --print "say
  hello" --resume test-session-resume-demo --permission-mode dont_ask` — real
  LLM call, real checkpoint saved to `.agent_missions/test-session-resume-demo/`.
- **A real `--continue` run** immediately after: correctly resolved to that
  exact mission (the only one that existed), loaded its checkpoint, and the
  model correctly recalled "we said hello" — proving the checkpoint context
  actually reaches the model, not just that a file was written.
- **`--output-format json`** produced real, valid, parseable JSON:
  `{"result": "We said hello to establish a connection.", "mission_id":
  "test-session-resume-demo"}`.
- **`--resume ... --permission-mode plan`**: asked the agent to write a file;
  the model itself explained it was in plan mode and structurally could not
  — verified independently by confirming the file was never created on disk,
  not by trusting the model's own claim.

Full test suite: `test/main_session_resume_test.py` (14 scenarios covering
flag parsing, mutual-exclusion rejection, missing-value handling, most-
recent-mission resolution, empty-state handling, and a mocked-LLM proof that
`--permission-mode plan` genuinely restricts a *resumed mission's* tools, not
just a plain `run_agent` call). Full regression sweep across all 14
pre-existing test files afterward — zero regressions.
