# DRAFT — NOT SUBMITTED

This is a prepared issue body for `anthropics/anthropic-sdk-python`. It has
**not** been filed, and nothing in this directory has been sent anywhere.
Filing it is a separate decision.

Target repo: https://github.com/anthropics/anthropic-sdk-python
Suggested title: `transform_schema raises AssertionError on type arrays (e.g. type: ["string","null"])`

---

## Body

### Summary

`transform_schema` in `anthropic/lib/_parse/_transform.py` raises
`AssertionError: Expected code to be unreachable, but got: ['string', 'null']`
when a JSON Schema uses an array for `type`. It fails before any request is
sent, so a caller gets an `AssertionError` rather than a validation error or a
400.

`type` as an array is valid JSON Schema (draft 4 onward), and it is the default
output of `z.string().nullable()` in Zod and `Optional[str]` in Pydantic — so it
arrives in tool schemas constantly rather than exceptionally.

It is also a shape the strict-tool-use documentation appears to expect. The
complexity-limits table counts these parameters explicitly:

> "Total parameters that use `anyOf` or type arrays (for example,
> `"type": ["string", "null"]`) across all strict schemas."

A schema shape that has its own budget line in the limits table should not be
unrepresentable in the transform.

### Version

- `anthropic` 1.0.0
- Python 3.12.13

### Reproduction

Self-contained, no API key, no network — the failure is in local schema
normalisation:

```python
from anthropic.lib._parse._transform import transform_schema

transform_schema({
    "type": "object",
    "properties": {"cursor": {"type": ["string", "null"]}},
    "required": ["cursor"],
    "additionalProperties": False,
})
```

```
AssertionError: Expected code to be unreachable, but got: ['string', 'null']
```

A runnable script with controls is attached as `repro_type_array_null.py`.
Observed output:

| case | result |
|---|---|
| `{"type": ["string","null"]}` | `AssertionError: ... but got: ['string', 'null']` |
| `{"type": ["integer","null"]}` | `AssertionError: ... but got: ['integer', 'null']` |
| `{"type": ["number","null"]}` | `AssertionError: ... but got: ['number', 'null']` |
| `{"type": ["string","number"]}` | `AssertionError: ... but got: ['string', 'number']` |
| `{"anyOf": [{"type":"string"},{"type":"null"}]}` | OK |
| `{"type": "string"}` | OK |

The last two are controls: the `anyOf` spelling of exactly the same constraint
transforms fine. Only the type-array spelling crashes.

### Cause

In `transform_schema` (`anthropic/lib/_parse/_transform.py`):

```python
type_: Optional[SupportedTypes] = json_schema.pop("type", None)
...
    strict_schema["type"] = type_          # a list is accepted here unchecked
...
elif type_ == "boolean" or type_ == "integer" or type_ == "number" or type_ == "null" or type_ is None:
    pass
else:
    assert_never(type_)                     # reached with type_ == ['string', 'null']
```

`type_` is annotated `Optional[SupportedTypes]`, where `SupportedTypes` is a
union of string literals. A list is not one of them, but nothing enforces that
at runtime: the value is written straight into `strict_schema["type"]`, and then
the dispatch chain falls through to `assert_never`, which is a static-exhaustiveness
device and not an input validator.

So this is a missing input-validation path rather than an intentional
restriction — the annotation says lists cannot occur, and the runtime lets them
in anyway.

### Expected behaviour

Any of these would be an improvement on `AssertionError`; the first seems most
consistent with what the transform already does elsewhere:

1. **Normalise it.** `{"type": ["string","null"]}` is semantically
   `{"anyOf": [{"type":"string"}, {"type":"null"}]}`, and the `anyOf` branch
   already works. The transform already rewrites `oneOf` into `anyOf`, so
   rewriting type arrays the same way would be in keeping with the existing
   design.
2. **Reject it explicitly** with a `ValueError` naming the offending pointer, as
   the sibling path already does for a missing `type`:
   `ValueError: Schema must have a 'type', 'anyOf', 'oneOf', or 'allOf' field.`
3. At minimum, do not surface `assert_never` to callers — an `AssertionError`
   reads as an SDK invariant break, which makes it hard to tell whether the
   caller's schema is at fault.

### How often this shape appears

I hit this while running `transform_schema` over a corpus of 14,804 tool schemas
collected from 617 public MCP servers (real `tools/list` responses, not scraped
manifests). Counts, tool-unit:

| `type` array | tools | servers |
|---|---:|---:|
| `["string","null"]` | 57 | 17 |
| `["integer","null"]` | 9 | 2 |
| `["number","null"]` | 7 | 6 |
| `["string","number"]` | 7 | 3 |
| other arrays (5 shapes) | 8 | 5 |
| **any type array** | **88** | **30** |

75 of the 88 involve an array containing `"null"` — i.e. the plain
"this field is optional/nullable" case, not anything exotic.

For context, in the same run `transform_schema` raised on 75/617 servers overall
(12.2%); this `AssertionError` is the second-largest cause after
`ValueError: Schema must have a 'type', ...` (150 tools).

I have not included any third-party schema in this report. The reproduction
above is written from scratch and the corpus numbers are aggregate counts.
