"""Camoufox MCP — stealth browser MCP server using Camoufox (anti-detect Firefox)."""

from mcp.server.fastmcp import FastMCP
from .browser import BrowserManager

mcp = FastMCP("Camoufox Browser")
manager = BrowserManager()

# Register all tool modules (each uses @mcp.tool() decorator on import)
from . import tools_core  # noqa: F401, E402
from . import tools_storage  # noqa: F401, E402
from . import tools_network  # noqa: F401, E402
from . import tools_vision  # noqa: F401, E402
from . import tools_extra  # noqa: F401, E402
