# sdk-bug — filed upstream

An upstream defect found while running the `mcp-schema-census` corpus through
the official Anthropic Python SDK as an independent oracle.

**Filed 2026-08-23 as [anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876).** The issue body
below is what was submitted; the script is what it links to.

## Contents

| file | what it is |
|---|---|
| `repro_type_array_null.py` | a minimal, **from-scratch** reproduction with controls. No third-party schema is pasted anywhere in it. |
| `ISSUE_DRAFT.md` | the issue body, as filed at [#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876) |

## The defect

`anthropic` 1.0.0, `anthropic/lib/_parse/_transform.py::transform_schema`
raises `AssertionError: Expected code to be unreachable, but got: ['string',
'null']` on any schema whose `type` is an array.

`type_` is annotated `Optional[SupportedTypes]` (a union of string literals),
but a list is written into `strict_schema["type"]` unchecked and then falls
through the dispatch chain to `assert_never` — a static-exhaustiveness device
being reached by ordinary runtime input.

`type: ["string","null"]` is what `z.string().nullable()` and `Optional[str]`
emit by default, and the strict-tool-use complexity-limits table explicitly
budgets for "type arrays (for example, `"type": ["string", "null"]`)". The
`anyOf` spelling of the identical constraint transforms fine — only the type-array
spelling crashes.

## Running it

```bash
pip install 'anthropic==1.0.0'
python3 repro_type_array_null.py
```

No API key. No network. Exits 1 if the bug is present.

Observed on `anthropic` 1.0.0 / Python 3.12.13: 4 of 6 cases fail, and both
controls (the `anyOf` spelling, and a plain `type: "string"`) pass.

## Scope

Measured over 14,804 tool schemas from 617 public MCP servers: **88 tools across
30 servers** hit this, of which **75** use an array containing `"null"`. Aggregate
counts only — no third-party schema is reproduced here or in the draft.
