#!/usr/bin/env python3
"""Recompute every number quoted in the documentation, straight from the
published JSONL. Nothing here is typed by hand into the docs without first
appearing in this output.

Usage:  python3 dataset/scripts/stats.py > dataset/STATS.txt
"""
import collections
import json
import os

DATASET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(name):
    with open(os.path.join(DATASET, name)) as f:
        for line in f:
            yield json.loads(line)


def main():
    S = list(rows("servers.jsonl"))
    T = list(rows("tools.jsonl"))
    V = list(rows("violations.jsonl"))
    F = list(rows("failures.jsonl"))
    C = list(rows("controls.jsonl"))
    N = len(S)
    NT = len(T)

    def pct(c, n=N):
        return f"{c:4}/{n} = {100.0*c/n:5.1f}%"

    ax = lambda s, a: s["axes"][a]["fail"]

    print("=" * 84)
    print(f"mcp-schema-census -- STATS  (regenerated from the published JSONL)")
    print("=" * 84)
    print(f"servers {N}   tools {NT}   violation rows {len(V)}   "
          f"startup failures {len(F)}   controls {len(C)}")
    print()
    print("--- server-unit axis rates -------------------------------------------------")
    for label, a in (("A  MCP spec (whole-server reject)      not opt-in", "A_mcp_spec"),
                     ("B  OpenAI strict, hard reject          opt-in    ", "B_openai_strict_hard"),
                     ("B' OpenAI strict, silent loss          opt-in    ", "B_openai_strict_silent"),
                     ("C0 Anthropic Messages API baseline     not opt-in", "C0_anthropic_api_baseline"),
                     ("C  Anthropic strict:true subset        opt-in    ", "C_anthropic_strict"),
                     ("CL Anthropic request complexity limits opt-in    ", "CL_anthropic_limits"),
                     ("C* Anthropic any of C0/C/CL            opt-in*   ", "C_star_anthropic_any")):
        print(f"{label}  {pct(sum(1 for s in S if ax(s, a)))}")

    print()
    print("--- tool-unit rates --------------------------------------------------------")
    for label, a in (("A ", "A_mcp_spec"), ("B ", "B_openai_strict_hard"),
                     ("B'", "B_openai_strict_silent"),
                     ("C0", "C0_anthropic_api_baseline"), ("C ", "C_anthropic_strict")):
        c = sum(1 for t in T if t["verdicts"][a]["fail"])
        print(f"{label}  {c:6}/{NT} = {100.0*c/NT:5.1f}%")

    print()
    print("--- per population ---------------------------------------------------------")
    print(f"{'slice':10} {'eco':6} {'N':>5}  {'A':>7} {'B':>7} {'C0':>7} {'C':>7} {'CL':>7} {'C*':>7}")
    for sl in ("npm", "pypi", "holdout"):
        ks = [s for s in S if s["slice"] == sl]
        eco = ks[0]["ecosystem"]
        v = [100.0*sum(1 for s in ks if ax(s, a))/len(ks) for a in
             ("A_mcp_spec", "B_openai_strict_hard", "C0_anthropic_api_baseline",
              "C_anthropic_strict", "CL_anthropic_limits", "C_star_anthropic_any")]
        print(f"{sl:10} {eco:6} {len(ks):5}  " + " ".join(f"{x:6.1f}%" for x in v))

    print()
    print("--- axis independence ------------------------------------------------------")
    b = {s["package"] for s in S if ax(s, "B_openai_strict_hard")}
    bs = {s["package"] for s in S if ax(s, "B_openai_strict_silent")}
    a_ = {s["package"] for s in S if ax(s, "A_mcp_spec")}
    c = {s["package"] for s in S if ax(s, "C_anthropic_strict")}
    cst = {s["package"] for s in S if ax(s, "C_star_anthropic_any")}
    print(f"|A| = {len(a_)}   |B| = {len(b)}   |C*| = {len(cst)}")
    print(f"B and C* = {len(b & cst)}   B only = {len(b - cst)}   C* only = {len(cst - b)}")
    print(f"Jaccard(B,C*) = {len(b & cst)/max(1,len(b | cst)):.3f}")
    print(f"P(C*|B) = {len(b & cst)/max(1,len(b)):.3f}   P(B|C*) = {len(b & cst)/max(1,len(cst)):.3f}")
    print(f"containment A subset-of B subset-of C* : "
          f"{a_ <= b} / {b <= cst}")
    print(f"clean on A and B, fails C*  : {pct(len(cst - b - a_))}")
    print(f"OpenAI silent-loss only -> Anthropic hard 400 : {pct(len((bs - b) & c))}")

    print()
    print("--- violation codes (hard verdicts only, ambiguous excluded) ---------------")
    perserver = collections.defaultdict(set)
    perhit = collections.Counter()
    for v in V:
        if v["severity"] == "ambiguous":
            continue
        perserver[v["code"]].add(v["package"])
        perhit[v["code"]] += 1
    print(f"{'code':42} {'servers':>8} {'hits':>8}")
    for code, n in perhit.most_common():
        print(f"{code:42} {len(perserver[code]):8} {n:8}")

    print()
    print("--- DOCUMENTED AMBIGUITIES (excluded from every count above) ---------------")
    ambserver = collections.defaultdict(set)
    ambhit = collections.Counter()
    for v in V:
        if v["severity"] != "ambiguous":
            continue
        ambserver[v["code"]].add(v["package"])
        ambhit[v["code"]] += 1
    print(f"{'code':42} {'servers':>8} {'hits':>8}")
    fam = collections.defaultdict(lambda: [set(), 0])
    for code, n in sorted(ambhit.items(), key=lambda kv: -kv[1]):
        print(f"{code:42} {len(ambserver[code]):8} {n:8}")
        f = code.split(":")[0]
        fam[f][0] |= ambserver[code]
        fam[f][1] += n
    print()
    print("by family:")
    for f, (ss, n) in sorted(fam.items(), key=lambda kv: -len(kv[1][0])):
        print(f"{f:42} {len(ss):8} {n:8}")

    print()
    print("--- SDK oracle (anthropic-python-sdk 1.0.0 transform_schema) ---------------")
    raises = sum(1 for s in S if s["sdk_oracle"]["raises"])
    drops = sum(1 for s in S if s["sdk_oracle"]["drops_constraints"])
    agree = sum(1 for s in S if s["sdk_oracle"]["drops_constraints"] == ax(s, "C_anthropic_strict"))
    fp = sum(1 for s in S if ax(s, "C_anthropic_strict") and not s["sdk_oracle"]["drops_constraints"])
    fn = sum(1 for s in S if not ax(s, "C_anthropic_strict") and s["sdk_oracle"]["drops_constraints"])
    print(f"SDK raises                      {pct(raises)}")
    print(f"SDK strips >=1 constraint       {pct(drops)}")
    print(f"agreement with axis-C rule      {pct(agree)}")
    print(f"  rule fires / SDK keeps  (FP)  {fp}")
    print(f"  rule silent / SDK strips (FN) {fn}")
    print(f"  FP + FN                       {fp + fn}")
    exc = collections.Counter()
    for t in T:
        r = t["sdk_oracle"]["raises"]
        if r:
            exc[r.split(":")[0] + (": " + r.split(": ", 1)[1][:40] if ": " in r else "")] += 1
    print("\nSDK exceptions, tool unit (top 8):")
    for k, n in exc.most_common(8):
        print(f"  {n:5}  {k}")
    ta = collections.Counter()
    tasrv = collections.defaultdict(set)
    for t in T:
        r = t["sdk_oracle"]["raises"] or ""
        if r.startswith("AssertionError") and "but got: " in r:
            m = r.split("but got: ", 1)[1]
            ta[m] += 1
            tasrv[m].add(t["package"])
    print("\nSDK AssertionError by type array (this is the upstream SDK defect):")
    for m, n in ta.most_common():
        print(f"  {n:5} tools  {len(tasrv[m]):3} servers  {m}")
    print(f"  {sum(ta.values()):5} tools  "
          f"{len(set().union(*tasrv.values())) if tasrv else 0:3} servers  ANY type array")
    print(f"  {sum(n for m, n in ta.items() if 'null' in m):5} tools      "
          f"        any array containing 'null'")

    print()
    print("--- controls ---------------------------------------------------------------")
    pos = [c_ for c_ in C if c_["kind"] == "positive" and c_.get("passed") is not None]
    neg = [c_ for c_ in C if c_["kind"] == "negative" and c_.get("passed") is not None]
    print(f"axis-C positive controls  : {sum(1 for x in pos if x['passed'])}/{len(pos)} pass")
    print(f"axis-C negative controls  : {sum(1 for x in neg if x['passed'])}/{len(neg)} pass")
    ab = [c_ for c_ in C if c_["axis_under_test"] == "A+B"]
    print(f"axis-A/B control cases    : {len(ab)}  "
          f"(oracle A throws on {sum(1 for x in ab if x['oracle_A_listTools_throws'])})")

    print()
    print("--- subsets (activity) -----------------------------------------------------")
    print(f"{'subset':34} {'N':>5} {'C':>7} {'CL':>7} {'C*':>7}")
    subsets = [
        ("all", lambda s: True),
        ("repository URL in registry", lambda s: bool(s["repo_slug"])),
        ("GitHub API resolved (stars known)", lambda s: s["stars"] is not None),
        ("stars >= 10", lambda s: (s["stars"] or -1) >= 10),
        ("stars >= 100", lambda s: (s["stars"] or -1) >= 100),
        ("tools >= 5", lambda s: s["n_tools"] >= 5),
        ("npm weekly downloads >= 1000", lambda s: (s["npm_weekly_downloads"] or 0) >= 1000),
    ]
    for label, f in subsets:
        ks = [s for s in S if f(s)]
        if not ks:
            continue
        v = [100.0*sum(1 for s in ks if ax(s, a))/len(ks) for a in
             ("C_anthropic_strict", "CL_anthropic_limits", "C_star_anthropic_any")]
        print(f"{label:34} {len(ks):5} " + " ".join(f"{x:6.1f}%" for x in v))

    print()
    print("--- startup failures (not in the corpus) -----------------------------------")
    print(f"servers attempted : {N + len(F)} raw rows ({len(F)} failed, "
          f"{N} distinct packages returned tools/list)")
    for k, n in collections.Counter(f["status"] for f in F).most_common():
        print(f"  {k:24} {n}")
    print(f"  env-var retry attempted  {sum(1 for f in F if f['env_retry_attempted'])}")
    for k, n in collections.Counter(f["ecosystem"] for f in F).most_common():
        print(f"  ecosystem {k:14} {n}")

    print()
    print("--- description prose (removed; length/digest retained) --------------------")
    lens = [t["description_len"] for t in T]
    has = sum(1 for x in lens if x)
    print(f"tools with a description : {has}/{NT}")
    print(f"total characters removed : {sum(lens)}")
    print(f"median / max length      : {sorted(lens)[len(lens)//2]} / {max(lens)}")


if __name__ == "__main__":
    main()
