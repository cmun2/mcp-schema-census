#!/usr/bin/env python3
"""End-to-end CLI behaviour: the stdio launch, the exit codes, --json, and the
error paths a CI pipeline will actually hit.

    python3 checker/tests/test_cli.py

Every case runs against checker/examples/demo_server.py, a local child process.
Nothing here touches the network.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.dirname(HERE)
ROOT = os.path.dirname(CHECKER)
CLI = os.path.join(CHECKER, "mcp_schema_check.py")
DEMO = f'{sys.executable} {os.path.join(CHECKER, "examples", "demo_server.py")}'

fails = []


def run(args, expect_exit):
    p = subprocess.run([sys.executable, CLI] + args, capture_output=True,
                       text=True, cwd=ROOT)
    ok = p.returncode == expect_exit
    label = " ".join(a if len(a) < 46 else a[:43] + "..." for a in args)
    print(f"[{'PASS' if ok else 'FAIL'}] exit {p.returncode} (want {expect_exit})  {label}")
    if not ok:
        fails.append(label)
        print("        stderr:", p.stderr.strip()[:300])
    return p


def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if detail:
        print(f"        {detail}")
    if not ok:
        fails.append(label)


# ---- (a) --cmd : launch a local stdio server -----------------------------
p = run(["--cmd", DEMO, "--no-color"], 1)
check("--cmd reached the server and read serverInfo",
      "demo-flawed-server 0.1.0" in p.stdout)
check("--cmd found all 4 tools", "4 tool(s) checked" in p.stdout)

# ---- exit codes ----------------------------------------------------------
run(["--cmd", DEMO, "--exit-zero"], 0)
run(["--cmd", DEMO, "--axis", "mcp"], 0)        # demo server is MCP-spec clean
run(["--cmd", DEMO, "--axis", "openai"], 1)
run(["--cmd", DEMO, "--axis", "anthropic"], 1)
run(["--cmd", f"{sys.executable} -c 'import sys; sys.exit(1)'"], 2)
run(["--cmd", DEMO, "--timeout", "0.001"], 2)

# ---- (b) --tools : a tools/list dump, in all three shapes ----------------
tools = json.loads(subprocess.run(
    [sys.executable, CLI, "--cmd", DEMO, "--json"], capture_output=True,
    text=True, cwd=ROOT).stdout)
check("--json is parseable and reports its own exit code",
      tools["exit_code"] == 1 and tools["n_tools"] == 4)
check("--json names the shared rule engine",
      tools["rules_engine"] == os.path.join("dataset", "scripts"),
      tools["rules_engine"])
check("every --json finding carries a source URL, a quote and a fix",
      all(f["source"] and f["source_quote"] and f["fix"] for f in tools["findings"]),
      f"{len(tools['findings'])} findings")

import importlib.util                                   # noqa: E402
spec = importlib.util.spec_from_file_location("mcp_schema_check", CLI)
mod = importlib.util.module_from_spec(spec)
sys.modules["mcp_schema_check"] = mod
spec.loader.exec_module(mod)
raw = [{"name": "search", "inputSchema": {"type": "object", "properties": {
    "q": {"type": "string", "maxLength": 5}}, "additionalProperties": False}}]
with tempfile.TemporaryDirectory() as d:
    for shape, doc in [("envelope", {"result": {"tools": raw}}),
                       ("result", {"tools": raw}),
                       ("bare array", raw)]:
        fp = os.path.join(d, "t.json")
        json.dump(doc, open(fp, "w"))
        p = run(["--tools", fp, "--no-color"], 1)
        check(f"--tools accepts the {shape} shape",
              "C3-string-constraint:maxLength" in p.stdout)

    # ---- (c) --schema : a single inputSchema -------------------------------
    fp = os.path.join(d, "one.json")
    json.dump(raw[0]["inputSchema"], open(fp, "w"))
    p = run(["--schema", fp, "--no-color"], 1)
    check("--schema judges a bare inputSchema",
          "C3-string-constraint:maxLength" in p.stdout)
    run(["--schema", fp, "--axis", "mcp"], 0)

    # ---- error paths ------------------------------------------------------
    run(["--tools", os.path.join(d, "nope.json")], 2)
    open(os.path.join(d, "bad.json"), "w").write("not json")
    run(["--tools", os.path.join(d, "bad.json")], 2)
    json.dump({"nope": 1}, open(os.path.join(d, "shape.json"), "w"))
    run(["--tools", os.path.join(d, "shape.json")], 2)

# ---- clean input passes ---------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    fp = os.path.join(d, "clean.json")
    json.dump({"tools": [{"name": "ping", "inputSchema": {
        "type": "object", "properties": {}, "additionalProperties": False}}]},
        open(fp, "w"))
    p = run(["--tools", fp, "--no-color"], 0)
    check("a clean schema reports 0 hard rejects",
          "0 hard rejects" in p.stdout)

# ---- --fail-on silent -----------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    fp = os.path.join(d, "soft.json")
    # `pattern` is dropped by OpenAI strict but is SUPPORTED by Anthropic --
    # so this schema is silent-loss only, with no hard reject anywhere.
    json.dump({"tools": [{"name": "t", "inputSchema": {
        "type": "object", "properties": {"a": {"type": "string", "pattern": "^x"}},
        "additionalProperties": False}}]}, open(fp, "w"))
    run(["--tools", fp], 0)
    run(["--tools", fp, "--fail-on", "silent"], 1)
    p = run(["--tools", fp, "--no-color"], 0)
    check("a silent-loss-only schema is reported but does not fail by default",
          "silently-dropped constraint" in p.stdout)

# ---- --sdk-oracle degrades cleanly when `anthropic` is absent -------------
p = run(["--cmd", DEMO, "--sdk-oracle", "--no-color", "--exit-zero"], 0)
check("--sdk-oracle either runs or explains itself; it never crashes",
      "Anthropic Python SDK transformer" in p.stdout)

print()
if fails:
    print(f"{len(fails)} FAILED")
    raise SystemExit(1)
print("CLI behaviour: confirmed")
