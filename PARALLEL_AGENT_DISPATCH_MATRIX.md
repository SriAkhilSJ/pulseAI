# PulseCodeAI — Parallel Agent Dispatch Matrix
**CTO Guide to Spawning Concurrently Decoupled AI Agents**
*How to run 4 PaperclipAI / AI Agents simultaneously without file collisions or merge conflicts*

---

## 🚀 Why Parallel Execution Works Here (Zero Dependency Matrix)

Because we structured **PulseCodeAI** as a clean monorepo (`apps/` vs. independent `packages/*`), **Ticket 1 (`apps/desktop` VS Code OSS Fork)** is completely decoupled from your backend intelligence (`packages/ai-core/`) and your tool engine (`packages/tools/`).

While **Agent 1** is compiling and scaffolding `Ticket 1` inside `apps/desktop/`, you can spawn **3 additional parallel agents right now** on completely separate folders. None of these touches `apps/desktop/` or each other’s files!

---

## ⚡ The 4-Agent Parallel Dispatch Map (Run These Right Now!)

```
+-----------------------------------------------------------------------------------+
|                        PULSECODE_AI MONOREPO ROOT                                 |
+-----------------------------------------------------------------------------------+
       |                    |                    |                    |
       v                    v                    v                    v
[ 🤖 AGENT 1 ]       [ 🤖 AGENT 2 ]       [ 🤖 AGENT 3 ]       [ 🤖 AGENT 4 ]
  IN PROGRESS           SPAWN NOW            SPAWN NOW            SPAWN NOW
  (Ticket 1)            (Ticket 4)           (Ticket 8)           (Ticket 7)
       |                    |                    |                    |
       v                    v                    v                    v
apps/desktop/        packages/ai-core/    packages/tools/      packages/ai-core/
(VS Code OSS Fork)   models/              filesystem/          memory/
                     (Model Manager)      (Tool Registry &     (SQLite FTS5
                                           Path Guard)          Memory Engine)
```

---

### 📦 Copy-Paste Dispatch Box for Agent 2 (Ticket 4: Model Manager)
*Zero dependency on Ticket 1. Runs inside `packages/ai-core/models/`.*

```markdown
### PaperclipAI Parallel Task: Ticket 4 — Multi-Provider Model Manager (`ModelManager`)
**Target Directory:** `packages/ai-core/models/`
**Isolation Guarantee:** Do NOT touch `apps/desktop/` or `packages/tools/`. Only write inside `packages/ai-core/models/` and `test/`.

**Detailed Specifications:**
1. Create `packages/ai-core/models/` directory structure and clean package configuration (`package.json` or `pyproject.toml` depending on your runtime choice, utilizing `litellm` / `ai-sdk`).
2. Implement `class ModelManager` with standardized interface:
   - `streamCompletion(messages, modelConfig, tools?): AsyncGenerator<TokenDelta>`
   - `complete(messages, modelConfig, tools?): Promise<CompletionResult>`
3. Implement **Automatic Failover Circuit Breaker**: if primary provider (`e.g., Anthropic / Groq`) throws `RateLimitError` (`429`) or `503 Service Unavailable`, automatically retry the request on the fallback provider (`e.g., OpenRouter / Gemini`) within 2 seconds without crashing.
4. Build `TokenManager` utility calculating exact prompt and completion costs using model tokenizers.

**Acceptance Verification Plan (Run via TDD):**
- Write and run unit test `test_model_manager_failover.py` (or `.ts`): Mock primary API throwing `429 Too Many Requests` and verify `ModelManager` intercepts and returns clean completion via secondary fallback provider.
- Write and run unit test `test_token_calculator.py` ensuring accurate token calculations.
```

---

### 📦 Copy-Paste Dispatch Box for Agent 3 (Ticket 8: Base Tool Registry & Filesystem)
*Zero dependency on Ticket 1 or Ticket 4. Runs inside `packages/tools/filesystem/`.*

```markdown
### PaperclipAI Parallel Task: Ticket 8 — Base Tool Registry & Secure Filesystem Tools
**Target Directory:** `packages/tools/filesystem/`
**Isolation Guarantee:** Do NOT touch `apps/desktop/` or `packages/ai-core/`. Only write inside `packages/tools/filesystem/` and `test/`.

**Detailed Specifications:**
1. Create `packages/tools/filesystem/` directory structure.
2. Define universal tool schema:
   ```typescript
   interface BaseTool {
     name: string;
     description: string;
     parameters: JSONSchema;
     isMutating: boolean;
     execute(args: Record<string, any>, context: ExecutionContext): Promise<ToolResult>;
   }
   ```
3. Implement `ToolRegistry`: registers tools, validates inputs against `JSONSchema` before calling `execute()`, and returns structured `{ status: "success" | "error", output: string }`.
4. Implement core filesystem tools:
   - `filesystem_read_file(path, startLine?, endLine?)`: reads file with line numbers.
   - `filesystem_write_file(path, content)`: overwrites or creates file (`isMutating = true`).
   - `apply_edit(path, old_text, new_text)`: fuzzy/exact string replacement (`isMutating = true`).
5. Implement **Security Sandbox Guard (`PathGuard`)**:
   - Reject outright (`SecurityViolationError`) any attempt to access files outside `workspaceRoot` (`../../etc/passwd`) or sensitive files (`.env`, `id_rsa`, `.git/credentials`).

**Acceptance Verification Plan (Run via TDD):**
- Write and run unit test `test_path_guard.py` (or `.ts`): Attempt `filesystem_read_file("../../passwd")` and `filesystem_read_file(".env")`; verify both immediately throw `SecurityViolationError`.
- Write and run unit test `test_apply_edit.py`: Verify `apply_edit` replaces exact code blocks cleanly and returns a unified diff string.
```

---

### 📦 Copy-Paste Dispatch Box for Agent 4 (Ticket 7: FTS5 SQLite Memory Engine)
*Zero dependency on Ticket 1, 4, or 8. Runs inside `packages/ai-core/memory/`.*

```markdown
### PaperclipAI Parallel Task: Ticket 7 — SQLite FTS5 Conversation Memory Engine
**Target Directory:** `packages/ai-core/memory/`
**Isolation Guarantee:** Do NOT touch `apps/desktop/`, `packages/tools/`, or `packages/ai-core/models/`. Only write inside `packages/ai-core/memory/` and `test/`.

**Detailed Specifications:**
1. Create `packages/ai-core/memory/` directory and configure SQLite dependencies (`sqlite3` / `sql.js` / `better-sqlite3`).
2. Implement `class ConversationMemory`:
   - Initialize schema: `sessions(id, timestamp, title, summary)` and `turns_fts USING fts5(session_id, role, content, tags)`.
   - `recordTurn(sessionId: str, role: str, content: str, tags?: str[]): Promise<void>`
   - `searchHistory(queryText: str, limit: number = 5): Promise<MemorySearchResult[]>`
3. Implement **Auto-Memory Tagging & Extraction**:
   - Create `extractNotes(sessionId)` helper that extracts high-level architectural decisions (`["auth: using JWT", "db: pooled 20"]`) into a dedicated `project_notes` table.

**Acceptance Verification Plan (Run via TDD):**
- Write and run unit test `test_fts_search.py` (or `.ts`): Insert 20 mock conversations across different session IDs. Run `searchHistory("JWT authentication")` and verify exact relevant turns return with high FTS5 match scores in <15ms.
```

---

## 🔄 What Happens When Agent 1, 2, 3, and 4 Finish? (Next Wave)

As soon as these first 4 parallel agents complete their tickets:
1. **When Agent 1 finishes Ticket 1 (`apps/desktop` scaffolding)** $\rightarrow$ Spawn **Ticket 2 (Rebranding & Open VSX)** right inside `apps/desktop/`.
2. **When Agent 2 finishes Ticket 4 (`ai-core/models`)** $\rightarrow$ Spawn **Ticket 5 (Context Manager & Auto-Compression)** right inside `packages/ai-core/context/`.
3. **When Agent 3 finishes Ticket 8 (`tools/filesystem`)** $\rightarrow$ Spawn **Ticket 9 (Terminal Tool & Confirmation Gate)** inside `packages/tools/terminal/`.
4. **When Agent 4 finishes Ticket 7 (`ai-core/memory`)** $\rightarrow$ Spawn **Ticket 6 (Dynamic Prompt & Rule Manager)** inside `packages/ai-core/prompt/`.

By keeping every agent restricted to its exact target directory inside `packages/*`, you will complete the first 8 major foundational systems of **PulseCodeAI** in a fraction of the time with **zero merge conflicts**!
