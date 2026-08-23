# Limitations

Everything this dataset does not establish. Read this before citing a number.

---

## 1. No API was ever called

**Not one request was sent to any provider endpoint.** This run operated under a
no-spend constraint.

Every "reject" verdict here is a **prediction** from one of three things:

1. the provider's published constraint table, quoted verbatim (axes B, B′, C, CL);
2. the provider's own production code, executed on the schemas (axes A and B, and
   the axis-C corroboration);
3. publicly reported, observed 400s (axis C0 only, labelled `empirical`) —
   seven such reports are read and mapped to axes in `README.md` >
   "Field evidence"; four of them are the C0 error string, three could not be
   mapped to any code here.

What is missing is the fourth thing: sending a schema to `/v1/messages` with
`strict: true` and recording what comes back. Until that is done, **63.0% is a
documented-subset violation rate, not a measured 400 rate.** If Anthropic's
endpoint is more permissive than its documentation, this number is high. If it
enforces the ambiguous cases too, it is low (see #6).

This is the single largest caveat and it applies to every Anthropic figure here.

## 2. Go and OCI servers were not measured at all

~130 registry servers (~2.1% of 6,100) ship as OCI container images. The
collection environment had no Docker, so none of them were launched.

This matters specifically for axis A. Every real-world axis-A violation reported
in the wild has come from **hand-written Go schemas** (`interface{}` serialising
to a bare `true`), and Go servers are exactly the ones distributed as containers.
**A = 0.0% is therefore "0.0% among ecosystems where the SDK generates the
schema."**

It is bounded, though: even if every single OCI server were broken, the
ecosystem-wide rate would be capped at 2.1%.

## 3. 360 servers would not start

Of 980 sampled packages, 620 responded to `tools/list`; 360 did not
(`timeout_or_crash` 356, `rpc_error` 4). They are listed in `failures.jsonl`.

Nothing rules out their being systematically different — a server that crashes on
launch may well be one with an unusual schema. There is no evidence either way,
and this dataset cannot produce any.

An earlier report split those 360 into "81 requiring credentials / 279 other".
**That split is not recoverable from the stored fields**, so it is not reproduced
in `failures.jsonl`. What is there is what was actually kept: the status, the env
var names supplied, and whether a retry was attempted.

## 4. The registry is self-registered and contains bulk publishers

Anyone can register. Bulk publishers are present and identifiable: `mcparmory`
(37 packages), `CSOAI-ORG` (28), `pulsemcp` (19).

The rates survive filtering — and go **up**, not down:

| subset | N | C | CL | C\* |
|---|---:|---:|---:|---:|
| all | 617 | 63.0% | 37.3% | 72.4% |
| repository URL present | 554 | 62.6% | 38.3% | 72.6% |
| GitHub API resolved | 354 | 59.6% | 39.5% | 70.1% |
| ★ ≥ 10 | 87 | 59.8% | 58.6% | 77.0% |
| ★ ≥ 100 | 11 | 54.5% | 45.5% | 72.7% |
| ≥ 5 tools | 450 | 66.4% | 50.0% | 78.9% |
| npm weekly downloads ≥ 1000 | 20 | **85.0%** | 65.0% | **85.0%** |

Axis A was 0.0% on every one of these subsets in the 2026-08-09 round, including
after de-duplicating to one package per GitHub owner.

The direction is worth stating plainly: **the more a server is actually used,
the more constraint keywords its schemas carry, and the more of them the strict
subset rejects.** This is not spam inflation. If anything, the toy servers are
what pull the rate down.

The ★ ≥ 100 cell is 11 servers. Do not read a trend into it.

## 5. The CL limits assume one server per request

`CL1` (20 strict tools), `CL2` (24 optional params) and `CL3` (16 union params)
are **per request, combined across all strict schemas** — the documentation says
so explicitly. Each server here is measured as if it were alone in the request.

Real clients connect several servers at once. **37.3% is a lower bound.** A
client wiring up three medium servers can exceed CL1 without any individual
server being anywhere near the limit.

Conversely, a client that marks only a few tools `strict` never hits these
limits at all. CL is as much a property of the client's tool-selection strategy
as of the server.

## 6. One documentation ambiguity can move 63.0% into the 90s

`additionalProperties` **absent** (not set to a non-`false` value — simply not
present) affects **412 of 617 servers**. The documentation's supported list says
it "must be set to `false` for objects"; its unsupported list names only values
"other than `false`". Omission is addressed nowhere.

We take the conservative reading and do **not** count it. The other reading is
defensible and would push axis C from 63.0% into the 90s. We publish 63.0% and
this paragraph.

Four more ambiguities are enumerated in README.md and CONSTRAINTS.md. All are
excluded from all counts.

## 7. Clients using the official Anthropic SDK see none of these 400s

`transform_schema` strips unsupported keywords before the request is sent and
appends them to a description string. For those clients the outcome is not a
rejection at all — it is a **silently unenforced constraint**, which happens to
**72.3%** of servers.

So the practical reading of axis C is narrower than it looks: it applies to a
client that takes MCP `inputSchema` and passes it through to the API with
`strict: true` and no normalisation. That is a real client shape, but it is not
every client.

The same structure defends axis B: `openai-agents` demotes a failing tool to
non-strict rather than failing the request.

## 8. Axis C0 rests on observation, not on any specification

The root-combinator rule comes from bug reports and one error string. It is not
in any published constraint document. It is marked `empirical` in
`violations.jsonl` for that reason.

An earlier version of this file said "a single observation". On 2026-08-23 three
further independent reports of the identical error string were read
([claudesidian-mcp#6](https://github.com/ProfSynapse/claudesidian-mcp/issues/6),
2025-06-27, Claude Code v1.0.35;
[countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64),
2026-02-23; plus the original
[claude-code#10606](https://github.com/anthropics/claude-code/issues/10606)),
spanning fourteen months and three unrelated servers. That is stronger evidence
than one report — but it is still observation, not documentation, and it is
still four users' error messages rather than a controlled test. **No client
version is attributed**; see `README.md` > "Field evidence" for why the
"v2.0.21 introduced it" reading does not hold.

It fires on 0 servers here, so it changes nothing — but if you reuse the rule,
know that its basis is observation, not a specification.

## 9. Axis B and axis C are opt-in; axis A and C0 are not

Repeating this because it is the easiest thing to lose in a citation.

- **A (0.0%)** — a spec-conformant MCP client, no flags: every server's tools load.
- **C0 (0.0%)** — every tool sent to the Messages API, strict or not: no rejects.
- **B (27.6%), B′ (56.9%), C (63.0%), CL (37.3%)** — only when a client opts
  into a strict mode.

"63% of MCP servers are broken" is not a claim this dataset supports, and the
0.0% figures are not a footnote to the 63% — they are the other half of the
finding.

Two refinements to "opt-in", added 2026-08-23:

- **Opt-in is the *client's* choice, not the server author's.** The author
  controls the schema and never the flag, and cannot prevent someone else's
  client from setting it. 63.0% is an exposure surface, not a live outage —
  but it is also not something a server author can decline.
- **On the non-opt-in axes there is no user-side escape either.**
  [countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64)
  reports that Claude Code's `skipSchemaValidation` "only bypasses local
  validation — the API itself still rejects the schema."

## 10. Tool descriptions are not in this dataset

Every free-text field written by a server author was removed — 4,327,823
characters. If your research needs the prose (description quality, prompt
injection surface, semantic analysis), this dataset cannot serve it. It gives
you `description_len` and `description_sha256_12`, and everything needed to
re-collect the text yourself: `package`, `ecosystem`, `package_version`,
`repository`. See METHODOLOGY.md §7 and LICENSE §3.

Removing the prose cost no analytical fidelity for schema-compatibility work —
`scripts/verify_verdicts.py` re-derives all 19,159 hits from the stripped
schemas with 0 differences. But that is a claim about *these* axes only.

## 11. Snapshot dates, and what has certainly moved since

- schemas collected **2026-08-09**
- star counts and npm download counts as of **2026-08-09**
- provider constraint documents read **2026-08-23**
- verdicts computed **2026-08-23**

Packages have published new versions since. Provider constraint tables change —
axis C exists *because* Anthropic shipped a constraint table that did not exist
when the 2026-08-09 round was run. `schemas_collected_at` and
`verdicts_computed_at` are separate fields so that a re-judge is visibly a
re-judge and not a re-measurement.

## 12. What would settle the open questions

In rough order of value per unit of effort:

1. **Call the API.** ~20 requests against a handful of schemas per ambiguity
   would resolve all five, and would convert axis C from predicted to measured.
   Ambiguity #1 alone is worth two requests.
2. **Run the Go/OCI slice** in an environment with Docker. It is the only known
   population where axis A might be non-zero.
3. **Re-collect quarterly** and publish the delta. A constraint-compatibility
   rate is only interesting as a time series.
4. **Ask the three providers to publish a machine-readable constraint table.**
   Every ambiguity in this dataset exists because the constraints are prose.
