#!/usr/bin/env python3
"""Cross-check: does the checker say the same thing as the published corpus?

Picks servers out of ../dataset/, rebuilds each one's tools/list response from
dataset/tools.jsonl, feeds it to the checker exactly as a server author would
feed their own dump, and compares the checker's findings -- code by code, tool
by tool, pointer by pointer -- against the rows recorded in
dataset/violations.jsonl.

    python3 checker/tests/crosscheck_corpus.py            # 5 dirty + 5 clean
    python3 checker/tests/crosscheck_corpus.py --all      # every server (slow)
    python3 checker/tests/crosscheck_corpus.py --server io.github.foo/bar

WHAT IS AND IS NOT COMPARED
  Compared exactly: axes B (hard), B' (silent), C0, C, CL and the AMB rows.
  Those verdicts in violations.jsonl were produced by the same static rule
  engine the checker now imports, so any difference is a real defect.

  NOT compared: axis A. The corpus records axis A from an EXTERNAL oracle
  (modelcontextprotocol/typescript-sdk ListToolsResultSchema.safeParse) under
  the single code `A-oracle-reject`, not from the static A1..A6 rules. The
  corpus has zero axis-A rows (A is 0/617 = 0.0%), so there is nothing to
  compare; the script asserts that zero-ness rather than pretending to check
  a mapping that does not exist.

Exit code 0 if every selected server matches, 1 otherwise.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.dirname(HERE)
ROOT = os.path.dirname(CHECKER)
DATASET = os.path.join(ROOT, "dataset")
sys.path.insert(0, CHECKER)

from mcp_strict_check import analyse            # noqa: E402


def load_jsonl(name):
    with open(os.path.join(DATASET, name)) as f:
        for line in f:
            yield json.loads(line)


def key(row):
    """The identity of a violation: everything that makes it a distinct claim."""
    return (row["tool"] if "tool" in row else row["tool_name"],
            row["code"], row["json_pointer"],
            json.dumps(row["value"], sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--server", action="append")
    ap.add_argument("-n", type=int, default=5)
    a = ap.parse_args()

    print("loading dataset/tools.jsonl and dataset/violations.jsonl ...", flush=True)
    tools_by_pkg = collections.defaultdict(list)
    name_by_pkg = {}
    for t in load_jsonl("tools.jsonl"):
        tools_by_pkg[t["package"]].append(t)
        name_by_pkg[t["package"]] = t["server_name"]
    viol_by_pkg = collections.defaultdict(list)
    for v in load_jsonl("violations.jsonl"):
        viol_by_pkg[v["package"]].append(v)
    servers = list(load_jsonl("servers.jsonl"))

    n_a_rows = sum(1 for vs in viol_by_pkg.values() for v in vs
                   if v["axis"] == "A")
    print(f"axis-A rows in the corpus: {n_a_rows}  "
          f"(expected 0 -- axis A is 0/617; nothing to cross-check there)")
    if n_a_rows:
        print("!! the corpus now HAS axis-A rows; this script's exclusion is stale")
        return 1

    # ---- pick the servers ------------------------------------------------
    if a.server:
        picked = [s for s in servers if s["server_name"] in a.server
                  or s["package"] in a.server]
    elif a.all:
        picked = servers
    else:
        # 5 with recorded violations, chosen to span axes rather than to
        # flatter the tool: prefer servers whose rows cover the most codes.
        dirty = sorted((s for s in servers if s["n_violations"] > 0),
                       key=lambda s: (-len({v["code"].split(":")[0]
                                            for v in viol_by_pkg[s["package"]]}),
                                      s["package"]))[:a.n]
        clean = sorted((s for s in servers
                        if not viol_by_pkg[s["package"]] and s["n_tools"] > 0),
                       key=lambda s: (-s["n_tools"], s["package"]))[:a.n]
        picked = dirty + clean

    print(f"cross-checking {len(picked)} server(s)\n")
    bad = 0
    for s in picked:
        pkg = s["package"]
        tools = [{"name": t["tool_name"], "inputSchema": t["input_schema"],
                  **({"outputSchema": t["output_schema"]} if t["output_schema"] else {})}
                 for t in tools_by_pkg[pkg]]
        findings, _ = analyse(tools, label=pkg)
        # axis A excluded, per the docstring
        got = collections.Counter(key(f) for f in findings if f["axis"] != "A")
        want = collections.Counter(key(v) for v in viol_by_pkg[pkg])

        only_checker = got - want
        only_corpus = want - got
        status = "MATCH" if not only_checker and not only_corpus else "MISMATCH"
        if status == "MISMATCH":
            bad += 1
        label = "dirty" if s["n_violations"] else "clean"
        print(f"[{status:8}] {label:5} {s['server_name']}")
        print(f"             package={pkg}  tools={len(tools)}  "
              f"checker_findings={sum(got.values())}  corpus_rows={sum(want.values())}")
        if only_checker:
            print(f"             checker found, corpus lacks ({sum(only_checker.values())}):")
            for k, n in list(only_checker.items())[:10]:
                print(f"               x{n} {k}")
        if only_corpus:
            print(f"             corpus has, checker missed ({sum(only_corpus.values())}):")
            for k, n in list(only_corpus.items())[:10]:
                print(f"               x{n} {k}")

    print()
    print(f"{len(picked) - bad}/{len(picked)} servers match exactly; {bad} mismatch(es)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
