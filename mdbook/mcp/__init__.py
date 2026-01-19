"""MCP server module for MD Book Tools.

Exposes book operations as Model Context Protocol tools for Claude Code.
"""

from .server import run_server

__all__ = ["run_server"]
