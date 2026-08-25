"""`python -m mcp_strict_check` -- the same entry point as the console script.

Used by the repo-mode launcher `checker/mcp-strict-check`, which puts
`checker/` on PYTHONPATH so a checkout needs no install."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
