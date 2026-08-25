#!/usr/bin/env python3
"""A deliberately-flawed MCP server, for exercising `--cmd` without a network.

Four tools, each carrying one shape that a provider strict mode rejects, plus
one that is clean. Speaks the minimum stdio JSON-RPC needed for
initialize -> notifications/initialized -> tools/list.

    ./checker/mcp-strict-check --cmd "python3 checker/examples/demo_server.py"
"""
import json
import sys

TOOLS = [
    {   # clean on every axis
        "name": "ping",
        "description": "no arguments, nothing to reject",
        "inputSchema": {"type": "object", "properties": {},
                        "additionalProperties": False},
    },
    {   # C2/C3 + B5: constraints Anthropic 400s on and OpenAI silently drops
        "name": "search",
        "description": "string and numeric constraints",
        "inputSchema": {"type": "object", "properties": {
            "q": {"type": "string", "minLength": 1, "maxLength": 200},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            "required": ["q"], "additionalProperties": False},
    },
    {   # C0 + B1: root combinator
        "name": "fetch_either",
        "description": "root oneOf, the countly-mcp-server#64 shape",
        "inputSchema": {"type": "object",
                        "anyOf": [{"required": ["url"]}, {"required": ["id"]}],
                        "properties": {"url": {"type": "string"},
                                       "id": {"type": "string"}},
                        "additionalProperties": False},
    },
    {   # C1 + B3: open object
        "name": "upsert",
        "description": "additionalProperties left open",
        "inputSchema": {"type": "object", "properties": {
            "key": {"type": "string"},
            "meta": {"type": "object", "additionalProperties": True}},
            "required": ["key"]},
    },
]


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, rid = msg.get("method"), msg.get("id")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "demo-flawed-server", "version": "0.1.0"}}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif rid is not None:
            send({"jsonrpc": "2.0", "id": rid,
                  "error": {"code": -32601, "message": f"no such method: {method}"}})


if __name__ == "__main__":
    main()
