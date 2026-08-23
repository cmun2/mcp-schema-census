"""One-line remediation per verdict code.

This is PRESENTATION, not a rule. It never decides whether something fails --
codes.py and the two judge modules do that. It only answers "so what do I
change?" once a code has already fired.

It lives next to codes.py on purpose: a second registry keyed by the same
codes, kept in a different file tree, is exactly the drift the rule engine is
structured to prevent. `tests/test_rules_single_source.py` asserts every
non-ambiguous code in CODES has an entry here.

Each hint is phrased as an edit to YOUR schema, not as a complaint. Where the
fix costs you a real constraint (the provider will not enforce it either way),
the hint says so rather than pretending the change is free.
"""

FIXES = {
    # ---- axis A : MCP specification conformance -------------------------
    "A0-tool-not-object":           'emit each tool as a JSON object; a bare scalar in the `tools` array fails the spec parse.',
    "A1-inputSchema-missing":       'add `"inputSchema": {"type": "object", "properties": {}}` -- it is required even when the tool takes no arguments.',
    "A2-inputSchema-not-object":    'inputSchema must be a JSON object, not `true`/`false`/a string; a Go `interface{}` or a bare `true` schema serialises to this.',
    "A3-type-missing":              'add `"type": "object"` to the root of inputSchema.',
    "A3-type-array":                'the root `type` must be the string "object", not a one-element array; write `"type": "object"`.',
    "A3-type-not-object":           'set the root `type` to "object"; a top-level array/string schema is not a valid tool input.',
    "A4-properties-not-object":     '`properties` must be an object mapping name -> schema; an array or null here fails the spec parse.',
    "A4-required-not-string-array": '`required` must be an array of strings -- drop the key entirely rather than emitting `null`.',
    "A5-name-missing":              'give the tool a non-empty string `name`.',
    "A6-outputSchema-not-object":   'outputSchema must be a JSON object, or omitted entirely.',
    "A6-outputSchema-type":         'set `outputSchema.type` to "object", or drop outputSchema if the tool returns unstructured content.',
    "A-oracle-reject":              'the official MCP SDK rejected this tool; the parse error above names the field.',

    # ---- axis B : OpenAI strict mode, hard reject ------------------------
    "B1-root-anyOf":                'lift the root `anyOf` into a single object with a discriminator property; strict mode cannot branch at the root.',
    "B2-root-nullable":             'the root must be a plain non-nullable object: `"type": "object"`, not a type array.',
    "B2-root-not-object":           'wrap the schema in an object: `{"type":"object","properties":{"value": <your schema>},"required":["value"],"additionalProperties":false}`.',
    "B3-additionalProperties-open": 'set `"additionalProperties": false` on this object (strict mode rejects any other value).',
    "B4-untyped-open-object":       'add `"type": "object"` and `"additionalProperties": false` to this node, or give it a concrete type.',
    "B4-no-type-additionalProps":   'add `"type": "object"` and `"additionalProperties": false` to this node, or give it a concrete type.',
    "B6-too-many-properties":       'split the tool: strict mode allows 100 object properties per schema, counted across all nesting levels.',
    "B6-too-deep":                  'flatten to at most 5 levels of nesting -- promote the deep sub-object to a sibling property or a separate tool.',

    # ---- axis B' : OpenAI strict mode, silent constraint loss ------------
    "B5-unsupported-keyword":       'strict mode drops this keyword silently -- it is NOT enforced. Re-validate it inside your handler, or state the rule in the description.',

    # ---- axis C0 : Anthropic Messages API baseline (NOT opt-in) ----------
    "C0-root-combinator":           'move the oneOf/allOf/anyOf off the root: keep a flat root object and put the branch under a property.',

    # ---- axis C : Anthropic strict:true subset ---------------------------
    "C1-additionalProperties-not-false": 'set `"additionalProperties": false` -- strict:true rejects every other value.',
    "C2-numeric-constraint":        'remove minimum/maximum/multipleOf and range-check the value in your handler instead.',
    "C3-string-constraint":         'remove minLength/maxLength and length-check in your handler instead (`pattern` IS supported on this axis).',
    "C4-array-constraint":          'remove maxItems/uniqueItems; only `minItems` of 0 or 1 survives. Enforce the rest in your handler.',
    "C5-external-ref":              'inline the referenced schema, or move it into `$defs` and use a local `#/$defs/...` pointer.',
    "C6-recursive-schema":          'unroll to a fixed depth, or replace the recursive node with `{"type":"string"}` carrying serialised JSON.',
    "C7-complex-enum":              'enum members must be scalars; replace the object/array members with a discriminator string.',
    "C7-enum-complex-type":         'enum members must be scalars; replace the object/array members with a discriminator string.',
    "C8-allOf-with-ref":            'inline the $ref subschema into the allOf branch, or merge the branches into one object.',

    # ---- axis CL : Anthropic request-scoped complexity limits -----------
    "CL1-too-many-strict-tools":    'at most 20 tools may carry strict:true in one request -- leave the rest non-strict, or split the server.',
    "CL2-too-many-optional-params": 'at most 24 optional parameters across all strict schemas -- move rarely-used arguments into `required` with a sentinel, or split the tool.',
    "CL3-too-many-union-params":    'at most 16 union-typed parameters (anyOf or type arrays) across all strict schemas -- pick one concrete type per parameter.',

    # ---- ambiguous : reported, never counted, never fatal ---------------
    "AMB-additionalProperties-absent": 'not a verdict. The docs say additionalProperties "must be set to false for objects" but never say omission is an error. Setting it to false is the safe read.',
    "AMB-numeric":                  'not a verdict. The unsupported list is a "such as" list, so this keyword may or may not 400. Removing it is the safe read.',
    "AMB-array":                    'not a verdict. "beyond minItems of 0 or 1" is open-ended; removing the keyword is the safe read.',
    "AMB-format-unlisted":          'not a verdict. The docs enumerate 10 supported formats and never say what happens to others; the Python SDK strips them.',
    "AMB-unlisted":                 'not a verdict. This keyword is in neither the supported nor the unsupported list.',
}


def fix_for(code):
    """Resolve a full code (possibly `family:detail`) to its one-line fix."""
    if code in FIXES:
        return FIXES[code]
    family = code.split(":", 1)[0]
    return FIXES.get(family, "")
