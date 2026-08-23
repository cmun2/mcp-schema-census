# mcp-schema-census

**617 public MCP servers, launched over stdio. 14,804 real `tools/list` schemas.
Three provider strict-mode constraint sets applied to the same corpus.**

The finding is not a failure rate. On the axes that apply whether or not a
client opts in, this ecosystem is clean — **0.0%**. The finding is that three
providers, judging the same 617 servers, **disagree by 44.9 percentage points**.

## → [Start here: `dataset/README.md`](dataset/README.md)

That is the dataset's front page: the three axes, what each one does and does
not claim, the controls, the documented ambiguities, and how to reproduce or
dispute any single verdict.

한국어 요약: [`dataset/README.ko.md`](dataset/README.ko.md)

---

## Read this before quoting a number

**63.0% does not mean 63% of MCP servers are broken.** It is an opt-in number —
what happens if a client takes a server's `inputSchema` as published and sends
it with `strict: true`. Server authors control the schema but never the flag,
so it is an *exposure surface*, not a live outage.

**No API was called.** Verdicts come from the providers' published constraint
tables (quoted verbatim, with URLs), the providers' own production code, and
publicly reported errors. End-to-end verification against a live endpoint was
not performed, by design. `dataset/LIMITATIONS.md` says where that matters.

**We do not write "this server is broken."** We write "this schema is rejected
on this axis because of this value at this pointer." There is no leaderboard
here and no worst-offenders table. Please keep it that way if you reuse this.

**If a verdict looks wrong, it may well be — open an issue.** Every row in
`violations.jsonl` carries a `repro` field with the one-line command that
re-derives that verdict from the schema. Server authors who want their rows
removed only have to ask.

## Layout

| path | what it is |
|---|---|
| [`dataset/`](dataset/) | the published artifact — data, docs, verification scripts |
| [`src/`](src/) | collection harness and the rule implementations |
| [`oracle_ts/`](oracle_ts/) | the MCP TypeScript SDK oracle used for axis A |
| [`sdk-bug/`](sdk-bug/) | minimal reproduction of an `AssertionError` in the official Anthropic Python SDK on `type: ["string","null"]`, found by running that SDK over this corpus as an oracle. 88 tools across 30 servers. Filed upstream as [anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876). |
| [`REPORT.md`](REPORT.md) | 2026-08-09 — axes A and B (result: 0.0%) |
| [`REPORT_ANTHROPIC.md`](REPORT_ANTHROPIC.md) | 2026-08-23 — the Anthropic strict axis (0.0% → 63.0%) |
| [`checker/`](checker/) | a per-server checker CLI, started and halted. See `WIP-HALTED.md`. |

The raw collection output is **not** published: it contains tool descriptions
written by server authors, and this repository redistributes verdicts about
schemas rather than the prose those schemas carry. `dataset/CONSTRAINTS.md`
explains the rule; `dataset/scripts/prose.py` is where it is enforced.

## Licence

Measurement results: CC BY 4.0. Scripts: MIT. Neither re-licenses anything
written by a server author — see [`dataset/LICENSE`](dataset/LICENSE).
