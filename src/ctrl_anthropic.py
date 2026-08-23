#!/usr/bin/env python3
"""Positive + negative control for AXIS C (Anthropic).

Positive cases are taken ONLY from constraints the docs name verbatim, or from
the observed 400 in claude-code#10606. Negative cases are Anthropic's OWN
documented example schemas -- if the checker flags those, it is broken.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_anthropic import judge_server

def T(name, schema):
    return {"name": name, "inputSchema": schema}

CASES = []

def case(cid, expect, tools, note):
    CASES.append({"server_name": "CTRL-C/" + cid, "pkg": cid, "status": "ok",
                  "tools": tools, "_expect": expect, "_note": note})

# ---------------- POSITIVE: must be flagged --------------------------------
case("root-anyOf", "C0", [T("bad", {"anyOf": [{"type": "object", "properties": {}, "additionalProperties": False}]})],
     "claude-code#10606: input_schema does not support anyOf at the top level")
case("root-oneOf", "C0", [T("bad", {"oneOf": [{"type": "object", "properties": {}, "additionalProperties": False}]})],
     "claude-code#10606, oneOf variant")
case("root-allOf", "C0", [T("bad", {"allOf": [{"type": "object", "properties": {}, "additionalProperties": False}]})],
     "claude-code#10606, allOf variant")
case("numeric-minimum", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"n": {"type": "integer", "minimum": 1}}, "required": ["n"]})],
     'docs: "Numerical constraints (such as minimum, maximum, multipleOf)" not supported')
case("numeric-multipleOf", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"n": {"type": "number", "multipleOf": 0.5}}, "required": ["n"]})], "same bullet")
case("string-minLength", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"s": {"type": "string", "minLength": 3}}, "required": ["s"]})],
     'docs: "String constraints (minLength, maxLength)" not supported')
case("array-maxItems", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"a": {"type": "array", "items": {"type": "string"}, "maxItems": 5}}, "required": ["a"]})],
     'docs: "Array constraints beyond minItems of 0 or 1"')
case("array-minItems-2", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"a": {"type": "array", "items": {"type": "string"}, "minItems": 2}}, "required": ["a"]})],
     "docs: only minItems 0 or 1 supported")
case("addprops-open", "C", [T("bad", {"type": "object", "additionalProperties": {"type": "string"},
      "properties": {}, "required": []})],
     'docs: "additionalProperties set to anything other than false"')
case("external-ref", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"x": {"$ref": "http://example.com/s.json"}}, "required": ["x"]})],
     "docs: external $ref not supported")
case("recursive", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "$defs": {"Node": {"type": "object", "additionalProperties": False,
                          "properties": {"child": {"$ref": "#/$defs/Node"}}, "required": []}},
      "properties": {"root": {"$ref": "#/$defs/Node"}}, "required": ["root"]})],
     "docs: recursive schemas not supported")
case("enum-complex", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {"e": {"enum": [{"a": 1}, "x"]}}, "required": ["e"]})],
     "docs: complex types within enums not supported")
case("allOf-with-ref", "C", [T("bad", {"type": "object", "additionalProperties": False,
      "$defs": {"A": {"type": "object", "additionalProperties": False, "properties": {}, "required": []}},
      "properties": {"x": {"allOf": [{"$ref": "#/$defs/A"}]}}, "required": ["x"]})],
     "docs: allOf with $ref not supported")
case("limit-optional-25", "CL", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {f"p{i}": {"type": "string"} for i in range(25)}, "required": []})],
     "docs explicit limit: 24 optional parameters per request")
case("limit-tools-21", "CL", [T(f"t{i}", {"type": "object", "additionalProperties": False,
      "properties": {"a": {"type": "string"}}, "required": ["a"]}) for i in range(21)],
     "docs explicit limit: 20 strict tools per request")
case("limit-union-17", "CL", [T("bad", {"type": "object", "additionalProperties": False,
      "properties": {f"p{i}": {"type": ["string", "null"]} for i in range(17)},
      "required": [f"p{i}" for i in range(17)]})],
     "docs explicit limit: 16 union-typed parameters per request")

# ---------------- NEGATIVE: must NOT be flagged ----------------------------
# Anthropic's own documented strict:true example (strict-tool-use page).
case("DOC-get_weather", "clean", [T("get_weather", {
      "type": "object",
      "properties": {"location": {"type": "string", "description": "The city and state"},
                     "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}},
      "required": ["location"], "additionalProperties": False})],
     "Anthropic's own strict:true example -- must pass")
# Anthropic's own second documented example, uses `format: date` (a supported format).
case("DOC-search_flights", "clean", [T("search_flights", {
      "type": "object",
      "properties": {"destination": {"type": "string"},
                     "departure_date": {"type": "string", "format": "date"},
                     "passengers": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}},
      "required": ["destination", "departure_date"], "additionalProperties": False})],
     "Anthropic's own example with format:date + integer enum -- must pass")
# `pattern` is SUPPORTED on this axis (unlike OpenAI strict) -- must not be flagged.
case("NEG-pattern-ok", "clean", [T("ok", {"type": "object", "additionalProperties": False,
      "properties": {"id": {"type": "string", "pattern": "^[a-z]+$"}}, "required": ["id"]})],
     "pattern is supported by Anthropic (whole regex accordion) -- flagging it would be a FP")
# minItems 0/1 is explicitly allowed.
case("NEG-minItems-1-ok", "clean", [T("ok", {"type": "object", "additionalProperties": False,
      "properties": {"a": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, "required": ["a"]})],
     "minItems 1 is explicitly supported -- flagging it would be a FP")
# 24 optional params is AT the limit, not over.
case("NEG-optional-24-ok", "clean", [T("ok", {"type": "object", "additionalProperties": False,
      "properties": {f"p{i}": {"type": "string"} for i in range(24)}, "required": []})],
     "exactly at the documented 24-optional limit -- must not fire")


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/ctrl_anthropic.jsonl")
    rows, ok, bad = [], 0, 0
    print(f"{'case':24} {'expect':7} {'C0':>3} {'C':>3} {'CL':>3}  verdict")
    for c in CASES:
        j = judge_server(c)
        got = {"C0": j["C0_fail"], "C": j["C_strict_fail"], "CL": j["C_limit_fail"]}
        exp = c["_expect"]
        if exp == "clean":
            good = not any(got.values())
        else:
            good = got[exp]
        ok += good; bad += (not good)
        print(f"{c['pkg']:24} {exp:7} {str(got['C0'])[0]:>3} {str(got['C'])[0]:>3} {str(got['CL'])[0]:>3}  "
              f"{'PASS' if good else 'FAIL'}   {c['_note']}")
        j["_expect"] = exp; j["_note"] = c["_note"]; j["_pass"] = good
        rows.append(j)
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    npos = sum(1 for c in CASES if c["_expect"] != "clean")
    nneg = len(CASES) - npos
    posok = sum(1 for c, r in zip(CASES, rows) if c["_expect"] != "clean" and r["_pass"])
    negok = sum(1 for c, r in zip(CASES, rows) if c["_expect"] == "clean" and r["_pass"])
    print()
    print(f"POSITIVE (must be caught): {posok}/{npos}")
    print(f"NEGATIVE (must pass clean): {negok}/{nneg}")


if __name__ == "__main__":
    main()
