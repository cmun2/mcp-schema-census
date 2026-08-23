"""mcp-schema-census rule engine -- the single source of truth.

The verdict rules live here and only here. The dataset build, the collection
scripts, the per-verdict re-derivation command, and the server-author checker
all import this package. Nothing re-implements a rule; nothing transcribes a
constraint table by hand.

    from rules import check_A, check_B, check_C, meta_for

Why this matters: the published rates (A 0.0%, B 27.6%, B' 56.9%, C0 0.0%,
C 63.0%, CL 37.3%, C* 72.4%) were computed by these functions over 617
servers / 14,804 tools, and are re-asserted on every `verify_all.sh`. If a
consumer kept its own copy, the corpus and the tool could disagree inside a
single release and neither would be checkable.

Layers
    codes.py       verdict code -> axis, severity, source URL, verbatim quote
    mcp_openai.py  axis A (MCP spec) and axis B/B' (OpenAI strict)
    anthropic.py   axis C0 / C / CL (Anthropic Messages API + strict:true)
    fixes.py       one-line remediation per code (presentation, not a rule)
"""

from .codes import CODES, SRC, lookup, meta_for                      # noqa: F401
from .mcp_openai import (                                            # noqa: F401
    check_A, check_B,
    UNSUPPORTED_KEYWORDS, MAX_PROPS, MAX_DEPTH,
    judge_server as judge_server_mcp_openai,
)
from .anthropic import (                                             # noqa: F401
    check_C,
    SUPPORTED_FORMATS, NUMERIC_HARD, STRING_HARD, ARRAY_HARD,
    LIM_TOOLS, LIM_OPTIONAL, LIM_UNION,
    judge_server as judge_server_anthropic,
)
from .fixes import fix_for                                           # noqa: F401


def split_pointer(value):
    """Split a raw hit `value` into (json_pointer, offending_value).

    The judge modules attach location information in three shapes:
      {"at": ptr, "value": v}   most axis-C and axis-B object hits
      {"at": ptr}               hits where the pointer alone is the evidence
      "#/..." (a bare string)   axis-B' soft-keyword hits
      anything else             axis-A hits, which carry the value and no pointer

    Both the dataset build (build_dataset._viol) and the checker call this, so
    a violation row and a checker finding describe the same node the same way.
    """
    if isinstance(value, dict) and "at" in value:
        return value.get("at"), value.get("value")
    if isinstance(value, str) and value.startswith("#"):
        return value, None
    return None, value

__all__ = [
    "CODES", "SRC", "lookup", "meta_for",
    "check_A", "check_B", "check_C", "split_pointer",
    "judge_server_mcp_openai", "judge_server_anthropic",
    "fix_for",
    "UNSUPPORTED_KEYWORDS", "MAX_PROPS", "MAX_DEPTH",
    "SUPPORTED_FORMATS", "NUMERIC_HARD", "STRING_HARD", "ARRAY_HARD",
    "LIM_TOOLS", "LIM_OPTIONAL", "LIM_UNION",
]
