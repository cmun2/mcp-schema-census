#!/usr/bin/env python3
"""Verdict code -> axis, severity, source URL, verbatim source quote.

Every row in violations.jsonl carries the URL and the verbatim sentence the
verdict was derived from. The claim this dataset makes is never "we decided
this schema is wrong"; it is "this published sentence says this value is
rejected, and this value is present at this pointer".
"""

SRC = {
    "MCP_SPEC":   "https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json",
    "MCP_TOOLS":  "https://modelcontextprotocol.io/specification/2025-06-18/server/tools",
    "OPENAI_SO":  "https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs",
    "OPENAI_AG":  "https://github.com/openai/openai-agents-python/blob/main/src/agents/strict_schema.py",
    "ANTH_STRICT":"https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use",
    "ANTH_LIMITS":"https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations",
    "ANTH_CPLX":  "https://platform.claude.com/docs/en/build-with-claude/structured-outputs#schema-complexity-limits",
    "ANTH_EMPIR": "https://github.com/anthropics/claude-code/issues/10606",
    "ANTH_SDK":   "https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/lib/_parse/_transform.py",
}

# severity vocabulary
#   hard-reject   the request is rejected (whole server for axis A, request for B/C)
#   silent-loss   accepted, but the constraint is dropped and never enforced
#   empirical     observed in the wild; NOT in any published constraint doc
#   ambiguous     the published docs do not settle this case (excluded from counts)
CODES = {
    # ---- axis A : MCP specification conformance (not opt-in) ----------------
    "A1-inputSchema-missing":       ("A", "hard-reject", "MCP_SPEC",  'Tool.required = ["inputSchema","name"]'),
    "A2-inputSchema-not-object":    ("A", "hard-reject", "MCP_SPEC",  'Tool.required = ["inputSchema","name"]; inputSchema must be an object'),
    "A3-type-missing":              ("A", "hard-reject", "MCP_SPEC",  'inputSchema.properties.type = {"const":"object"}'),
    "A3-type-array":                ("A", "hard-reject", "MCP_SPEC",  'inputSchema.properties.type = {"const":"object"}'),
    "A3-type-not-object":           ("A", "hard-reject", "MCP_SPEC",  'inputSchema.properties.type = {"const":"object"}'),
    "A4-required-not-string-array": ("A", "hard-reject", "MCP_SPEC",  'required: z.array(z.string()).optional()'),
    "A5-name-missing":              ("A", "hard-reject", "MCP_SPEC",  'Tool.required = ["inputSchema","name"]'),
    "A6-outputSchema-type":         ("A", "hard-reject", "MCP_SPEC",  'outputSchema carries the same {"const":"object"} type constraint'),

    # ---- axis B : OpenAI strict mode, hard reject ---------------------------
    "B1-root-anyOf":                ("B", "hard-reject", "OPENAI_SO", "Root objects can't be the anyOf type"),
    "B2-root-nullable":             ("B", "hard-reject", "OPENAI_AG", "_ensure_strict_root: root must be a non-nullable object"),
    "B3-additionalProperties-open": ("B", "hard-reject", "OPENAI_SO", "Always set additionalProperties: false in objects"),
    "B4-no-type-additionalProps":   ("B", "hard-reject", "OPENAI_AG", "_ADDITIONAL_PROPERTIES_ERROR"),
    "B6-too-many-properties":       ("B", "hard-reject", "OPENAI_SO", "up to 100 object properties total, with up to five levels of nesting"),
    "B6-too-deep":                  ("B", "hard-reject", "OPENAI_SO", "up to 100 object properties total, with up to five levels of nesting"),

    # ---- axis B' : OpenAI strict mode, silent constraint loss ---------------
    "B5-unsupported-keyword":       ("B_silent", "silent-loss", "OPENAI_SO",
                                     "unsupported keywords are ignored in strict mode; the constraint is not enforced"),

    # ---- axis C0 : Anthropic Messages API baseline (NOT opt-in) ------------
    "C0-root-combinator":           ("C0", "empirical", "ANTH_EMPIR",
                                     "tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level"),

    # ---- axis C : Anthropic strict:true subset (opt-in, per tool) ----------
    "C1-additionalProperties-not-false": ("C", "hard-reject", "ANTH_LIMITS", "additionalProperties set to anything other than false"),
    "C2-numeric-constraint":             ("C", "hard-reject", "ANTH_LIMITS", "Numerical constraints (such as minimum, maximum, multipleOf)"),
    "C3-string-constraint":              ("C", "hard-reject", "ANTH_LIMITS", "String constraints (minLength, maxLength)"),
    "C4-array-constraint":               ("C", "hard-reject", "ANTH_LIMITS", "Array constraints beyond minItems of 0 or 1"),
    "C5-external-ref":                   ("C", "hard-reject", "ANTH_LIMITS", "External $ref (for example, '$ref': 'http://...')"),
    "C6-recursive-schema":               ("C", "hard-reject", "ANTH_LIMITS", "Recursive schemas"),
    "C7-complex-enum":                   ("C", "hard-reject", "ANTH_LIMITS", "Complex types within enums"),
    "C8-allOf-with-ref":                 ("C", "hard-reject", "ANTH_LIMITS", "anyOf and allOf (with limitations - allOf with $ref not supported)"),

    # ---- axis CL : Anthropic request-scoped complexity limits --------------
    "CL1-too-many-strict-tools":    ("CL", "hard-reject", "ANTH_CPLX",
                                     "Maximum number of tools with strict: true. Non-strict tools don't count toward this limit. (limit: 20)"),
    "CL2-too-many-optional-params": ("CL", "hard-reject", "ANTH_CPLX",
                                     "Total optional parameters across all strict tool schemas and JSON output schemas. Each parameter not listed in required counts toward this limit. (limit: 24)"),
    "CL3-too-many-union-params":    ("CL", "hard-reject", "ANTH_CPLX",
                                     'Total parameters that use anyOf or type arrays (for example, "type": ["string","null"]) across all strict schemas. (limit: 16)'),

    # ---- ambiguous : the published docs do not settle these ----------------
    "AMB-additionalProperties-absent": ("AMB", "ambiguous", "ANTH_LIMITS",
        'Supported list says additionalProperties "must be set to false for objects"; the unsupported list only names values "other than false". Omission is never addressed.'),
    "AMB-numeric":                     ("AMB", "ambiguous", "ANTH_LIMITS",
        'Numerical constraints (such as minimum, maximum, multipleOf) -- "such as" leaves the list open.'),
    "AMB-format-unlisted":             ("AMB", "ambiguous", "ANTH_LIMITS",
        "Ten string formats are enumerated as supported; the docs never say whether a format outside that set is a 400 or is ignored."),
    "AMB-unlisted":                    ("AMB", "ambiguous", "ANTH_LIMITS",
        "Keyword appears in neither the supported nor the unsupported list."),
}


def lookup(code):
    """Resolve a full code (possibly `family:detail`) to its metadata."""
    if code in CODES:
        return CODES[code]
    family = code.split(":", 1)[0]
    if family in CODES:
        return CODES[family]
    return ("?", "unknown", "MCP_SPEC", "")


def meta_for(code):
    axis, severity, src_key, quote = lookup(code)
    return {"axis": axis, "severity": severity,
            "source": SRC[src_key], "source_quote": quote}
