# mcp-schema-census

**617 public MCP servers, launched over stdio; 14,804 real `tools/list` schemas;
three provider strict-mode axes applied to the same corpus.**

Schemas collected **2026-08-09**. Provider constraint documents read
**2026-08-23**. Verdicts computed **2026-08-23**.

한국어 요약: [README.ko.md](README.ko.md)

---

## Read this before you quote a number

**63.0% does not mean 63% of MCP servers are broken.** It is an *opt-in*
number. It means: if a client takes a server's `inputSchema` exactly as
published and sends it to the Anthropic Messages API with `strict: true` set
on that tool, 63.0% of servers have at least one tool whose schema contains a
value the published constraint list says is rejected.

The axes that are **not** opt-in — the ones that apply whether or not a client
asks for anything — are **0.0%**:

| axis | opt-in? | servers failing |
|---|---|---:|
| **A** MCP spec conformance (`client.listTools()` throws → the whole server's tools vanish) | **no** | **0/617 = 0.0%** |
| **C0** Anthropic Messages API baseline (root `oneOf`/`allOf`/`anyOf`) | **no** | **0/617 = 0.0%** |

That 0.0% is not a new result and it is not being walked back. It was the
finding of the 2026-08-09 measurement, and re-measuring against a third
provider axis did not move it. **On the non-opt-in axes this ecosystem is
clean.** The interesting result is not a failure rate; it is that three
provider axes over one corpus disagree with each other by 44.9 percentage
points.

**What "opt-in" means here, precisely, because it is easy to over-read.** It
means a *client* has to set `strict: true` on the tool before the axis-C
constraint list applies. It does **not** mean a server author gets to decide:
the author controls the schema, never the flag, and cannot opt out of someone
else's client turning it on. So "opt-in" is not a synonym for "safe" — it is
"not yet triggered by the clients we can observe." Read the 63.0% as an
exposure surface, not as a live outage.

And for the axes that are *not* opt-in, there is no user-side escape either.
[Countly/countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64)
reports that Claude Code's `skipSchemaValidation` option "only bypasses local
validation — the API itself still rejects the schema." That is why the C0 row
above is marked **no**. See [Field evidence](#field-evidence-seven-public-reports-of-the-failure-this-dataset-predicts)
for the seven public reports this is drawn from.

**No API was called.** Verdicts come from (1) the providers' published
constraint tables, quoted verbatim with URLs, (2) the providers' own
production code (the MCP TypeScript SDK parser, `openai-agents`'
`ensure_strict_json_schema`, the Anthropic Python SDK's `transform_schema`),
and (3) empirically observed 400s reported publicly — seven such reports are
read and mapped to axes in [Field evidence](#field-evidence-seven-public-reports-of-the-failure-this-dataset-predicts).
**No end-to-end verification against a live endpoint was performed**, by
design — this run had a no-spend constraint. Where a document is silent, we say so rather than guess;
see [Documented ambiguities](#documented-ambiguities).

### Framing rule, used consistently throughout

We do not write "this server is broken." We write **"this schema is rejected on
this axis because of this value at this pointer."** A `minimum: 1` is not a
defect — it is a correct JSON Schema that one provider's opt-in subset does not
accept. This repository contains no ranking of servers, no leaderboard, and no
"worst offenders" table, and we ask that reuse keep it that way.

---

## Correcting a verdict

**If you think a verdict here is wrong, it may well be. Open an issue.** A
verdict is a claim that a published sentence rejects a specific value; both the
sentence and the value are checkable, and provider documents change.

Every row in `violations.jsonl` carries a `repro` field with the exact one-line
command that re-derives just that verdict, live, from the published schema:

```console
$ jq -r 'select(.code=="C2-numeric-constraint:minimum") | .repro' violations.jsonl | head -1
python3 scripts/explain.py --server "io.github.1clawAI/1claw-mcp" --code "C2-numeric-constraint:minimum" --tool "test_binding" --pointer "#/properties/timeout_ms"

$ python3 scripts/explain.py --server "io.github.1clawAI/1claw-mcp" --code "C2-numeric-constraint:minimum" --tool "test_binding" --pointer "#/properties/timeout_ms"
==============================================================================
server : io.github.1clawAI/1claw-mcp
package: @1claw/mcp   (npm, slice=holdout)
code   : C2-numeric-constraint:minimum
axis   : C    severity: hard-reject
source : https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations
quote  : "Numerical constraints (such as minimum, maximum, multipleOf)"
==============================================================================

re-derived from dataset/tools.jsonl : 1 matching hit(s)

  tool         : test_binding
  json_pointer : #/properties/timeout_ms
  value        : 100
  rule says    : numerical constraints are not supported

recorded in violations.jsonl        : 1 row(s)
agreement                           : MATCH
```

`explain.py` does not trust `violations.jsonl`. It loads the schema, re-runs
the rule, and tells you whether the live result and the recorded row agree.
Paste that output into the issue.

**Server authors:** if you want your server's rows removed, open an issue and
say so. We will remove them; you do not have to make a legal argument first.

---

## The three axes

De-duplicated globally by package. **N = 617 servers / 14,804 tools.**

| axis | what it measures | judged by | opt-in? | servers | tools |
|---|---|---|---|---:|---:|
| **A** | MCP spec conformance — `client.listTools()` throws, so *every* tool on that server disappears | official MCP TypeScript SDK 1.30.0 `ListToolsResultSchema.safeParse` (the real production parser) | no | **0/617 = 0.0%** | 0/14,804 = 0.0% |
| **B** | OpenAI `strict` — hard reject | `openai-agents` `ensure_strict_json_schema` (the real production converter) | yes | **170/617 = 27.6%** | 868/14,804 = 5.9% |
| **B′** | OpenAI `strict` — silent constraint loss (accepted, constraint never enforced) | documented unsupported-keyword table | yes | 351/617 = 56.9% | 3,332/14,804 = 22.5% |
| **C0** | Anthropic Messages API baseline — root `oneOf`/`allOf`/`anyOf` | observed 400 ([claude-code#10606](https://github.com/anthropics/claude-code/issues/10606)); **not in any published constraint doc** | no | **0/617 = 0.0%** | 0/14,804 = 0.0% |
| **C** | Anthropic `strict: true` JSON Schema subset | published constraint table, quoted verbatim; cross-checked against the official Anthropic Python SDK 1.0.0 `transform_schema` | yes | **389/617 = 63.0%** | **3,411/14,804 = 23.0%** |
| **CL** | Anthropic request-scoped complexity limits (20 strict tools / 24 optional params / 16 union params) | published explicit-limits table | yes | **230/617 = 37.3%** | n/a (request-scoped) |
| **C\*** | Anthropic, any of C0 / C / CL | | | **447/617 = 72.4%** | 3,411/14,804 = 23.0% |

### By population

`holdout` is a separate npm slice collected **after** the axis-A and axis-B
rules were frozen.

| slice | ecosystem | N | A | B | C0 | C | CL | C\* |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| npm | npm | 298 | 0.0% | 26.2% | 0.0% | 62.8% | 38.6% | 73.5% |
| pypi | PyPI | 117 | 0.0% | 42.7% | 0.0% | 53.8% | 41.9% | 63.2% |
| holdout | npm | 202 | 0.0% | 20.8% | 0.0% | **68.8%** | 32.7% | 76.2% |

The holdout rate is *higher* than the tuning slices'. Axis C is not an artifact
of the slice the rules were written against.

---

## The axes are not measuring the same thing

This is the part that is actually new. If the three axes were three ways of
detecting one underlying defect, the sets would overlap. They do not.

```
                   C* fail   C* pass
    B fail             170         0
    B pass             277       170
```

- **Containment chain: A ⊂ B ⊂ C\*.** Verified on the published data
  (`stats.py` prints `True / True`). 0 ⊂ 170 ⊂ 447.
- **Jaccard(B, C\*) = 0.380.**
- **P(C\* | B) = 1.000** — every server that OpenAI's strict converter rejects
  is also rejected on some Anthropic axis. No exceptions.
- **P(B | C\*) = 0.380** — the converse fails badly.
- **277/617 = 44.9% of servers are clean on both previously-measured axes and
  fail the Anthropic axis.** This is information neither axis A nor axis B
  could produce.
- **219/617 = 35.5%** of servers have *no* hard OpenAI problem — their only
  OpenAI issue is a constraint being silently dropped — but are a hard reject
  on Anthropic. This is the decisive asymmetry.

The cause is that the two providers dispose of the *same keyword* differently:

| keyword in the schema | OpenAI `strict` | Anthropic `strict: true` |
|---|---|---|
| `additionalProperties` ≠ `false` | reject | reject |
| `minimum` / `maximum` | **silently dropped** | **reject** |
| `minLength` / `maxLength` | **silently dropped** | **reject** |
| `maxItems` / `uniqueItems` | **silently dropped** | **reject** |
| `minItems` ≥ 2 | silently dropped | reject |
| `pattern` (regex) | silently dropped | **supported** |
| optional params (not in `required`) | must list every property in `required` | supported, up to 24 per request |
| > 20 strict tools per request | no such limit | reject |

Axis B is dominated by a single cause (`additionalProperties`, 99.9% of its
tool hits). Axis C is dominated by `minimum`/`maximum`/`minLength`/`maxLength`
— precisely the keywords axis B drops in silence. That is why the two axes
barely overlap.

### Verdict codes, de-duplicated corpus

Ambiguous codes are excluded from every count in this table and in the axis
rates above; they are in [their own section](#documented-ambiguities).

| code | servers | tool hits |
|---|---:|---:|
| `C2-numeric-constraint:minimum` | 267 | 2,828 |
| `C2-numeric-constraint:maximum` | 259 | 2,380 |
| `C3-string-constraint:minLength` | 158 | 2,369 |
| `C1-additionalProperties-not-false` | 169 | 1,704 |
| `C3-string-constraint:maxLength` | 138 | 1,409 |
| `C4-array-constraint:maxItems` | 94 | 296 |
| `C6-recursive-schema` | 5 | 63 |
| `C4-array-constraint:minItems` (≥ 2) | 24 | 32 |
| `C8-allOf-with-ref` | 1 | 11 |
| `C4-array-constraint:uniqueItems` | 1 | 6 |
| `CL2-too-many-optional-params` | 210 | — |
| `CL1-too-many-strict-tools` | 141 | — |
| `CL3-too-many-union-params` | 18 | — |

`STATS.txt` has the axis-B codes and every count in this README, regenerated
from the published files by `scripts/stats.py`.

---

## Related work

Everything cited here was opened and read on **2026-08-23**. Where a source
could not be opened, that is said instead of summarised.

### Published studies of the MCP ecosystem

| study | corpus | what it measures | opened? |
|---|---:|---|---|
| Li & Gao, *A First Look at the Security Issues in the Model Context Protocol Ecosystem*, DSN 2026 — [arXiv:2510.16558](https://arxiv.org/html/2510.16558) | **67,057** servers, six registries | Registry-level vetting and ownership weaknesses, and post-integration attacks driven by attacker-controlled tool *metadata* (tool poisoning, tool shadowing, context-dangling tools); their `MCPInspect` flags 833 vulnerable servers and 18 with suspicious descriptions. | yes |
| Lin, Ruan, Liu & Zhao, *MCPCorpus* — [arXiv:2506.23474](https://arxiv.org/abs/2506.23474) (2025-06-30) | ~**14,000** servers + **300** clients | A reproducible ecosystem snapshot: each artifact normalised to 20+ attributes covering identity, interface configuration, GitHub activity and metadata, for studying adoption trends and ecosystem health. | yes |
| Chen et al. (Fudan / Shanghai Innovation Institute), *Rethinking MCP Security: A Large-Scale Study of Runtime MCP Servers and Security Scanner Reliability* — [arXiv:2607.11086](https://arxiv.org/html/2607.11086) (2026-07-13) | **64,611** unique servers from ten markets; **37,288** actually deployed for live runtime interaction (57.7% deploy success) | The reliability of MCP security scanners against runtime servers: 96.89% of interactable servers are flagged risky by at least one of eight scanners, mean scanner precision 45.53% (range 10.40–96.88%), mean cross-scanner Jaccard 15.66%, recall on confirmed vulnerabilities 24.17%. | yes |
| Hasan, Li, Fallahzadeh, Rajbahadur, Adams & Hassan, *MCP at First Glance: Studying the Security and Maintainability of MCP Servers* — [arXiv:2506.13538](https://arxiv.org/abs/2506.13538) (v1 2025-06-16, v5 2026-04-13) | **1,899** open-source servers | Source-code health: a general static analyser plus an MCP-specific scanner. 7.2% of servers carry general vulnerabilities, 5.5% MCP-specific tool poisoning, 66% code smells, 14.4% known bug patterns. | yes |

**None of the four measures wire-schema conformance, and none applies a
provider's strict-mode constraint set.** Three measure security properties of
servers or of the scanners that judge them; one builds a metadata corpus.

### Where this dataset sits

**On corpus size we are far behind all of them: 617 servers against 67,057.**
That gap is real and it is not being argued away. Our servers were launched
over stdio and their live `tools/list` responses captured, which is closer to
the runtime study's method than to a registry crawl, but the scale is not
comparable.

The claim here is not scale. It is the **cross-application of several
providers' strict-mode constraint sets to one and the same corpus, in order to
measure how far the axes disagree** — the 44.9-point gap between what OpenAI's
strict converter rejects and what Anthropic's strict subset rejects, on
identical schemas. That is a question about provider disagreement, not about
server quality, and it is not answerable from any single-axis measurement.

**Within our search we did not find prior work at this angle.** We did not run
an exhaustive survey, and "we found none" is a statement about our search, not
about the literature. If work like this exists, we would like the citation.

### Tools a server author can run today

These are prior art in the more immediate sense: a server author who wants to
know whether their schemas are acceptable has these to reach for already. Each
was checked directly, on 2026-08-23, for one specific question — **does it
apply a provider's strict-mode constraints, or only the MCP specification?**

| tool | what it checks | axis, in this dataset's terms | how it was verified |
|---|---|---|---|
| **Official MCP Inspector** — `npx @modelcontextprotocol/inspector --cli --method tools/list` | Connects to a server and prints `tools/list`, `resources/list`, `prompts/list`, `tools/call` results. No schema-strictness validation. | none — it is a client, not a validator | read `clients/cli/src/cli.ts` (40,381 bytes): **zero occurrences of the string `strict`**, and `--strict` is not among the long-form flags defined there |
| **`@yawlabs/mcp-compliance`** — `npx @yawlabs/mcp-compliance@latest test <target>` | 88 tests over 8 categories — transport, lifecycle, tools, resources, prompts, error handling, schema validation, security — against MCP spec 2025-11-25, scored A–F. Its `--strict` is a CI **exit-code** mode, not schema strictness. | **A** (MCP spec). Its `tools-schema` rule is literally "All tools have name and inputSchema" — our `A1`/`A5`. | read its published rule catalog `mcp-compliance-rules.json` (47,917 bytes, 88 rules): **zero** occurrences of `anyOf`, `oneOf`, `allOf`, `additionalProperties`, `minLength`, `maxLength`, `minimum`, `maximum`, `maxItems`, `uniqueItems`, `input_schema`, `Anthropic`, `OpenAI` |
| **mcptools.tools** — [MCP Schema Validator](https://mcptools.tools/schema-validator) | Browser-side. Its own text: validates "against the MCP specification schemas" — tool name charset, `inputSchema` is a JSON Schema object with `type: "object"`, manifest and client-config structure. | **A**, plus client-config hygiene we do not measure | fetched the page; zero occurrences of any provider constraint keyword in the source, including inline JS |
| **DevTk.AI** — [MCP Config Validator](https://devtk.ai/en/tools/mcp-validator/) | Validates a server config against the MCP spec, plus style warnings (description shorter than 20 characters, missing `required` array, duplicate names). | **A**, plus style advice | fetched the page; zero occurrences of any provider constraint keyword in the source, including inline JS |
| **mcpserverspot** — [validator](https://www.mcpserverspot.com/tools/validator) | **Could not open.** | unknown | the URL returned `HTTP 402 DEPLOYMENT_DISABLED` on 2026-08-23, to both a browser-agent fetch and `curl`. From a search-index snapshot its "compatibility warnings" are *more than 50 tools* and *missing version string* — client-performance and hygiene, not provider constraints — but **this is second-hand and was not verified first-hand.** |
| **mcp-probe / `mcp-conform`** — [castrocrest/mcp-probe-cli](https://github.com/castrocrest/mcp-probe-cli) (found in the #1005 thread) | JSON-RPC envelope, initialize response, `tools/list` structure, JSON Schema validity (catches the bare `true` schema that Claude Code rejects), error codes, method-not-found. | **A** — the bare-`true` case is our `A2` | read the README |

**A correction, because it circulates.** The invocation
`npx @modelcontextprotocol/inspector --cli --method tools/list --strict` does
not work: **the Inspector has no `--strict` flag.** That text comes from the
*proposal body* of
[modelcontextprotocol/inspector#1005](https://github.com/modelcontextprotocol/inspector/issues/1005),
which is **open and not approved for work** — triaged 2026-08-01 at 7/16
("Medium"), project board status "Incoming". What #1005 proposes is also, in
our terms, **axis A**: bare `true` schemas, `"type": ["null","boolean"]`, a
missing `type`. Its own opening example is the Go SDK emitting `true` for
`interface{}`.

**The consequence, stated plainly.** Every tool above checks the axis on which
this corpus is already at **0.0%** — MCP-specification conformance, 0/617 —
or a client-config axis we do not measure at all. None of them applies OpenAI
`strict`, Anthropic `strict: true`, or the Anthropic Messages API baseline.
This is a statement about what these tools cover, not about how good they are;
`mcp-compliance` in particular tests far more of the protocol than we do, and
publishes its rubric and rule catalog under CC BY so the rules can be forked.

---

## Field evidence: seven public reports of the failure this dataset predicts

This dataset called no API, so every 400 in it is *predicted*. That limitation
stands and is not being softened. What follows is the nearest available
substitute: **public issues filed by people who actually received the 400**,
each opened and read on 2026-08-23 and mapped — or explicitly not mapped — to
an axis and a verdict code here.

The mapping rule: an issue is mapped only when the error string names a
construct one of our codes covers. Where it does not, the row says **not
mapped**, rather than being forced onto the nearest axis.

| # | report | date / client | error, verbatim | axis | code |
|---|---|---|---|---|---|
| 1 | [anthropics/claude-code#10606](https://github.com/anthropics/claude-code/issues/10606) — closed `not_planned` by a staleness bot, no maintainer reply | 2025-10-30, Claude Code v2.0.21–2.0.29 | `tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level` | **C0** | `C0-root-combinator:*` |
| 2 | [ProfSynapse/claudesidian-mcp#6](https://github.com/ProfSynapse/claudesidian-mcp/issues/6) | 2025-06-27, Claude Code **v1.0.35** | same string, at `tools.136` | **C0** | `C0-root-combinator:*` |
| 3 | [Countly/countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64) — fixed upstream | 2026-02-23, Claude Code | same string, at `tools.29`; the reporter attributes the top-level `anyOf` to `@modelcontextprotocol/sdk` ≥1.26.0's Zod→JSON-Schema conversion, not to hand-written schemas | **C0** | `C0-root-combinator:*` |
| 4 | [microsoft/pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986) | 2026-04-13, VS Code Copilot on Claude Sonnet 4.6 | `tools.47.custom.input_schema.properties: Property keys should match pattern '^[a-zA-Z0-9_.-]{1,64}$'` — `$schema` used as a *property key* | **not mapped** | — |
| 5 | [anthropics/claude-code#1690](https://github.com/anthropics/claude-code/issues/1690) — closed by a maintainer with "IIUC, this is working as expected" | 2025-06-06, Claude Code v1.0.16, local WordPress MCP server | `tools.16.custom.input_schema: JSON schema is invalid. It must match JSON Schema draft 2020-12` | **not mapped** | — |
| 6 | [anthropics/claude-code#20720](https://github.com/anthropics/claude-code/issues/20720) — closed as a duplicate of #11678 | 2026-01-25, Claude Code v2.1.19 | same generic draft-2020-12 message at `tools.17`, reported with `{"mcpServers": {}}` — i.e. with no MCP server configured at all | **not mapped** | — |
| 7 | [anthropics/claude-code#10858](https://github.com/anthropics/claude-code/issues/10858) — closed as a duplicate of #8014, reported fixed since v2.0.33 | 2025-11-02, `claude mcp serve` read by Claude Desktop | no 400; Claude Desktop showed "No tools available" because the tools/list response carried `"strict": true` on six tools — an Anthropic-API field that is not part of the MCP spec | **not mapped** | — |

Why 4–7 are not mapped:

- **#4** is a real, non-opt-in Messages API constraint — a regex on property
  keys — that **this dataset does not check at all.** It is a gap in our rule
  set, not a gap in the report. (Informationally, and outside every count in
  this README: 2 of 617 servers publish a property key that fails that regex —
  `$schema` on one, MongoDB-style `$in`/`$ne`/`$eq`/`$nin`/`$and` on another.
  Reproduce with `jq -r 'select([.input_schema|..|objects|(.properties//{})|keys[]]|any(test("^[a-zA-Z0-9_.-]{1,64}$")|not))|.package' tools.jsonl | sort -u`.
  This number is **not** an axis, is **not** in `STATS.txt`, and moves no
  verdict.) Note also that the thread is disputed: the Pylance maintainer
  could not reproduce it and suspects VS Code injects the `$schema` key.
- **#5** and **#6** carry the generic "must match JSON Schema draft 2020-12"
  message, which names no keyword, and neither thread shows the schema. There
  is no construct to match a code against. #6 additionally reports no MCP
  server configured, which puts it outside this corpus entirely.
- **#7** is the *reverse* direction and a genuinely different failure: a client
  rejecting a non-spec **tool-level** field rather than an API rejecting a
  schema. Our axis-A oracle is the official TypeScript SDK parser, whose
  `ToolSchema` ends in `.catchall(z.unknown())`, so an extra key such as
  `strict` does not fail it. Worth recording anyway, because it is
  provider-API vocabulary leaking outward into the MCP wire format — the same
  seam this dataset measures, pointed the other way.

### What #10606 did and did not change here

The top-of-page guard says 63.0% is an *opt-in* number. #10606 is titled
"Strict MCP schema validation in v2.0.21+ breaks working MCPs with **no
opt-out**", which would undercut that guard if it held. Read in full, it does
not — but two other things in it do need correcting, and both are framing, not
arithmetic. **No number in this repository moved.**

1. **63.0% is still an opt-in number.** Every concrete error in #10606 — and
   in #2 and #3 above — is the top-level-combinator 400, which is axis **C0**.
   C0 is already classified here as *not* opt-in and already reported at
   **0/617 = 0.0%**. 63.0% is axis **C**, the `strict: true` JSON Schema subset
   (`minimum`, `maxLength`, `maxItems`, …). None of the seven reports shows a
   client setting `strict: true` on a server's published schema. The issue's
   phrase "strict validation" means client-side schema checking, not the
   Anthropic `strict` tool flag; they are different things that share a word.

2. **The "v2.0.21 introduced it" attribution is not supported by its own
   thread, and has been removed from this repository.** The reporter's own
   follow-up comment says v2.0.20 rejected the same packages, and observes
   that the Perplexity MCP package had shipped two releases in the preceding
   24 hours — so the change may have been on the server side, not the client
   side. Report #2 above settles it: the identical 400 was hit on Claude Code
   **v1.0.35 on 2025-06-27**, four months before v2.0.21. No Anthropic
   engineer replied in the thread; a staleness bot closed it. The docstrings
   in `scripts/judge_anthropic.py` and `../src/lint_anthropic.py` previously
   read "Claude Code v2.0.21 began forwarding this"; that sentence is gone.
   **The observed-400 citation stands — the version attribution does not.**

3. **On "no opt-out": there is one, and it does not help.** Report #3 states
   that Claude Code has a `skipSchemaValidation` option and that using it does
   not fix this class of failure — *"`skipSchemaValidation` in Claude Code only
   bypasses local validation — the API itself still rejects the schema."* That
   **sharpens** the non-opt-in classification of C0 rather than weakening it:
   on the axes this dataset reports at 0.0%, a user has no way to opt out. It
   is a good thing for the ecosystem that those axes are the clean ones.

MCP TypeScript SDK issues [#1028](https://github.com/modelcontextprotocol/typescript-sdk/issues/1028)
and [#702](https://github.com/modelcontextprotocol/typescript-sdk/issues/702),
cited by report #3 as the upstream cause of top-level `anyOf`, are recorded
here as leads. **They were not opened or verified**, and nothing in this
dataset depends on them.

---

## Did the detector actually work?

A 0.0% and a 63.0% out of the same detector both need proving. Four checks:

**1. Positive controls: 16/16 detected.** Each case is a schema built to
contain exactly one thing the documentation forbids verbatim — root `anyOf` /
`oneOf` / `allOf`, `minimum`, `multipleOf`, `minLength`, `maxItems`,
`minItems: 2`, `additionalProperties: {type: string}`, external `http://` `$ref`,
a recursive `$defs` cycle, an object inside an `enum`, `allOf` + `$ref`, 25
optional params, 21 strict tools, 17 union-typed params. All 16 fire.

**2. Negative controls: 5/5 pass clean — including Anthropic's own examples.**
The `get_weather` and `search_flights` schemas from Anthropic's published
strict-tool-use documentation are run through the detector and come out clean.
So does a schema using `pattern` (supported on Anthropic, unlike OpenAI), a
schema using `minItems: 1` (supported), and a schema with exactly 24 optional
parameters (the boundary). The detector does not over-fire on the provider's
own examples.

**3. An independent production implementation agrees.** The official Anthropic
Python SDK 1.0.0 `transform_schema` was run over all 14,804 schemas. Whatever
it strips from the wire schema is what its authors consider unsupported —
derived from the implementation, not from our reading of the prose.

| | value |
|---|---:|
| SDK `transform_schema` raises (cannot normalise the schema at all) | 75/617 = 12.2% |
| SDK strips ≥ 1 constraint | **446/617 = 72.3%** |
| agrees with our static axis-C verdict, server unit | 510/617 = 82.7% |

Per keyword, the two implementations land on nearly the same server counts:
`minimum` 260 vs 267, `maximum` 253 vs 259, `minLength` 154 vs 158,
`maxLength` 131 vs 138, `maxItems` 87 vs 94, `minItems` 19 vs 24,
`uniqueItems` 1 vs 1.

**4. All 107 disagreements are accounted for — none is an unexplained error.**

- **25 "false positives"** (our rule fires, the SDK strips nothing), and all 25
  are accounted for: **22** carry `C1-additionalProperties-not-false`, and the
  remaining **3** are servers where the SDK *raised* before it could strip
  anything (8 of the 25 raised in total; 5 of those also carry C1). The C1 case
  is an oracle blind spot, not a rule error: the SDK does not *remove*
  `additionalProperties`, it **overwrites** it with `false`, and an oracle that
  detects removal structurally cannot see an overwrite.
- **82 "false negatives"** (the SDK strips something, our rule is silent). The
  keywords it strips on those servers are `default` (72 servers),
  `exclusiveMinimum` (4), `const` (3), `pattern` (2), `oneOf` (1). The
  documentation lists `default`, `const` and `pattern` as **supported**, and
  says nothing at all about `exclusiveMinimum` and `oneOf`. Our rule follows the
  documentation and stays silent on purpose. This gap *is* finding #4 in
  [Documented ambiguities](#documented-ambiguities): the docs and the official
  SDK disagree with each other, and without calling the API we cannot say which
  one the endpoint follows.

Axis A's detector was verified the same way in the 2026-08-09 round: 7/7 known-bad
schemas caught by the real SDK parser, 3/3 good schemas passed. That control set
also found a real bug in our own axis-A rule before the headline was computed.
Details in `../REPORT.md` §5.

---

## Documented ambiguities

These are cases where the published documentation does not settle the question.
They are **excluded from every count above** and reported separately, because
guessing would make the dataset unfalsifiable. Five families:

| # | code family | servers | tool hits | why it is unresolved |
|---|---|---:|---:|---|
| 1 | `AMB-additionalProperties-absent` | **412** | 6,690 | The supported list says `additionalProperties` "must be set to `false` for objects". The unsupported list names only values "other than `false`". **Omission is never addressed.** |
| 2 | `AMB-numeric:*` (`exclusiveMinimum`, `exclusiveMaximum`) | 69 | 380 | "Numerical constraints (**such as** `minimum`, `maximum`, `multipleOf`)" — "such as" leaves the list open. |
| 3 | `AMB-unlisted:*` (`oneOf` 13 servers, `propertyNames` 29, `not`, `if`, `then`, `minProperties`, `dependentRequired`) | 41 | 512 | `anyOf` and `allOf` are listed as supported; `oneOf` appears in **neither** list. Same for the rest. |
| 4 | docs vs. official SDK | — | — | The docs list `const`, `default` and `pattern` as supported. The official Python SDK **removes all three** from the wire schema and appends them to a description string. Which one the endpoint follows cannot be determined without calling it. |
| 5 | `AMB-format-unlisted:*` | 15 | 110 | Ten string `format` values are enumerated as supported. Whether a format outside that set is a 400 or is silently ignored is not stated. |

**Ambiguity #1 is the one that can move the headline.** It affects 412 of 617
servers. Our axis-C rule takes the conservative reading — an *absent*
`additionalProperties` is **not** counted as a violation. Under the other
reading, C would rise from 63.0% into the 90s. We report 63.0% and this
paragraph, rather than the larger number.

> Note on 412 vs 414: `../REPORT_ANTHROPIC.md` §2 quotes 414 for this row. That
> count was taken over the 620-row pre-de-duplication pooled file; three
> packages appear in two slices each, and two of them carry this code. Over the
> de-duplicated N=617 corpus published here it is 412. No verdict changed.

Ambiguity #4 is why 82 of the 107 oracle disagreements exist. It is not noise;
it is a documentation defect worth fixing upstream.

---

## What is in the files

| file | rows | one row is |
|---|---:|---|
| `servers.jsonl` | 617 | one server: identity, provenance, per-axis verdict, complexity counters, SDK-oracle result, ambiguity counts |
| `tools.jsonl` | 14,804 | one tool: prose-stripped `inputSchema`/`outputSchema`, per-axis verdict with codes, SDK-oracle result |
| `violations.jsonl` | 31,954 | one verdict: axis, code, severity, JSON pointer, the value that caused it, the source URL, the verbatim quote, and a one-line `repro` |
| `controls.jsonl` | 31 | one control case: input, expected verdict, observed verdict, pass/fail |
| `failures.jsonl` | 360 | one server that would not start: status, env vars supplied (names only), retry outcome |
| `STATS.txt` | — | every number in this README, regenerated from the five files above |
| `VERIFY.txt` | — | the full output of the last `scripts/verify_all.sh` run: prose scan, verdict round-trip, frozen-rate assertions, stats |

`severity` values in `violations.jsonl`: `hard-reject`, `silent-loss`,
`empirical` (observed, not documented), `ambiguous` (excluded from counts).

**No third-party prose is in any of these files.** Tool descriptions and every
`description`/`title`/`examples` field inside every schema were removed —
4,327,823 characters in total — and replaced by `description_len` and
`description_sha256_12`. Structure, property names, types, `enum` members,
`pattern` regexes and every constraint value are retained, because those are
the measurement. See [LICENSE](LICENSE) §3 and [CONSTRAINTS.md](CONSTRAINTS.md).

Removing the prose changed **no verdict** — `scripts/verify_verdicts.py` re-runs
the judge over the stripped schemas and compares all 19,159 hits.

---

## Reproducing

**Layer 1 — re-derive the verdicts. Seconds, no network, no API key.**

```bash
python3 scripts/verify_no_prose.py    # 0 prose fields, 0 credentials, 0 PII
python3 scripts/verify_verdicts.py    # re-judge stripped schemas: 0 differences
python3 scripts/stats.py              # every number in this README
python3 scripts/explain.py --help     # one verdict at a time
```

**Layer 2 — re-collect the schemas.** Hours, and it **executes arbitrary
third-party code on your machine**. Run it in a container or a throwaway VM.
See [METHODOLOGY.md](METHODOLOGY.md).

**Re-check the constraint tables** (provider docs move):

```bash
mkdir -p snapshots
curl -sL https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md \
  > snapshots/anthropic-$(date +%F).md
```

No snapshot is checked in — we quote the provider's documentation, we do not
redistribute it. Take the first snapshot yourself and diff later ones against
it. Every sentence the rules were derived from is quoted verbatim in
[CONSTRAINTS.md](CONSTRAINTS.md) as of 2026-08-23, so a fresh fetch has
something concrete to be checked against.

`schemas_collected_at` and `verdicts_computed_at` are separate fields on every
server row on purpose. If you re-judge this corpus against a newer constraint
table, only the second one moves, and readers should be able to see that.

---

## Limitations

Summarised here, in full in [LIMITATIONS.md](LIMITATIONS.md).

1. **No API was called.** Every 400 in this dataset is predicted from published
   constraints, provider SDK behaviour, or one publicly reported observation —
   never observed by us.
2. **Go/OCI servers were not measured at all.** No Docker in the collection
   environment; ~130 OCI-distributed servers (~2.1% of the registry) were
   skipped. Hand-written Go schemas are exactly where axis-A violations have
   historically been reported.
3. **360 servers failed to start** and are not in the corpus. They are listed in
   `failures.jsonl` with their status. Nothing rules out their being
   systematically different.
4. **The registry is self-registered and contains spam.** Bulk publishers are
   present (`mcparmory` 37 packages, `CSOAI-ORG` 28, `pulsemcp` 19). Rates hold
   on the starred, downloaded and multi-tool subsets — on those they go *up*,
   not down.
5. **The CL limits assume one server per request.** Real clients mix tools from
   several servers, so 37.3% is a lower bound.
6. **Ambiguity #1 could move 63.0% into the 90s.** See above.
7. **Clients using the official Anthropic SDK never see these 400s.** The SDK
   strips the unsupported keywords first. For them the outcome is not a
   rejection but a silently unenforced constraint — which happens to 72.3%.
8. **The axis set is not complete, and one gap is documented.** The Anthropic
   Messages API also enforces a regex on property keys
   (`^[a-zA-Z0-9_.-]{1,64}$`), reported in
   [pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986).
   No axis here checks it. See [Field evidence](#field-evidence-seven-public-reports-of-the-failure-this-dataset-predicts),
   row 4. Three of the seven field reports could not be mapped to any code
   here at all; that is reported as a gap rather than papered over.

---

## Related files in this repository

- `../checker/` — **`mcp-schema-check`**, a CLI for server authors: point it at
  your own server and it reports which of your tool schemas each provider's
  strict mode would reject, with the JSON pointer, the verbatim doc quote and a
  one-line fix. It imports this directory's `scripts/rules/` rather than
  keeping its own copy, and `checker/tests/crosscheck_corpus.py` replays all
  617 servers through it to prove its output matches `violations.jsonl` exactly.
  `../checker/HALT-AND-RESTART.md` records why it was stopped before any code
  was written the first time — the falsification pass in
  [Related work](#related-work) found five tools already in that space — and
  what changed on the restart.
- `../REPORT.md` — the 2026-08-09 axis-A/B measurement (result: 0.0%, parked)
- `../REPORT_ANTHROPIC.md` — the 2026-08-23 axis-C re-measurement
- `../sdk-bug/` — a minimal, independently written reproduction of an
  `AssertionError` crash in `anthropic` 1.0.0 `transform_schema` on
  `type: ["string","null"]`, plus the issue body as filed. **Filed upstream
  2026-08-23 as [anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876).**
