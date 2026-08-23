#!/usr/bin/env python3
"""Build the public mcp-schema-census dataset from the frozen measurement run.

This script RE-SERIALISES an existing measurement. It re-runs no server, calls
no API, and changes no verdict. Every headline rate it emits is asserted
against the frozen values in ../../out/THREE_AXIS.txt; if a rate moves, the
build fails loudly rather than publishing a different number.

Usage:  python3 dataset/scripts/build_dataset.py
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.dirname(HERE)
ROOT = os.path.dirname(DATASET)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from prose import strip_prose, sha12          # noqa: E402
from codes import meta_for                    # noqa: E402

SCHEMAS_COLLECTED_AT = "2026-08-09"
VERDICTS_COMPUTED_AT = "2026-08-23"
CONSTRAINTS_CHECKED_AT = "2026-08-23"

# Frozen from out/THREE_AXIS.txt. The build refuses to emit anything else.
EXPECTED = {
    "n_servers": 617, "n_tools": 14804,
    "A": 0, "B": 170, "B_soft": 351, "C0": 0, "C": 389, "CL": 230, "Cstar": 447,
    "tools_A": 0, "tools_B": 868, "tools_Bsoft": 3332, "tools_C": 3411,
    "clean_on_AB_fail_C": 277, "soft_to_hard": 219,
    "sdk_raises": 75, "sdk_drops": 446, "sdk_agree": 510, "sdk_fp": 25, "sdk_fn": 82,
}


def load(rel):
    p = os.path.join(ROOT, rel)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def main():
    # ------------------------------------------------------------------ load
    pops = [("npm", "npm", "npm"), ("pypi", "pypi", "pypi"), ("holdout", "holdout", "npm")]
    A, B, C, J, TOOLS, ECO = {}, {}, {}, {}, {}, {}
    for slice_lbl, suf, eco in pops:
        for r in load(f"data/oracleA_{suf}.jsonl"):
            A.setdefault(r["pkg"], (slice_lbl, r))
        for r in load(f"data/oracleB_{suf}.jsonl"):
            B.setdefault(r["pkg"], (slice_lbl, r))
        for r in load(f"data/anth_{suf}.jsonl"):
            C.setdefault(r["pkg"], (slice_lbl, r))
        for r in load(f"data/judged_{suf}.jsonl"):
            J.setdefault(r["pkg"], r)
    SDK = {}
    for r in load("data/oracleC_sdk.jsonl"):
        SDK.setdefault(r["pkg"], r)

    raw_files = [("data/tools_stdio.jsonl", "npm", "npm"),
                 ("data/tools_pypi.jsonl", "pypi", "pypi"),
                 ("data/tools_stdio_holdout.jsonl", "holdout", "npm")]
    RAW, FAILS = {}, []
    for rel, slice_lbl, eco in raw_files:
        for r in load(rel):
            r["_slice"], r["_eco"] = slice_lbl, eco
            if r.get("status") == "ok":
                RAW.setdefault(r["pkg"], r)
            else:
                FAILS.append(r)
            ECO.setdefault(r["pkg"], eco)

    pkgs = sorted(set(A) & set(B) & set(C))
    assert len(pkgs) == EXPECTED["n_servers"], f"server count moved: {len(pkgs)}"

    stars = {}
    act = json.load(open(os.path.join(ROOT, "data/repo_activity.json")))
    dl = json.load(open(os.path.join(ROOT, "data/npm_downloads.json")))

    def repo_slug(url):
        if not url:
            return None
        u = url.rstrip("/").removesuffix(".git")
        for pre in ("https://github.com/", "http://github.com/", "git+https://github.com/"):
            if u.startswith(pre):
                return u[len(pre):]
        return None

    # ----------------------------------------------------------- servers/tools
    servers, tools_rows, violations = [], [], []
    for k in pkgs:
        slice_lbl, c = C[k]
        a, b, j = A[k][1], B[k][1], J.get(k, {})
        raw = RAW.get(k)
        sdk = SDK.get(k, {})
        eco = ECO.get(k, "npm")
        slug = repo_slug(c.get("repository"))
        st = (act.get(slug) or {}).get("stars") if isinstance(act.get(slug), dict) else None

        a_fail = bool(a["listTools_throws"])
        b_fail = bool(b["oracleB_fail"])
        bs_fail = bool(j.get("B_soft"))
        c0, cs, cl = bool(c["C0_fail"]), bool(c["C_strict_fail"]), bool(c["C_limit_fail"])

        amb = collections.Counter(h["code"] for h in c.get("C_amb_hits") or [])
        dropped_kw = sorted({kw for d in (sdk.get("detail") or []) for kw in (d.get("dropped") or [])})

        # ---- per-tool verdicts ------------------------------------------
        b_hard_tools = {f["tool"] for f in (b.get("fails") or [])}
        b_hard_err = {f["tool"]: f["err"] for f in (b.get("fails") or [])}
        bs_tools = collections.defaultdict(list)
        for h in j.get("B_soft_hits") or []:
            bs_tools[h["tool"]].append(h)
        bh_tools = collections.defaultdict(list)
        for h in j.get("B_hits") or []:
            bh_tools[h["tool"]].append(h)
        a_bad = {t["tool"]: t.get("issues") for t in (a.get("bad_tools") or [])}
        c_tools = collections.defaultdict(list)
        for h in c.get("C_hits") or []:
            c_tools[h["tool"]].append(h)
        c0_tools = collections.defaultdict(list)
        for h in c.get("C0_hits") or []:
            c0_tools[h["tool"]].append(h)
        amb_tools = collections.defaultdict(list)
        for h in c.get("C_amb_hits") or []:
            amb_tools[h["tool"]].append(h)
        sdk_tools = {d["tool"]: d for d in (sdk.get("detail") or [])}

        n_tools = 0
        for t in (raw.get("tools") if raw else []) or []:
            n_tools += 1
            tname = t.get("name")
            desc = t.get("description") or ""
            inp = strip_prose(t.get("inputSchema")) if isinstance(t.get("inputSchema"), (dict, list)) else t.get("inputSchema")
            outp = strip_prose(t.get("outputSchema")) if isinstance(t.get("outputSchema"), dict) else None
            row = {
                "server_name": c["server_name"], "package": k, "ecosystem": eco,
                "slice": slice_lbl, "tool_name": tname,
                # third-party prose removed; only these two non-expressive facts remain
                "description_len": len(desc),
                "description_sha256_12": sha12(desc) if desc else None,
                "input_schema": inp,
                "output_schema": outp,
                "verdicts": {
                    "A_mcp_spec":            {"fail": tname in a_bad},
                    "B_openai_strict_hard":  {"fail": tname in b_hard_tools,
                                              "codes": sorted({h["code"] for h in bh_tools.get(tname, [])}),
                                              "oracle_error": b_hard_err.get(tname)},
                    "B_openai_strict_silent": {"fail": bool(bs_tools.get(tname)),
                                               "codes": sorted({h["code"] for h in bs_tools.get(tname, [])})},
                    "C0_anthropic_api_baseline": {"fail": bool(c0_tools.get(tname)),
                                                  "codes": sorted({h["code"] for h in c0_tools.get(tname, [])})},
                    "C_anthropic_strict":    {"fail": bool(c_tools.get(tname)),
                                              "codes": sorted({h["code"] for h in c_tools.get(tname, [])})},
                },
                "ambiguous_codes": sorted({h["code"] for h in amb_tools.get(tname, [])}),
                "sdk_oracle": {"raises": (sdk_tools.get(tname) or {}).get("raises"),
                               "dropped": (sdk_tools.get(tname) or {}).get("dropped") or []},
            }
            tools_rows.append(row)

            # ---- violations (long format) -------------------------------
            for h in c0_tools.get(tname, []) + c_tools.get(tname, []) + amb_tools.get(tname, []):
                violations.append(_viol(c, k, eco, slice_lbl, tname, h))
            for h in bh_tools.get(tname, []):
                violations.append(_viol(c, k, eco, slice_lbl, tname, h))
            for h in bs_tools.get(tname, []):
                violations.append(_viol(c, k, eco, slice_lbl, tname, h))
            for h in (a_bad.get(tname) or []):
                violations.append(_viol(c, k, eco, slice_lbl, tname,
                                        {"code": "A-oracle-reject", "msg": h, "value": None}))

        for h in c.get("C_limit_hits") or []:
            violations.append(_viol(c, k, eco, slice_lbl, None, h))

        servers.append({
            "server_name": c["server_name"], "package": k, "ecosystem": eco,
            "slice": slice_lbl,
            "package_version": (raw or {}).get("pkg_version"),
            "server_version": (raw or {}).get("version"),
            "repository": c.get("repository"), "repo_slug": slug,
            "stars": st, "stars_as_of": SCHEMAS_COLLECTED_AT,
            "npm_weekly_downloads": dl.get(k) if eco == "npm" else None,
            "schemas_collected_at": SCHEMAS_COLLECTED_AT,
            "verdicts_computed_at": VERDICTS_COMPUTED_AT,
            "n_tools": n_tools,
            "axes": {
                "A_mcp_spec":              {"fail": a_fail, "tools_affected": len(a_bad),
                                            "oracle": "modelcontextprotocol/typescript-sdk@1.30.0 ListToolsResultSchema.safeParse",
                                            "opt_in": False},
                "B_openai_strict_hard":    {"fail": b_fail, "tools_affected": len(b_hard_tools),
                                            "oracle": "openai-agents ensure_strict_json_schema",
                                            "opt_in": True},
                "B_openai_strict_silent":  {"fail": bs_fail,
                                            "tools_affected": len({h["tool"] for h in (j.get("B_soft_hits") or [])}),
                                            "oracle": "documented-unsupported-keyword table",
                                            "opt_in": True},
                "C0_anthropic_api_baseline": {"fail": c0, "tools_affected": c["C0_tools_affected"],
                                              "oracle": "empirical-400 (claude-code#10606)",
                                              "opt_in": False},
                "C_anthropic_strict":      {"fail": cs, "tools_affected": c["C_tools_affected"],
                                            "oracle": "documented-constraint-table",
                                            "corroborated_by": "anthropic-python-sdk@1.0.0 transform_schema",
                                            "opt_in": True},
                "CL_anthropic_limits":     {"fail": cl,
                                            "codes": sorted({h["code"] for h in c.get("C_limit_hits") or []}),
                                            "oracle": "documented-explicit-limits-table",
                                            "opt_in": True},
                "C_star_anthropic_any":    {"fail": c0 or cs or cl},
            },
            "complexity": {"optional_params_top_level": c.get("opt_top"),
                           "optional_params_all_levels": c.get("opt_all"),
                           "union_typed_params": c.get("union_top")},
            "sdk_oracle": {"raises": bool(sdk.get("sdk_raises")),
                           "drops_constraints": bool(sdk.get("sdk_drops_constraints")),
                           "dropped_keywords": dropped_kw},
            "ambiguous_excluded_from_counts": dict(sorted(amb.items())),
            "n_violations": sum(1 for v in violations if v["package"] == k and v["severity"] != "ambiguous"),
        })

    # --------------------------------------------------------------- controls
    controls = _build_controls()

    # --------------------------------------------------------------- failures
    failures = []
    for r in FAILS:
        stderr = r.get("stderr") or ""
        failures.append({
            "server_name": r["server_name"], "package": r["pkg"],
            "ecosystem": r["_eco"], "slice": r["_slice"],
            "package_version": r.get("pkg_version"),
            "repository": r.get("repository"),
            "attempted_at": SCHEMAS_COLLECTED_AT,
            "status": r.get("status"),
            "env_var_names_supplied": sorted((r.get("env") or {}).keys()),
            "env_retry_attempted": bool(r.get("retry_env")),
            "env_var_names_retried": sorted(r.get("retry_env") or []),
            "retry_status": r.get("retry_status"),
            # stderr is third-party program output: length + digest only
            "stderr_len": len(stderr),
            "stderr_sha256_12": sha12(stderr) if stderr else None,
        })

    # ------------------------------------------------------------------ write
    out = {
        "servers.jsonl": servers,
        "tools.jsonl": tools_rows,
        "violations.jsonl": violations,
        "controls.jsonl": controls,
        "failures.jsonl": failures,
    }
    for name, rows in out.items():
        p = os.path.join(DATASET, name)
        with open(p, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")
        print(f"wrote {name:20} {len(rows):7} rows  {os.path.getsize(p):>10} bytes")

    _assert_frozen(servers, tools_rows)
    print("\nfrozen-rate assertions: PASS (no verdict moved)")


def _viol(c, pkg, eco, slice_lbl, tname, h):
    code = h["code"]
    m = meta_for(code)
    val = h.get("value")
    ptr, v = None, val
    if isinstance(val, dict) and "at" in val:
        ptr, v = val.get("at"), val.get("value")
    elif isinstance(val, str) and val.startswith("#"):
        ptr, v = val, None
    if isinstance(v, (dict, list)):
        v = strip_prose(v)
    row = {
        "server_name": c["server_name"], "package": pkg, "ecosystem": eco,
        "slice": slice_lbl, "tool_name": tname,
        "axis": m["axis"], "code": code, "severity": m["severity"],
        "json_pointer": ptr, "value": v,
        "message": h.get("msg"),
        "source": m["source"], "source_quote": m["source_quote"],
    }
    row["repro"] = _repro(row)
    return row


def _repro(row):
    q = lambda s: json.dumps(s or "")
    return ("python3 scripts/explain.py --server %s --code %s%s%s"
            % (q(row["server_name"]), q(row["code"]),
               " --tool %s" % q(row["tool_name"]) if row["tool_name"] else "",
               " --pointer %s" % q(row["json_pointer"]) if row["json_pointer"] else ""))


def _build_controls():
    """Positive + negative controls, one row per case, with expected vs actual."""
    rows = []
    inputs = {r["server_name"]: r for r in load("data/positive_control.jsonl")}
    ctrlA = {r["server_name"]: r for r in load("data/ctrl_A.jsonl")}
    ctrlB = {r["server_name"]: r for r in load("data/ctrl_B.jsonl")}
    ctrlL = {r["server_name"]: r for r in load("data/ctrl_lint.jsonl")}
    for name, r in ctrlL.items():
        a, b = ctrlA.get(name, {}), ctrlB.get(name, {})
        src = inputs.get(name, {})
        rows.append({
            "control_id": name, "axis_under_test": "A+B",
            "kind": "positive" if (a.get("listTools_throws") or b.get("oracleB_fail")) else "negative",
            "input_schemas": [strip_prose(t.get("inputSchema")) if isinstance(t.get("inputSchema"), dict) else t.get("inputSchema")
                              for t in (src.get("tools") or [])],
            "tool_names": [t.get("name") for t in (src.get("tools") or [])],
            "oracle_A_listTools_throws": a.get("listTools_throws"),
            "oracle_A_issues": [i for t in (a.get("bad_tools") or []) for i in (t.get("issues") or [])],
            "oracle_B_fail": b.get("oracleB_fail"),
            "oracle_B_errors": [f.get("err") for f in (b.get("fails") or [])],
            "static_rule_A_fatal": r.get("A_fatal"), "static_rule_B_hard": r.get("B_hard"),
            "static_rule_codes": sorted({h["code"] for h in (r.get("A_hits") or []) + (r.get("B_hits") or [])}),
            "passed": None,
            "note": "axis-A/B control set; see METHODOLOGY.md 'Controls'",
        })
    for r in load("data/ctrl_anthropic.jsonl"):
        codes = sorted({h["code"] for h in (r.get("C0_hits") or []) + (r.get("C_hits") or []) + (r.get("C_limit_hits") or [])})
        rows.append({
            "control_id": r["server_name"], "axis_under_test": r.get("_expect") or "clean",
            "kind": "negative" if (r.get("_expect") in (None, "", "clean")) else "positive",
            "expected": r.get("_expect") or "clean",
            "observed_codes": codes,
            "C0_fail": r["C0_fail"], "C_strict_fail": r["C_strict_fail"], "C_limit_fail": r["C_limit_fail"],
            "passed": r.get("_pass"),
            "note": r.get("_note"),
        })
    return rows


def _assert_frozen(servers, tools_rows):
    def cnt(f):
        return sum(1 for s in servers if f(s))
    got = {
        "n_servers": len(servers),
        "n_tools": len(tools_rows),
        "A": cnt(lambda s: s["axes"]["A_mcp_spec"]["fail"]),
        "B": cnt(lambda s: s["axes"]["B_openai_strict_hard"]["fail"]),
        "B_soft": cnt(lambda s: s["axes"]["B_openai_strict_silent"]["fail"]),
        "C0": cnt(lambda s: s["axes"]["C0_anthropic_api_baseline"]["fail"]),
        "C": cnt(lambda s: s["axes"]["C_anthropic_strict"]["fail"]),
        "CL": cnt(lambda s: s["axes"]["CL_anthropic_limits"]["fail"]),
        "Cstar": cnt(lambda s: s["axes"]["C_star_anthropic_any"]["fail"]),
        "tools_A": sum(1 for t in tools_rows if t["verdicts"]["A_mcp_spec"]["fail"]),
        "tools_B": sum(1 for t in tools_rows if t["verdicts"]["B_openai_strict_hard"]["fail"]),
        "tools_Bsoft": sum(1 for t in tools_rows if t["verdicts"]["B_openai_strict_silent"]["fail"]),
        "tools_C": sum(1 for t in tools_rows if t["verdicts"]["C_anthropic_strict"]["fail"]),
        "clean_on_AB_fail_C": cnt(lambda s: s["axes"]["C_star_anthropic_any"]["fail"]
                                  and not s["axes"]["B_openai_strict_hard"]["fail"]
                                  and not s["axes"]["A_mcp_spec"]["fail"]),
        "soft_to_hard": cnt(lambda s: s["axes"]["B_openai_strict_silent"]["fail"]
                            and not s["axes"]["B_openai_strict_hard"]["fail"]
                            and s["axes"]["C_anthropic_strict"]["fail"]),
        "sdk_raises": cnt(lambda s: s["sdk_oracle"]["raises"]),
        "sdk_drops": cnt(lambda s: s["sdk_oracle"]["drops_constraints"]),
        "sdk_agree": cnt(lambda s: s["sdk_oracle"]["drops_constraints"] == s["axes"]["C_anthropic_strict"]["fail"]),
        "sdk_fp": cnt(lambda s: s["axes"]["C_anthropic_strict"]["fail"] and not s["sdk_oracle"]["drops_constraints"]),
        "sdk_fn": cnt(lambda s: not s["axes"]["C_anthropic_strict"]["fail"] and s["sdk_oracle"]["drops_constraints"]),
    }
    bad = {k: (v, EXPECTED[k]) for k, v in got.items() if v != EXPECTED[k]}
    if bad:
        for k, (g, e) in bad.items():
            print(f"  FROZEN-RATE MISMATCH {k}: got {g}, expected {e}", file=sys.stderr)
        raise SystemExit("build aborted: a verdict moved")


if __name__ == "__main__":
    main()
