"""Static strict-client judgement for MCP tool schemas.

Two rule sets, frozen BEFORE looking at the collected corpus.

RULE SET A -- MCP spec conformance. WHOLE-SERVER FATAL.
  Sources:
   [A-src1] https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json
            Tool.required = ["inputSchema","name"];
            Tool.inputSchema.required = ["type"]; Tool.inputSchema.properties.type = {"const":"object"}
   [A-src2] https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/core-internal/src/wire/rev2025-11-25/buildSchemas.ts
            ToolSchema.inputSchema = z.object({type: z.literal('object'), properties: z.record(...).optional(),
                                               required: z.array(z.string()).optional()}).catchall(z.unknown())
            ListToolsResultSchema = PaginatedResultSchema.extend({ tools: z.array(ToolSchema) })
            -> ONE bad tool fails the whole z.array parse -> client.listTools() throws -> zero tools from that server.
   [A-src3] https://github.com/modelcontextprotocol/inspector/issues/1005 (official Inspector admits it does NOT validate this)

RULE SET B -- OpenAI strict mode. Per-tool in the current Agents SDK; whole-request 400 at the raw API.
  Sources:
   [B-src1] https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs
   [B-src2] https://github.com/openai/openai-agents-python/blob/main/src/agents/strict_schema.py

SINGLE SOURCE OF TRUTH. This module holds the rules themselves and nothing
else -- no I/O, no CLI, no file paths. Every consumer imports it:
  dataset/scripts/judge_mcp_and_openai.py  (dataset build CLI)
  src/lint.py                              (collection-time CLI)
  checker/mcp_schema_check.py              (the server-author CLI)
Do not copy a rule out of here. Two copies drift, and the day they disagree
neither the dataset nor the checker can be trusted.
"""

# ---------------------------------------------------------------- Rule set A

def check_A(tool):
    """MCP-spec violations. Any hit => the whole tools/list response fails to
    parse in the official TS SDK => the entire server is unusable."""
    v = []
    if not isinstance(tool, dict):
        return [("A0-tool-not-object", "tool entry is not an object", None)]
    name = tool.get("name")
    if not isinstance(name, str) or name == "":
        v.append(("A5-name-missing", "Tool.name missing or not a string", name))

    if "inputSchema" not in tool:
        v.append(("A1-inputSchema-missing", "Tool.inputSchema is REQUIRED by the MCP schema", None))
        return v
    s = tool["inputSchema"]
    if not isinstance(s, dict):
        v.append(("A2-inputSchema-not-object",
                  "inputSchema is not a JSON object (e.g. bare `true` from Go interface{})", s))
        return v
    t = s.get("type")
    if t != "object":
        if t is None:
            v.append(("A3-type-missing", 'inputSchema.type is REQUIRED and must be "object"', None))
        elif isinstance(t, list):
            v.append(("A3-type-array", 'inputSchema.type must be the string "object", not a type array', t))
        else:
            v.append(("A3-type-not-object", 'inputSchema.type must be "object"', t))
    props = s.get("properties")
    if props is not None and not isinstance(props, dict):
        v.append(("A4-properties-not-object", "inputSchema.properties must be an object", props))
    # NB: must test presence, not `is not None` -- `"required": null` is a real
    # observed failure (opencode#35528 "null is not of type array") and an
    # `is not None` guard silently skips it. Caught by the positive control.
    req = s.get("required")
    if "required" in s and (not isinstance(req, list) or any(not isinstance(x, str) for x in req)):
        v.append(("A4-required-not-string-array",
                  "inputSchema.required must be an array of strings", req))

    o = tool.get("outputSchema")
    if o is not None:
        if not isinstance(o, dict):
            v.append(("A6-outputSchema-not-object", "outputSchema is not a JSON object", o))
        elif o.get("type") != "object":
            v.append(("A6-outputSchema-type", 'outputSchema.type must be "object"', o.get("type")))
    return v


# ---------------------------------------------------------------- Rule set B

# [B-src1] "Unsupported type-specific keywords" table.
UNSUPPORTED_KEYWORDS = {
    "minLength", "minlength", "maxLength", "pattern", "format",
    "minimum", "maximum", "multipleOf",
    "patternProperties", "unevaluatedProperties", "propertyNames",
    "minProperties", "maxProperties",
    "unevaluatedItems", "contains", "minContains", "maxContains",
    "minItems", "maxItems", "uniqueItems",
}
MAX_PROPS = 100      # [B-src1] "up to 100 object properties total"
MAX_DEPTH = 5        # [B-src1] "up to five levels of nesting"


def _walk(node, depth, state, path):
    if not isinstance(node, dict):
        return
    state["depth"] = max(state["depth"], depth)
    typ = node.get("type")
    props = node.get("properties")
    is_object = typ == "object" or (isinstance(typ, list) and "object" in typ) or isinstance(props, dict)

    # [B-src2] raises UserError when additionalProperties is present and is not False.
    if is_object and "additionalProperties" in node and node["additionalProperties"] is not False:
        state["v"].append(("B3-additionalProperties-open",
                           "object sets additionalProperties to something other than false "
                           "(strict conversion raises)", {"at": path, "value": node["additionalProperties"]}))
    # [B-src2]: type absent AND additionalProperties truthy -> UserError
    if typ is None and not isinstance(props, dict) and node.get("additionalProperties", False) is not False:
        state["v"].append(("B4-untyped-open-object",
                           "node has no `type` and a non-false additionalProperties", {"at": path}))

    for k in node.keys():
        if k in UNSUPPORTED_KEYWORDS:
            state["kw"].append((k, path))

    if isinstance(props, dict):
        state["nprops"] += len(props)
        for k, sub in props.items():
            _walk(sub, depth + 1, state, path + "/properties/" + str(k))
    it = node.get("items")
    if isinstance(it, dict):
        _walk(it, depth + 1, state, path + "/items")
    elif isinstance(it, list):
        for i, sub in enumerate(it):
            _walk(sub, depth + 1, state, f"{path}/items/{i}")
    for comb in ("anyOf", "oneOf", "allOf"):
        c = node.get(comb)
        if isinstance(c, list):
            for i, sub in enumerate(c):
                _walk(sub, depth, state, f"{path}/{comb}/{i}")
    for defs in ("$defs", "definitions"):
        d = node.get(defs)
        if isinstance(d, dict):
            for k, sub in d.items():
                _walk(sub, depth, state, f"{path}/{defs}/{k}")


def check_B(tool):
    """OpenAI strict-mode problems, split into hard rejects and silent losses."""
    hard, soft = [], []
    s = tool.get("inputSchema") if isinstance(tool, dict) else None
    if not isinstance(s, dict):
        return hard, soft

    # [B-src2] _ensure_strict_root: root anyOf -> UserError
    if isinstance(s.get("anyOf"), list):
        hard.append(("B1-root-anyOf", "the root of a strict JSON schema must not use `anyOf`", None))
    rt = s.get("type")
    if isinstance(rt, list) and "object" in rt and rt != ["object"]:
        hard.append(("B2-root-nullable", "root must be a non-nullable object", rt))
    if rt is not None and not isinstance(rt, list) and rt != "object":
        hard.append(("B2-root-not-object", "strict root must be an object", rt))

    state = {"v": [], "kw": [], "nprops": 0, "depth": 1}
    _walk(s, 1, state, "#")
    hard.extend(state["v"])
    if state["nprops"] > MAX_PROPS:
        hard.append(("B6-too-many-properties", f">{MAX_PROPS} object properties total", state["nprops"]))
    if state["depth"] > MAX_DEPTH:
        hard.append(("B6-too-deep", f"nesting deeper than {MAX_DEPTH} levels", state["depth"]))
    for k, p in state["kw"]:
        soft.append(("B5-unsupported-keyword:" + k,
                     "keyword is unsupported in strict mode (documented; constraint is lost)", p))
    return hard, soft


# ---------------------------------------------------------------- driver

def judge_server(rec):
    tools = rec.get("tools") or []
    a_hits, b_hard, b_soft = [], [], []
    for t in tools:
        for code, msg, val in check_A(t):
            a_hits.append({"tool": (t.get("name") if isinstance(t, dict) else None),
                           "code": code, "msg": msg, "value": val})
        h, s = check_B(t)
        for code, msg, val in h:
            b_hard.append({"tool": (t.get("name") if isinstance(t, dict) else None),
                           "code": code, "msg": msg, "value": val})
        for code, msg, val in s:
            b_soft.append({"tool": (t.get("name") if isinstance(t, dict) else None),
                           "code": code, "msg": msg, "value": val})
    return {
        "server_name": rec["server_name"], "pkg": rec["pkg"],
        "repository": rec.get("repository"),
        "n_tools": len(tools),
        "A_fatal": len(a_hits) > 0,
        "A_hits": a_hits,
        "A_tools_affected": len(set(x["tool"] for x in a_hits)),
        "B_hard": len(b_hard) > 0,
        "B_hits": b_hard,
        "B_soft_hits": b_soft,
        "B_soft": len(b_soft) > 0,
    }


