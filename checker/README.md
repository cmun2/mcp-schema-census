# `mcp-schema-check`

Point it at your own MCP server. It tells you which of your tool schemas a
model provider's **strict mode** would reject, at which JSON pointer, with the
sentence from that provider's own documentation the verdict rests on, and one
line saying what to change.

```console
$ ./checker/mcp-schema-check --cmd "python3 checker/examples/demo_server.py"

mcp-schema-check 0.1.0  ·  python3 checker/examples/demo_server.py
rules: dataset/scripts  (the engine that produced the 617-server corpus in dataset/)

4 tool(s) checked  ·  server: demo-flawed-server 0.1.0

  axis                                          scope  verdict  tools   corpus
  --------------------------------------------------------------------------
  MCP specification conformance                always  PASS        0     0.0%
  OpenAI strict mode (hard reject)             opt-in  FAIL        2    27.6%
  OpenAI strict mode (silent constraint loss)  opt-in  WARN        1    56.9%
  Anthropic Messages API baseline              always  FAIL        1     0.0%
  Anthropic strict:true subset                 opt-in  FAIL        2    63.0%
  Anthropic request complexity limits          opt-in  PASS        0    37.3%
  --------------------------------------------------------------------------
```

…followed by, for every finding:

```
  C3-string-constraint:minLength   (1 occurrence(s))
    string constraints are not supported
    docs  "String constraints (minLength, maxLength)"
          https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations
    fix   remove minLength/maxLength and length-check in your handler instead (`pattern` IS supported on this axis).

      search  #/properties/q  = 1
```

---

## What this is *not*

**It is not an MCP-specification validator, and it should not be your first
stop if that is what you need.** Several tools already do that, some of them
much more thoroughly than this one does anything:

| tool | what it checks |
|---|---|
| [Official MCP Inspector](https://github.com/modelcontextprotocol/inspector) — `npx @modelcontextprotocol/inspector --cli --method tools/list` | connects to a server and prints `tools/list`, `resources/list`, `prompts/list`, `tools/call` |
| [`@yawlabs/mcp-compliance`](https://github.com/YawLabs/mcp-compliance) — `npx @yawlabs/mcp-compliance@latest test <target>` | 88 tests over 8 categories against MCP spec 2025-11-25, graded A–F, with a published rule catalog under CC BY |
| [mcptools.tools Schema Validator](https://mcptools.tools/schema-validator) | browser-side validation against the MCP specification schemas, plus manifest and client-config structure |
| [DevTk.AI MCP Config Validator](https://devtk.ai/en/tools/mcp-validator/) | server config against the MCP spec, plus style warnings |
| [mcp-probe / `mcp-conform`](https://github.com/castrocrest/mcp-probe-cli) | JSON-RPC envelope, initialize response, `tools/list` structure, JSON Schema validity |

`mcp-compliance` in particular tests far more of the protocol than this
command does. If your question is "is my server a valid MCP server", use one
of those. They are better at it.

**The reason this exists anyway is that they all look at the same axis, and on
that axis almost nobody is failing.** In the 617-server corpus in
[`../dataset/`](../dataset/) — real servers, launched over stdio, live
`tools/list` responses captured — MCP-specification conformance fails
**0 of 617 servers, 0.0%**. That axis is solved in practice.

What is not solved is the **provider strict-mode subset**: the narrower JSON
Schema each provider accepts once you turn strict tool use or structured
outputs on. On the same 617 servers:

- **27.6%** (170/617) are hard-rejected by OpenAI's strict converter;
- **63.0%** (389/617) fail Anthropic's `strict: true` subset;
- **72.4%** (447/617) fail *some* Anthropic axis (`C0`, `C` or `CL`) — a
  **44.9-point** gap over OpenAI's 27.6%.

And the two are nested, not parallel: every one of the 170 OpenAI failures also
fails an Anthropic axis, while **277 servers pass OpenAI's converter and still
fail Anthropic's**. Clearing one provider tells you very little about the
other.

That is the gap this command reports. It is a different question from
specification conformance, not a better answer to the same one.

The distinction is not ours. An MCP Inspector maintainer, triaging
[inspector#1005](https://github.com/modelcontextprotocol/inspector/issues/1005)
on 2026-08-01, scored its severity 4/5 with this reasoning:

> Inspector accepts schemas that real clients reject, so a server can pass
> here and fail in Claude Code. Reporting a server as healthier than it is
> undermines the point of the tool.

Note which way the measurement runs, though: the axis *that* issue is about
fails 0 of 617 servers. The layer that bites is the provider subset above it.

Full evidence for those numbers, including what was verified about each tool
above and how, is in
[`../dataset/README.md` § Related work](../dataset/README.md#related-work).

---

## Install

There is nothing to install. Python 3.8+, standard library only, run it from a
clone of this repository:

```console
git clone https://github.com/cmun2/mcp-schema-census && cd mcp-schema-census
./checker/mcp-schema-check --help
```

Every example below is written as `./checker/mcp-schema-check`, which works
from the repository root with nothing else set up. If you would rather type the
bare name, alias it once:

```console
alias mcp-schema-check="$PWD/checker/mcp-schema-check"
```

It must run from inside the repository, because the rules it applies **are**
`../dataset/scripts/rules/` — the same module that produced the published
corpus. See "One engine" below for why that is a feature rather than packaging
laziness.

Optional: `pip install anthropic` unlocks `--sdk-oracle` (see below). Still no
network call, still no API key.

---

## Three ways in

```console
# (a) start YOUR server as a local child process and call tools/list over stdio
./checker/mcp-schema-check --cmd "npx -y my-server"
./checker/mcp-schema-check --cmd "python -m my_server" --env API_KEY=dummy --cwd ./server

# (b) a tools/list response you already have
./checker/mcp-schema-check --tools tools.json

# (c) a single inputSchema
./checker/mcp-schema-check --schema one-input-schema.json
```

`--tools` accepts whichever shape you happen to have: the full JSON-RPC
envelope `{"result":{"tools":[…]}}`, the bare result `{"tools":[…]}`, or just
the array `[…]`.

**No network calls, ever.** `--cmd` starts your server as a local child
process and speaks newline-delimited JSON-RPC to its stdin/stdout. Nothing
leaves the machine, no provider API is contacted, and no API key is read or
needed. The verdicts are static: they come from published constraint documents,
not from trying a request and seeing what 400s.

---

## For CI

```console
./checker/mcp-schema-check --cmd "node dist/index.js" --axis anthropic
```

| exit code | meaning |
|---:|---|
| `0` | no hard reject on the selected axes |
| `1` | at least one hard reject |
| `2` | the input could not be read, or the server did not start |

- `--exit-zero` always exits 0 (report-only).
- `--axis anthropic\|openai\|mcp\|all` (default `all`).
- `--fail-on silent` *also* fails on constraints that are accepted and then
  silently dropped. Off by default, because they do not reject your request —
  they just stop being enforced.
- `--json` for machine-readable output; every finding carries `axis`, `code`,
  `severity`, `tool`, `json_pointer`, `value`, `source`, `source_quote`, `fix`.
- `--max-per-code N` caps how many occurrences of each code are printed
  (default 10). Anything hidden is counted out loud; nothing is silently
  truncated.

---

## What the axes mean

| axis | scope | what it is |
|---|---|---|
| **MCP specification conformance** | always | the wire schema every MCP client parses. One bad tool fails the whole `tools/list` parse in the official TypeScript SDK. |
| **OpenAI strict mode (hard reject)** | opt-in | `strict: true` structured outputs / function calling. The converter raises. |
| **OpenAI strict mode (silent loss)** | opt-in | keywords strict mode documents as unsupported. **The request succeeds and the constraint is never enforced.** Nothing tells you. |
| **Anthropic Messages API baseline** | always | applies to every tool sent to `/v1/messages`, strict or not. Currently one rule: no `oneOf`/`allOf`/`anyOf` at the top level of `input_schema`. Empirically observed 400, not in any published constraint document — flagged as such. |
| **Anthropic `strict: true` subset** | opt-in | the documented JSON Schema subset for strict tool use. |
| **Anthropic request complexity limits** | opt-in | 20 strict tools, 24 optional parameters, 16 union-typed parameters — counted across the whole request, not per tool. |

"scope: always" means the axis applies whether or not you opt into strict mode.
"opt-in" means you only meet it if you turn that provider feature on.

### Ambiguities are reported as ambiguities

Where a provider's documentation does not settle a case, this command says so
instead of guessing. Those findings are printed only with `--show-ambiguous`,
are labelled "not a verdict", and **never affect the exit code**. Example: the
Anthropic docs say `additionalProperties` "must be set to `false` for objects"
but the unsupported list only names values *other than* `false` — whether
omitting it entirely is a 400 is never stated. That is reported as
`AMB-additionalProperties-absent`, not as a failure.

---

## `--sdk-oracle`

```console
pip install anthropic
./checker/mcp-schema-check --cmd "npx -y my-server" --sdk-oracle
```

Runs Anthropic's *own* `transform_schema` over your schemas, locally, in
process. This is an **oracle, not a rule**: it reports what the shipped client
actually does, including its defects, rather than what a document says.

It is how you catch things no published constraint list covers. A property
typed `["string","null"]` is legal under both providers' documentation and
fires no rule here — but `anthropic` 1.0.0 raises `AssertionError: Expected
code to be unreachable` on it. That is
[anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876),
filed from this repository; the corpus records it for 88 tools across 30
servers. A `transform_schema` raise counts toward the exit code, because your
call really will crash there.

Without the `anthropic` package the flag prints one line explaining that and
carries on. It never crashes and never becomes a hidden requirement.

---

## One engine

**The rules are not in this directory.** They are in
[`../dataset/scripts/rules/`](../dataset/scripts/rules/), and this command
imports them — the same module objects that judged 617 servers and 14,804
tools to produce the published rates.

```
dataset/scripts/rules/
  codes.py       verdict code -> axis, severity, source URL, verbatim doc quote
  mcp_openai.py  axis A (MCP spec), axis B/B' (OpenAI strict)
  anthropic.py   axis C0 / C / CL (Messages API baseline + strict:true)
  fixes.py       one-line remediation per code   (presentation, not a rule)
  sdk_oracle.py  the vendor transformer wrapper  (oracle, not a rule)
```

Everything else is a driver over that engine: `dataset/scripts/judge_*.py`,
`src/lint*.py`, `dataset/scripts/explain.py`, and this checker.

This is the design constraint the whole thing is built around. If the dataset
and the checker each kept their own copy of the rules, they could disagree
inside a single release — and at that point neither the corpus's numbers nor
this command's output would be worth anything, with no way to tell which was
wrong. So:

- `checker/tests/test_single_source.py` asserts, by object identity, that every
  consumer resolves to the *same* function objects, and walks the tree to
  assert each rule body exists in exactly one file.
- `checker/tests/crosscheck_corpus.py` replays servers out of the published
  corpus through this command and compares its findings against
  `dataset/violations.jsonl` **code by code, tool by tool, pointer by
  pointer**. All 617 match exactly.

If you want to add a rule, add it to `rules/` and re-run
`cd dataset && bash scripts/verify_all.sh`, which rebuilds the corpus and
refuses to publish a moved rate.

---

## Tests

```console
bash checker/tests/run_all.sh
```

| | |
|---|---|
| `test_single_source.py` | one copy of the rules; every consumer imports the same object; every code resolves to a quote and a fix |
| `crosscheck_corpus.py` | checker output vs `dataset/violations.jsonl`, per server (`--all` for all 617) |
| `github_issue_repros.py` | minimal repros of schemas that failed in real public GitHub issues |
| `test_cli.py` | stdio launch, exit codes, `--json`, the error paths |

`github_issue_repros.py` records the **not-applicable** cases too, deliberately.
A `$schema` key inside `properties`
([pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986))
fires nothing here, and should not: no provider constraint document we cite
says anything about it, so there is no sentence to quote and no verdict to
make. That case belongs to the MCP-spec validators listed at the top of this
file, not here.

---

## Correcting a verdict

Every finding is a claim that a *published sentence* says a *specific value at
a specific pointer* is rejected. Published sentences change, and can be
misread. If a verdict is wrong, that is a bug worth filing — the code, the
pointer, the quote and the URL are all in `--json` output, which is everything
needed to argue about it. See
[`../dataset/README.md` § Correcting a verdict](../dataset/README.md).

## Licence

Same as the dataset — see [`../dataset/LICENSE`](../dataset/LICENSE).
