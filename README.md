# mcp-schema-census

[![data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue)](dataset/LICENSE)
[![code: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![servers: 617](https://img.shields.io/badge/servers-617-informational)](dataset/servers.jsonl)
[![tool schemas: 14,804](https://img.shields.io/badge/tool%20schemas-14%2C804-informational)](dataset/tools.jsonl)

**Your MCP server is valid MCP and still gets a 400 from Claude. This tells you
why, at which JSON pointer, quoting the sentence the rejection rests on.**

```console
$ git clone https://github.com/cmun2/mcp-schema-census && cd mcp-schema-census
$ ./checker/mcp-schema-check --cmd "npx -y your-server"

  axis                                          scope  verdict  tools   corpus
  --------------------------------------------------------------------------
  MCP specification conformance                always  PASS        0     0.0%
  OpenAI strict mode (hard reject)             opt-in  FAIL        2    27.6%
  OpenAI strict mode (silent constraint loss)  opt-in  WARN        1    56.9%
  Anthropic Messages API baseline              always  FAIL        1     0.0%
  Anthropic strict:true subset                 opt-in  FAIL        2    63.0%
  Anthropic request complexity limits          opt-in  PASS        0    37.3%
  --------------------------------------------------------------------------

  C3-string-constraint:minLength   (1 occurrence(s))
    string constraints are not supported
    docs  "String constraints (minLength, maxLength)"
          https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations
    fix   remove minLength/maxLength and length-check in your handler instead
          (`pattern` IS supported on this axis).

      search  #/properties/q  = 1
```

Python 3.8+, standard library only. No install, no API key, no network call, no
account. It starts your server as a local child process and reads
`tools/list`. → [`checker/README.md`](checker/README.md)

The `corpus` column is why this repo exists.

---

## The measurement behind that column

617 public MCP servers were launched over stdio and their real `tools/list`
responses captured — 14,804 tool schemas. Three providers' published strict-mode
constraint sets were then applied to that one corpus.

**The result is not a failure rate. It is a disagreement.**

| axis | opt-in? | servers failing |
|---|---|---:|
| MCP specification conformance | no | **0/617 = 0.0%** |
| Anthropic Messages API baseline | no | **0/617 = 0.0%** |
| OpenAI `strict` — hard reject | yes | 170/617 = 27.6% |
| Anthropic `strict: true` subset | yes | **389/617 = 63.0%** |
| Anthropic — any axis | yes | 447/617 = 72.4% |

On the axes that apply whether or not anyone opts in, **this ecosystem is
clean**. That was the 2026-08-09 finding and re-measuring did not move it.

What moved is the gap. Every one of the 170 OpenAI failures also fails an
Anthropic axis — but **277 servers pass OpenAI's converter and still fail
Anthropic's**. Clearing one provider tells you almost nothing about the other.

→ [`dataset/README.md`](dataset/README.md) — the axes, the controls, the
documented ambiguities, and a reproduction command for every single verdict.
한국어: [`dataset/README.ko.md`](dataset/README.ko.md)

---

## Read this before quoting a number

**63.0% does not mean 63% of MCP servers are broken.** It is an opt-in number —
what happens if a client takes a server's `inputSchema` as published and sends
it with `strict: true`. Server authors control the schema but never the flag,
so it is an *exposure surface*, not a live outage.

**No API was called.** Verdicts come from the providers' published constraint
tables (quoted verbatim, with URLs), the providers' own production code, and
publicly reported errors. End-to-end verification against a live endpoint was
not performed, by design. [`dataset/LIMITATIONS.md`](dataset/LIMITATIONS.md)
says where that matters.

**We do not write "this server is broken."** We write "this schema is rejected
on this axis because of this value at this pointer." There is no leaderboard
here and no worst-offenders table. Please keep it that way if you reuse this.

**If a verdict looks wrong, it may well be — open an issue.** Every row in
`violations.jsonl` carries a `repro` field with the one-line command that
re-derives that verdict from the schema. Server authors who want their rows
removed only have to ask; no legal argument required.

---

## What already exists, and why this is not that

Several tools check MCP-specification conformance, some far more thoroughly
than this one does anything: the [official MCP
Inspector](https://github.com/modelcontextprotocol/inspector),
[`@yawlabs/mcp-compliance`](https://github.com/YawLabs/mcp-compliance) (88 tests,
A–F grading), [mcptools.tools](https://mcptools.tools/schema-validator),
[DevTk.AI](https://devtk.ai/en/tools/mcp-validator/). **If your question is "is
my server a valid MCP server", use one of those. They are better at it.**

They all read the same axis, and on that axis the corpus fails **0 of 617**.
The provider strict-mode subset — the narrower JSON Schema each provider
accepts once strict tool use is on — is a different question, and nobody was
answering it. That is the only reason this exists.

## Layout

| path | what it is |
|---|---|
| [`checker/`](checker/) | `mcp-schema-check` — run it against your own server |
| [`dataset/`](dataset/) | the corpus, the docs, the verification scripts |
| [`dataset/scripts/rules/`](dataset/scripts/rules/) | the one rule engine. The corpus and the checker import the same objects; a test asserts it by identity |
| [`src/`](src/) | collection harness |
| [`sdk-bug/`](sdk-bug/) | an `AssertionError` in the official Anthropic Python SDK on `type: ["string","null"]`, found by running that SDK over this corpus. 88 tools, 30 servers. Filed as [anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876) |
| [`REPORT.md`](REPORT.md) · [`REPORT_ANTHROPIC.md`](REPORT_ANTHROPIC.md) | the two measurement runs |

The raw collection output is **not** published: it contains tool descriptions
written by server authors, and this repository redistributes verdicts about
schemas rather than the prose those schemas carry.
[`dataset/CONSTRAINTS.md`](dataset/CONSTRAINTS.md) states the rule;
[`dataset/scripts/prose.py`](dataset/scripts/prose.py) enforces it; a scan in
CI asserts zero prose fields survive.

## Licence

Measurement results CC BY 4.0, scripts MIT. Neither re-licenses anything
written by a server author — see [`dataset/LICENSE`](dataset/LICENSE).
