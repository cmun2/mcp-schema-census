#!/usr/bin/env python3
"""Three-axis comparison + axis-independence analysis.

Axis A -- MCP spec conformance          (oracle: official MCP TS SDK ListToolsResultSchema.safeParse)
Axis B -- OpenAI strict mode            (oracle: openai-agents ensure_strict_json_schema)
Axis C -- Anthropic strict / API subset (rules from the official docs; corroborated by the
                                         official Anthropic Python SDK's transform_schema)
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p):
    p = os.path.join(ROOT, p)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def by_pkg(rows):
    d = {}
    for r in rows:
        d.setdefault(r["pkg"], r)
    return d


def main():
    pops = [("npm", "npm"), ("pypi", "pypi"), ("holdout", "holdout")]
    A, B, C, SDK, TOOLS = {}, {}, {}, {}, {}
    for lbl, suf in pops:
        for r in load(f"data/oracleA_{suf}.jsonl"):
            A.setdefault(r["pkg"], (lbl, r))
        for r in load(f"data/oracleB_{suf}.jsonl"):
            B.setdefault(r["pkg"], (lbl, r))
        for r in load(f"data/anth_{suf}.jsonl"):
            C.setdefault(r["pkg"], (lbl, r))
    for r in load("data/oracleC_sdk.jsonl"):
        SDK.setdefault(r["pkg"], r)
    for f in ("data/tools_stdio.jsonl", "data/tools_pypi.jsonl", "data/tools_stdio_holdout.jsonl"):
        for r in load(f):
            if r.get("status") == "ok":
                TOOLS.setdefault(r["pkg"], r)

    pkgs = sorted(set(A) & set(B) & set(C))
    print("=" * 92)
    print(f"THREE-AXIS COMPARISON   (globally de-duplicated by package; N={len(pkgs)} servers)")
    print("=" * 92)

    # ---------------- server unit --------------------------------------
    def rate(pred, subset=None):
        ks = subset if subset is not None else pkgs
        c = sum(1 for k in ks if pred(k))
        return c, len(ks), (100.0 * c / len(ks) if ks else 0.0)

    axes = [
        ("A  MCP spec  (whole-server reject)", lambda k: A[k][1]["listTools_throws"]),
        ("B  OpenAI strict  hard reject", lambda k: B[k][1]["oracleB_fail"]),
        ("B' OpenAI strict  silent loss", lambda k: bool(C[k][1])
            and _b_soft(k)),
        ("C0 Anthropic API baseline (root oneOf/allOf/anyOf)", lambda k: C[k][1]["C0_fail"]),
        ("C  Anthropic strict  subset violation", lambda k: C[k][1]["C_strict_fail"]),
        ("CL Anthropic strict  complexity limits", lambda k: C[k][1]["C_limit_fail"]),
        ("C* Anthropic ANY (C0 or C or CL)",
         lambda k: C[k][1]["C0_fail"] or C[k][1]["C_strict_fail"] or C[k][1]["C_limit_fail"]),
    ]

    global _JUDGED
    _JUDGED = {}
    for suf in ("npm", "pypi", "holdout"):
        for r in load(f"data/judged_{suf}.jsonl"):
            _JUDGED.setdefault(r["pkg"], r)

    print(f"\n{'axis':52} {'servers':>16}   {'tools':>16}")
    ntools_total = sum(len(TOOLS[k].get("tools") or []) for k in pkgs if k in TOOLS)
    for label, pred in axes:
        c, n, p = rate(pred)
        tc, tn = tool_rate(label, pkgs, TOOLS, C, A, B, _JUDGED)
        tstr = f"{tc}/{tn} = {100*tc/tn:5.1f}%" if tn and tc is not None else "        n/a"
        print(f"{label:52} {c:5}/{n} = {p:5.1f}%   {tstr:>16}")
    print(f"\n(total tools in the de-duplicated corpus: {ntools_total})")

    # ---------------- per population -----------------------------------
    print("\n" + "=" * 92)
    print("PER-POPULATION (holdout was collected AFTER the axis-A/B rules were frozen)")
    print("=" * 92)
    print(f"{'population':12} {'N':>5}  {'A':>7}  {'B':>7}  {'C0':>7}  {'C':>7}  {'CL':>7}  {'C*':>7}")
    for lbl, _ in pops:
        ks = [k for k in pkgs if C[k][0] == lbl]
        if not ks:
            continue
        vals = []
        for label, pred in axes:
            if label.startswith("B'"):
                continue
            vals.append(rate(pred, ks)[2])
        print(f"{lbl:12} {len(ks):5}  {vals[0]:6.1f}%  {vals[1]:6.1f}%  {vals[2]:6.1f}%  "
              f"{vals[3]:6.1f}%  {vals[4]:6.1f}%  {vals[5]:6.1f}%")

    # ---------------- axis overlap -------------------------------------
    print("\n" + "=" * 92)
    print("AXIS INDEPENDENCE  -- are the axes measuring the same thing?")
    print("=" * 92)
    a = set(k for k in pkgs if A[k][1]["listTools_throws"])
    b = set(k for k in pkgs if B[k][1]["oracleB_fail"])
    bs = set(k for k in pkgs if _b_soft(k))
    c = set(k for k in pkgs if C[k][1]["C_strict_fail"])
    cl = set(k for k in pkgs if C[k][1]["C_limit_fail"])
    cany = c | cl | set(k for k in pkgs if C[k][1]["C0_fail"])
    N = len(pkgs)
    print(f"  A (MCP spec)        n={len(a):4}")
    print(f"  B (OpenAI hard)     n={len(b):4}")
    print(f"  C* (Anthropic any)  n={len(cany):4}")
    print()
    print(f"  B and C*   : {len(b & cany):4}      B only: {len(b - cany):4}      C* only: {len(cany - b):4}")
    print(f"  Jaccard(B,C*) = {len(b & cany)/max(1,len(b | cany)):.3f}")
    print(f"  P(C* | B)  = {len(b & cany)/max(1,len(b)):.3f}     P(B | C*) = {len(b & cany)/max(1,len(cany)):.3f}")
    print()
    print("  Servers that are CLEAN on both existing axes but FAIL the Anthropic axis:")
    only_c = cany - b - a
    print(f"    {len(only_c)}/{N} = {100*len(only_c)/N:.1f}%   <-- this is the information the 2026-08-09 POC missed")
    print()
    print("  Cross-tab (server counts):")
    print(f"    {'':22} {'C* fail':>9} {'C* pass':>9}")
    print(f"    {'B fail':22} {len(b & cany):9} {len(b - cany):9}")
    print(f"    {'B pass':22} {len(cany - b):9} {N - len(b | cany):9}")
    print()
    print("  Anthropic-strict violation categories vs OpenAI-strict treatment of the SAME keyword:")
    print(f"    {'keyword':22} {'OpenAI strict':>16} {'Anthropic strict':>18}")
    for kw, oa, an in (("additionalProperties!=false", "400 (hard)", "400 (hard)"),
                       ("minimum / maximum", "silently dropped", "400 (hard)"),
                       ("minLength / maxLength", "silently dropped", "400 (hard)"),
                       ("maxItems / uniqueItems", "silently dropped", "400 (hard)"),
                       ("minItems >= 2", "silently dropped", "400 (hard)"),
                       ("pattern", "silently dropped", "SUPPORTED"),
                       (">24 optional params", "no such limit", "400 (hard)"),
                       (">20 strict tools", "no such limit", "400 (hard)")):
        print(f"    {kw:22} {oa:>16} {an:>18}")

    # ---------------- soft->hard conversion ----------------------------
    print()
    print("  The decisive asymmetry: servers whose ONLY OpenAI problem was a SILENT loss,")
    print("  but which are a HARD 400 on Anthropic:")
    conv = (bs - b) & c
    print(f"    {len(conv)}/{N} = {100*len(conv)/N:.1f}%")

    # ---------------- SDK oracle corroboration -------------------------
    print("\n" + "=" * 92)
    print("ORACLE CORROBORATION -- official Anthropic Python SDK v1.0.0 transform_schema")
    print("=" * 92)
    ks = [k for k in pkgs if k in SDK]
    raises = sum(1 for k in ks if SDK[k]["sdk_raises"])
    drops = sum(1 for k in ks if SDK[k]["sdk_drops_constraints"])
    print(f"  N={len(ks)}")
    print(f"  SDK transform_schema RAISES (schema cannot be normalised) : {raises}/{len(ks)} = {100*raises/len(ks):.1f}%")
    print(f"  SDK transform_schema STRIPS >=1 constraint                : {drops}/{len(ks)} = {100*drops/len(ks):.1f}%")
    agree = sum(1 for k in ks if SDK[k]["sdk_drops_constraints"] == C[k][1]["C_strict_fail"])
    print(f"  agreement with my static axis-C rule (server unit)        : {agree}/{len(ks)} = {100*agree/len(ks):.1f}%")
    fp = sum(1 for k in ks if C[k][1]["C_strict_fail"] and not SDK[k]["sdk_drops_constraints"])
    fn = sum(1 for k in ks if not C[k][1]["C_strict_fail"] and SDK[k]["sdk_drops_constraints"])
    print(f"    rule fires / SDK keeps everything (possible FP)         : {fp}")
    print(f"    rule silent / SDK strips something  (possible FN)       : {fn}")

    # ---------------- worked examples ----------------------------------
    print("\n" + "=" * 92)
    print("EXAMPLES -- highest-profile servers failing the Anthropic axis")
    print("=" * 92)
    act = {}
    p = os.path.join(ROOT, "data/repo_activity.json")
    if os.path.exists(p):
        act = json.load(open(p))
    scored = []
    for k in pkgs:
        r = C[k][1]
        if not (r["C_strict_fail"] or r["C_limit_fail"]):
            continue
        repo = r.get("repository") or ""
        st = (act.get(repo) or {}).get("stars", -1) if isinstance(act.get(repo), dict) else -1
        scored.append((st, k, r))
    scored.sort(key=lambda x: -x[0])
    for st, k, r in scored[:12]:
        codes = collections.Counter(h["code"] for h in r["C_hits"])
        lim = ",".join(h["code"] for h in r["C_limit_hits"])
        print(f"  * {r['server_name']:46} stars={st:6}  tools={r['n_tools']:3}")
        print(f"      {dict(codes.most_common(4))}  {lim}")


def _b_soft(k):
    r = _JUDGED.get(k)
    return bool(r and r.get("B_soft"))


def tool_rate(label, pkgs, TOOLS, C, A, B, J):
    """Tool-unit counts where they are meaningful."""
    tot = 0
    hit = 0
    for k in pkgs:
        rec = TOOLS.get(k)
        if not rec:
            continue
        n = len(rec.get("tools") or [])
        tot += n
        if label.startswith("A "):
            hit += len(A[k][1].get("bad_tools") or [])
        elif label.startswith("B "):
            hit += len(set(f["tool"] for f in (B[k][1].get("fails") or [])))
        elif label.startswith("B'"):
            r = J.get(k)
            hit += len(set(h["tool"] for h in (r.get("B_soft_hits") or []))) if r else 0
        elif label.startswith("C0"):
            hit += C[k][1]["C0_tools_affected"]
        elif label.startswith("C "):
            hit += C[k][1]["C_tools_affected"]
        elif label.startswith("CL"):
            return None, tot
        elif label.startswith("C*"):
            hit += max(C[k][1]["C_tools_affected"], C[k][1]["C0_tools_affected"])
    return hit, tot


if __name__ == "__main__":
    main()
