# Pulse AI — Engineering Gap Analysis & Surpass Plan

> **Discipline:** TDD (RED→GREEN→REFACTOR), no fabrication, 3-tier testing (unit/wiring/live), bite-sized tasks, frequent commits, safety first.

---

## 1. Where Pulse Agent Wins Already

| Capability | OpenClaude | Hermes Agent | Pulse Agent |
|---|---|---|---|
| **Multi-provider LLM routing** | Bolted-on shim | Configurable | **Best** — verified live failover across 5 providers with 90s wall-clock timeout |
| **Safety (secret hard-block)** | Prompt-level | Tool-level | **Best** — hard-blocked at filesystem level, no override possible |
| **File safety (backups+undo)** | Partial | Partial | **Best** — auto-backup before every write, undo tool, diff preview |
| **Permission modes** | 4 modes | Custom | **6 modes** — incl. `dont_ask` which structurally removes tools from registry |
| **Codebase size** | 133K lines / 21 MB | 203K lines / 57 MB | **18K lines / 845 KB** — focused, no bloat |
| **Ownership** | Leaked Anthropic IP | Nous Research | **YOUR code** — full IP ownership |
| **VS Code fork** | Extension only | None | **Extension + fork in progress** |
| **Long-task checkpoints** | None | None | **Missions** — compact handoff between sessions |

---

## 2. Engineering Gaps to Close

### Tier 1 — Must Have (Product-Defining)

| # | Feature | Why | Competitors Have It | Effort |
|---|---|---|---|---|
| 1 | **Working VS Code fork** | Without this you have an agent library, not an IDE. Fork at `D:\vscodesfresh\` is ~80% built — needs the agent wired in as default chat participant | All of them | Medium |
| 2 | **Repo map** | Tree-sitter + PageRank codebase index auto-injected into every prompt. Agent never asks "where is the file?" | OpenClaude, Cursor, Windsurf | Medium |
| 3 | **Streaming agent responses** | Agent streaming tokens in real-time vs blocking until full response. Feels 10x faster. | Everyone | Medium |

### Tier 2 — Should Have (Competitive Parity)

| # | Feature | Why | Competitors Have It | Effort |
|---|---|---|---|---|
| 4 | **Tab completions** | The "always-on" feature — predicts your next edit inline. Cursor's killer feature | Cursor, Windsurf | High |
| 5 | **Context compression** | Auto-compress when near context window limit. Without it, long sessions hit the wall | OpenClaude, Cursor, Windsurf, Hermes | Medium |
| 6 | **Memory with search** | Cross-session memory with FTS5. "What did we decide about auth last week?" | OpenClaude (sessionMemory), Hermes (memory_manager) | Low |
| 7 | **Ink/React TUI** | Proper terminal UI with streaming output, status bar, keybindings. Current REPL is basic | OpenClaude, Hermes, Claude Code | Medium |

### Tier 3 — Nice to Have (Feature Depth)

| # | Feature | Why | Competitors Have It | Effort |
|---|---|---|---|---|
| 8 | **Daemon/background mode** | Persistent background agent you can resume | OpenClaude (gRPC), Hermes (gateway) | Medium |
| 9 | **Plugin marketplace** | Third-party extensions | OpenClaude, Hermes | High |
| 10 | **NPM/installer package** | Users can install with one command | OpenClaude, Cursor, Windsurf | Low |
| 11 | **MCP tool depth** | More MCP server integrations (filesystem, fetch already done) | OpenClaude (vscodeSdkMcp), Hermes | Low |
| 12 | **Browser/vision tools** | Screenshot + vision for web testing | Hermes (browser_camofox), Cursor | Low |

---

## 3. The Discipline Rules

Every feature must follow:

```
1. WRITE FAILING TEST FIRST     (RED)
2. RUN TEST → verify it fails   (RED VERIFIED)
3. WRITE MINIMAL CODE           (GREEN)
4. RUN TEST → verify it passes  (GREEN VERIFIED)
5. REFACTOR if needed           (REFACTOR)
6. COMMIT                       (COMMIT)
```

**3-tier testing** (already your pattern, keep it):
- `*_test.py` — unit, no real LLM, fast
- `*_wiring_test.py` — integration through dispatch chain, LLMs mocked
- `*_live_test.py` — real LLM calls, authoritative proof

**Never** fabricate results. **Never** skip tests. **Never** commit untested code.

---

## 4. Build Order (Vertical Slices)

### Slice 1: Working IDE (Week 1)
Get `D:\vscodesfresh\` launching with Pulse Agent as the built-in chat participant.

### Slice 2: Repo Map (Week 2)
Tree-sitter + PageRank codebase index, auto-injected into every prompt.

### Slice 3: Streaming + TUI (Week 3)
Streaming LLM responses + Ink/React terminal UI.

### Slice 4: Tab Completions (Week 4)
GhostText inline completion engine.

### Slice 5: Memory + Context (Week 5-6)
FTS5 memory with search + auto context compression.

### Slice 6: Package & Ship (Week 7)
NPM installer, documentation, landing page.

---
