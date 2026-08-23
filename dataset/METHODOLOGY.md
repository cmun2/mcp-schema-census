# Methodology

How the 14,804 schemas were obtained, how each verdict was reached, and how to
redo either.

---

## 1. Sampling

Source: the official MCP registry, `https://registry.modelcontextprotocol.io/v0/servers`
— public, free, unauthenticated. Fully paginated on **2026-08-09**, yielding
6,100 servers at their latest version.

From that, the stdio-launchable subsets: ~1,110 npm packages and ~690 PyPI
packages. Random samples were drawn with a fixed seed, in three slices:

| slice | ecosystem | drawn | started | in the corpus (after global de-dup) |
|---|---|---:|---:|---:|
| npm | npm | 420 | 298 | 298 |
| pypi | PyPI | 260 | 118 | 117 |
| holdout | npm | 300 | 204 | 202 |
| **total** | | **980** | **620** | **617** |

**The holdout slice was drawn and collected after the axis-A and axis-B rules
were frozen.** It is a genuine out-of-sample check, not a re-split. Axis C was
applied to all three slices at once on 2026-08-23; the holdout is out-of-sample
for A and B, and in-sample for C.

**De-duplication.** Three packages appear in two slices each
(`pagewatch-mcp`, `@rubric-protocol/mcp-server`, `geomelon-mcp`). Every rate in
this dataset is computed over the 617 **distinct packages**; the first slice a
package appears in (npm → pypi → holdout) is the one recorded in its `slice`
field. Where an older report quotes 620, it was counting rows before this
de-duplication — see README.md's note on 412 vs 414.

**Not sampled: Go / OCI-distributed servers.** ~130 servers (~2.1% of the
registry) ship as container images and the collection environment had no Docker.
This is the largest known hole; see LIMITATIONS.md.

---

## 2. Collection — the schemas are real, not scraped

Each server was **actually launched** as a local subprocess over stdio (`npx`
for npm, `uvx` for PyPI), spoken to with the MCP handshake, and asked
`tools/list`. The recorded `inputSchema` is the exact object the running server
returned. Nothing was parsed out of a repository, a README, or a registry
manifest.

Environment variables were supplied as **dummy values**
(`POC_DUMMY_NOT_A_REAL_KEY`) or as the public URLs the registry itself declares.
No real credential was ever passed to any server, and none is in this dataset —
`verify_no_prose.py` scans for eleven credential formats and reports 0.

Three things made this harder than it sounds, all of them recorded here because
they shaped the 620/980 success rate:

1. **`npx` zombie deadlock.** `npx` spawns a grandchild `node` process. Killing
   only `npx` leaves the grandchild holding the stderr pipe, and
   `p.stderr.read()` blocks forever. The first collection run processed 2 of 400
   servers and stopped. Fixed with `start_new_session=True` + `os.killpg` on the
   whole process group, and a separate reader thread for stderr. Success rate
   went from 2/12 to ~85%.
2. **Undeclared environment variables.** Many servers require env vars the
   registry metadata does not declare. On failure, `[A-Z_]{5,}` tokens were
   scraped from stderr and the launch retried once with dummy values for them.
   55 of the 360 failures had such a retry attempted.
3. **`mcp` SDK v2 removed `mcp.server.fastmcp`**, which killed most PyPI servers
   at import. Pinning `UV_CONSTRAINT` to `mcp<2` took that slice from 0/8 to
   4/8.

**360 servers never started.** They are in `failures.jsonl` with their status
(`timeout_or_crash` 356, `rpc_error` 4) and whether an env retry was attempted.
Their stderr is **not** published — it is third-party program output — only its
length and a 12-character digest.

> An earlier report (`../REPORT.md` §8) splits those 360 into "81 requiring
> credentials / 279 other". That split is **not recoverable** from the fields
> that were stored, so it is not reproduced here. What `failures.jsonl` records
> is what was actually kept.

---

## 3. Judging

Three axes, three different kinds of authority. This distinction matters more
than any individual number.

| axis | authority | kind |
|---|---|---|
| **A** | MCP TypeScript SDK 1.30.0 `ListToolsResultSchema.safeParse()` | **a real production parser ran on the data** |
| **B** | `openai-agents` `ensure_strict_json_schema` | **a real production converter ran on the data** |
| **B′** | documented unsupported-keyword list | static rule from documentation |
| **C0** | one publicly reported, observed 400 | empirical, marked as such |
| **C / CL** | Anthropic's published constraint tables, quoted verbatim | static rule from documentation |

For A and B the headline is not our opinion — the vendors' own code produced it.
For C, no such converter exists that *rejects* (the Anthropic SDK silently
*transforms* instead), so the rule was written from the documentation, frozen
before looking at the corpus, and then cross-checked against the SDK's transform
behaviour as an independent oracle (§5).

Static-rule error rates were measured against the oracles on axes A and B:
axis A 0 false positives / 0 false negatives across all three slices; axis B
2.0% / 0.8% / 2.0% false positives, 1 false negative. Since A and B headlines
come from the oracles rather than the rules, those rates do not touch the
published figures.

All verdict codes, with their sources and verbatim quotes, are in
[CONSTRAINTS.md](CONSTRAINTS.md).

---

## 4. Controls

**Controls must be built per axis.** The 2026-08-09 axis-A control set, replayed
against axis C, mostly passes — correctly, because a bare `true` `inputSchema`
violates the *MCP specification*, not Anthropic's *strict subset*. Reusing one
control set across axes would have looked like a broken detector. This is
recorded because it was the round's clearest methodological lesson.

**Axis C: 16 positive, 5 negative.** Each positive case isolates exactly one
verbatim-forbidden feature. All 16 fire.

The negatives are the more interesting half, because they test for
over-detection:

- `get_weather` — from Anthropic's own strict-tool-use documentation
- `search_flights` — from the same page, using `format: date` and an integer `enum`
- a schema using `pattern` — supported on Anthropic, silently dropped on OpenAI
- a schema using `minItems: 1` — supported
- a schema with exactly 24 optional parameters — the CL2 boundary

All 5 pass clean. The detector does not fire on the provider's own examples, and
does not fire on the boundary.

**Axis A/B: 10 cases**, drawn from real bug reports (Go `interface{}` bare
`true`, missing `type`, `type: ["object","null"]`, missing `inputSchema`,
`required: null` from opencode#35528, `type: "string"` root,
`outputSchema.type: "array"`, plus 3 that must *not* trip axis A). The real SDK
parser throws on 7/7 and passes 3/3. That control set also surfaced a genuine
bug in our own axis-A rule — a `required: null` slipping past an `is not None`
guard — before the headline was computed.

Every case, with its input schema, expected verdict, observed verdict and
pass/fail, is a row in `controls.jsonl`.

---

## 5. The independent oracle

Believing our own reading of a prose document is exactly the failure mode this
work was supposed to avoid. So the official **Anthropic Python SDK 1.0.0**'s
`transform_schema` (`anthropic/lib/_parse/_transform.py`) was run over all
14,804 schemas. What it strips from the wire schema is what its authors consider
unsupported — an opinion derived from an implementation rather than from our
reading.

| | value |
|---|---:|
| `transform_schema` raises | 75/617 = 12.2% |
| `transform_schema` strips ≥ 1 constraint | 446/617 = 72.3% |
| agrees with the static axis-C verdict (server unit) | 510/617 = 82.7% |

Per-keyword server counts, SDK vs. our rule: `minimum` 260/267, `maximum`
253/259, `minLength` 154/158, `maxLength` 131/138, `maxItems` 87/94, `minItems`
19/24, `uniqueItems` 1/1. Two independent implementations, near-identical
answers.

The 107 disagreements are enumerated and explained in README.md. In short: of
the 25 where our rule fires and the oracle is silent, 22 are an oracle blind
spot (the SDK *overwrites* `additionalProperties` rather than removing it, so a
removal-detector cannot see it) and 3 are servers where the SDK raised before
reaching the stripping stage. The 82 in the other direction are the
documentation-vs-SDK contradiction that is itself finding #4 in the ambiguities
list. None of the 107 is an unexplained error.

### A side finding: the SDK crashes on nullable type arrays

`transform_schema` raised on 75 servers. Tool-unit breakdown:

| exception | tools |
|---|---:|
| `ValueError: Schema must have a 'type', 'anyOf', 'oneOf', or 'allOf' field.` | 150 |
| `AssertionError: Expected code to be unreachable, but got: [...]` | 88 |
| `TypeError: 'list' object is not a mapping` | 6 |

Of the 88 `AssertionError`s, 57 are exactly `["string","null"]` (17 servers) and
75 involve some array containing `"null"`. `type: ["string","null"]` is what
Zod's `.nullable()` and Pydantic's `Optional[...]` routinely emit, so this is
not an exotic input. An `assert_never` reached by ordinary user data reads as an
implementation defect rather than a documented limitation. A minimal, from-scratch
reproduction is in `../sdk-bug/` — **not filed upstream**.

---

## 6. Reproducing layer 1 — verdicts only

Seconds. No network, no API key, no server execution. The published schemas are
enough.

```bash
cd dataset

python3 scripts/verify_no_prose.py   # 0 prose fields / 0 credentials / 0 PII
python3 scripts/verify_verdicts.py   # re-judge stripped schemas: 0 differences
python3 scripts/stats.py             # every number in README.md
python3 scripts/explain.py --server "<name>" --code "<code>" [--tool T] [--pointer P]
```

`scripts/judge_anthropic.py` and `scripts/judge_mcp_and_openai.py` are the
verbatim judges used in the measurement, vendored here so this directory stands
alone.

Axes A and B need their external oracles:

```bash
# axis A -- the real MCP TypeScript SDK parser (node required)
npm i @modelcontextprotocol/sdk@1.30.0
node oracle_ts/oracleA.mjs < tools.jsonl

# axis B -- the real OpenAI strict converter
pip install openai-agents
python3 ../src/oracle_strict.py

# axis C corroboration -- the official Anthropic SDK transform
uv venv .venv-anth --python 3.12 && uv pip install --python .venv-anth/bin/python anthropic
.venv-anth/bin/python ../src/oracle_anthropic_sdk.py <tools files> oracleC_sdk.jsonl
```

---

## 7. Reproducing layer 2 — collect the schemas again

Hours, and it **downloads and executes arbitrary third-party code on your
machine**. Run it in a container or a disposable VM. This is not a formality:
the corpus is 617 packages published by strangers to public registries.

```bash
python3 ../src/fetch_registry.py    # public MCP registry, free, no auth
python3 ../src/collect_stdio.py     # npx launch -> tools/list
python3 ../src/collect_pypi.py      # uvx launch -> tools/list
```

This is also the path to the **original tool descriptions**, which this dataset
deliberately does not redistribute. Every row of `servers.jsonl` carries
`package`, `ecosystem`, `package_version` and `repository`; that is everything
needed to fetch the same package and read its prose from the source, under
whatever license its author chose.

A re-collection will not reproduce the corpus exactly. Packages get new
versions, servers change their tools, and the ~60% startup rate depends on the
local `npx`/`uvx` environment. `package_version` is recorded per server so the
delta is at least attributable.

---

## 8. Updating

The two dates on every server row move independently, and that is deliberate.

| layer | cost | realistic cadence |
|---|---|---|
| re-read the provider constraint docs, diff them | 3 `curl`s + human judgement | monthly — **this is the real update**, provider constraints do change |
| re-judge the existing corpus against a new table | seconds, no network | monthly, fully automatable |
| re-collect the schemas | hours, ~60% startup rate, executes third-party code | quarterly at most |

Translating a change in documentation wording into a rule is a **human**
judgement — the five ambiguities are the standing proof. Do not automate that
step. Automating the diff and the re-judge is fine; automating the
interpretation is how a dataset starts publishing guesses.
