# PulseCodeAI — Master PaperclipAI Architecture & 20-Ticket Execution Plan
**CTO & Senior Architectural Blueprint for an AI-First IDE**
*Designed for step-by-step autonomous execution with PaperclipAI, Cursor, Windsurf, or Claude Code*

---

## 🏛️ CTO Architectural Endorsement & Strategy

You are 100% right on the money. As the CTO of cutting-edge AI IDEs, I can confirm: **attempting to build an entire AI-first IDE in a single prompt or monolithic script guarantees failure due to context bloat, hallucination, and tight coupling.** 

By splitting **PulseCodeAI** into **five distinct foundational systems** inside a clean **Monorepo (`apps/` + `packages/`)**, and assigning **one hyper-focused ticket at a time** to PaperclipAI, you achieve what multi-million dollar engineering teams do: **strict modularity, clear interface boundaries, and verifiable testing at every tier.**

### How Your Current Code (`my-agent/`) Maps to the New Monorepo
You do **not** need to throw out your existing verified 18K-line core. Here is exactly how your existing assets transition into the `PulseCodeAI` enterprise monorepo:

```
PulseCodeAI/
├── apps/
│   └── desktop/                  # Phase 1 & 5: VS Code OSS Fork (your D:\vscodesfresh\) + AI Sidebar UI
├── packages/
│   ├── ai-core/                  # Phase 2: AI Core Foundation
│   │   ├── models/               # Migrated from my-agent/llm_client.py (LiteLLM router + failover)
│   │   ├── context/              # Migrated & upgraded from my-agent/repo_map.py + context_compressor
│   │   ├── prompt/               # Migrated from my-agent/rules.py + AGENTS.md loader
│   │   └── memory/               # Migrated & upgraded from my-agent/memory.py -> fts_memory.py
│   ├── agent-runtime/            # Phase 3: Multi-Agent Framework
│   │   ├── orchestrator/         # Migrated & upgraded from my-agent/missions.py + subagents.py
│   │   └── roles/                # Planner, Architect, Coder, Reviewer, Tester, Debugger, Fixer, Docs
│   ├── tools/                    # Phase 4: Sandboxed Tool System
│   │   ├── filesystem/           # Migrated from my-agent/tools.py filesystem_* tools
│   │   ├── terminal/             # Migrated from my-agent/tools.py run_command + confirm_bridge.py
│   │   ├── git/                  # Migrated from my-agent/git_tools.py
│   │   ├── browser/              # Migrated from my-agent/tools_browser.py (Playwright)
│   │   └── lsp/                  # Migrated from my-agent/tools_lsp.py + completions.py
│   └── ui-components/            # Shared React / Webview components (chat, timeline, status bar)
└── services/
    └── bridge-server/            # Migrated from my-agent/bridge_server.py (IPC/gRPC/Stdio Gateway)
```

---

## 📋 The 20-Ticket PaperclipAI Master Execution Deck

Whenever you launch **PaperclipAI** (or any agentic IDE tool), feed it **exactly ONE Ticket Box at a time**. Do not combine them. Let PaperclipAI build the package, run the verification tests, ensure zero regressions, and commit before moving to the next ticket.

---

### Phase 1: VS Code OSS Fork & Foundation (Tickets 1–3)

#### Ticket 1: VS Code OSS Fork & Core Build Pipeline (`apps/desktop`)
```markdown
### PaperclipAI Task: Ticket 1 — VS Code OSS Fork & Build Scaffolding
**Goal:** Establish a clean, buildable fork of VS Code OSS inside `apps/desktop/` with automated build checks and zero custom branding yet.

**Target Directory:** `apps/desktop/` (or linking local `D:\vscodesfresh\`)
**Prerequisites:** Node.js 20+, Yarn/npm, Git.

**Detailed Specifications:**
1. Initialize monorepo workspace configuration (`package.json`, `pnpm-workspace.yaml` or `lerna.json`).
2. Set up `apps/desktop/` containing the VS Code OSS source tree.
3. Verify `yarn/npm run compile` and `yarn run watch` execute cleanly without compilation errors.
4. Remove default telemetry / tracking endpoints from the OSS build scripts (`product.json`).
5. Ensure local launch configuration (`launch.json`) allows running the unbranded IDE instance cleanly in development mode (`F5`).

**Acceptance Criteria / Verification Plan:**
- Running the build script produces a functional, runnable VS Code OSS binary.
- All baseline unit tests (`yarn test:unit`) pass without modification errors.
```

---

#### Ticket 2: Rebranding & Customization Engine (`apps/desktop/product.json`)
```markdown
### PaperclipAI Task: Ticket 2 — Rebranding, Icons, & Open VSX Configuration
**Goal:** Transform the generic VS Code OSS appearance into the branded **PulseCodeAI** IDE and switch the marketplace to Open VSX.

**Target Directory:** `apps/desktop/`
**Prerequisites:** Ticket 1 completed cleanly.

**Detailed Specifications:**
1. Edit `product.json`:
   - Set `"nameShort": "PulseCodeAI"`, `"nameLong": "PulseCodeAI IDE"`.
   - Set `"applicationName": "pulsecodeai"`, `"dataFolderName": ".pulsecodeai"`.
2. Configure Open VSX extension marketplace endpoints inside `product.json`:
   - `"extensionsGallery": { "serviceUrl": "https://open-vsx.org/vscode/gallery", "itemUrl": "https://open-vsx.org/vscode/item" }`.
3. Replace application icon assets (`resources/win32/code.ico`, `resources/darwin/code.icns`, `resources/linux/code.png`) with PulseCodeAI vector/PNG icons.
4. Modify custom onboarding splash screen and default settings (`settings.json` defaults) to pre-configure clean editor typography and AI theme defaults.

**Acceptance Criteria / Verification Plan:**
- Launching the application displays "PulseCodeAI" in the window title bar, macOS/Linux menu bar, and about dialog.
- Extension search drawer connects to Open VSX and successfully searches public extensions.
```

---

#### Ticket 3: AI Sidebar Webview Scaffolding & Chat UI Shell (`apps/desktop/src/vs/pulse/ui`)
```markdown
### PaperclipAI Task: Ticket 3 — AI Sidebar Webview Scaffolding & Chat Shell
**Goal:** Create the dedicated PulseCodeAI Sidebar View (`@pulse`) inside the editor layout with a modern React/HTML chat shell before connecting backend logic.

**Target Directory:** `apps/desktop/src/vs/pulse/` or `packages/ui-components/`
**Prerequisites:** Ticket 2 completed cleanly.

**Detailed Specifications:**
1. Register a new View Container (`pulse.sidebar.view`) inside the VS Code Activity Bar with the PulseCodeAI spark icon.
2. Build a high-performance Webview Panel containing:
   - **Chat Input Container:** Multi-line textarea supporting `@` symbol reference dropdowns (`@file`, `@folder`, `@codebase`) and `/` command completions (`/explain`, `/refactor`, `/test`).
   - **Message Timeline:** Scrolling view supporting Markdown rendering, syntax-highlighted code blocks with 1-click "Apply to Editor" and "Copy" buttons.
   - **Status Bar Indicator:** Small pill indicator showing `Active Model (Groq/Claude/DeepSeek) | Mode (Plan/Normal) | Tokens`.
3. Establish clean message-passing bridge (`webview.postMessage` / `onDidReceiveMessage`) to the extension host/backend gateway.

**Acceptance Criteria / Verification Plan:**
- Clicking the Pulse Activity Bar icon opens the sidebar cleanly.
- Typing dummy text and pressing Enter renders a formatted user message and a simulated streaming response without UI freeze.
```

---

### Phase 2: AI Core Foundation (Tickets 4–7)

#### Ticket 4: AI Core — Multi-Provider Model Manager (`packages/ai-core/models`)
```markdown
### PaperclipAI Task: Ticket 4 — Multi-Provider Model Manager (`ModelManager`)
**Goal:** Build a robust model abstraction layer inside `packages/ai-core/models/` supporting OpenAI, Anthropic, Gemini, Groq, Cerebras, Ollama, and OpenRouter with automatic failover and rate-limit handling.

**Target Directory:** `packages/ai-core/models/` (Migrating logic from `llm_client.py`)
**Prerequisites:** Python 3.11+ / TypeScript (`litellm` or `ai-sdk` equivalent).

**Detailed Specifications:**
1. Implement `class ModelManager` with standardized interface:
   - `async streamCompletion(messages, modelConfig, tools?): AsyncGenerator<TokenDelta>`
   - `async complete(messages, modelConfig, tools?): Promise<CompletionResult>`
2. Implement **Automatic Failover Circuit Breaker**: if primary provider (`e.g., Anthropic / Groq`) throws `RateLimitError` or `503 Service Unavailable`, automatically retry the request on the fallback provider (`e.g., OpenRouter / Gemini`) within 2 seconds without crashing the user session.
3. Build token counting utility (`TokenManager`) accurately calculating exact prompt and completion costs per provider using model tokenizer definitions.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_model_manager_failover.py`: Mock primary API returning `429 Too Many Requests` and verify `ModelManager` seamlessly intercepts and completes via secondary fallback provider.
- Unit test verifying accurate token counts (`test_token_calculator.py`).
```

---

#### Ticket 5: AI Core — Context Manager (`packages/ai-core/context`)
```markdown
### PaperclipAI Task: Ticket 5 — Workspace Context Manager (`ContextManager`)
**Goal:** Build the contextual engine that reads workspace structure, builds Tree-sitter + PageRank dependency graphs, tracks active editor tabs, and compresses history when near token limits.

**Target Directory:** `packages/ai-core/context/` (Migrating `repo_map.py` & `context_compressor.py`)
**Prerequisites:** Ticket 4 completed (`ModelManager` & `TokenManager` available).

**Detailed Specifications:**
1. Implement `class ContextManager`:
   - `getWorkspaceMap(tokenBudget: number): Promise<string>` — returns top-down structural AST definitions ranked by importance (`PageRank`).
   - `getActiveEditorContext(): Promise<EditorContext>` — returns current open file, cursor selection offset, and visible viewport lines.
   - `resolveFileReferences(symbols: string[]): Promise<FileChunk[]>` — fetches exact code definitions for `@file` or `@symbol` mentions.
2. Implement **Auto-Context Compression Engine (`ContextCompressor`)**:
   - When total conversation history exceeds `0.8 * maxTokenLimit`, retain the system prompt + last 6 turns, and summarize all intermediate turns into a structured `{"role": "system", "content": "Compacted Summary: ..."}` block using a fast/cheap model (`haiku / llama-3-8b`).

**Acceptance Criteria / Verification Plan:**
- Unit test `test_context_compression.py`: Feed 150,000 tokens of mock chat history into `ContextCompressor.compressIfNeeded()`, verifying output is reduced under 30,000 tokens while preserving critical file modification decisions.
- Unit test `test_workspace_map_caching.py`: Verify AST parsing caches results by `(path, mtime, size)` and responds in <50ms when files are unchanged.
```

---

#### Ticket 6: AI Core — Prompt Manager (`packages/ai-core/prompt`)
```markdown
### PaperclipAI Task: Ticket 6 — Dynamic Prompt & Rule Manager (`PromptManager`)
**Goal:** Build the prompt assembly layer that dynamically constructs system prompts, injects custom `.pulsecode/rules.md` project rules, formats tool JSON schemas, and enforces safety boundaries.

**Target Directory:** `packages/ai-core/prompt/` (Migrating `rules.py` & `AGENTS.md`)
**Prerequisites:** Ticket 5 completed (`ContextManager`).

**Detailed Specifications:**
1. Implement `class PromptManager`:
   - `buildSystemPrompt(role: AgentRole, workspacePath: string, activeTools: ToolSpec[]): Promise<string>`
2. Implement **Dynamic Rule Loader**:
   - Auto-detect and parse `.pulsecode/rules.md`, `AGENTS.md`, and `.cursorrules` in the root workspace folder.
   - Extract frontmatter and Markdown instructions, injecting them under `### Custom Project Rules`.
3. Implement **Role-Specific Prompt Templates**:
   - `Planner`: Focus on architectural breakdown, strict read-only tool access.
   - `Coder`: Focus on clean diff generation, TDD adherence (`RED -> GREEN -> REFACTOR`).
   - `Reviewer`: Focus on security vulnerabilities, edge cases, memory leaks.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_prompt_assembly.py`: Verify that if a workspace contains `.pulsecode/rules.md` with `"Always use TypeScript strict mode"`, the generated `system_prompt` explicitly contains that exact text under `Custom Project Rules`.
- Unit test verifying tool definitions are cleanly injected into function-calling schema formats.
```

---

#### Ticket 7: AI Core — Cross-Session FTS5 Conversation Memory (`packages/ai-core/memory`)
```markdown
### PaperclipAI Task: Ticket 7 — SQLite FTS5 Conversation Memory Engine (`ConversationMemory`)
**Goal:** Build a persistent SQLite Full-Text Search (`FTS5`) memory storage system so agents and users can recall decisions, bugs, and historical context across sessions (`"What did we decide about database pooling last week?"`).

**Target Directory:** `packages/ai-core/memory/` (Migrating & upgrading `memory.py`)
**Prerequisites:** Ticket 4 & 6 completed.

**Detailed Specifications:**
1. Implement `class ConversationMemory` backed by `SQLite3` (or `sql.js` / `better-sqlite3`):
   - Initialize tables: `sessions(id, timestamp, title, summary)` and `turns_fts USING fts5(session_id, role, content, tags)`.
   - `async recordTurn(sessionId: str, role: str, content: str, tags?: str[]): Promise<void>`
   - `async searchHistory(queryText: str, limit: number = 5): Promise<MemorySearchResult[]>`
2. Implement **Auto-Memory Tagging & Extraction**:
   - At the end of a long task/mission, run an extraction pass (`extractNotes()`) saving high-level architectural notes (e.g., `["auth: migrated to JWT", "db: using connection pool of 20"]`) into a dedicated `project_notes` table.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_fts_search.py`: Insert 20 mock conversations across different session dates. Run `searchHistory("JWT authentication")` and verify only exact relevant turns are returned with high match scores in <15ms.
```

---

### Phase 3: Sandboxed Tool System (Tickets 8–11)

#### Ticket 8: Tool System — Base Registry & Filesystem Tool (`packages/tools/filesystem`)
```markdown
### PaperclipAI Task: Ticket 8 — Base Tool Registry & Secure Filesystem Tools
**Goal:** Establish the foundational tool execution interface (`BaseTool` & `ToolRegistry`) and implement secure, high-performance filesystem read/write/diff operations with hard workspace boundary checks.

**Target Directory:** `packages/tools/filesystem/` (Migrating `tools.py` & `apply_edit`)
**Prerequisites:** Ticket 7 completed (`packages/ai-core/` functional).

**Detailed Specifications:**
1. Define universal tool schema:
   ```typescript
   interface BaseTool {
     name: string;
     description: string;
     parameters: JSONSchema;
     isMutating: boolean;
     execute(args: Record<string, any>, context: ExecutionContext): Promise<ToolResult>;
   }
   ```
2. Implement `ToolRegistry`: registers tools, validates inputs against JSONSchema before calling `execute()`, and returns structured `{ status: "success" | "error", output: string }`.
3. Implement core filesystem tools:
   - `filesystem_read_file(path, startLine?, endLine?)`: reads file with line-number indexing.
   - `filesystem_write_file(path, content)`: overwrites or creates file (`isMutating = true`).
   - `apply_edit(path, old_text, new_text)`: fuzzy/exact string replacement (`isMutating = true`).
4. Implement **Security Sandbox Guard (`PathGuard`)**:
   - Reject outright (`PathTraversalError`) any attempt to access files outside the `workspaceRoot` or sensitive files (`.env`, `id_rsa`, `.git/credentials`).

**Acceptance Criteria / Verification Plan:**
- Unit test `test_path_guard.py`: Attempt `filesystem_read_file("../../etc/passwd")` and `filesystem_read_file(".env")`; verify both immediately throw `SecurityViolationError`.
- Unit test `test_apply_edit.py`: Verify `apply_edit` successfully replaces target lines and returns a clean unified git diff string of the change.
```

---

#### Ticket 9: Tool System — Terminal Tool & Confirmation Gate (`packages/tools/terminal`)
```markdown
### PaperclipAI Task: Ticket 9 — Terminal Tool & User Confirmation Gate (`confirm_bridge`)
**Goal:** Build sandboxed terminal/shell execution (`run_command`) with mandatory destructive action interception (`confirm_bridge`) that prompts the user for approval before running risky commands (`rm`, `git reset`, `npm publish`).

**Target Directory:** `packages/tools/terminal/` (Migrating `run_command` & `confirm_bridge.py`)
**Prerequisites:** Ticket 8 completed (`ToolRegistry`).

**Detailed Specifications:**
1. Implement `run_command(command: str, cwd?: str, timeoutSecs: number = 60)` tool:
   - Spawns child process, captures stdout and stderr via streaming buffers.
   - Kills process cleanly if `timeoutSecs` is exceeded (`TimeoutError`).
2. Implement **Destructive Action Confirmation Gate (`ConfirmationBridge`)**:
   - Inspect command syntax before execution against regex deny/warn lists (`rm -rf`, `git push --force`, `drop database`, `kill -9`).
   - If `isMutating` or destructive, pause execution and emit `ConfirmationRequestEvent(command, reason)` to the UI Sidebar webview.
   - Resume execution ONLY when `web_view_confirm(requestId) === true`; otherwise throw `UserAbortedError`.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_terminal_timeout.py`: Execute `run_command("sleep 10", timeoutSecs=1)` and verify process is terminated after 1 second with clean timeout output.
- Unit test `test_confirmation_gate.py`: Execute `run_command("rm -rf node_modules")` in `normal` mode and verify execution blocks pending confirmation callback.
```

---

#### Ticket 10: Tool System — Git & Codebase Search Tools (`packages/tools/git`)
```markdown
### PaperclipAI Task: Ticket 10 — Git Operations & High-Speed Codebase Search Tools
**Goal:** Equip agents with direct Git control (`status`, `diff`, `commit`, `branch`) and high-speed multi-file search (`grep_files`, `find_files`) using `ripgrep` (`rg`) architecture.

**Target Directory:** `packages/tools/git/` & `packages/tools/search/`
**Prerequisites:** Ticket 8 completed (`ToolRegistry`).

**Detailed Specifications:**
1. Implement Git tools (`GitTools` using `GitPython` or `simple-git`):
   - `git_status()`: returns clean list of staged/unstaged/untracked files.
   - `git_diff(file_path?)`: returns exact line-by-line diffs of pending edits.
   - `git_commit(message)`: stages modified files and commits (`isMutating = true`).
   - `git_create_branch(branch_name)`: creates and checks out new feature branch (`isMutating = true`).
2. Implement High-Speed Search tools:
   - `grep_files(query: str, path_pattern?: str)`: executes fast regex search across workspace using `ripgrep` engine (falling back to Python/Node regex walker). Returns matching file paths and snippet context lines.
   - `find_files(name_pattern: str)`: fuzzy file finder matching `*Controller.ts` across directories.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_git_tools.py`: Initialize temporary git repo, modify a file, verify `git_status()` lists the file, and `git_commit("test commit")` commits cleanly.
- Unit test `test_grep_files.py`: Search for a known function name across 500 files and verify exact line numbers are returned in <100ms.
```

---

#### Ticket 11: Tool System — LSP, AST, & Browser Automation Tools (`packages/tools/lsp`)
```markdown
### PaperclipAI Task: Ticket 11 — Language Server Protocol (LSP) & Playwright Browser Tools
**Goal:** Enable deep code intelligence via LSP (`find_references`, `get_diagnostics`, `rename_symbol`) and visual web verification via headless browser (`browser_screenshot`, `evaluate_js`).

**Target Directory:** `packages/tools/lsp/` & `packages/tools/browser/`
**Prerequisites:** Ticket 8 completed.

**Detailed Specifications:**
1. Implement LSP Client tools (`LSPTools` connecting via `python-lsp-server` / `typescript-language-server`):
   - `lsp_get_diagnostics(file_path)`: returns live compiler/linter errors (`[{"line": 12, "severity": "error", "message": "Cannot find name 'foo'"}]`).
   - `lsp_find_references(file_path, line, character)`: returns every cross-file usage of a symbol.
   - `lsp_preview_rename(file_path, line, character, new_name)`: returns workspace-wide diff of renaming a variable/class.
2. Implement Playwright Browser tools (`BrowserTools` migrating `tools_browser.py`):
   - `browser_open_url(url)`: navigates headless Chromium instance to URL.
   - `browser_screenshot(url, selector?)`: captures PNG screenshot and returns base64 string for vision-LLM verification.
   - `browser_evaluate_js(script)`: executes JS inside page DOM to check console errors or UI state.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_lsp_diagnostics.py`: Create a TS file with deliberate syntax error (`const x: int = "hi";`), run `lsp_get_diagnostics()`, and verify exact line and compiler error code (`TS2322`) are returned.
- Unit test `test_browser_screenshot.py`: Verify Playwright opens local test HTML and returns a valid PNG image buffer.
```

---

### Phase 4: Multi-Agent Framework & Specialized Roles (Tickets 12–16)

#### Ticket 12: Multi-Agent Framework — Core Orchestrator & Task Dispatcher (`packages/agent-runtime/orchestrator`)
```markdown
### PaperclipAI Task: Ticket 12 — Multi-Agent Orchestrator & Sub-Agent Dispatcher
**Goal:** Build the core execution engine that runs isolated ReAct agent loops (`run_agent`), manages long-running mission checkpoints (`MissionManager`), and enforces strict sub-agent tool restrictions (`dispatch_agent`).

**Target Directory:** `packages/agent-runtime/orchestrator/` (Migrating `agent.py`, `missions.py`, `subagents.py`)
**Prerequisites:** Tickets 4–11 completed (`ai-core` & `tools` available).

**Detailed Specifications:**
1. Implement `AgentOrchestrator`:
   - `runAgentLoop(prompt, role, allowedTools, permissionMode, missionId?): AsyncGenerator<AgentEvent>`
   - ReAct cycle: `Assemble Prompt -> Call Model -> Parse Tool Calls -> Check Permissions/Confirm Gate -> Execute Tools -> Append Observation -> Repeat` (capped at `maxTurns = 30`).
2. Implement `MissionManager` (checkpointing):
   - `saveCheckpoint(missionId, state)`: persists conversation history, diff state, and current goal to `.pulsecode/missions/<id>/checkpoint.json` before every tool write.
   - `resumeMission(missionId)`: cleanly restores context after IDE restart or crash.
3. Implement `dispatch_agent` tool:
   - Allows parent agent to delegate a sub-task to a specialized sub-agent (`subagent_type: "Explore" | "Review"`).
   - **Enforced Tool Allowlist:** If an `Explore` sub-agent is dispatched, its `allowedTools` dict structurally excludes `filesystem_write_file` and `run_command`.
   - Returns exactly **ONE final summary message** back to the parent agent, preventing token pollution from intermediate tool turns.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_subagent_tool_isolation.py`: Dispatch an `Explore` sub-agent with prompt `"Write hello.py"`. Verify `runAgentLoop` intercepts any `filesystem_write_file` tool call with `"ERROR: unknown tool 'filesystem_write_file'"` and returns read-only summary.
- Unit test `test_mission_checkpoint_recovery.py`: Simulate crash mid-execution (`turn 5`), verify `resumeMission()` reloads exact turn state without re-running completed steps.
```

---

#### Ticket 13: Specialized Agents — Planner & Architect Agents (`packages/agent-runtime/roles/planner`)
```markdown
### PaperclipAI Task: Ticket 13 — Planner & Architect Agents
**Goal:** Implement the specialized read-only architectural agents (`PlannerAgent` & `ArchitectAgent`) responsible for analyzing codebases, breaking high-level user requests into concrete execution steps, and proposing unified plans.

**Target Directory:** `packages/agent-runtime/roles/`
**Prerequisites:** Ticket 12 completed (`AgentOrchestrator`).

**Detailed Specifications:**
1. Implement `PlannerAgent` configuration:
   - **Allowed Tools:** `grep_files`, `find_files`, `filesystem_read_file`, `repo_map_query`, `memory_search`.
   - **System Prompt Focus:** "You are the Principal Systems Architect. Do NOT write code. Read existing files, analyze data structures, check cross-file imports, and produce a numbered, step-by-step Implementation Plan (`PLAN.md`). Identify edge cases, required tool calls, and testing strategies."
2. Implement `PlanApprovalMode`:
   - When user invokes `@pulse /plan <feature>`, `PlannerAgent` generates `PlanSpec(steps: PlanStep[])`.
   - The orchestrator suspends execution and presents the visual Plan Checklist in the UI Sidebar.
   - No mutating tools (`CoderAgent`) can be invoked until user clicks `[Approve Implementation Plan]`.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_planner_read_only.py`: Verify `PlannerAgent` structurally cannot access `filesystem_write_file` or `git_commit`.
- Unit test `test_plan_generation.py`: Feed a complex feature request (`"Add Stripe webhook handling"`); verify output matches strict `PlanSpec` JSON schema with clear file-path step breakdown.
```

---

#### Ticket 14: Specialized Agents — Coder & Reviewer Agents (`packages/agent-runtime/roles/coder`)
```markdown
### PaperclipAI Task: Ticket 14 — Coder & Reviewer Agents
**Goal:** Implement the high-precision code execution agent (`CoderAgent`) and the automated code review/security enforcement agent (`ReviewerAgent`).

**Target Directory:** `packages/agent-runtime/roles/`
**Prerequisites:** Ticket 13 completed.

**Detailed Specifications:**
1. Implement `CoderAgent` configuration:
   - **Allowed Tools:** All filesystem, Git, LSP (`lsp_get_diagnostics`), and terminal (`run_command`) tools.
   - **Execution Workflow:** Follows approved `PlanSpec` step-by-step. For every modified file:
     1. Read original file context.
     2. Apply minimal edit via `apply_edit` tool.
     3. Immediately run `lsp_get_diagnostics(file)` to verify zero new linter/compiler errors introduced.
     4. If diagnostics report errors, self-correct (`ReAct loop`) before yielding step complete.
2. Implement `ReviewerAgent` configuration:
   - **Allowed Tools:** `git_diff`, `filesystem_read_file`, `lsp_get_diagnostics`, `grep_files`.
   - **System Prompt Focus:** "Analyze the `git_diff` of recent changes. Check for: SQL injections, unhandled null checks, hardcoded API keys, missing TypeScript types, and memory leaks. Output structured `ReviewResult(approved: boolean, comments: ReviewComment[])`."

**Acceptance Criteria / Verification Plan:**
- Unit test `test_coder_lsp_self_correction.py`: Mock `CoderAgent` introducing a type error (`TS2322`); verify `CoderAgent` reads the diagnostic observation and automatically calls `apply_edit` to fix the type mismatch before returning.
- Unit test `test_reviewer_vulnerability_detection.py`: Feed a git diff containing `eval(user_input)` to `ReviewerAgent`; verify `ReviewResult` returns `approved: false` with exact line vulnerability comment.
```

---

#### Ticket 15: Specialized Agents — Tester & Debugger Agents (`packages/agent-runtime/roles/tester`)
```markdown
### PaperclipAI Task: Ticket 15 — Tester & Debugger Agents
**Goal:** Implement the autonomous test suite execution agent (`TesterAgent`) and deep root-cause investigation agent (`DebuggerAgent`).

**Target Directory:** `packages/agent-runtime/roles/`
**Prerequisites:** Ticket 14 completed.

**Detailed Specifications:**
1. Implement `TesterAgent` configuration:
   - **Allowed Tools:** `run_command` (restricted to `pytest`, `npm test`, `jest`, `cargo test`), `filesystem_read_file`, `filesystem_write_file` (restricted to `*test*` files).
   - **Workflow:** Detects project test runner from `package.json` / `pyproject.toml`. Executes target unit test suite. If tests fail, parses exact stack trace and line failure into `TestFailureSummary`.
2. Implement `DebuggerAgent` configuration:
   - **Allowed Tools:** `grep_files`, `lsp_find_references`, `filesystem_read_file`, `run_command` (`git log -S`, `git blame`).
   - **Workflow:** Receives `TestFailureSummary` or runtime error stack trace. Conducts multi-file root-cause investigation. Traces variable mutation history across call stack and outputs precise `BugRootCause(file, line, explanation, proposedFix)` without guessing.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_tester_stacktrace_parser.py`: Feed raw `pytest` failure traceback string into `TesterAgent`; verify exact failing function name, file, and line number are parsed into `TestFailureSummary`.
- Unit test `test_debugger_root_cause.py`: Verify `DebuggerAgent` correctly traces an uninitialized variable back to its missing assignment in an upstream imported helper module.
```

---

#### Ticket 16: Specialized Agents — Fixer & Documentation Agents (`packages/agent-runtime/roles/fixer`)
```markdown
### PaperclipAI Task: Ticket 16 — Fixer & Documentation Agents
**Goal:** Implement the rapid patch application agent (`FixerAgent`) that resolves verified bugs, and the automated documentation writer (`DocumentationAgent`).

**Target Directory:** `packages/agent-runtime/roles/`
**Prerequisites:** Ticket 15 completed.

**Detailed Specifications:**
1. Implement `FixerAgent`:
   - **Inputs:** `BugRootCause` from `DebuggerAgent` or linter errors.
   - **Allowed Tools:** `apply_edit`, `run_command` (`pytest / jest`).
   - **Workflow:** Applies surgical patch to target lines identified by `DebuggerAgent`. Immediately triggers `TesterAgent` on the specific failing test to verify `RED -> GREEN` transition. Re-commits fix if green.
2. Implement `DocumentationAgent`:
   - **Allowed Tools:** `filesystem_read_file`, `filesystem_write_file` (`*.md`, JSDoc/docstring comments only), `git_diff`.
   - **Workflow:** Scans newly created or modified functions (`ast_find_untyped_functions`). Auto-generates clean JSDoc/Sphinx docstrings with parameter types (`ast_add_jsdoc`) and updates `README.md` / `CHANGELOG.md` with high-level summaries of new user-facing features.

**Acceptance Criteria / Verification Plan:**
- Unit test `test_fixer_red_to_green.py`: Simulate `FixerAgent` applying a patch that turns a failing unit test into a passing test, verifying it halts immediately upon verification (`GREEN`).
- Unit test `test_doc_agent_jsdoc.py`: Pass undocumented JS function `function add(a, b) { return a + b; }`; verify `DocumentationAgent` emits complete, typed `@param {number} a` JSDoc comment block.
```

---

### Phase 5: UI & Full IDE Integration (Tickets 17–20)

#### Ticket 17: UI — Full AI Sidebar Chat & Task Queue View (`apps/desktop/src/vs/pulse/ui/chat`)
```markdown
### PaperclipAI Task: Ticket 17 — Full AI Sidebar Chat & Task Queue Webview
**Goal:** Connect the React webview shell (`Ticket 3`) to the live `AgentOrchestrator` (`Ticket 12`), enabling real-time streaming token display, multi-agent status visualization, and task queue monitoring.

**Target Directory:** `apps/desktop/src/vs/pulse/ui/` & `packages/ui-components/`
**Prerequisites:** Tickets 3 and 12 completed.

**Detailed Specifications:**
1. Implement **Real-Time Streaming Markdown Renderer**:
   - Render incoming `token` deltas from `AgentOrchestrator` smoothly (<16ms frame rate) using virtualized list rendering (`react-window`).
   - Render code blocks with live syntax highlighting and two floating actions: `[Apply to Editor]` and `[Insert at Cursor]`.
2. Implement **Multi-Agent Task Queue Drawer**:
   - Visual step progress pipeline (`[✓ Planner] -> [⏳ Coder] -> [ Reviewer] -> [ Tester]`).
   - Expandable Tool Call Accordion: when `CoderAgent` calls `filesystem_read_file("auth.ts")`, display expandable row showing exact tool arguments and execution status (`2ms - Success`).
3. Implement **Inline Permission Gate Dialog**:
   - When `ConfirmationBridge` emits confirmation request (`run_command("rm -rf ...")`), slide out modal inside chat bar: `[⚠️ Destructive Command] [Allow Once] [Always Allow for Session] [Deny]`.

**Acceptance Criteria / Verification Plan:**
- Automated Playwright/Webview test `test_sidebar_streaming_ui.ts`: Send 500 fast token chunks from backend; verify chat viewport scrolls smoothly without UI freeze or missing markdown closing tags.
- Verify clicking `[Allow Once]` on confirmation gate resumes blocked tool call on backend instantly.
```

---

#### Ticket 18: UI — Inline GhostText Completions Engine (`apps/desktop/src/vs/pulse/editor`)
```markdown
### PaperclipAI Task: Ticket 18 — Inline Tab Completions Engine (GhostText Copilot)
**Goal:** Implement real-time, speculative inline code completions (`GhostText`) directly inside the VS Code editor viewport using low-latency FIM (`Fill-In-The-Middle`) prompts (`<PRE>...<SUF>...<MID>`).

**Target Directory:** `apps/desktop/src/vs/pulse/editor/` & `packages/tools/lsp/`
**Prerequisites:** Ticket 11 completed.

**Detailed Specifications:**
1. Register `vscode.languages.registerInlineCompletionItemProvider({ pattern: '**/*' }, provider)`:
   - Listen to keystrokes (`onDidChangeTextDocument`). Debounce requests by `150ms`.
   - If cursor pauses, extract `prefix` (up to 1,200 tokens before cursor) and `suffix` (up to 400 tokens after cursor).
2. Send FIM prompt to low-latency model (`qwen-2.5-coder-32b` or `deepseek-coder-v2` via LiteLLM):
   - Prompt format: `<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>`.
3. Render returned `<MID>` completion as gray inline ghost text (`vscode.InlineCompletionItem`).
4. Handle keystroke acceptance: when user presses `Tab`, insert suggestion into document buffer and cache recent completions in LRU cache to avoid duplicate API calls.

**Acceptance Criteria / Verification Plan:**
- Extension host test `test_inline_completions.ts`: Open test buffer `function multiply(x, y) {\n    `, position cursor at indent, trigger FIM request, verify gray suggestion `return x * y;` appears and `Tab` inserts text cleanly.
- Verify typing a new character invalidates and hides stale ghost text within 10ms.
```

---

#### Ticket 19: UI — Activity Timeline & Model Selector Bar (`apps/desktop/src/vs/pulse/ui/timeline`)
```markdown
### PaperclipAI Task: Ticket 19 — Activity Timeline, Mission Checkpoints, & Model Selector UI
**Goal:** Build the interactive Activity Timeline allowing developers to inspect past agent actions, jump back to historical mission checkpoints (`Undo`), and hot-swap active LLM models on the fly.

**Target Directory:** `apps/desktop/src/vs/pulse/ui/timeline/`
**Prerequisites:** Tickets 12 and 17 completed.

**Detailed Specifications:**
1. Implement **Activity Timeline View**:
   - Displays chronological tree of every tool call, file diff, and sub-agent handoff in the session.
   - For every file modification, show `[Undo to this Checkpoint]` button calling `MissionManager.restoreCheckpoint(turnId)`.
2. Implement **Model Selector & Routing Drawer**:
   - Status bar pop-up menu allowing user to select active model per role (`Planner: Claude 3.5 Sonnet`, `Coder: DeepSeek Coder V2`, `Explore: Groq Llama 3 70B`).
   - Live Token Cost Dashboard: displays running API cost (`$0.042 spent this session`) and remaining rate-limit quota per provider.

**Acceptance Criteria / Verification Plan:**
- Webview test `test_checkpoint_undo_ui.ts`: Simulate 3 file edits, click `[Undo to Checkpoint 1]` in timeline, verify editor buffer instantly reverts to turn 1 state and confirmation toast appears.
- Verify selecting `Groq Llama 3 70B` in dropdown updates `ModelManager` active configuration instantly without restarting session.
```

---

#### Ticket 20: End-to-End Orchestrator Integration & Production Desktop Packaging (`apps/desktop/build`)
```markdown
### PaperclipAI Task: Ticket 20 — End-to-End Wiring & Multi-Platform Desktop Packaging
**Goal:** Conduct final wiring of all `packages/*` into the `apps/desktop` VS Code OSS runtime, perform end-to-end multi-agent integration testing, and build standalone desktop installers (`.exe`, `.dmg`, `.deb`/`.AppImage`).

**Target Directory:** `apps/desktop/` & monorepo root
**Prerequisites:** Tickets 1–19 completed cleanly.

**Detailed Specifications:**
1. Verify End-to-End Multi-Agent Pipeline:
   - `@pulse /feature Add user authentication login form with validation and Jest tests`.
   - Verify `PlannerAgent` creates `PLAN.md` -> User approves -> `CoderAgent` writes files -> `TesterAgent` runs Jest -> `ReviewerAgent` verifies zero vulnerabilities -> `DocumentationAgent` adds JSDoc comments.
2. Configure **Electron Packaging & Build Script (`electron-builder` / `vsce`)**:
   - Bundle Python/Rust `bridge-server` binary alongside Node.js extension host (`resources/app/server/`).
   - Generate production installers:
     - Windows: `PulseCodeAI-Setup-x64.exe` (`NSIS`).
     - macOS: `PulseCodeAI-Universal.dmg` (Apple Silicon + Intel universal binary).
     - Linux: `PulseCodeAI-x86_64.AppImage` & `.deb`.
3. Ensure offline startup capability: IDE launches immediately <2 seconds without requiring active cloud connection until AI chat is invoked.

**Acceptance Criteria / Verification Plan:**
- Live E2E Integration Suite (`yarn test:e2e`): Launch packaged binary in sandboxed CI environment, execute full multi-agent workflow prompt, and assert all files and passing unit tests are produced cleanly within 120 seconds wall-clock time.
- Verify generated `.exe`/`.dmg`/`.AppImage` binaries install and launch cleanly on fresh desktop test environments.
```

---

## 🏆 CTO Final Sign-Off Checklist
As you supervise PaperclipAI through these 20 tickets, strictly enforce these three Golden Rules:
1. **Never skip `pytest` / `jest`**: If a ticket fails its verification tests, order PaperclipAI to fix the failure before opening the next ticket.
2. **Strict Tool Allowlists**: Never grant `CoderAgent` or `PlannerAgent` permission to execute raw arbitrary bash scripts without going through `ToolRegistry.execute()` and `confirm_bridge`.
3. **Commit After Every Green Ticket**: `git commit -m "feat(package-name): completed Ticket X - description"` so you maintain absolute point-in-time recovery across your monorepo.
