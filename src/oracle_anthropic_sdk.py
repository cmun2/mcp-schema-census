#!/usr/bin/env python3
"""ORACLE for axis C -- runs the REAL Anthropic Python SDK schema transformer
(anthropic.lib._parse._transform.transform_schema, v1.0.0) over every collected
MCP inputSchema.

Why this is an oracle and not another rule set: `transform_schema` is the code
path the official SDK uses to make a schema acceptable to the structured-outputs
/ strict-tool-use grammar compiler. Everything it *keeps* is API-safe by
construction; everything it *moves into the description string* is a keyword the
SDK's authors consider unsupported. So the set of dropped keywords is an
independent, production-sourced statement of the same constraint list I read out
of the prose docs.

Two outputs per tool:
  sdk_raises   -- transform_schema threw (schema cannot even be normalised)
  dropped      -- keywords the SDK stripped out of the wire schema
                  (i.e. the constraint is LOST unless the caller re-validates)

Run with the venv that has `anthropic` installed.
"""
import json, os, sys, copy

from anthropic.lib._parse._transform import transform_schema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WATCH = ["minimum", "maximum", "multipleOf", "exclusiveMinimum", "exclusiveMaximum",
         "minLength", "maxLength", "pattern", "maxItems", "minItems", "uniqueItems",
         "additionalProperties", "format", "const", "default", "propertyNames",
         "patternProperties", "oneOf", "not", "examples"]


def keywords_present(node, acc=None):
    if acc is None:
        acc = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in WATCH:
                acc.add(k)
            if k in ("properties", "$defs", "definitions") and isinstance(v, dict):
                for sub in v.values():
                    keywords_present(sub, acc)
            elif k in ("anyOf", "oneOf", "allOf") and isinstance(v, list):
                for sub in v:
                    keywords_present(sub, acc)
            elif k == "items":
                if isinstance(v, dict):
                    keywords_present(v, acc)
                elif isinstance(v, list):
                    for sub in v:
                        keywords_present(sub, acc)
    return acc


def main():
    out_path = sys.argv[-1]
    rows = []
    seen = set()
    for src in sys.argv[1:-1]:
        for line in open(src):
            r = json.loads(line)
            if r.get("status") != "ok" or r["pkg"] in seen:
                continue
            seen.add(r["pkg"])
            raises, dropped_any, per_tool = 0, 0, []
            for t in (r.get("tools") or []):
                s = t.get("inputSchema") if isinstance(t, dict) else None
                if not isinstance(s, dict):
                    continue
                before = keywords_present(copy.deepcopy(s))
                try:
                    after_schema = transform_schema(copy.deepcopy(s))
                    err = None
                except Exception as e:  # noqa: BLE001
                    raises += 1
                    per_tool.append({"tool": t.get("name"), "raises": type(e).__name__ + ": " + str(e)[:120]})
                    continue
                after = keywords_present(after_schema)
                # additionalProperties is ADDED by the transformer, never dropped
                dropped = sorted((before - after) - {"additionalProperties"})
                if dropped:
                    dropped_any += 1
                    per_tool.append({"tool": t.get("name"), "dropped": dropped})
            rows.append({"server_name": r["server_name"], "pkg": r["pkg"],
                         "n_tools": len(r.get("tools") or []),
                         "sdk_raises": raises > 0,
                         "sdk_drops_constraints": dropped_any > 0,
                         "detail": per_tool[:40]})
    with open(out_path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows) or 1
    print(f"SDK-transform oracle: servers={len(rows)}")
    print(f"  transform_schema raises        : {sum(1 for r in rows if r['sdk_raises'])}/{len(rows)} "
          f"= {100*sum(1 for r in rows if r['sdk_raises'])/n:.1f}%")
    print(f"  transform_schema drops constr. : {sum(1 for r in rows if r['sdk_drops_constraints'])}/{len(rows)} "
          f"= {100*sum(1 for r in rows if r['sdk_drops_constraints'])/n:.1f}%")


if __name__ == "__main__":
    main()
