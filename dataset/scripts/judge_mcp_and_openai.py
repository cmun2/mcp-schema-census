#!/usr/bin/env python3
"""AXIS A + B driver -- CLI wrapper around the shared rule engine.

    python3 scripts/judge_mcp_and_openai.py <tools.jsonl> <out.jsonl>

The rules themselves are NOT here. They live in `rules/mcp_openai.py`, which
this file, src/lint.py and checker/mcp_strict_check/cli.py all import.
See rules/__init__.py for why.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rules.mcp_openai import (         # noqa: E402,F401  -- re-exported for callers
    UNSUPPORTED_KEYWORDS, MAX_PROPS, MAX_DEPTH,
    check_A, check_B, judge_server,
)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/tools_stdio.jsonl")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data/judged.jsonl")
    rows = []
    seen = set()
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
    n = len(rows)
    nt = sum(r["n_tools"] for r in rows)
    a = sum(1 for r in rows if r["A_fatal"])
    b = sum(1 for r in rows if r["B_hard"])
    ab = sum(1 for r in rows if r["A_fatal"] or r["B_hard"])
    sf = sum(1 for r in rows if r["B_soft"])
    print(f"servers N={n}  tools={nt}")
    print(f"A (MCP-spec, whole-server fatal) : {a}/{n} = {100*a/n:.1f}%")
    print(f"B (OpenAI strict hard reject)    : {b}/{n} = {100*b/n:.1f}%")
    print(f"A or B                           : {ab}/{n} = {100*ab/n:.1f}%")
    print(f"B soft (silent validation loss)  : {sf}/{n} = {100*sf/n:.1f}%")


if __name__ == "__main__":
    main()
