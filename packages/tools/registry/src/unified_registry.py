"""
unified_registry.py
-------------------
PulseCodeAI Unified Tool Registry (`packages/tools/registry`).
Aggregates all sandboxed tools across all sub-packages into a unified dispatcher.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List


def _ensure_paths_loaded():
    curr = Path(__file__).resolve()
    # Ascend until we find 'packages' directory or repo root
    repo_root = curr.parents[4] if len(curr.parents) >= 5 else curr.parents[-1]
    for p in curr.parents:
        if (p / "packages" / "tools").exists():
            repo_root = p
            break
        elif p.name == "packages" and (p / "tools").exists():
            repo_root = p.parent
            break

    tools_dir = repo_root / "packages" / "tools"
    for sub in ("filesystem", "terminal", "git", "lsp", "rag", "browser", "web", "process", "ui"):
        sub_src = tools_dir / sub / "src"
        if sub_src.exists() and str(sub_src) not in sys.path:
            sys.path.insert(0, str(sub_src))


_ensure_paths_loaded()


class UnifiedToolRegistry:
    """Central registry holding all PulseCodeAI sandboxed tools with JSON schema and permission checking."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.tools: Dict[str, Any] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        _ensure_paths_loaded()
        from filesystem_tools import ReadFileTool, WriteFileTool
        from terminal_tools import RunCommandTool
        from git_tools import GitStatusTool, GitDiffTool, GitCommitTool, GrepFilesTool
        from lsp_ast_tools import AstFindUntypedFunctionsTool, AstAddJsDocTool, LspGetDiagnosticsTool
        from rag_tools import RagIndexDirectoryTool, RagSearchTool
        from browser_tools import BrowserEvaluateJsTool, BrowserScreenshotTool
        from web_tools import WebSearchTool, FetchTool
        from process_tools import ProcessManagerTool
        from ui_tools import RenderUiTool, ClearUiTool

        classes = [
            ReadFileTool, WriteFileTool, RunCommandTool,
            GitStatusTool, GitDiffTool, GitCommitTool, GrepFilesTool,
            AstFindUntypedFunctionsTool, AstAddJsDocTool, LspGetDiagnosticsTool,
            RagIndexDirectoryTool, RagSearchTool,
            BrowserEvaluateJsTool, BrowserScreenshotTool,
            WebSearchTool, FetchTool, ProcessManagerTool,
            RenderUiTool, ClearUiTool
        ]
        for cls in classes:
            tool_instance = cls()
            self.tools[tool_instance.name] = tool_instance

    def register_tool(self, tool_instance: Any) -> None:
        self.tools[tool_instance.name] = tool_instance

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return a structured summary list of all registered tools and their mutation status."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_mutating": getattr(t, "is_mutating", False)
            }
            for t in self.tools.values()
        ]

    def execute(self, tool_name: str, args: Dict[str, Any], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"status": "error", "output": f"Unknown tool: '{tool_name}'"}
        
        ctx = {"workspace_root": self.workspace_root}
        if context:
            ctx.update(context)

        tool = self.tools[tool_name]
        try:
            return tool.execute(args, ctx)
        except Exception as exc:
            return {"status": "error", "output": f"ExecutionError inside {tool_name}: {exc}"}
