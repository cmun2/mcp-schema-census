#!/usr/bin/env python3
"""Re-derive one verdict, live, from the published schema.

Every row in violations.jsonl carries a `repro` field holding the exact
command that reproduces just that verdict. Run it from the dataset root:

    cd dataset
    python3 scripts/explain.py --server "io.github.foo/bar" \
        --code "C2-numeric-constraint:minimum" \
        --tool "search" --pointer "#/properties/limit"

It does not trust violations.jsonl. It loads the schema out of tools.jsonl,
re-runs the axis rule over it, and prints what the rule found -- then compares
that against the recorded row and says whether they agree.

THINK THE VERDICT IS WRONG? That is the point of this command. Paste its
output into an issue (see README "Correcting a verdict"). A verdict is a claim
about a published sentence, and published sentences change.

Axes A and B are recorded, not re-derived here: their oracles are external
(node + @modelcontextprotocol/sdk, and openai-agents). METHODOLOGY.md has the
commands.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import judge_anthropic          # noqa: E402  (vendored copy of src/lint_anthropic.py)
from codes import meta_for      # noqa: E402


def load_tools(server=None, package=None):
    rows = []
    with open(os.path.join(DATASET, "tools.jsonl")) as f:
        for line in f:
            t = json.loads(line)
            if server and t["server_name"] != server:
                continue
            if package and t["package"] != package:
                continue
            rows.append(t)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", help="server_name, e.g. io.github.foo/bar")
    ap.add_argument("--package", help="package name (alternative to --server)")
    ap.add_argument("--tool", help="tool_name (omit for request-scoped CL codes)")
    ap.add_argument("--code", required=True, help="verdict code, e.g. C3-string-constraint:minLength")
    ap.add_argument("--pointer", help="JSON pointer of the offending node")
    a = ap.parse_args()

    if not a.server and not a.package:
        ap.error("give --server or --package")

    tools = load_tools(a.server, a.package)
    if not tools:
        print(f"no such server in tools.jsonl: {a.server or a.package}")
        return 2
    server_name = tools[0]["server_name"]

    m = meta_for(a.code)
    print("=" * 78)
    print(f"server : {server_name}")
    print(f"package: {tools[0]['package']}   ({tools[0]['ecosystem']}, slice={tools[0]['slice']})")
    print(f"code   : {a.code}")
    print(f"axis   : {m['axis']}    severity: {m['severity']}")
    print(f"source : {m['source']}")
    print(f'quote  : "{m["source_quote"]}"')
    print("=" * 78)

    if m["axis"] in ("A", "B", "B_silent"):
        print("\nAxis A / B verdicts come from external oracles and are recorded, not\n"
              "re-derived here. See METHODOLOGY.md > 'Reproducing layer 1'.\n")
        _print_recorded(server_name, a)
        return 0

    rec = {"server_name": server_name, "pkg": tools[0]["package"],
           "tools": [{"name": t["tool_name"], "inputSchema": t["input_schema"]} for t in tools]}
    got = judge_anthropic.judge_server(rec)

    hits = (got["C0_hits"] + got["C_hits"] + got["C_amb_hits"]
            + [dict(h, tool=None) for h in got["C_limit_hits"]])
    sel = [h for h in hits if h["code"] == a.code
           and (a.tool is None or h.get("tool") == a.tool)
           and (a.pointer is None or (isinstance(h.get("value"), dict)
                                      and h["value"].get("at") == a.pointer))]

    print(f"\nre-derived from dataset/tools.jsonl : {len(sel)} matching hit(s)")
    for h in sel:
        v = h.get("value")
        ptr = v.get("at") if isinstance(v, dict) else None
        val = v.get("value") if isinstance(v, dict) and "at" in v else v
        print(f"\n  tool         : {h.get('tool')}")
        print(f"  json_pointer : {ptr}")
        print(f"  value        : {json.dumps(val)[:400]}")
        print(f"  rule says    : {h['msg']}")

    _print_recorded(server_name, a, n_rederived=len(sel))
    print("\nfull schema for that tool:")
    print(f"  jq -c 'select(.server_name==\"{server_name}\""
          + (f" and .tool_name==\"{a.tool}\")' " if a.tool else ")' ")
          + "tools.jsonl")
    print("\nre-collect the ORIGINAL schema (prose included) from the source:")
    print("  see METHODOLOGY.md > 'Reproducing layer 2' -- the repository URL is in servers.jsonl")
    return 0


def _print_recorded(server_name, a, n_rederived=None):
    recorded = []
    with open(os.path.join(DATASET, "violations.jsonl")) as f:
        for line in f:
            v = json.loads(line)
            if v["server_name"] == server_name and v["code"] == a.code \
                    and (a.tool is None or v["tool_name"] == a.tool) \
                    and (a.pointer is None or v["json_pointer"] == a.pointer):
                recorded.append(v)
    print(f"\nrecorded in violations.jsonl        : {len(recorded)} row(s)")
    if n_rederived is not None:
        print("agreement                           : "
              + ("MATCH" if n_rederived == len(recorded) else
                 f"MISMATCH ({n_rederived} re-derived vs {len(recorded)} recorded) -- please open an issue"))


if __name__ == "__main__":
    raise SystemExit(main())
