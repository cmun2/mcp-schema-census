"""AXIS C -- Anthropic. Static judgement of MCP tool schemas against the
constraints Anthropic actually ships. Frozen from the official docs BEFORE
looking at the corpus (see REPORT_ANTHROPIC.md for the verbatim source table).

Three sub-axes, because Anthropic imposes constraints at three different
levels and conflating them would be dishonest:

C0 -- Messages API baseline. NOT opt-in. Applies to EVERY tool sent to
      /v1/messages, strict or not.
  [C0-src1] https://github.com/anthropics/claude-code/issues/10606
            observed 400: "tools.XX.custom.input_schema: input_schema does not
            support oneOf, allOf, or anyOf at the top level"
            (Reported against Claude Code with the official Perplexity MCP
             and time-mcp. Issue closed as not-planned by a staleness bot, no
             maintainer reply.)
            NO VERSION ATTRIBUTION IS MADE. The issue title blames Claude Code
            v2.0.21, but its own follow-up comment says v2.0.20 rejected the
            same packages, and claudesidian-mcp#6 hit the identical 400 on
            Claude Code v1.0.35 on 2025-06-27, four months earlier. Three
            further reports of the same error string:
              https://github.com/Countly/countly-mcp-server/issues/64
              https://github.com/ProfSynapse/claudesidian-mcp/issues/6
            See dataset/README.md > "Field evidence".
      NOTE: this error string is NOT in the published constraint docs. It is an
      empirically observed API error. Marked EMPIRICAL below.

C1..C9 -- `strict: true` JSON Schema subset. Opt-in per tool.
  [C-src1] https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
           "The schema uses standard JSON Schema format with some limitations"
           -> defers to [C-src2] for the subset.
  [C-src2] https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations
           "Not supported:
              * Recursive schemas
              * Complex types within enums
              * External `$ref` (for example, `'$ref': 'http://...'`)
              * Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)
              * String constraints (`minLength`, `maxLength`)
              * Array constraints beyond `minItems` of 0 or 1
              * `additionalProperties` set to anything other than `false`
            If you use an unsupported feature, you'll receive a 400 error with details."
           Supported list includes: `required` and `additionalProperties`
           (must be set to `false` for objects); string formats limited to
           date-time,time,date,duration,email,hostname,uri,ipv4,ipv6,uuid;
           `anyOf` and `allOf` (allOf with $ref NOT supported).

CL1..CL3 -- request-scoped complexity limits, also 400.
  [C-src3] same page, "Schema complexity limits / Explicit limits" table:
           strict tools per request 20 / optional parameters 24 /
           parameters with union types 16, "combined total across all strict
           schemas in a single request".

Anything the docs do not settle is emitted with an `AMB-` prefix and counted
separately. Nothing here is invented; ambiguity is reported as ambiguity.

SINGLE SOURCE OF TRUTH. This module holds the rules themselves and nothing
else -- no I/O, no CLI, no file paths. Every consumer imports it:
  dataset/scripts/judge_anthropic.py   (dataset build CLI)
  src/lint_anthropic.py                (collection-time CLI)
  dataset/scripts/explain.py           (per-verdict re-derivation)
  checker/mcp_schema_check.py          (the server-author CLI)
Do not copy a rule out of here. Two copies drift, and the day they disagree
neither the dataset nor the checker can be trusted.
"""

# [C-src2] supported string formats, verbatim list.
SUPPORTED_FORMATS = {
    "date-time", "time", "date", "duration", "email",
    "hostname", "uri", "ipv4", "ipv6", "uuid",
}

# [C-src2] "Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)"
NUMERIC_HARD = {"minimum", "maximum", "multipleOf"}
# "such as" -> the list is open. These are numeric constraints too but are not
# named. Ambiguous.
NUMERIC_AMB = {"exclusiveMinimum", "exclusiveMaximum"}

# [C-src2] "String constraints (`minLength`, `maxLength`)"
STRING_HARD = {"minLength", "maxLength"}
# `pattern` is explicitly SUPPORTED on this axis (there is a whole
# "Pattern support (regex)" accordion) -- this is a real difference from
# OpenAI strict, where pattern is silently dropped. Only exotic regex features
# 400. We do not attempt to judge regex feature support statically.

# [C-src2] "Array constraints beyond `minItems` of 0 or 1"
ARRAY_HARD = {"maxItems", "uniqueItems"}
ARRAY_AMB = {"contains", "minContains", "maxContains", "prefixItems", "additionalItems", "unevaluatedItems"}

# Not named in EITHER the supported or the unsupported list. `anyOf`/`allOf`
# are explicitly supported; `oneOf` is conspicuously absent from both lists.
UNLISTED_AMB = {"oneOf", "not", "if", "then", "else", "patternProperties",
                "propertyNames", "dependentSchemas", "dependentRequired",
                "minProperties", "maxProperties", "unevaluatedProperties"}


def _is_object_node(node):
    t = node.get("type")
    return t == "object" or (isinstance(t, list) and "object" in t) or isinstance(node.get("properties"), dict)


def _walk(node, path, st, defstack):
    if not isinstance(node, dict):
        return
    st["depth"] = max(st["depth"], len(path.split("/")))

    ref = node.get("$ref")
    if isinstance(ref, str):
        if not ref.startswith("#"):
            st["hard"].append(("C5-external-ref", "external $ref is not supported", {"at": path, "value": ref}))
        else:
            # recursion: a $ref that points at a $def we are already inside
            if ref in defstack:
                st["hard"].append(("C6-recursive-schema", "recursive schema is not supported",
                                   {"at": path, "value": ref}))
            else:
                target = _resolve(st["root"], ref)
                if isinstance(target, dict):
                    _walk(target, path + "->" + ref, st, defstack | {ref})

    if _is_object_node(node):
        if "additionalProperties" in node:
            if node["additionalProperties"] is not False:
                st["hard"].append(("C1-additionalProperties-not-false",
                                   "additionalProperties set to anything other than false",
                                   {"at": path, "value": node["additionalProperties"]}))
        else:
            # Docs say additionalProperties "must be set to false for objects"
            # (supported-features list) but the unsupported list only names
            # non-false VALUES. Whether OMISSION 400s is not stated.
            st["amb"].append(("AMB-additionalProperties-absent",
                              "object does not set additionalProperties; docs say it 'must be set to "
                              "false for objects' but never say omission is an error",
                              {"at": path}))

    for k in node:
        if k in NUMERIC_HARD:
            st["hard"].append(("C2-numeric-constraint:" + k, "numerical constraints are not supported",
                               {"at": path, "value": node[k]}))
        elif k in STRING_HARD:
            st["hard"].append(("C3-string-constraint:" + k, "string constraints are not supported",
                               {"at": path, "value": node[k]}))
        elif k in ARRAY_HARD:
            st["hard"].append(("C4-array-constraint:" + k, "array constraints beyond minItems 0/1 unsupported",
                               {"at": path, "value": node[k]}))
        elif k in NUMERIC_AMB:
            st["amb"].append(("AMB-numeric:" + k, "numeric constraint not named in the docs ('such as' list is open)",
                              {"at": path, "value": node[k]}))
        elif k in ARRAY_AMB:
            st["amb"].append(("AMB-array:" + k, "array constraint not named; 'beyond minItems 0/1' is open-ended",
                              {"at": path, "value": node[k]}))
        elif k in UNLISTED_AMB:
            st["amb"].append(("AMB-unlisted:" + k, "keyword appears in neither the supported nor the unsupported list",
                              {"at": path, "value": True}))

    if "minItems" in node:
        mi = node["minItems"]
        if mi not in (0, 1):
            st["hard"].append(("C4-array-constraint:minItems", "only minItems 0 or 1 is supported",
                               {"at": path, "value": mi}))

    fmt = node.get("format")
    if isinstance(fmt, str) and fmt not in SUPPORTED_FORMATS:
        # supported list is enumerated, but unlisted formats are never called
        # out as an error. The Python SDK strips them (lib/_parse/_transform.py).
        st["amb"].append(("AMB-format-unlisted:" + fmt,
                          "string format outside the enumerated supported set",
                          {"at": path, "value": fmt}))

    en = node.get("enum")
    if isinstance(en, list) and any(isinstance(x, (dict, list)) for x in en):
        st["hard"].append(("C7-enum-complex-type", "complex types within enums are not supported", {"at": path}))

    ao = node.get("allOf")
    if isinstance(ao, list):
        for i, sub in enumerate(ao):
            if isinstance(sub, dict) and "$ref" in sub:
                st["hard"].append(("C8-allOf-with-ref", "allOf with $ref is not supported",
                                   {"at": f"{path}/allOf/{i}"}))

    props = node.get("properties")
    if isinstance(props, dict):
        for k, sub in props.items():
            _walk(sub, path + "/properties/" + str(k), st, defstack)
    it = node.get("items")
    if isinstance(it, dict):
        _walk(it, path + "/items", st, defstack)
    elif isinstance(it, list):
        for i, sub in enumerate(it):
            _walk(sub, f"{path}/items/{i}", st, defstack)
    for comb in ("anyOf", "oneOf", "allOf"):
        c = node.get(comb)
        if isinstance(c, list):
            for i, sub in enumerate(c):
                _walk(sub, f"{path}/{comb}/{i}", st, defstack)


def _resolve(root, ref):
    if not ref.startswith("#/"):
        return None
    cur = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def check_C(tool):
    """Returns (c0_hits, hard_hits, amb_hits, counts) for one tool."""
    c0, counts = [], {"optional_top": 0, "union_top": 0, "optional_all": 0, "n_props_top": 0}
    s = tool.get("inputSchema") if isinstance(tool, dict) else None
    if not isinstance(s, dict):
        return c0, [], [], counts

    # ---- C0 : Messages API baseline (not opt-in) -------------------------
    for comb in ("oneOf", "allOf", "anyOf"):
        if comb in s:
            c0.append(("C0-root-combinator:" + comb,
                       "input_schema does not support oneOf, allOf, or anyOf at the top level "
                       "(EMPIRICAL: observed 400, not in the published constraint docs)",
                       {"at": "#", "value": True}))

    # ---- C1..C9 : strict subset -----------------------------------------
    st = {"hard": [], "amb": [], "depth": 1, "root": s}
    _walk(s, "#", st, frozenset())

    # ---- request-scoped counters ----------------------------------------
    props = s.get("properties")
    req = s.get("required") if isinstance(s.get("required"), list) else []
    if isinstance(props, dict):
        counts["n_props_top"] = len(props)
        for k, sub in props.items():
            if k not in req:
                counts["optional_top"] += 1
            if isinstance(sub, dict) and ("anyOf" in sub or isinstance(sub.get("type"), list)):
                counts["union_top"] += 1
    counts["optional_all"] = _count_optional_deep(s)
    return c0, st["hard"], st["amb"], counts


def _count_optional_deep(node, seen=None):
    if not isinstance(node, dict):
        return 0
    n = 0
    props = node.get("properties")
    req = node.get("required") if isinstance(node.get("required"), list) else []
    if isinstance(props, dict):
        for k, sub in props.items():
            if k not in req:
                n += 1
            n += _count_optional_deep(sub)
    it = node.get("items")
    if isinstance(it, dict):
        n += _count_optional_deep(it)
    for comb in ("anyOf", "oneOf", "allOf"):
        c = node.get(comb)
        if isinstance(c, list):
            for sub in c:
                n += _count_optional_deep(sub)
    return n


# [C-src3] explicit limits
LIM_TOOLS, LIM_OPTIONAL, LIM_UNION = 20, 24, 16


def judge_server(rec):
    tools = rec.get("tools") or []
    c0_hits, hard_hits, amb_hits = [], [], []
    tot_opt_top = tot_opt_all = tot_union = 0
    tools_c0 = set()
    tools_hard = set()
    for t in tools:
        nm = t.get("name") if isinstance(t, dict) else None
        c0, hard, amb, cnt = check_C(t)
        for code, msg, val in c0:
            c0_hits.append({"tool": nm, "code": code, "msg": msg, "value": val}); tools_c0.add(nm)
        for code, msg, val in hard:
            hard_hits.append({"tool": nm, "code": code, "msg": msg, "value": val}); tools_hard.add(nm)
        for code, msg, val in amb:
            amb_hits.append({"tool": nm, "code": code, "msg": msg, "value": val})
        tot_opt_top += cnt["optional_top"]
        tot_opt_all += cnt["optional_all"]
        tot_union += cnt["union_top"]

    lim = []
    if len(tools) > LIM_TOOLS:
        lim.append({"code": "CL1-too-many-strict-tools",
                    "msg": f"more than {LIM_TOOLS} strict tools in one request", "value": len(tools)})
    if tot_opt_top > LIM_OPTIONAL:
        lim.append({"code": "CL2-too-many-optional-params",
                    "msg": f"more than {LIM_OPTIONAL} optional parameters across strict schemas",
                    "value": tot_opt_top})
    if tot_union > LIM_UNION:
        lim.append({"code": "CL3-too-many-union-params",
                    "msg": f"more than {LIM_UNION} union-typed parameters across strict schemas",
                    "value": tot_union})

    return {
        "server_name": rec["server_name"], "pkg": rec["pkg"],
        "repository": rec.get("repository"),
        "n_tools": len(tools),
        "C0_fail": len(c0_hits) > 0,
        "C0_hits": c0_hits,
        "C0_tools_affected": len(tools_c0),
        "C_strict_fail": len(hard_hits) > 0,
        "C_hits": hard_hits,
        "C_tools_affected": len(tools_hard),
        "C_limit_fail": len(lim) > 0,
        "C_limit_hits": lim,
        "C_amb_hits": amb_hits,
        "opt_top": tot_opt_top, "opt_all": tot_opt_all, "union_top": tot_union,
    }


