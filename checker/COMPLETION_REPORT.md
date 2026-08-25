# Completion report — `checker/` (`mcp-strict-check`)

**2026-08-23.** Commits `1728bb1` (rule extraction) and `be52dfa` (the checker).
Nothing pushed; the repository has no git remote configured at all.

---

## 1. Is the rule source actually singular?

Yes, and it is asserted mechanically rather than asserted in prose.

Before this work the rule logic existed in **four** files, two pairs of them
byte-identical (`diff` produced no output):

```
src/lint_anthropic.py  ==  dataset/scripts/judge_anthropic.py
src/lint.py            ==  dataset/scripts/judge_mcp_and_openai.py
```

The rules now live only in `dataset/scripts/rules/`:

```
rules/codes.py       verdict code -> axis, severity, source URL, verbatim quote
rules/mcp_openai.py  axis A (MCP spec), axis B/B' (OpenAI strict)
rules/anthropic.py   axis C0 / C / CL (Anthropic baseline + strict:true)
rules/fixes.py       one-line remediation per code   (presentation, not a rule)
rules/sdk_oracle.py  the vendor transformer wrapper  (oracle, not a rule)
```

Six consumers import it: `checker/mcp_strict_check/cli.py`,
`dataset/scripts/judge_anthropic.py`, `dataset/scripts/judge_mcp_and_openai.py`,
`dataset/scripts/explain.py`, `src/lint_anthropic.py`, `src/lint.py`.
`dataset/scripts/codes.py` remains as a shim so `from codes import meta_for`
keeps working in `build_dataset.py` and `explain.py`.

### Evidence: `python3 checker/tests/test_single_source.py` → exit 0

The identity checks are `is`, not `==` — the same function *object*, not an
equal copy:

```
[PASS] same object: checker/mcp_strict_check/cli.py -> judge_server_anthropic
[PASS] same object: checker/mcp_strict_check/cli.py -> judge_server_mcp_openai
[PASS] same object: checker/mcp_strict_check/cli.py -> meta_for
[PASS] same object: dataset/scripts/judge_anthropic.py -> check_C
[PASS] same object: dataset/scripts/judge_mcp_and_openai.py -> check_A
[PASS] same object: dataset/scripts/judge_mcp_and_openai.py -> check_B
[PASS] same object: src/lint_anthropic.py -> check_C
[PASS] same object: src/lint.py -> check_A
[PASS] same object: dataset/scripts/explain.py -> judge_server
[PASS] same object: dataset/scripts/codes.py -> meta_for

  check_C   defined once at dataset/scripts/rules/anthropic.py
  check_A/B defined once at dataset/scripts/rules/mcp_openai.py
  meta_for  defined once at dataset/scripts/rules/codes.py

[PASS] exactly one copy of the axis-C rule body
        found in: ['dataset/scripts/rules/anthropic.py']
[PASS] exactly one copy of the axis-A rule body
        found in: ['dataset/scripts/rules/mcp_openai.py']
[PASS] exactly one copy of the axis-B rule body
        found in: ['dataset/scripts/rules/mcp_openai.py']
[PASS] exactly one copy of the code -> doc-quote table
        found in: ['dataset/scripts/rules/codes.py']
[PASS] exactly one copy of the code -> metadata resolver
        found in: ['dataset/scripts/rules/codes.py']
[PASS] exactly one copy of the code -> one-line-fix table
        found in: ['dataset/scripts/rules/fixes.py']
[PASS] exactly one copy of the OpenAI unsupported-keyword table
        found in: ['dataset/scripts/rules/mcp_openai.py']
[PASS] exactly one copy of the Anthropic supported-format table
        found in: ['dataset/scripts/rules/anthropic.py']
[PASS] every registered code carries a verbatim source quote
[PASS] every registered code carries a one-line fix
[PASS] no code the judges emit falls through lookup() to ('?','unknown')
        codes seen in the rule sources: 27
single source of truth: confirmed
```

The second block is a filesystem walk: it greps the whole tree (excluding
`.git`, `.venv-anth`, `data/`, `out/`, and the test file itself) and fails if a
rule body appears in more than one file. A future copy-paste breaks the build.

**No JSON export, no Node front end.** The CLI is Python, so the "generate a
JSON rule table from the Python source" escape hatch was not needed and was not
built. If a Node front end is ever wanted, that path is still the right one —
generation, never transcription.

---

## 2. Checker vs `dataset/violations.jsonl`

**617 of 617 servers match exactly. 0 mismatches.** The requested 5+5 sample
matches; so does every other server in the corpus.

The comparison is not a count. Each finding is keyed on
`(tool_name, code, json_pointer, value)` and compared as a multiset, so a right
count with a wrong pointer, a wrong value, or a hit attributed to the wrong tool
all register as mismatches.

### The requested sample — `python3 checker/tests/crosscheck_corpus.py` → exit 0

The five "dirty" servers were chosen to span the most distinct violation code
families, not to be easy; the five "clean" ones are the zero-violation servers
with the most tools, so the null result is over real surface area (64 tools of
it) rather than over empty schemas.

```
axis-A rows in the corpus: 0  (expected 0 -- axis A is 0/617; nothing to cross-check there)
cross-checking 10 server(s)

[MATCH   ] dirty com.mailrith/mailrith
             package=@mailrith/mcp-server  tools=52  checker_findings=309  corpus_rows=309
[MATCH   ] dirty com.smartbear/smartbear-mcp
             package=@smartbear/mcp  tools=296  checker_findings=1247  corpus_rows=1247
[MATCH   ] dirty ai.ravenmcp/raven-mcp
             package=raven-mcp  tools=105  checker_findings=212  corpus_rows=212
[MATCH   ] dirty com.run402/mcp
             package=run402-mcp  tools=198  checker_findings=216  corpus_rows=216
[MATCH   ] dirty io.github.BASIC-BIT/vrchat-mcp
             package=@basicbit/vrchat-mcp  tools=69  checker_findings=660  corpus_rows=660
[MATCH   ] clean ai.demomagic/interactive-video-guide
             package=@demomagic/mcp  tools=18  checker_findings=0  corpus_rows=0
[MATCH   ] clean io.github.A0Nexus-bit/a0nexus-bitcoin-mcp
             package=a0nexus-bitcoin-mcp  tools=17  checker_findings=0  corpus_rows=0
[MATCH   ] clean dev.dungbeetle/mcp
             package=dungbeetle-mcp  tools=12  checker_findings=0  corpus_rows=0
[MATCH   ] clean io.github.Ayo-Fam/mcp-google-ads
             package=mcp-google-ads-multi  tools=10  checker_findings=0  corpus_rows=0
[MATCH   ] clean email.templated/mcp
             package=@templatedemails/mcp  tools=7  checker_findings=0  corpus_rows=0

10/10 servers match exactly; 0 mismatch(es)
```

### The whole corpus — `crosscheck_corpus.py --all` → exit 0

```
617/617 servers match exactly; 0 mismatch(es)
```

`grep -c MATCH` over that run returns `617`; `grep -c MISMATCH` returns `0`.
That covers all 14,804 tools and all 31,954 violation rows.

### One exclusion, stated rather than hidden

**Axis A is excluded from the comparison**, and the script fails loudly if that
exclusion ever goes stale. The corpus records axis A from an *external* oracle
(`modelcontextprotocol/typescript-sdk@1.30.0 ListToolsResultSchema.safeParse`)
under a single code `A-oracle-reject`, not from the static `A1..A6` rules the
checker runs. There is nothing to compare because the corpus contains **zero**
axis-A rows — axis A is 0/617 = 0.0%. Rather than assume that, the script
asserts it and aborts if a row ever appears.

So the honest statement is: on every axis where `violations.jsonl` was produced
by the static rule engine (B, B', C0, C, CL, and the AMB rows), the checker
agrees exactly. On axis A the checker applies the documented spec rules while
the corpus applied an SDK oracle; those two happen to both be empty here, but
they are not the same measurement and are not claimed to be.

---

## 3. GitHub-issue schema reproductions

`python3 checker/tests/github_issue_repros.py` → **8/8 as recorded, exit 0.**

| # | case | issue | result |
|---|---|---|---|
| 1 | root `oneOf` | [countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64) | **caught** — `C0-root-combinator:oneOf` |
| 2 | root `allOf` | [claudesidian-mcp#6](https://github.com/ProfSynapse/claudesidian-mcp/issues/6) | **caught** — `C0-root-combinator:allOf` |
| 3 | root `anyOf` | [claude-code#10606](https://github.com/anthropics/claude-code/issues/10606) | **caught on two axes** — `C0-root-combinator:anyOf` + `B1-root-anyOf` |
| 4 | `$schema` inside `properties` | [pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986) | **not applicable** — fires nothing, deliberately |
| 5 | `$schema` at root | same | **not applicable** — fires nothing, deliberately |
| 6 | property `type: ["string","null"]` | [anthropic-sdk-python#1876](https://github.com/anthropics/anthropic-sdk-python/issues/1876) | **not caught by any static axis** — caught by `--sdk-oracle` |
| 7 | root `type: ["object","null"]` | same | **caught** — `A3-type-array` + `B2-root-nullable` |
| 8 | 17 union-typed properties | same | **caught** — `CL3-too-many-union-params` |

### Case 1–3: root combinators — caught

```
PASS  root-oneOf
  issue    : https://github.com/Countly/countly-mcp-server/issues/64
             https://github.com/ProfSynapse/claudesidian-mcp/issues/6
             https://github.com/anthropics/claude-code/issues/10606
  reported : 400 tools.0.custom.input_schema: input_schema does not support
             oneOf, allOf, or anyOf at the top level
  expected : ['C0-root-combinator:oneOf']
  got      : ['C0-root-combinator:oneOf']
      C0-root-combinator:oneOf  root-oneOf  #
        docs: "tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level"
              https://github.com/anthropics/claude-code/issues/10606
        fix : move the oneOf/allOf/anyOf off the root: keep a flat root object and put the branch under a property.
```

`anyOf` fires twice, on two different providers' axes, which is the kind of
thing the tool exists to show:

```
PASS  root-anyOf
  expected : ['B1-root-anyOf', 'C0-root-combinator:anyOf']
  got      : ['B1-root-anyOf', 'C0-root-combinator:anyOf']
```

Note the C0 quote's source is a GitHub issue, not a constraint document, and it
is labelled `empirical` in `codes.py` and printed as "EMPIRICAL: observed 400,
not in the published constraint docs". This axis is 0/617 in the corpus — no
collected server trips it. The repro is the evidence that the rule fires at all.

### Case 4–5: `$schema` — NOT APPLICABLE, and not forced

**This is the case the task flagged as contested, and the answer is that it does
not map to any axis here.** The checker reports nothing for it, deliberately.

```
PASS  dollar-schema-inside-properties
  issue    : https://github.com/microsoft/pylance-release/issues/7986
  reported : a `$schema` key appearing inside `properties`
  expected : (no code on any axis)
  got      : (no code on any axis)
```

Reasoning, recorded in the test file itself so it cannot drift from the code:
every verdict this tool emits is a claim that a *published provider sentence*
rejects a *specific value at a specific pointer*. No constraint document cited
in `rules/codes.py` — OpenAI's structured-outputs page, the Agents SDK's
`strict_schema.py`, Anthropic's strict-tool-use and structured-outputs pages,
the Anthropic complexity-limits table — says anything about a property named
`$schema`. There is no sentence to quote, so there is no verdict to make.
Inventing a rule to make the tool look more capable is exactly the failure mode
the single-source design is meant to prevent.

The dispute in #7986 is about JSON-Schema/MCP hygiene, which is the axis the
five existing validators cover. The README says so and links them.

Worth adding: a root-level `$schema` annotation is *common and benign* in this
corpus — `io.github.1clawAI/1claw-mcp` and many others ship
`"$schema": "http://json-schema.org/draft-07/schema#"` and pass every axis.

### Case 6: `type: ["string","null"]` — the honest split

A property typed `["string","null"]` fires **no static rule**, and that is
correct: it is legal under both providers' published constraint documents. It
counts only toward Anthropic's union-parameter limit, which is a per-*request*
limit of 16 — case 8 shows it firing at 17.

```
PASS  type-array-string-null-property
  issue    : https://github.com/anthropics/anthropic-sdk-python/issues/1876
  reported : AssertionError "Expected code to be unreachable" from
             transform_schema on a property typed ["string", "null"]
  expected : (no code on any axis)
  got      : (no code on any axis)
```

What breaks is the Anthropic Python SDK's own transformer — a **defect**, not a
documented constraint. That belongs to an oracle, not to a rule, and
`--sdk-oracle` reports it:

```
$ .venv-anth/bin/python checker/mcp_strict_check/cli.py --tools t2.json --sdk-oracle

==============================================================================
Anthropic Python SDK transformer  —  oracle, not a rule
==============================================================================
  anthropic==1.0.0  (the corpus was measured against 1.0.0)

  transform_schema RAISED on 1 tool(s) — the SDK cannot even normalise these.
      page  AssertionError: Expected code to be unreachable, but got: ['string', 'null']
      An AssertionError here is an SDK DEFECT, not a documented
      constraint: see anthropics/anthropic-sdk-python#1876 for the
      ["string","null"] case.
```

The corpus records the same crash for **88 tools across 30 servers**
(`STATS.txt`, "SDK AssertionError by type array"), 75 of them on a type array
containing `null`.

The root-level sibling *is* caught, but by two axes neither of which is
Anthropic's strict subset — the MCP spec pins the root `type` to the string
`"object"`, and OpenAI's `_ensure_strict_root` requires a non-nullable object
root:

```
PASS  type-array-string-null-root
  expected : ['A3-type-array', 'B2-root-nullable']
  got      : ['A3-type-array', 'B2-root-nullable']
```

---

## 4. `verify_all.sh` — before and after

| when | exit code | notes |
|---|---:|---|
| before any change (baseline) | **0** | all 4 checks passed |
| after the rule extraction (`1728bb1`) | **0** | all 4 checks passed |
| after the checker + `codes.py` additions (`be52dfa`) | **0** | all 4 checks passed |

All four checks ran on every pass (this machine has the unpublished `../data/`,
so checks 2 and 3 were not skipped):

```
1/4  no third-party prose, no credentials, no PII        RESULT: PASS
2/4  prose removal changed no verdict                    RESULT: PASS
3/4  rebuild from source and assert every frozen rate     frozen-rate assertions: PASS (no verdict moved)
4/4  regenerate every number quoted in the docs          (STATS.txt rewritten)
# ALL CHECKS PASSED
```

**Stronger than the exit code:** check 3 rewrites `dataset/*.jsonl` and check 4
rewrites `STATS.txt` from source. After every run,

```
$ git diff --stat -- dataset/*.jsonl dataset/STATS.txt
(no output)
```

The rebuild reproduced all 41 MB of published data **byte for byte**. Not one
verdict, count, pointer or rate moved.

The frozen judgement figures are untouched and re-asserted by
`build_dataset.py`: A 0.0% · B 27.6% · B' 56.9% · C0 0.0% · C **63.0%** ·
CL **37.3%** · C* **72.4%** · 27.6 → 72.4 gap **44.9** · clean-on-A-and-B but
failing C* **277/617 = 44.9%** · OpenAI-silent-only → Anthropic-hard-400
**219/617 = 35.5%**. Every one of the six figures the task pinned
(63.0 / 72.4 / 27.6 / 44.9 / 56.9 / 37.3) is present and unchanged.
`dataset/scripts/prose.py` was not modified at all
(`git log --oneline -- dataset/scripts/prose.py` shows no new commit).

`checker/tests/run_all.sh` → **exit 0**, all four suites.

---

## 5. Git state — nothing pushed

```
$ git status --short
?? .DS_Store

$ git log --oneline -3
be52dfa Add mcp-strict-check, a strict-mode checker for server authors
1728bb1 Extract the verdict rules into one shared engine
423358f Record that the SDK defect was filed as anthropic-sdk-python#1876

$ git remote -v
(no output — no remote is configured)

$ git log --oneline --branches --not --remotes | wc -l
13
```

**No remote exists**, so no push was possible and none was attempted. All 13
commits on this branch are local. No npm publish, no PyPI publish, no new login,
no OAuth, no paid API call, no API key created, no payment method touched. The
only third-party code executed was `anthropic==1.0.0`'s local
`transform_schema` from the pre-existing `.venv-anth`, which is a pure function
call.

`.DS_Store` is untracked and was left untracked; it predates this task.

---

## 6. Two dormant bugs closed on the way past

Neither changes a published number — both were verified to have zero hits in the
corpus before being touched.

**(a) `C7` code mismatch** (already noted in the halt record).
`rules/anthropic.py` emits `C7-enum-complex-type`; `codes.py` registered only
`C7-complex-enum`. `lookup()` fell through to `("?", "unknown", "MCP_SPEC", "")`,
so a complex-enum schema would have produced an unresolved axis and an **empty
source quote** — a finding with no evidence behind it. Both spellings are now
registered. The emitted string is unchanged.

**(b) Five more of the same, found by the new test.** `test_single_source.py`
extracts every code literal from the rule sources and asserts none falls through
`lookup()`. It caught five that had never been noticed:

```
unresolved: ['A0-tool-not-object', 'A4-properties-not-object',
             'A6-outputSchema-not-object', 'B2-root-not-object',
             'B4-untyped-open-object']
```

All five are now registered. `A0` and `A4` are cited to the TypeScript SDK's
wire schema (`buildSchemas.ts`) under a new `MCP_TS_SDK` source key rather than
to the JSON spec URL, because the quoted text is Zod source, not spec prose.

---

## 7. What I did not do, and what I am not certain of

**Not done, deliberately:**

- **No JSON rule-table export and no Node front end.** The CLI is Python and
  imports the engine directly, so the generated-JSON escape hatch was never
  needed. If a Node front end is wanted later, generate the table from the
  Python source; do not transcribe it.
- **Not packaged for npm or PyPI.** The tool must run from inside this
  repository, because "the rules and the dataset are one tree" is the whole
  design. Publishing it standalone would require either vendoring the rules —
  reintroducing the drift this work removed — or shipping the corpus with it.
  That trade-off is a product decision, not mine to make. `checker/README.md`
  states the constraint plainly rather than hiding it.
- **No rule was added, widened or weakened.** `--sdk-oracle` is an oracle, not a
  rule, and is opt-in.
- **The `A4-required-not-string-array` citation was left alone.** It quotes Zod
  source (`required: z.array(z.string()).optional()`) under the JSON-spec URL,
  which is imprecise in the same way the two entries I added would have been.
  Changing it would alter the `source` field semantics of a pre-existing code, so
  I flag it here instead of quietly editing it. Zero corpus rows carry it, so
  correcting it later costs nothing.

**Genuinely uncertain:**

- **Whether a sixth tool is the right vehicle at all.** The halt record's open
  question — contribute the rules to `@yawlabs/mcp-compliance`, which already has
  distribution and a CC BY rule catalog, versus ship a separate tool — is *still
  open*. This work makes either path cheaper (the rules are now one importable
  module with a machine-readable code/quote/fix table), but it does not answer
  it. I built what was asked; I do not claim it settles the distribution question.
- **The C0 axis has never fired on a real collected server** (0/617). Its
  evidence is four public issue reports plus these repros. If that empirical 400
  has since been fixed upstream, the axis would be stale — and nothing here would
  detect that, because the tool makes no API call by design.
- **The `--cmd` stdio client is minimal and hand-rolled.** It handles the
  handshake, `notifications/initialized`, `tools/list` pagination, protocol
  version fallback (`2025-06-18` → `2024-11-05`), non-JSON stdout noise, and
  timeouts. It has been exercised against one local demo server and the CLI test
  suite, **not** against a wide range of real servers. A server that only speaks
  HTTP/SSE, requires a specific initialize capability, or writes framed rather
  than line-delimited JSON will fail to start; the failure is a clean exit 2 with
  the reason, not a wrong verdict, but the coverage claim is narrow.
- **`--max-per-code` defaults to 10.** Anything hidden is counted in the output,
  and `--json` is never truncated, but a terminal reader who ignores the "and N
  more" line will under-count.
