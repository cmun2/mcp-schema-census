#!/usr/bin/env python3
"""Minimal reproductions of schemas that failed in real, public GitHub issues.

Each case is the smallest schema that carries the reported shape. The point is
not that the checker fires -- it is that the checker's behaviour on a real,
independently-reported failure is written down, including the cases where the
honest answer is "this is not on any axis we measure".

    python3 checker/tests/github_issue_repros.py

Exit 0 if every case behaves as recorded below, 1 if any drifted.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.dirname(HERE)
sys.path.insert(0, CHECKER)

from mcp_strict_check import analyse            # noqa: E402


CASES = [
    # ---------------------------------------------------------------- 1
    {
        "id": "root-oneOf",
        "issue": "https://github.com/Countly/countly-mcp-server/issues/64",
        "also": ["https://github.com/ProfSynapse/claudesidian-mcp/issues/6",
                 "https://github.com/anthropics/claude-code/issues/10606"],
        "reported": "400 tools.0.custom.input_schema: input_schema does not "
                    "support oneOf, allOf, or anyOf at the top level",
        "schema": {"type": "object",
                   "oneOf": [{"required": ["a"]}, {"required": ["b"]}],
                   "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                   "additionalProperties": False},
        "expect_codes": ["C0-root-combinator:oneOf"],
        "note": "Caught. Axis C0 -- the Anthropic Messages API baseline, which "
                "applies whether or not you opt into strict mode.",
    },
    {
        "id": "root-allOf",
        "issue": "https://github.com/ProfSynapse/claudesidian-mcp/issues/6",
        "reported": "same 400, allOf spelling",
        "schema": {"type": "object", "allOf": [{"required": ["a"]}],
                   "properties": {"a": {"type": "string"}},
                   "additionalProperties": False},
        "expect_codes": ["C0-root-combinator:allOf"],
        "note": "Caught. Same axis.",
    },
    {
        "id": "root-anyOf",
        "issue": "https://github.com/anthropics/claude-code/issues/10606",
        "reported": "same 400, anyOf spelling",
        "schema": {"type": "object", "anyOf": [{"required": ["a"]}],
                   "properties": {"a": {"type": "string"}},
                   "additionalProperties": False},
        "expect_codes": ["C0-root-combinator:anyOf", "B1-root-anyOf"],
        "note": "Caught on TWO axes: Anthropic's baseline 400, and OpenAI "
                "strict mode, whose _ensure_strict_root also refuses a root anyOf.",
    },

    # ---------------------------------------------------------------- 2
    {
        "id": "dollar-schema-inside-properties",
        "issue": "https://github.com/microsoft/pylance-release/issues/7986",
        "reported": "a `$schema` key appearing inside `properties`",
        "schema": {"type": "object",
                   "properties": {"$schema": {"type": "string"},
                                  "path": {"type": "string"}},
                   "required": ["path"],
                   "additionalProperties": False},
        "expect_codes": [],
        "note": "NOT APPLICABLE, and deliberately not forced onto an axis. "
                "No provider constraint document we cite says anything about a "
                "property literally named `$schema`, so there is no sentence to "
                "quote and no verdict to make. The dispute in that issue is "
                "about whether the key belongs there at all, which is an MCP / "
                "JSON-Schema-hygiene question, not a provider-strict-mode one. "
                "The five MCP-spec validators listed in the README are the right "
                "tools for it.",
    },
    {
        "id": "dollar-schema-at-root",
        "issue": "https://github.com/microsoft/pylance-release/issues/7986",
        "reported": "the sibling case: `$schema` as a root-level annotation",
        "schema": {"type": "object", "$schema": "http://json-schema.org/draft-07/schema#",
                   "properties": {"path": {"type": "string"}},
                   "required": ["path"], "additionalProperties": False},
        "expect_codes": [],
        "note": "NOT APPLICABLE for the same reason. Note this shape is common "
                "and benign in the corpus -- 1claw-mcp and many others ship it "
                "and pass every axis.",
    },

    # ---------------------------------------------------------------- 3
    {
        "id": "type-array-string-null-property",
        "issue": "https://github.com/anthropics/anthropic-sdk-python/issues/1876",
        "reported": 'AssertionError "Expected code to be unreachable" from '
                    "transform_schema on a property typed [\"string\", \"null\"]",
        "schema": {"type": "object",
                   "properties": {"cursor": {"type": ["string", "null"]}},
                   "additionalProperties": False},
        "expect_codes": [],
        "note": "NOT caught by any STATIC axis, and this is the honest answer. "
                "A union-typed property is legal under both providers' published "
                "constraint documents; it only counts toward Anthropic's "
                "union-parameter limit (CL3, 16 per request). What breaks is the "
                "Anthropic Python SDK's own transformer, which is a DEFECT rather "
                "than a documented constraint -- so it belongs to the SDK oracle, "
                "not to a rule. Run with --sdk-oracle to see it; the corpus "
                "records it for 88 tools across 30 servers (STATS.txt).",
        "sdk_oracle_raises": True,
    },
    {
        "id": "type-array-string-null-root",
        "issue": "https://github.com/anthropics/anthropic-sdk-python/issues/1876",
        "reported": "the root-level sibling of the same shape",
        "schema": {"type": ["object", "null"],
                   "properties": {"cursor": {"type": "string"}},
                   "additionalProperties": False},
        "expect_codes": ["A3-type-array", "B2-root-nullable"],
        "note": "Caught on two axes, neither of them Anthropic's strict subset: "
                "the MCP specification pins the root type to the string "
                '"object", and OpenAI\'s _ensure_strict_root requires a '
                "non-nullable object root. Anthropic's published constraint "
                "list says nothing about it -- only its SDK breaks, and only "
                "as a defect.",
    },
    {
        "id": "type-array-over-CL3-limit",
        "issue": "https://github.com/anthropics/anthropic-sdk-python/issues/1876",
        "reported": "the aggregate case the published Anthropic docs DO cover",
        "schema": {"type": "object", "additionalProperties": False,
                   "properties": {f"p{i}": {"type": ["string", "null"]}
                                  for i in range(17)}},
        "expect_codes": ["CL3-too-many-union-params"],
        "note": "Caught. 17 union-typed parameters exceeds the documented "
                "limit of 16 per request.",
    },
]


def run_case(c):
    tools = [{"name": c["id"], "inputSchema": c["schema"]}]
    findings, _ = analyse(tools, label=c["id"])
    got = sorted({f["code"] for f in findings if f["axis"] != "AMB"})
    want = sorted(c["expect_codes"])
    return got, want, findings


def main():
    bad = 0
    for c in CASES:
        got, want, findings = run_case(c)
        ok = got == want
        bad += 0 if ok else 1
        print("=" * 78)
        print(f"{'PASS' if ok else 'DRIFT'}  {c['id']}")
        print(f"  issue    : {c['issue']}")
        for u in c.get("also", []):
            print(f"             {u}")
        print(f"  reported : {c['reported']}")
        print(f"  schema   : {json.dumps(c['schema'])[:200]}")
        print(f"  expected : {want or '(no code on any axis)'}")
        print(f"  got      : {got or '(no code on any axis)'}")
        if not ok:
            print("  !! the checker's behaviour on this real-world case CHANGED")
        print(f"  verdict  : {c['note']}")
        for f in findings:
            if f["axis"] == "AMB":
                continue
            print(f"      {f['code']}  {f['tool']}  {f['json_pointer']}")
            print(f"        docs: \"{f['source_quote']}\"")
            print(f"              {f['source']}")
            print(f"        fix : {f['fix']}")
        print()
    print("=" * 78)
    print(f"{len(CASES) - bad}/{len(CASES)} cases behave as recorded")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
