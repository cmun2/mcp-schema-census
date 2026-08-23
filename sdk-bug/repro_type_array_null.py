#!/usr/bin/env python3
"""Minimal reproduction: anthropic 1.0.0 transform_schema raises AssertionError
on a JSON Schema that uses a nullable type array.

    type: ["string", "null"]

This schema is written from scratch for this reproduction. It is not copied
from anyone's server. It is the shape that Zod's `.nullable()` and Pydantic's
`Optional[str]` produce by default, so any tool schema generated from either
can hit it.

No network access. No API key. No request is sent -- the failure happens in
the SDK's local schema normalisation, before anything leaves the process.

    pip install 'anthropic==1.0.0'
    python3 repro_type_array_null.py
"""
import json
import sys
import traceback

try:
    import anthropic
    from anthropic.lib._parse._transform import transform_schema
except Exception as e:                                    # pragma: no cover
    print(f"cannot import the SDK: {e}")
    print("install it with:  pip install 'anthropic==1.0.0'")
    raise SystemExit(2)

print(f"anthropic version: {getattr(anthropic, '__version__', 'unknown')}")
print(f"python:            {sys.version.split()[0]}\n")


CASES = [
    ("nullable string  -- zod .nullable() / pydantic Optional[str]", {
        "type": "object",
        "properties": {"cursor": {"type": ["string", "null"]}},
        "required": ["cursor"],
        "additionalProperties": False,
    }),
    ("nullable integer -- pydantic Optional[int]", {
        "type": "object",
        "properties": {"limit": {"type": ["integer", "null"]}},
        "required": ["limit"],
        "additionalProperties": False,
    }),
    ("nullable number", {
        "type": "object",
        "properties": {"score": {"type": ["number", "null"]}},
        "required": ["score"],
        "additionalProperties": False,
    }),
    ("union without null -- zod z.union([z.string(), z.number()])", {
        "type": "object",
        "properties": {"id": {"type": ["string", "number"]}},
        "required": ["id"],
        "additionalProperties": False,
    }),
    ("CONTROL: the anyOf spelling of the same thing (expected to work)", {
        "type": "object",
        "properties": {"cursor": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
        "required": ["cursor"],
        "additionalProperties": False,
    }),
    ("CONTROL: plain string (expected to work)", {
        "type": "object",
        "properties": {"cursor": {"type": "string"}},
        "required": ["cursor"],
        "additionalProperties": False,
    }),
]

failures = 0
for label, schema in CASES:
    print("-" * 72)
    print(label)
    print("  schema: " + json.dumps(schema["properties"]))
    try:
        transform_schema(schema)
        print("  -> OK")
    except AssertionError as e:
        failures += 1
        print(f"  -> AssertionError: {e}")
        tb = traceback.extract_tb(sys.exc_info()[2])[-1]
        print(f"     raised at {tb.filename}:{tb.lineno}  ({tb.line})")
    except Exception as e:
        failures += 1
        print(f"  -> {type(e).__name__}: {e}")

print("-" * 72)
print(f"\n{failures} of {len(CASES)} cases failed.")
print("\nExpected, if the bug is present: the four type-array cases raise")
print("AssertionError from an assert_never / unreachable branch, and the two")
print("controls pass. `type` as an array is valid JSON Schema (draft 4 onward)")
print("and the SDK's own docs describe type arrays as a supported input to")
print("strict schemas -- the complexity-limits table counts them explicitly:")
print('  "Total parameters that use anyOf or type arrays (for example,')
print('   \\"type\\": [\\"string\\", \\"null\\"]) across all strict schemas."')
raise SystemExit(1 if failures else 0)
