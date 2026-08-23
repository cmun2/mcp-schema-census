#!/usr/bin/env python3
"""strip_prose() -- the single place where third-party authored text is removed.

LEGAL RULE (see CONSTRAINTS.md "Redistribution"):
  This dataset redistributes VERDICTS about third-party schemas, never the
  third-party prose those schemas contain. Every free-text field written by a
  server author is removed here and replaced by two non-expressive facts:
  its length in characters and the first 12 hex chars of its sha256.

WHAT IS REMOVED (PROSE_KEYS, unconditionally, wherever the key sits in a JSON
Schema *keyword* position):
    description, title, $comment, summary, examples, example,
    markdownDescription, deprecationMessage, errorMessage, x-description
`examples`/`example` are dropped whatever their type -- they routinely hold
objects full of author-written sample text, not just strings.

WHAT IS KEPT (this is deliberate -- it is what the dataset is FOR):
    property names, type, enum, const, default, required, format,
    pattern (a regex is a machine constraint, not prose),
    every numeric/string/array constraint VALUE that produced a verdict
    (minimum, maxLength, minItems, ...), $ref targets, structure and nesting.

KEY SUBTLETY: a schema may legitimately declare a *property named*
"description". That name lives under `properties` / `$defs` / ... and is a
name, not a keyword, so it must survive. strip_prose() is therefore
schema-aware: inside a name-map it recurses into the values but never treats
the keys as keywords.
"""
import hashlib
import json

PROSE_KEYS = frozenset({
    "description", "title", "$comment", "summary",
    "examples", "example",          # author-supplied sample content
    "markdownDescription", "deprecationMessage", "errorMessage",
    "message",                      # zod/ajv custom validation text
    "x-description",
})

# keyword -> {name: schema}. Keys here are AUTHOR-CHOSEN NAMES, not keywords.
NAME_MAP_KEYWORDS = frozenset({
    "properties", "$defs", "definitions", "patternProperties",
    "dependentSchemas", "dependencies",
})

# keyword -> raw JSON value. Recursing into these would misread data as schema.
VALUE_KEYWORDS = frozenset({
    "enum", "const", "default", "required", "type", "format", "pattern",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "minItems", "maxItems", "uniqueItems",
    "minProperties", "maxProperties", "minContains", "maxContains",
    "$ref", "$schema", "$id", "$anchor", "dependentRequired",
    "readOnly", "writeOnly", "deprecated",
})


def sha12(s):
    """First 12 hex chars of sha256 -- an identifier, not the text."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _is_prose_value(v):
    if isinstance(v, str):
        return True
    if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
        return True
    return False


def strip_prose(node, in_schema=True):
    """Return a copy of `node` with every third-party prose field removed.

    `in_schema` tracks whether dict keys at this level are JSON Schema
    keywords (True) or author-chosen names (False).
    """
    if isinstance(node, list):
        return [strip_prose(x, in_schema) for x in node]
    if not isinstance(node, dict):
        return node

    out = {}
    for k, v in node.items():
        if in_schema and k in PROSE_KEYS:
            # Dropped unconditionally. `examples`/`example` routinely hold
            # objects, not strings, and those objects are prose too.
            continue
        if in_schema and k in VALUE_KEYWORDS:
            # Raw data value. Do not read its keys as schema keywords, but do
            # scrub prose keys nested inside it (an enum member may be an
            # object carrying its own author-written description).
            out[k] = _scrub_data(v)
            continue
        if in_schema and k in NAME_MAP_KEYWORDS and isinstance(v, dict):
            out[k] = {name: strip_prose(sub, True) for name, sub in v.items()}
            continue
        if (in_schema and isinstance(v, str)
                and k not in STRING_BEARING_KEYWORDS):
            # Unknown keyword carrying free text. By definition it is not a
            # constraint any judge reads, so dropping it cannot move a verdict
            # (build_dataset.py asserts that), and keeping it is how prose we
            # never thought of survives. Symmetric with prose_findings()'s
            # allowlist backstop -- see the note in that docstring.
            continue
        # everything else: still a schema position (items, anyOf, not, ...)
        out[k] = strip_prose(v, in_schema)
    return out


def _scrub_data(node):
    """Remove prose keys from a raw DATA value (enum member, const, default).

    Keys here are data keys, not schema keywords, so this is deliberately
    narrow: it removes only keys in PROSE_KEYS whose value is a string or a
    collection of strings -- i.e. author-written text carried inside a value.
    """
    if isinstance(node, list):
        return [_scrub_data(x) for x in node]
    if not isinstance(node, dict):
        return node
    return {k: _scrub_data(v) for k, v in node.items()
            if not (k in PROSE_KEYS and _is_prose_value(v))}


# Keywords whose value may legitimately BE a string we deliberately keep.
# Anything outside this set holding a string is an unknown keyword, and an
# unknown keyword carrying free text is exactly how author prose sneaks in.
STRING_BEARING_KEYWORDS = frozenset({
    "type", "format", "pattern", "$ref", "$schema", "$id", "$anchor",
    "const", "default", "enum", "contentEncoding", "contentMediaType",
    "$dynamicRef", "$dynamicAnchor", "$vocabulary",
})


# Record fields whose value is a third-party schema. Everything OUTSIDE these
# is our own envelope (server_name, verdicts, our judgment messages) and is not
# subject to the prose rules -- we wrote it.
SCHEMA_BEARING_FIELDS = frozenset({
    "input_schema", "output_schema", "input_schemas", "output_schemas",
    "schema", "subschema",
})


def prose_findings(node, path="$", findings=None, keys_are_names=False,
                   in_schema=False):
    """Independent auditor used by verify_no_prose.py.

    It does NOT share strip_prose()'s traversal, so a bug there cannot hide
    itself here. Inside third-party schema subtrees, two rules apply:

    1. DENYLIST -- flag any key in PROSE_KEYS sitting in a keyword position.
    2. ALLOWLIST BACKSTOP -- flag any *unknown* keyword whose value is a
       string. Rule 1 alone can only catch prose we already thought of, and
       it shares PROSE_KEYS with strip_prose(), so a key missing from that
       set is invisible to both. Rule 2 caught `allOf[].message` (zod custom
       errors), which rule 1 missed.

    Rule 2 shrinks the blind spot rather than removing it: it shares
    STRING_BEARING_KEYWORDS with strip_prose(), so a prose key wrongly added
    to that allowlist would still hide from both. That set is deliberately
    short and holds only well-known JSON Schema keywords, which is a far
    smaller surface than an open-ended denylist -- but it is not zero.

    Both rules know that keys directly under `properties` / `$defs` / ... are
    author-chosen NAMES -- a property legally named "description" is a name,
    not prose, and is not flagged.

    SCOPE: rules fire only under SCHEMA_BEARING_FIELDS. Our own envelope is
    exempt by construction -- `violations.message` is our verdict text, not a
    server author's, and flagging it would drown the real findings.
    """
    MODE_ENVELOPE, MODE_SCHEMA, MODE_NAMES, MODE_DATA = 0, 1, 2, 3
    mode = MODE_SCHEMA if in_schema else MODE_ENVELOPE
    if keys_are_names:
        mode = MODE_NAMES
    if in_schema == "data":
        mode = MODE_DATA

    if findings is None:
        findings = []
    if isinstance(node, dict):
        for k, v in node.items():
            if mode == MODE_SCHEMA and k in PROSE_KEYS:
                prev = v if isinstance(v, str) else json.dumps(v)[:80]
                findings.append({"path": f"{path}.{k}", "key": k,
                                 "rule": "denylist", "preview": prev[:80]})
            elif (mode == MODE_SCHEMA and isinstance(v, str)
                    and k not in STRING_BEARING_KEYWORDS):
                findings.append({"path": f"{path}.{k}", "key": k,
                                 "rule": "unknown-keyword", "preview": v[:80]})
            elif mode == MODE_DATA and k in PROSE_KEYS and _is_prose_value(v):
                # Mirrors _scrub_data(): inside a raw data value the keys are
                # data keys, so only author text under a known prose key counts.
                prev = v if isinstance(v, str) else json.dumps(v)[:80]
                findings.append({"path": f"{path}.{k}", "key": k,
                                 "rule": "prose-in-data", "preview": prev[:80]})

            if mode == MODE_SCHEMA and k in VALUE_KEYWORDS:
                nxt = "data"                       # raw value: stop reading keys as keywords
            elif mode == MODE_DATA:
                nxt = "data"
            elif mode == MODE_SCHEMA and k in NAME_MAP_KEYWORDS:
                nxt = True                         # author-chosen names one level down
            elif mode in (MODE_SCHEMA, MODE_NAMES):
                nxt = True
            else:
                nxt = k in SCHEMA_BEARING_FIELDS
            prose_findings(v, f"{path}.{k}", findings,
                           keys_are_names=(mode == MODE_SCHEMA
                                           and k in NAME_MAP_KEYWORDS),
                           in_schema=nxt)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            prose_findings(v, f"{path}[{i}]", findings, keys_are_names=False,
                           in_schema=("data" if mode == MODE_DATA
                                      else mode in (MODE_SCHEMA, MODE_NAMES)))
    return findings


def walk_strings(node, path="$"):
    """Yield (path, string) for every string value anywhere in `node`."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node
