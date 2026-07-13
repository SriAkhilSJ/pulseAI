# PulseAI — Master Engineering Roadmap & Self-Contained AI Tasks
**Senior Engineering & CTO Execution Plan**
*For use with external AI coding agents (Cursor, Claude Code, Windsurf, Codex, Aider)*

---

## Executive CTO Summary & Current State Analysis

Your codebase (`pulseAI`) is a highly disciplined, modular, and lightweight AI-Native IDE engine (~18K lines across ~25 focused Python modules). It already beats multi-gigabyte monolithic competitors in key architectural areas:
- **Verified Multi-Provider Routing** (`llm_client.py` via LiteLLM: Groq, Gemini, Cerebras, OpenRouter with auto-failover).
- **Structural Safety & Undo** (`confirm_bridge.py`, `checkpoint.py`, `permissions.py` with 6 permission modes including `plan` and `dont_ask`).
- **Sub-Agent Delegation** (`subagents.py` implementing `dispatch_agent` with isolated ReAct loops and strict tool allowlists).
- **Codebase Indexing & AST Tools** (`repo_map.py` via Tree-sitter + PageRank, `ast_tools.py`, `rag_indexer.py`).

### Why Split Work into Self-Contained Tasks?
To maintain high velocity without hitting LLM context-window limits or file-count constraints, **every remaining feature is broken down below into bite-sized, self-contained vertical slices**. 

Each task follows your strict project discipline:
```
1. WRITE FAILING TEST FIRST     (RED)
2. RUN TEST → verify it fails   (RED VERIFIED)
3. WRITE MINIMAL CODE           (GREEN)
4. RUN TEST → verify it passes  (GREEN VERIFIED)
5. REFACTOR if needed           (REFACTOR)
6. COMMIT                       (COMMIT)
```

---

## How to Use This Document (For the Vibecoder)

Whenever you open **Claude Code, Cursor, Windsurf, or Codex**, copy-paste **ONE single Task Box (`Task Box X.Y`)** into your chat prompt. Do not combine multiple tasks in one prompt. Let the AI finish the task, run `pytest`, make sure all tests pass, commit, and only then move to the next box!

---

# Phase 1: Codebase Intelligence Auto-Injection & Graph Upgrades (Slice 2 Complete)

### Task Box 1.1: Auto-Inject Repo Map into Initial System Context
**Goal:** Auto-inject a concise, token-budgeted `repo_map` summary into the message history (`_build_messages` in `agent.py`) when a session starts, so the agent never has to ask *"where is file X?"*.

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Auto-Inject Repo Map into Initial System Context
1. Inspect `my-agent/repo_map.py` (specifically `generate_repo_map` or `repo_map_query`) and `my-agent/agent.py` (`_build_messages`).
2. Write a unit test `my-agent/test/repo_map_injection_test.py` that verifies:
   - When `_build_messages` is called with `inject_repo_map=True` (or via a memory/config setting), it calls `repo_map.get_cached_map()` (or `repo_map_query` with `--tokens 1024`) and appends a `{"role": "system", "content": "Codebase Structure Map:\n..."}` block.
   - When `inject_repo_map=False` or if `repo_map` fails/is empty, `_build_messages` falls back gracefully without breaking existing tests.
3. Run the test (`pytest test/repo_map_injection_test.py`) -> Verify it fails (RED).
4. Implement the minimal code in `my-agent/agent.py` inside `_build_messages()`. Add caching so `get_cached_map()` only re-parses when `(path, mtime, size)` changes.
5. Run `pytest test/repo_map_injection_test.py` -> Verify it passes (GREEN).
6. Run full regression unit tests (`pytest test/ -k "not live" --disable-warnings`) to ensure nothing broke.
```

---

### Task Box 1.2: Upgrade Hand-Rolled PageRank to NetworkX (`repo_map.py`)
**Goal:** Upgrade `repo_map._pagerank` from the 50-line hand-rolled linear algebra implementation to `networkx.pagerank` for 10x faster calculation on large repositories (`REPO_MAP_NETWORKX_UPGRADE.md`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Upgrade Repo Map PageRank to NetworkX
1. Read `my-agent/REPO_MAP_NETWORKX_UPGRADE.md` and `my-agent/repo_map.py`.
2. Add `networkx>=3.0` to `my-agent/requirements.txt` cleanly.
3. Write a unit test in `my-agent/test/repo_map_networkx_test.py` that builds a sample directed graph of 5 files where `A.py` is imported by `B.py`, `C.py`, and `D.py`, and verifies that `_pagerank_networkx(graph)` ranks `A.py` highest.
4. Run the test (`pytest test/repo_map_networkx_test.py`) -> Verify RED.
5. In `my-agent/repo_map.py`, implement `_calculate_pagerank(graph)` using `networkx.pagerank(graph, alpha=0.85)` with fallback to the hand-rolled implementation if `networkx` import fails.
6. Run `pytest test/repo_map_networkx_test.py` -> Verify GREEN.
7. Run `pytest test/repo_map_test.py` -> Verify all existing repo map tests pass cleanly!
```

---

# Phase 2: Token Streaming & Terminal UI (Slice 3)

### Task Box 2.1: Real-Time Token Streaming Generator in `llm_client.py` & `agent.py`
**Goal:** Enable real-time LLM token streaming (`stream=True`) so user sees partial tokens immediately rather than waiting 10–30s for blocking responses.

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Implement Token Streaming Generator in `agent.py`
1. Inspect `my-agent/llm_client.py` (`completion` wrapper around `litellm.completion`) and `my-agent/agent.py` (`_run_tool_calls` and `run_agent`).
2. Write a failing unit test `my-agent/test/agent_token_streaming_test.py` that mocks `llm_client.completion(..., stream=True)` to yield chunks (`{"choices": [{"delta": {"content": "Hello "}}]}`) and checks that a new generator function `run_agent_stream(...)` yields `("token", "Hello ")` events cleanly as they arrive.
3. Run `pytest test/agent_token_streaming_test.py` -> Verify RED.
4. Add `run_agent_stream(user_input, mem, ...)` in `agent.py` (or add a `stream_tokens=True` flag to `run_agent`) that requests `stream=True` from `llm_client.completion`, yields `("token", delta_str)` tuples in real time, and buffers the full response string to process tool calls (`_sanitize_tool_calls`) after completion.
5. Run `pytest test/agent_token_streaming_test.py` -> Verify GREEN.
6. Run existing tests (`pytest test/ -k "not live" --disable-warnings`) to ensure blocking `run_agent` still works 100% unchanged.
```

---

### Task Box 2.2: Rich / Ink Terminal UI (`tui.py`) with Live Status Bar
**Goal:** Create a polished, interactive Terminal UI (`my-agent/tui.py`) using `rich` / `prompt_toolkit` featuring live streaming output, active tool indicators, and a status bar (`Model | Permission Mode | Token Budget`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Build Rich Terminal UI (`tui.py`) for Pulse Agent
1. Add `rich>=13.0.0` and `prompt_toolkit>=3.0.0` to `my-agent/requirements.txt`.
2. Write a unit test `my-agent/test/tui_render_test.py` that initializes a `TerminalUI` controller with dummy state (`model="llama-3-70b"`, `mode="plan"`, `tokens=1420`) and verifies that `format_status_bar()` produces the exact expected formatted string without ANSI escape errors.
3. Run `pytest test/tui_render_test.py` -> Verify RED.
4. Create `my-agent/tui.py` implementing `class PulseTUI`:
   - `render_status_bar(model, permission_mode, active_mission)`
   - `stream_token(token_text)`: prints chunks with smooth Rich Live layout.
   - `render_tool_call(tool_name, args, status)`: shows a spinning indicator or green check box `[✓] Ran read_file(main.py)`.
5. Run `pytest test/tui_render_test.py` -> Verify GREEN.
6. Add a CLI flag `--tui` to `main.py` that launches `tui.py` instead of the raw `input()` REPL when invoked (`python main.py --tui`).
```

---

# Phase 3: Inline Tab Completions Engine — GhostText (Slice 4)

### Task Box 3.1: FIM (Fill-In-The-Middle) Code Completion Engine (`completions.py`)
**Goal:** Build the core engine that predicts next edits/insertions based on cursor position (`<PRE>...prefix...<SUF>...suffix...<MID>`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Implement FIM Tab Completion Engine (`completions.py`)
1. Create `my-agent/test/completions_test.py`. Write unit tests covering:
   - `build_fim_prompt(file_content, cursor_offset)`: splits code into `<PRE>` prefix and `<SUF>` suffix within a 1500-token window.
   - `predict_inline_completion(file_path, file_content, cursor_offset, llm_client)`: sends the FIM prompt to a low-latency model (e.g. `qwen-2.5-coder` or `deepseek-coder` via LiteLLM) and extracts the clean `<MID>` completed string.
   - Multi-line indentation trimming: strips unwanted trailing markdown or repetition from the completion.
2. Run `pytest test/completions_test.py` -> Verify RED.
3. Implement `my-agent/completions.py` with `build_fim_prompt()`, `predict_inline_completion()`, and `cache_completion(key, result)` (LRU cache to avoid re-querying the same keystrokes within 2 seconds).
4. Run `pytest test/completions_test.py` -> Verify GREEN.
```

---

### Task Box 3.2: Expose Tab Completion via Bridge Server & VS Code Extension
**Goal:** Connect `completions.py` to `bridge_server.py` and implement an `InlineCompletionItemProvider` in `vscode-extension/src/extension.ts`.

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Wire Inline Tab Completions into VS Code Extension Host
1. In `my-agent/test/bridge_server_test.py`, add a test verifying that sending `{"id": 1, "method": "complete", "params": {"path": "test.py", "content": "def add(a, b):\n    ", "offset": 19}}` via stdio returns `{"id": 1, "result": {"completion": "return a + b"}}`.
2. Run `pytest test/bridge_server_test.py` -> Verify RED.
3. In `my-agent/bridge_server.py`, add the `"complete"` method handler calling `completions.predict_inline_completion()`.
4. Run `pytest test/bridge_server_test.py` -> Verify GREEN.
5. In `my-agent/vscode-extension/src/extension.ts`, register `vscode.languages.registerInlineCompletionItemProvider({ pattern: '**/*' }, { ... })` that debounces keystrokes (200ms), sends `method: "complete"` to `bridge_server.py`, and returns `new vscode.InlineCompletionItem(completionText)`.
```

---

# Phase 4: Context Compression & Cross-Session FTS5 Memory (Slice 5)

### Task Box 4.1: Auto-Context Compression (`context_compressor.py`)
**Goal:** Automatically summarize and compact old conversation turns when the session approaches context window capacity (`>80% limit`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Auto-Context Compression for Long Sessions
1. Create `my-agent/test/context_compressor_test.py`. Write unit tests verifying:
   - `estimate_message_tokens(messages)`: accurately estimates token counts using character ratio (~4 chars per token).
   - `should_compress(messages, max_tokens=128000, threshold_ratio=0.8)`: returns `True` only when `estimate_message_tokens` exceeds 102,400 tokens.
   - `compress_message_history(messages, keep_recent_turns=6, summarizer_fn)`: retains the `system` prompt + the last 6 turns, and replaces all older turns with a single summary message `{"role": "system", "content": "Compacted History Summary:\n..."}`.
2. Run `pytest test/context_compressor_test.py` -> Verify RED.
3. Create `my-agent/context_compressor.py` implementing these functions.
4. Run `pytest test/context_compressor_test.py` -> Verify GREEN.
5. Integrate `compress_message_history` into `agent.py` inside `run_agent()` before `llm_client.completion()` is called!
```

---

### Task Box 4.2: FTS5 Cross-Session Memory Search (`fts_memory.py`)
**Goal:** Replace flat JSON memory lookup with SQLite full-text search (`FTS5`) so the agent can instantly find historical notes and decisions across past sessions ("What did we decide about auth last week?").

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: FTS5 SQLite Cross-Session Memory Engine
1. Create `my-agent/test/fts_memory_test.py`. Write unit tests verifying:
   - `init_fts_db(db_path)`: initializes SQLite database with virtual table `memory_fts USING fts5(session_id, timestamp, topic, content)`.
   - `store_memory(db_path, session_id, topic, content)`: inserts records and commits cleanly.
   - `search_memory(db_path, query_text, limit=5)`: performs FTS5 `MATCH` queries and returns relevant historical records with scores.
2. Run `pytest test/fts_memory_test.py` -> Verify RED.
3. Create `my-agent/fts_memory.py` using Python's built-in `sqlite3` module. Implement `init_fts_db()`, `store_memory()`, and `search_memory()`.
4. Run `pytest test/fts_memory_test.py` -> Verify GREEN.
5. Register a new tool `memory_search` inside `my-agent/tools.py` so the agent can invoke FTS5 search anytime during a coding task!
```

---

# Phase 5: Packaging, Daemon Mode, & Complete VS Code Fork Integration (Slice 1 & 6)

### Task Box 5.1: Persistent Background Gateway (`daemon.py`)
**Goal:** Create a background daemon/server that holds active agent sessions and allows multiple terminal windows or IDE instances to attach/detach (`python main.py --daemon`, `--attach <id>`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Persistent Background Daemon (`daemon.py`)
1. Create `my-agent/test/daemon_test.py`. Write unit tests verifying:
   - `DaemonServer(socket_path)` starts a local Unix domain socket (or localhost TCP loopback on Windows) and handles concurrent client connections.
   - Sending `{"action": "start_session", "mode": "plan"}` returns a unique `session_id`.
   - Sending `{"action": "send_prompt", "session_id": id, "prompt": "list files"}` processes in background and streams results back.
2. Run `pytest test/daemon_test.py` -> Verify RED.
3. Implement `my-agent/daemon.py` using `asyncio` (`asyncio.start_unix_server` / `start_server`).
4. Run `pytest test/daemon_test.py` -> Verify GREEN.
5. Add CLI flags `--daemon-start`, `--daemon-stop`, and `--attach <session_id>` to `main.py`.
```

---

### Task Box 5.2: One-Command NPM/Python Installer (`setup.py` + CLI Entrypoint)
**Goal:** Pack up `my-agent/` so any developer can install Pulse AI via `pip install -e .` (or `npm install -g @pulseai/cli`) and immediately run `pulse` from any folder.

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/`. 
Strictly follow our TDD workflow (RED -> GREEN -> REFACTOR).

### Task: Standard Package Setup & `pulse` CLI Entrypoint
1. Create `my-agent/pyproject.toml` and `my-agent/setup.py` defining package name `pulse-ai`, version `0.1.0`, dependencies from `requirements.txt`, and console scripts entrypoint `[project.scripts] pulse = "main:cli_main"`.
2. In `my-agent/main.py`, create a `cli_main()` entrypoint wrapper around `sys.argv` handling that returns exit codes cleanly (`sys.exit(cli_main())`).
3. Write a test `my-agent/test/package_cli_test.py` checking that invoking `cli_main(["--help"])` or `cli_main(["--list-missions"])` works without errors.
4. Run `pytest test/package_cli_test.py` -> Verify GREEN.
```

---

### Task Box 5.3: Wire VS Code Extension into `D:\vscodesfresh\` as Default Chat Participant
**Goal:** Package the VS Code extension (`vsce package`) and wire it as the built-in `@pulse` chat participant inside your custom VS Code OSS fork (`D:\vscodesfresh\`).

📋 **Copy-Paste Prompt for your AI Tool:**
```markdown
You are a senior software engineer working on `my-agent/vscode-extension/`. 

### Task: Package Extension & Wire into VS Code OSS Fork
1. In `my-agent/vscode-extension/package.json`, verify that `contributes.chatParticipants` registers `@pulse` (`{"id": "pulse.agent", "name": "pulse", "description": "Pulse AI Autonomous Agent", "isDefault": true}`).
2. In `src/extension.ts`, implement `vscode.chat.createChatParticipant('pulse.agent', async (request, context, response, token) => { ... })` that sends user requests over `bridgeProcess` to `bridge_server.py` and streams token deltas using `response.markdown(tokenText)`.
3. Build and package the `.vsix`:
   ```bash
   cd my-agent/vscode-extension
   npm install && npm run compile
   npx vsce package --out pulse-ai.vsix
   ```
4. Install `pulse-ai.vsix` into your custom VS Code OSS fork (`D:\vscodesfresh\`) and verify that `@pulse write hello.py` streams live tokens right in the editor sidebar!
```

---

## Technical Verification & Quality Checklist (CTO Sign-Off)
Before considering any task complete, check this matrix:
- [ ] Did `pytest test/` pass with zero regressions across pre-existing tests?
- [ ] Did you avoid hardcoding API keys or sensitive local paths?
- [ ] Are all new tools properly registered inside `TOOLS_FUNCTIONS` in `tools.py`?
- [ ] Is confirmation gating (`confirm_bridge.py`) respected for any destructive action (file writes, shell commands)?
