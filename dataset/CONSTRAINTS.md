# Constraint tables

Every rule applied in this dataset, the URL it came from, and the sentence it
came from. **Constraints checked: 2026-08-23.** Provider documentation changes;
re-check before reusing these verdicts (see "Re-checking" at the bottom).

Nothing in this file is inferred. Where a document does not settle a case, it
appears under [Ambiguities](#ambiguities) with an `AMB-` code and is excluded
from every count in this dataset.

---

## Sources

| key | URL |
|---|---|
| **S-MCP** | https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json |
| **S-MCP-SPEC** | https://modelcontextprotocol.io/specification/2025-06-18/server/tools |
| **S-MCP-SDK** | https://github.com/modelcontextprotocol/typescript-sdk |
| **S-OAI-DOC** | https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs |
| **S-OAI-IMPL** | https://github.com/openai/openai-agents-python/blob/main/src/agents/strict_schema.py |
| **S-OAI-MCP** | https://github.com/openai/openai-agents-python/blob/main/src/agents/mcp/util.py |
| **S-ANT-STRICT** | https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use |
| **S-ANT-LIMITS** | https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations |
| **S-ANT-CPLX** | https://platform.claude.com/docs/en/build-with-claude/structured-outputs#schema-complexity-limits |
| **S-ANT-EMPIRICAL** | https://github.com/anthropics/claude-code/issues/10606 |
| **S-ANT-SDK** | `anthropic` Python SDK 1.0.0, `anthropic/lib/_parse/_transform.py` |

The Anthropic pages have an unauthenticated Mintlify `.md` endpoint, so the
constraint text can be re-fetched for free and diffed:

```bash
curl -sL https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
```

---

## Axis A — MCP specification conformance

**Not opt-in.** This is the only axis where one bad tool takes down the whole
server: `ListToolsResultSchema` wraps tools in `z.array(ToolSchema)`, and a Zod
array fails entirely if any element fails. `client.listTools()` throws, so the
client sees **zero** tools from that server.

```ts
const ListToolsResultSchema = PaginatedResultSchema.extend({ tools: z.array(ToolSchema) })
```

| code | rejected | basis |
|---|---|---|
| `A1-inputSchema-missing` | no `inputSchema` | S-MCP `Tool.required = ["inputSchema","name"]` |
| `A2-inputSchema-not-object` | `inputSchema` is not a JSON object (e.g. bare `true`, which Go's `interface{}` can emit) | same |
| `A3-type-missing` / `A3-type-array` / `A3-type-not-object` | `inputSchema.type` absent, a type array, or not `"object"` | S-MCP `inputSchema.properties.type = {"const":"object"}` |
| `A4-required-not-string-array` | `required` is not an array of strings (`null` included) | S-MCP `required: z.array(z.string()).optional()` |
| `A5-name-missing` | `name` absent or not a string | S-MCP `Tool.required` |
| `A6-outputSchema-type` | `outputSchema.type` not `"object"` | S-MCP, same constraint as `inputSchema` |

**Judged by** the real parser, not by our rules: MCP TypeScript SDK 1.30.0
`ListToolsResultSchema.safeParse()`.

**Result: 0/617.** Not one server in the corpus trips this. The 2026-08-09
report explains why: npm servers overwhelmingly use the official TypeScript SDK,
which *generates* `inputSchema` from Zod, and PyPI servers use FastMCP, which
generates it from Pydantic. A hand-written violation is not expressible when no
human writes the schema.

---

## Axis B / B′ — OpenAI `strict` mode

**Opt-in, and per tool.** In `openai-agents`,
`convert_schemas_to_strict` defaults to `False`, and even when enabled,
`to_function_tool` catches a per-tool conversion failure and demotes that tool
to non-strict. The server does not go down; that one tool loses its strict
guarantee.

### B — hard reject (conversion raises)

| code | rejected | quote / basis |
|---|---|---|
| `B1-root-anyOf` | root schema is an `anyOf` | S-OAI-DOC "Root objects can't be the `anyOf` type" |
| `B2-root-nullable` | root is nullable or not an object | S-OAI-IMPL `_ensure_strict_root` |
| `B3-additionalProperties-open` | an object sets `additionalProperties` to anything but `false` | S-OAI-DOC "Always set `additionalProperties: false` in objects" |
| `B4-no-type-additionalProps` | no `type` and a truthy `additionalProperties` | S-OAI-IMPL `_ADDITIONAL_PROPERTIES_ERROR` |
| `B6-too-many-properties` | more than 100 object properties in total | S-OAI-DOC "up to 100 object properties total, with up to five levels of nesting" |
| `B6-too-deep` | nesting deeper than 5 levels | same |

**Judged by** `openai-agents`' `ensure_strict_json_schema` — the real converter.

### B′ — silent constraint loss (accepted, never enforced)

`B5-unsupported-keyword:<keyword>` for each of:

```
minLength maxLength pattern format
minimum maximum multipleOf
patternProperties unevaluatedProperties propertyNames minProperties maxProperties
unevaluatedItems contains minContains maxContains minItems maxItems uniqueItems
```

Basis: S-OAI-DOC's unsupported-keyword list. These do not raise. The request
succeeds and the constraint is simply not applied — which is why B′ matters:
it is the failure mode nobody sees.

---

## Axis C0 — Anthropic Messages API baseline

**Not opt-in.** Applies to every tool sent to `/v1/messages`, strict or not.

| code | rejected | basis |
|---|---|---|
| `C0-root-combinator:oneOf` / `:allOf` / `:anyOf` | root-level combinator in `input_schema` | S-ANT-EMPIRICAL, observed 400: `tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level` |

**This one is marked `empirical`, not `hard-reject`, on purpose.** That error
string does not appear in any published constraint document. Its only basis is
public bug reports. We treat it as a rule because it was observed, and we label
it so nobody mistakes it for documentation.

Four independent reports of this exact string were read on 2026-08-23:
[claude-code#10606](https://github.com/anthropics/claude-code/issues/10606)
(closed not-planned by a staleness bot, no maintainer reply),
[claudesidian-mcp#6](https://github.com/ProfSynapse/claudesidian-mcp/issues/6),
[countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64),
and, for the generic draft-2020-12 variant,
[claude-code#1690](https://github.com/anthropics/claude-code/issues/1690)
(closed by a maintainer with "IIUC, this is working as expected").
**No client-version attribution is made.** An earlier draft of this file said
"Claude Code v2.0.21 began forwarding this", following the title of #10606.
That is not supported: the reporter's own follow-up says v2.0.20 rejected the
same packages, and #6 hit the identical 400 on v1.0.35 on 2025-06-27, four
months before v2.0.21. See `README.md` > "Field evidence".

**Result: 0/617.**

---

## Axis C — Anthropic `strict: true` JSON Schema subset

**Opt-in, per tool.** S-ANT-STRICT: set `strict: true` at the top level of the
tool definition; "The schema uses standard JSON Schema format with some
limitations" — and defers the limitation list to S-ANT-LIMITS.

S-ANT-LIMITS is explicit that this is a rejection, not a degradation:

> "Structured outputs support standard JSON Schema with some limitations. **Both
> JSON outputs and strict tool use share these limitations.**"
>
> "If you use an unsupported feature, you'll receive a **400 error with details**."

### Rejected — quoted verbatim from the "Not supported" list

| code | verbatim constraint |
|---|---|
| `C1-additionalProperties-not-false` | "`additionalProperties` set to anything other than `false`" |
| `C2-numeric-constraint:*` | "Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)" |
| `C3-string-constraint:*` | "String constraints (`minLength`, `maxLength`)" |
| `C4-array-constraint:*` | "Array constraints beyond `minItems` of 0 or 1" → `maxItems`, `uniqueItems`, `minItems` ≥ 2 |
| `C5-external-ref` | "External `$ref` (for example, `'$ref': 'http://...'`)" |
| `C6-recursive-schema` | "Recursive schemas" |
| `C7-complex-enum` | "Complex types within enums" |
| `C8-allOf-with-ref` | "`anyOf` and `allOf` (with limitations — **`allOf` with `$ref` not supported**)" |

### Supported — and different from OpenAI

| keyword | Anthropic | OpenAI `strict` |
|---|---|---|
| `pattern` (regex) | **supported.** S-ANT-LIMITS has a dedicated "Pattern support (regex)" section; only backreferences, lookahead, `\b` and large `{n,m}` are excluded | silently ignored |
| optional parameters (not in `required`) | **supported**, subject to a 24-per-request total | every property must appear in `required` |
| `minItems` 0 or 1 | supported | ignored |
| string `format` | enumerated: `date-time, time, date, duration, email, hostname, uri, ipv4, ipv6, uuid` | all `format` values ignored |

This is why `pattern` is *not* a violation on axis C and *is* a silent loss on
axis B′ — the same keyword, opposite disposition.

---

## Axis CL — Anthropic request complexity limits

S-ANT-CPLX, "Explicit limits" table, quoted:

| code | limit | verbatim |
|---|---:|---|
| `CL1-too-many-strict-tools` | **20** | "Maximum number of tools with `strict: true`. Non-strict tools don't count toward this limit." |
| `CL2-too-many-optional-params` | **24** | "Total optional parameters across all strict tool schemas and JSON output schemas. **Each parameter not listed in `required` counts toward this limit.**" |
| `CL3-too-many-union-params` | **16** | "Total parameters that use `anyOf` or type arrays (for example, `\"type\": [\"string\", \"null\"]`) across all strict schemas." |

> S-ANT-CPLX note: "These limits apply to the **combined total across all strict
> schemas in a single request**."

**This makes 37.3% a lower bound, not an estimate.** We measure each server as
if it were alone in the request. A real client that connects three servers hits
these ceilings sooner, never later.

S-ANT-CPLX also mentions undocumented internal limits — a 400 reading `"Schema
is too complex for compilation."` and a 180-second compilation timeout. Neither
is quantified, so neither is measured here.

---

## Ambiguities

Cases the documentation does not settle. Emitted with an `AMB-` code, **excluded
from every count**, and reported in README.md.

| code | servers | hits | why unresolved |
|---|---:|---:|---|
| `AMB-additionalProperties-absent` | 412 | 6,690 | The supported list says `additionalProperties` "must be set to `false` for objects". The unsupported list names only values "other than `false`". Omission is addressed nowhere. The SDK always **adds** `additionalProperties: false` (S-ANT-SDK: "Add `additionalProperties: false` to all objects"), which suggests the API requires it — but "the SDK compensates" is not the same claim as "the API rejects". |
| `AMB-numeric:exclusiveMinimum`, `:exclusiveMaximum` | 69 | 380 | "Numerical constraints (**such as** …)" — an open list. |
| `AMB-unlisted:oneOf` | 13 | 329 | `anyOf` and `allOf` are named as supported. `oneOf` is in neither list. The SDK rewrites `oneOf` into `anyOf` (S-ANT-SDK). |
| `AMB-unlisted:propertyNames` | 29 | 165 | in neither list |
| `AMB-unlisted:not`, `:if`, `:then`, `:minProperties`, `:dependentRequired` | 1–2 each | 1–7 each | in neither list |
| `AMB-format-unlisted:*` | 15 | 110 | Ten formats are enumerated as supported; whether an unlisted format is a 400 or is ignored is not stated. The SDK strips it and appends it to a description string. |

### The documentation contradicts the official SDK

S-ANT-LIMITS lists `const`, `default` and `pattern` as **supported**. S-ANT-SDK
**removes all three** from the wire schema and appends them to a description
string. Only calling the endpoint settles which behaviour is authoritative, and
this run did not call it. Our rules follow the documentation, which is why the
oracle comparison shows 82 "false negatives" that are not errors — they are this
contradiction, counted.

---

## Redistribution

The rules above are ours; the sentences they quote are the providers'. The
schemas they were applied to are the server authors'.

We publish the verdicts, the JSON pointers and the constraint values that
triggered them. We do **not** publish any prose written by a server author —
`description`, `title`, `$comment`, `summary`, `examples`, `example` and their
variants are stripped at every depth by `scripts/prose.py::strip_prose()`,
replaced by a length and a 12-character digest.

`scripts/verify_no_prose.py` is the gate: it scans all 47,766 published records
and must find **0** prose fields, **0** credentials and **0** email addresses.
`scripts/verify_verdicts.py` proves the removal cost nothing analytically —
19,159 hits re-derived from the stripped schemas, 0 differences.

See [LICENSE](LICENSE) for the full statement, including how to check any
individual server's own license.

---

## Re-checking

These verdicts are only as current as the documents. To re-verify:

```bash
mkdir -p snapshots
curl -sL https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md \
  > snapshots/anthropic-$(date +%F).md
```

No snapshot of the provider's page is checked in — we quote it, we do not
redistribute it. What this file records instead is every sentence the rules were
derived from, verbatim, as read on 2026-08-23. Diff a fresh fetch against the
quotes above.

If the constraint table moved, re-run `scripts/judge_anthropic.py` over the
corpus — seconds, no network — and bump `verdicts_computed_at` only.
`schemas_collected_at` stays where it was. Keeping the two dates separate is the
point: "schemas from August, judged against November's constraint table" is a
real and legitimate state, and it should be visible rather than hidden.
