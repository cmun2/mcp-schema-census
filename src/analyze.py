#!/usr/bin/env python3
"""Self-attack: agreement vs oracles, population bias, holdout, template-fork dedup."""
import json, os, sys, re, collections, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p):
    p = os.path.join(ROOT, p)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def agreement(lint_rows, oracleA_rows, oracleB_rows, label):
    la = {r["pkg"]: r["A_fatal"] for r in lint_rows}
    lb = {r["pkg"]: r["B_hard"] for r in lint_rows}
    oa = {r["pkg"]: r["listTools_throws"] for r in oracleA_rows}
    ob = {r["pkg"]: r["oracleB_fail"] for r in oracleB_rows}
    out = []
    for name, mine, orc in (("A", la, oa), ("B", lb, ob)):
        keys = [k for k in mine if k in orc]
        tp = sum(1 for k in keys if mine[k] and orc[k])
        fp = sum(1 for k in keys if mine[k] and not orc[k])
        fn = sum(1 for k in keys if not mine[k] and orc[k])
        tn = sum(1 for k in keys if not mine[k] and not orc[k])
        wrong = fp + fn
        out.append((label, name, len(keys), tp, fp, fn, tn,
                    100 * wrong / len(keys) if keys else 0))
    return out


def main():
    print("=" * 78)
    print("1. HEADLINE  (primary metric = whole-server rejection by a spec-conformant client)")
    print("=" * 78)
    pops = [("npm  (registry, random sample)", "data/oracleA_npm.jsonl", "data/oracleB_npm.jsonl"),
            ("pypi (registry, random sample)", "data/oracleA_pypi.jsonl", "data/oracleB_pypi.jsonl"),
            ("npm  HOLDOUT (disjoint slice)", "data/oracleA_holdout.jsonl", "data/oracleB_holdout.jsonl")]
    tot_n = tot_a = tot_b = 0
    for label, fa, fb in pops:
        A, B = load(fa), load(fb)
        if not A:
            continue
        n = len(A)
        a = sum(1 for r in A if r["listTools_throws"])
        b = sum(1 for r in B if r["oracleB_fail"]) if B else 0
        tot_n += n; tot_a += a; tot_b += b
        print(f"  {label:32} N={n:4}  A(whole-server)={a:3}/{n} = {100*a/n:5.1f}%   "
              f"B(openai-strict)={b:3}/{n} = {100*b/n:5.1f}%")
    if tot_n:
        print(f"  {'POOLED':32} N={tot_n:4}  A(whole-server)={tot_a:3}/{tot_n} = {100*tot_a/tot_n:5.1f}%   "
              f"B(openai-strict)={tot_b:3}/{tot_n} = {100*tot_b/tot_n:5.1f}%")

    print()
    print("=" * 78)
    print("2. MISJUDGEMENT  (my static rules vs the real production validators)")
    print("=" * 78)
    print(f"  {'pop':10} {'rule':5} {'N':>5} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>5} {'err%':>7}")
    rowsets = [("npm", "data/judged_npm.jsonl", "data/oracleA_npm.jsonl", "data/oracleB_npm.jsonl"),
               ("pypi", "data/judged_pypi.jsonl", "data/oracleA_pypi.jsonl", "data/oracleB_pypi.jsonl"),
               ("holdout", "data/judged_holdout.jsonl", "data/oracleA_holdout.jsonl", "data/oracleB_holdout.jsonl"),
               ("control", "data/ctrl_lint.jsonl", "data/ctrl_A.jsonl", "data/ctrl_B.jsonl")]
    for lab, fl, fa, fb in rowsets:
        L, A, B = load(fl), load(fa), load(fb)
        if not L or not A:
            continue
        for r in agreement(L, A, B, lab):
            print(f"  {r[0]:10} {r[1]:5} {r[2]:5} {r[3]:4} {r[4]:4} {r[5]:4} {r[6]:5} {r[7]:6.1f}%")

    print()
    print("=" * 78)
    print("3. POPULATION BIAS  (is the number an artifact of dead / toy / template-fork servers?)")
    print("=" * 78)
    act = {}
    p = os.path.join(ROOT, "data/repo_activity.json")
    if os.path.exists(p):
        act = json.load(open(p))
    dl = {}
    p = os.path.join(ROOT, "data/npm_downloads.json")
    if os.path.exists(p):
        dl = json.load(open(p))

    corpus = []
    for fa, fb, eco in (("data/oracleA_npm.jsonl", "data/oracleB_npm.jsonl", "npm"),
                        ("data/oracleA_pypi.jsonl", "data/oracleB_pypi.jsonl", "pypi"),
                        ("data/oracleA_holdout.jsonl", "data/oracleB_holdout.jsonl", "npm")):
        A, B = load(fa), load(fb)
        bm = {r["pkg"]: r["oracleB_fail"] for r in B}
        for r in A:
            m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", r.get("repository") or "")
            repo = (m.group(1) + "/" + m.group(2).replace(".git", "")) if m else None
            a = act.get(repo, {}) if repo else {}
            corpus.append({"pkg": r["pkg"], "eco": eco, "repo": repo,
                           "owner": repo.split("/")[0] if repo else None,
                           "stars": a.get("stars"), "pushed": a.get("pushed"),
                           "fork": a.get("fork"), "dl": dl.get(r["pkg"]),
                           "A": r["listTools_throws"], "B": bm.get(r["pkg"]),
                           "n_tools": r["n_tools"]})

    def rate(rows, key):
        rows = [r for r in rows if r[key] is not None]
        if not rows:
            return "n/a"
        k = sum(1 for r in rows if r[key])
        return f"{k}/{len(rows)} = {100*k/len(rows):5.1f}%"

    print(f"  {'subset':44} {'N':>5}  {'A':>16}  {'B':>16}")
    def show(lab, rows):
        print(f"  {lab:44} {len(rows):5}  {rate(rows,'A'):>16}  {rate(rows,'B'):>16}")

    show("ALL", corpus)
    have = [r for r in corpus if r["stars"] is not None]
    show("has a resolvable GitHub repo", have)
    for th in (1, 5, 10, 50, 100):
        show(f"stars >= {th}", [r for r in have if r["stars"] >= th])
    for th in (10, 100, 1000):
        show(f"npm weekly downloads >= {th}", [r for r in corpus if (r["dl"] or 0) >= th])
    show("pushed in 2026 (active)", [r for r in have if (r["pushed"] or "") >= "2026-01-01"])
    show("not a GitHub fork", [r for r in have if r["fork"] is False])
    show("has >= 5 tools (non-toy)", [r for r in corpus if r["n_tools"] >= 5])

    # one-server-per-publisher: kills template-fork / spam-publisher inflation
    byowner = {}
    for r in corpus:
        k = r["owner"] or r["pkg"]
        byowner.setdefault(k, r)
    show("deduped to 1 server per GitHub owner", list(byowner.values()))
    oc = collections.Counter(r["owner"] for r in corpus if r["owner"])
    print(f"\n  top publishers by server count: {oc.most_common(6)}")
    tools = [r["n_tools"] for r in corpus]
    print(f"  tools per server: median={statistics.median(tools)} mean={statistics.mean(tools):.1f} "
          f"max={max(tools)}  servers with 0 tools={sum(1 for t in tools if t==0)}")
    if have:
        s = sorted(r["stars"] for r in have)
        print(f"  stars: median={statistics.median(s)} p90={s[int(.9*len(s))]} max={max(s)}  (N={len(s)})")


if __name__ == "__main__":
    main()
