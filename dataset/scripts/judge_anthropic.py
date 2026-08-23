#!/usr/bin/env python3
"""AXIS C driver -- CLI wrapper around the shared rule engine.

    python3 scripts/judge_anthropic.py <tools.jsonl> <out.jsonl>

The rules themselves are NOT here. They live in `rules/anthropic.py`, which
this file, src/lint_anthropic.py, scripts/explain.py and
checker/mcp_schema_check.py all import. See rules/__init__.py for why.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rules.anthropic import (          # noqa: E402,F401  -- re-exported for callers
    SUPPORTED_FORMATS, NUMERIC_HARD, NUMERIC_AMB, STRING_HARD,
    ARRAY_HARD, ARRAY_AMB, UNLISTED_AMB,
    LIM_TOOLS, LIM_OPTIONAL, LIM_UNION,
    check_C, judge_server,
)


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    rows, seen = [], set()
    for line in open(src):
        r = json.loads(line)
        if r.get("status") != "ok":
            continue
        if r["pkg"] in seen:
            continue
        seen.add(r["pkg"])
        rows.append(judge_server(r))
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows) or 1
    nt = sum(r["n_tools"] for r in rows)
    print(f"{os.path.basename(src)}: servers={len(rows)} tools={nt}")
    for key, label in (("C0_fail", "C0 API baseline (root oneOf/allOf/anyOf)"),
                       ("C_strict_fail", "C  strict subset violation"),
                       ("C_limit_fail", "CL request complexity limit")):
        c = sum(1 for r in rows if r[key])
        print(f"   {label:42} {c:4}/{len(rows)} = {100*c/n:5.1f}%")


if __name__ == "__main__":
    main()
