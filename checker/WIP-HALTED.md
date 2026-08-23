# checker/ — HALTED before any code was written

**Status: stopped 2026-08-23, by explicit instruction, after a pre-build
falsification pass. No source file was ever created in this directory.**

The plan was a `mcp-schema-check` CLI for server authors: launch your own
stdio server (or feed it a `tools/list` dump), and get back, per provider
axis, which of your tool schemas would be rejected — with the tool name, the
JSON pointer, the offending value, the verbatim sentence from the provider's
own documentation, and a one-line fix. The verdict rules were to be the
existing engine in `../dataset/scripts/` (`judge_anthropic.py`,
`judge_mcp_and_openai.py`, `codes.py`), imported rather than re-implemented,
so the checker and the dataset could not drift apart.

## Why it stopped

A search for prior art turned up five existing tools in the same space. They
were checked before writing code rather than after. See
[`../dataset/README.md` § Related work](../dataset/README.md#related-work)
for what each one was verified to check, and how.

- **Official MCP Inspector** — <https://github.com/modelcontextprotocol/inspector>
  - `npx @modelcontextprotocol/inspector --cli --method tools/list`
  - issue #1005, *Feature: Strict JSON Schema validation with actionable error
    messages in CLI mode* — <https://github.com/modelcontextprotocol/inspector/issues/1005>
- **`@yawlabs/mcp-compliance`** — <https://github.com/YawLabs/mcp-compliance>
  - `npx @yawlabs/mcp-compliance@latest test <target>`; 88 tests, 8 categories, A–F grade
  - published rule catalog: `mcp-compliance-rules.json`
- **mcptools.tools** — <https://mcptools.tools/schema-validator>
- **DevTk.AI MCP Config Validator** — <https://devtk.ai/en/tools/mcp-validator/>
- **mcpserverspot** — <https://www.mcpserverspot.com/tools/validator>
- (turned up while reading #1005) **mcp-probe / `mcp-conform`** —
  <https://github.com/castrocrest/mcp-probe-cli>

## Two corrections to the record, since they bear on any restart

1. **The MCP Inspector has no `--strict` flag.** `clients/cli/src/cli.ts`
   (40,381 bytes, read 2026-08-23) contains zero occurrences of the string
   `strict`, and `--strict` is not among the long-form flags defined there.
   The `--cli --method tools/list --strict` invocation that circulates is text
   from the *proposal body* of issue #1005. That issue is **open and not
   approved for work** — triaged 2026-08-01 at 7/16 ("Medium"), project board
   status "Incoming".

2. **None of the five checks a provider strict-mode subset.** Every one of
   them validates MCP-specification conformance, or client-config / style
   hygiene. That is the axis this corpus already measures at **0.0%** (axis
   A, 0/617). The provider-specific axes — OpenAI `strict`, Anthropic
   `strict: true`, the Anthropic Messages API baseline — are not covered by
   any of them. Evidence, per tool, is in the Related work section linked
   above; the strongest single piece is `mcp-compliance-rules.json` (47,917
   bytes, 88 rules), which contains zero occurrences of `anyOf`, `oneOf`,
   `allOf`, `additionalProperties`, `minLength`, `maxLength`, `minimum`,
   `maximum`, `maxItems`, `uniqueItems`, `input_schema`, `Anthropic`, or
   `OpenAI`.

So the gap the checker aimed at is not filled by these tools. It was still
right to stop and re-decide rather than build on an unchecked premise — and
whether that gap is worth a sixth tool, versus a rule contribution to one of
the five that already has distribution, is the open question.

## If it restarts

The design constraint that mattered most: **do not re-write the rules.** The
dataset's numbers and a checker's output have to come from one engine, or the
two will disagree within a release and neither will be trustworthy. Import
`dataset/scripts/judge_anthropic.py` and `dataset/scripts/judge_mcp_and_openai.py`;
add only presentation (fix hints, formatting, exit codes) on top.

One rule-level bug was noticed while reading the engine and is **not** fixed,
because fixing it here would have been out of scope: `judge_anthropic.py`
emits the code `C7-enum-complex-type`, while `codes.py` registers it as
`C7-complex-enum`. `codes.lookup()` therefore falls through to
`("?", "unknown", …)` for that code. No row in the published corpus carries
it (0 hits in `violations.jsonl`), so no verdict, count, or rate is affected —
but any consumer that hits a complex-enum schema would get an unresolved
axis and an empty source quote.
