#!/usr/bin/env python3
"""AXIS C -- Anthropic strict-mode judgement.

Collection-time CLI. The rules are NOT here -- they live in the shared engine
at `dataset/scripts/rules/`, which this file, the dataset build scripts and
`checker/mcp_strict_check/cli.py` all import. Before 2026-08-23 this file was a
byte-identical copy of dataset/scripts/judge_anthropic.py; that duplication is what the
extraction removed.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "dataset", "scripts"))

from rules.anthropic import (      # noqa: E402,F401  -- re-exported for callers
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
