"""Example 2: Minimal FastMCP server exposing safe, repo-scoped tools.

Run as an MCP stdio server:
  python examples/02_mcp_minimal.py

Or test the tool functions locally in demo mode:
  python examples/02_mcp_minimal.py --demo
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = (Path(__file__).resolve().parents[1] / "target_repo").resolve()


def _safe_resolve(rel_path: str) -> Path:
    """Ensure agents cannot escape target_repo via path traversal (e.g., ../../etc/passwd)."""
    candidate = (REPO_ROOT / rel_path).resolve()
    if not str(candidate).startswith(str(REPO_ROOT)):
        raise ValueError(f"Access denied outside target_repo: {rel_path}")
    return candidate


def list_repo_files(subdir: str = "src") -> list[str]:
    """List files inside a subdirectory of target_repo."""
    base = _safe_resolve(subdir)
    if not base.exists():
        return []
    return sorted(
        str(p.relative_to(REPO_ROOT))
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )


def read_repo_file(rel_path: str, max_lines: int = 120) -> str:
    """Read up to `max_lines` lines from a file inside target_repo."""
    path = _safe_resolve(rel_path)
    if not path.is_file():
        return f"Error: file not found: {rel_path}"
    lines = path.read_text(encoding="utf-8").splitlines()
    clipped = lines[:max_lines]
    numbered = [f"{idx + 1:>4}: {line}" for idx, line in enumerate(clipped)]
    if len(lines) > max_lines:
        numbered.append(f"... ({len(lines) - max_lines} more lines truncated)")
    return "\n".join(numbered)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        print("Files in target_repo/src:")
        for f in list_repo_files("src"):
            print(" -", f)
        print("\nPreview of src/taskflow/models.py (first 20 lines):")
        print(read_repo_file("src/taskflow/models.py", max_lines=20))
    else:
        from fastmcp import FastMCP

        mcp = FastMCP("taskflow-repo-tools")
        mcp.tool()(list_repo_files)
        mcp.tool()(read_repo_file)
        mcp.run()
