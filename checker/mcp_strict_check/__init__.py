"""mcp-strict-check -- which of your MCP tool schemas a provider's strict mode
would reject, and what to change.

    $ uvx mcp-strict-check --cmd "npx -y @modelcontextprotocol/server-everything"

The verdict rules are not implemented here. They are imported from the one
copy that also produced the published 617-server corpus; see `._rules`.
"""
from .cli import (                                              # noqa: F401
    VERSION, analyse, main,
    judge_server_anthropic, judge_server_mcp_openai,
    meta_for, fix_for, split_pointer,
)

__version__ = VERSION
__all__ = [
    "VERSION", "__version__", "analyse", "main",
    "judge_server_anthropic", "judge_server_mcp_openai",
    "meta_for", "fix_for", "split_pointer",
]
