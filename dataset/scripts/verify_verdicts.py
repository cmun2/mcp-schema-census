#!/usr/bin/env python3
"""Release gate: prove that removing the prose changed no verdict, and that
the published files alone are enough to re-derive the Anthropic axis.

It re-runs the axis-C judge (src/lint_anthropic.py, unmodified) over the
PROSE-STRIPPED schemas in dataset/tools.jsonl and compares, server by server
and hit by hit, against the verdicts recorded when the judge ran over the raw
schemas. Any difference is a build failure.

If this passes, two claims hold at once:
  1. prose removal is verdict-lossless -- no one loses reproducibility by us
     withholding the third-party text;
  2. the dataset is self-contained -- a reader needs nothing from us but these
     files to re-derive axis C0/C/CL.

Usage:  python3 dataset/scripts/verify_verdicts.py
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.dirname(HERE)
ROOT = os.path.dirname(DATASET)
sys.path.insert(0, os.path.join(ROOT, "src"))

sys.path.insert(0, HERE)

import lint_anthropic   # noqa: E402
from prose import strip_prose   # noqa: E402


def key(h):
    """Comparable identity of a single hit.

    A few hit values (C1) quote the offending SUBSCHEMA. On the raw side that
    subschema still carries the author's prose; on the published side it does
    not. Both are normalised through strip_prose() so the comparison asks
    "same verdict, same pointer, same constraint value?" and not "did we
    remove the prose we said we removed?" -- verify_no_prose.py answers that.
    """
    v = h.get("value")
    if isinstance(v, (dict, list)):
        v = strip_prose(v, in_schema=False) if not isinstance(v, dict) or "at" not in v else {
            "at": v.get("at"), "value": strip_prose(v.get("value"))}
    return (h.get("tool"), h["code"], json.dumps(v, sort_keys=True))


def main():
    published = {}
    for line in open(os.path.join(DATASET, "servers.jsonl")):
        r = json.loads(line)
        published[r["package"]] = r

    by_pkg = collections.OrderedDict()
    for pkg, r in published.items():          # include 0-tool servers
        by_pkg[pkg] = {"server_name": r["server_name"], "pkg": pkg, "tools": []}
    for line in open(os.path.join(DATASET, "tools.jsonl")):
        t = json.loads(line)
        by_pkg[t["package"]]["tools"].append(
            {"name": t["tool_name"], "inputSchema": t["input_schema"]})

    # the verdicts that were recorded against the RAW schemas
    raw = {}
    for suf in ("npm", "pypi", "holdout"):
        p = os.path.join(ROOT, f"data/anth_{suf}.jsonl")
        if os.path.exists(p):
            for line in open(p):
                r = json.loads(line)
                raw.setdefault(r["pkg"], r)

    diffs = []
    n_hits = 0
    for pkg, rec in by_pkg.items():
        got = lint_anthropic.judge_server(rec)
        want = raw[pkg]
        for field in ("C0_fail", "C_strict_fail", "C_limit_fail",
                      "C0_tools_affected", "C_tools_affected",
                      "opt_top", "opt_all", "union_top", "n_tools"):
            if got[field] != want[field]:
                diffs.append((pkg, field, got[field], want[field]))
        for hk in ("C0_hits", "C_hits", "C_limit_hits", "C_amb_hits"):
            g = collections.Counter(key(h) for h in got[hk])
            w = collections.Counter(key(h) for h in want[hk])
            n_hits += sum(w.values())
            if g != w:
                only_g = sorted((g - w).elements())[:3]
                only_w = sorted((w - g).elements())[:3]
                diffs.append((pkg, hk, only_g, only_w))
        # and against what we actually published per server
        pub = published[pkg]["axes"]
        for field, pubpath in (("C0_fail", "C0_anthropic_api_baseline"),
                               ("C_strict_fail", "C_anthropic_strict"),
                               ("C_limit_fail", "CL_anthropic_limits")):
            if got[field] != pub[pubpath]["fail"]:
                diffs.append((pkg, "published:" + pubpath, got[field], pub[pubpath]["fail"]))

    print("=" * 78)
    print("VERDICT ROUND-TRIP  --  re-judge the prose-stripped schemas")
    print("=" * 78)
    print(f"servers re-judged from dataset/tools.jsonl : {len(by_pkg)}")
    print(f"tools re-judged                            : {sum(len(v['tools']) for v in by_pkg.values())}")
    print(f"individual hits compared                   : {n_hits}")
    print(f"differences vs the raw-schema run          : {len(diffs)}")
    for d in diffs[:20]:
        print("   ", d)
    ok = not diffs
    print("\nRESULT:", "PASS  (prose removal changed no verdict)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
