"""ORACLE, not a rule: run the real Anthropic Python SDK schema transformer.

`anthropic.lib._parse._transform.transform_schema` is the code path the official
SDK uses to make a schema acceptable to the structured-outputs / strict-tool-use
grammar compiler. Everything it KEEPS is API-safe by construction; everything it
moves into the description string is a keyword its own authors treat as
unsupported. That makes it an independent, production-sourced statement of the
same constraint list -- which is why the dataset uses it to corroborate axis C
rather than to define it.

This is a LOCAL function call. It sends nothing anywhere, needs no API key, and
costs nothing. It is separated from `rules/` proper because its verdicts are not
derived from a published sentence: when the transformer raises, that is a
statement about the SDK's implementation, and sometimes about an SDK defect
(see anthropics/anthropic-sdk-python#1876, where a property typed
["string","null"] trips an internal assertion).

Shared by src/oracle_anthropic_sdk.py (corpus run) and
checker/mcp_schema_check.py (--sdk-oracle).
"""
import copy

# Keywords whose disappearance across the transform is evidence the SDK
# considers them unsupported. Frozen list -- changing it changes what the
# corpus's `sdk_oracle.dropped` column means.
WATCH = ["minimum", "maximum", "multipleOf", "exclusiveMinimum", "exclusiveMaximum",
         "minLength", "maxLength", "pattern", "maxItems", "minItems", "uniqueItems",
         "additionalProperties", "format", "const", "default", "propertyNames",
         "patternProperties", "oneOf", "not", "examples"]

SDK_VERSION_MEASURED = "1.0.0"


def available():
    """True if the anthropic package is importable in this interpreter."""
    try:
        from anthropic.lib._parse._transform import transform_schema  # noqa: F401
        return True
    except Exception:
        return False


def sdk_version():
    try:
        import anthropic
        return getattr(anthropic, "__version__", "unknown")
    except Exception:
        return None


def keywords_present(node, acc=None):
    if acc is None:
        acc = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in WATCH:
                acc.add(k)
            if k in ("properties", "$defs", "definitions") and isinstance(v, dict):
                for sub in v.values():
                    keywords_present(sub, acc)
            elif k in ("anyOf", "oneOf", "allOf") and isinstance(v, list):
                for sub in v:
                    keywords_present(sub, acc)
            elif k == "items":
                if isinstance(v, dict):
                    keywords_present(v, acc)
                elif isinstance(v, list):
                    for sub in v:
                        keywords_present(sub, acc)
    return acc


def run_one(schema):
    """Transform one inputSchema. Returns {"raises": str|None, "dropped": [kw]}.

    `additionalProperties` is excluded from `dropped`: the transformer ADDS it,
    never removes it, so counting it would be noise.
    """
    from anthropic.lib._parse._transform import transform_schema

    if not isinstance(schema, dict):
        return {"raises": None, "dropped": []}
    before = keywords_present(copy.deepcopy(schema))
    try:
        after_schema = transform_schema(copy.deepcopy(schema))
    except Exception as e:  # noqa: BLE001
        return {"raises": type(e).__name__ + ": " + str(e)[:120], "dropped": []}
    after = keywords_present(after_schema)
    return {"raises": None,
            "dropped": sorted((before - after) - {"additionalProperties"})}
