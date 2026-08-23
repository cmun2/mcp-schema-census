#!/usr/bin/env python3
"""mcp-schema-check -- which of your MCP tool schemas a provider's strict mode
would reject, and what to change.

This is NOT an MCP-specification validator. Five tools already do that well
(see checker/README.md, "What this is not"). In the 617-server corpus in
../dataset/, the MCP-spec axis fails 0 servers -- 0.0%. Everybody already
passes it.

What fails is the *provider strict-mode subset*: the narrower JSON Schema each
model provider accepts once you turn strict output on. On that axis 63.0% of
the same 617 servers are rejected. That gap is what this command reports.

Every rule comes from ../dataset/scripts/rules/, the same engine that produced
the published corpus. Nothing here re-implements a constraint, and every
finding carries the verbatim sentence from the provider's own documentation
that the verdict rests on, plus its URL.

No network calls. `--cmd` starts YOUR server as a local child process and
speaks stdio JSON-RPC to it; nothing leaves the machine.
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RULES_DIR = os.path.join(ROOT, "dataset", "scripts")
sys.path.insert(0, RULES_DIR)

try:
    from rules import (                                        # noqa: E402
        judge_server_anthropic, judge_server_mcp_openai,
        meta_for, fix_for, split_pointer,
    )
except ImportError as e:                                        # pragma: no cover
    sys.stderr.write(
        f"cannot import the rule engine from {RULES_DIR}: {e}\n"
        "mcp-schema-check must run from inside the mcp-schema-census repository;\n"
        "the rules and the dataset that validates them are deliberately one tree.\n")
    raise SystemExit(2)

VERSION = "0.1.0"
CLIENT_INFO = {"name": "mcp-schema-check", "version": VERSION}
PROTOCOL_VERSIONS = ["2025-06-18", "2024-11-05"]

# axis id -> (selector name, human label, opt-in?, corpus server-unit rate)
AXES = [
    ("A",        "mcp",       "MCP specification conformance",          False, "0.0%"),
    ("B",        "openai",    "OpenAI strict mode (hard reject)",       True,  "27.6%"),
    ("B_silent", "openai",    "OpenAI strict mode (silent constraint loss)", True, "56.9%"),
    ("C0",       "anthropic", "Anthropic Messages API baseline",        False, "0.0%"),
    ("C",        "anthropic", "Anthropic strict:true subset",           True,  "63.0%"),
    ("CL",       "anthropic", "Anthropic request complexity limits",    True,  "37.3%"),
]
AXIS_LABEL = {a: lbl for a, _, lbl, _, _ in AXES}
AXIS_SELECTOR = {a: sel for a, sel, _, _, _ in AXES}
AXIS_OPTIN = {a: o for a, _, _, o, _ in AXES}
AXIS_RATE = {a: r for a, _, _, _, r in AXES}
AXIS_ORDER = [a for a, _, _, _, _ in AXES]

HARD = ("hard-reject", "empirical")


# --------------------------------------------------------------- input: stdio

class ServerError(RuntimeError):
    pass


class BadInput(ValueError):
    """The file was readable JSON but not the shape we asked for."""


class StdioClient:
    """Minimal MCP stdio client. Launches a local child process and speaks
    newline-delimited JSON-RPC to it. No sockets, no network, no SDK."""

    def __init__(self, cmd, env=None, cwd=None, timeout=30.0):
        self.cmd, self.timeout = cmd, timeout
        e = dict(os.environ)
        e.update(env or {})
        self.proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd, env=e,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        self._q = queue.Queue()
        self._err = []
        self._nonjson = []
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()
        self._id = 0

    def _pump_stdout(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except ValueError:
                # some servers log to stdout; keep it for the error report
                self._nonjson.append(line[:400])

    def _pump_stderr(self):
        for line in self.proc.stderr:
            self._err.append(line.rstrip()[:400])

    def stderr_tail(self, n=15):
        return "\n".join(self._err[-n:])

    def _send(self, obj):
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            raise ServerError("the server closed its stdin before the handshake finished")

    def request(self, method, params=None):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = self.timeout
        while True:
            try:
                msg = self._q.get(timeout=deadline)
            except queue.Empty:
                raise ServerError(
                    f"no response to `{method}` within {self.timeout:g}s")
            if msg.get("id") == rid:
                if "error" in msg:
                    raise ServerError(f"{method} returned a JSON-RPC error: "
                                      f"{json.dumps(msg['error'])[:300]}")
                return msg.get("result", {})
            # a notification or a response to something else: keep waiting

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def tools_via_stdio(cmd, env=None, cwd=None, timeout=30.0):
    """Start the server locally, complete the MCP handshake, page through
    tools/list. Returns (tools, server_info)."""
    cli = StdioClient(cmd, env=env, cwd=cwd, timeout=timeout)
    try:
        info, last = None, None
        for pv in PROTOCOL_VERSIONS:
            try:
                info = cli.request("initialize", {
                    "protocolVersion": pv, "capabilities": {},
                    "clientInfo": CLIENT_INFO})
                break
            except ServerError as e:
                last = e
                if "no response" in str(e):
                    raise
        if info is None:
            raise last
        cli.notify("notifications/initialized")

        tools, cursor, pages = [], None, 0
        while True:
            res = cli.request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(res.get("tools") or [])
            cursor = res.get("nextCursor")
            pages += 1
            if not cursor or pages > 50:
                break
        return tools, (info.get("serverInfo") or {})
    finally:
        cli.close()


# ----------------------------------------------------------- input: json file

def tools_from_file(path):
    """Accept a tools/list result in any of the shapes people actually have:
    the full JSON-RPC envelope, the bare result, or just the array."""
    with open(path) as f:
        doc = json.load(f)
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        if isinstance(doc.get("tools"), list):
            return doc["tools"]
        r = doc.get("result")
        if isinstance(r, dict) and isinstance(r.get("tools"), list):
            return r["tools"]
    raise BadInput(
        f"expected a tools/list response. Give me one of:\n"
        '  {"result": {"tools": [...]}}   (the full JSON-RPC envelope)\n'
        '  {"tools": [...]}               (just the result)\n'
        '  [...]                          (just the array)')


def tool_from_schema_file(path):
    with open(path) as f:
        schema = json.load(f)
    name = os.path.splitext(os.path.basename(path))[0]
    return [{"name": name, "inputSchema": schema}]


# ----------------------------------------------------------------- judgement

def analyse(tools, label="(input)"):
    """Run the shared rule engine and flatten every hit into one finding list.

    The hits, the codes, the doc quotes and the pointer/value split are all the
    engine's -- this function adds ordering and the fix hint, nothing else."""
    rec = {"server_name": label, "pkg": label, "tools": tools}
    anth = judge_server_anthropic(rec)
    mo = judge_server_mcp_openai(rec)

    findings = []

    def add(tool, code, msg, value):
        m = meta_for(code)
        ptr, val = split_pointer(value)
        findings.append({
            "axis": m["axis"], "code": code, "severity": m["severity"],
            "tool": tool, "json_pointer": ptr, "value": val,
            "message": msg, "source": m["source"],
            "source_quote": m["source_quote"], "fix": fix_for(code),
        })

    for h in mo["A_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])
    for h in mo["B_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])
    for h in mo["B_soft_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])
    for h in anth["C0_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])
    for h in anth["C_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])
    for h in anth["C_limit_hits"]:
        add(None, h["code"], h["msg"], h["value"])
    for h in anth["C_amb_hits"]:
        add(h["tool"], h["code"], h["msg"], h["value"])

    return findings, {"complexity": {
        "optional_params_top_level": anth["opt_top"],
        "optional_params_all_levels": anth["opt_all"],
        "union_typed_params": anth["union_top"]}}


# ------------------------------------------------------------------- reporting

class Style:
    def __init__(self, on):
        self.on = on

    def _w(self, code, s):
        return f"\033[{code}m{s}\033[0m" if self.on else s

    bold = lambda self, s: self._w("1", s)
    dim = lambda self, s: self._w("2", s)
    red = lambda self, s: self._w("31", s)
    green = lambda self, s: self._w("32", s)
    yellow = lambda self, s: self._w("33", s)
    cyan = lambda self, s: self._w("36", s)


def render(findings, meta, args, st, out=sys.stdout):
    p = lambda s="": print(s, file=out)
    selected = meta["selected_axes"]

    p()
    p(st.bold(f"mcp-schema-check {VERSION}") + st.dim(f"  ·  {meta['input_label']}"))
    p(st.dim(f"rules: {os.path.relpath(RULES_DIR, ROOT)}  (the engine that produced "
             f"the {meta['corpus_n']}-server corpus in dataset/)"))
    p()
    p(f"{meta['n_tools']} tool(s) checked" +
      (f"  ·  server: {meta['server_info']}" if meta.get("server_info") else ""))
    p()

    by_axis = {}
    for f in findings:
        by_axis.setdefault(f["axis"], []).append(f)

    # ---- summary table --------------------------------------------------
    p(st.bold("  " + "axis".ljust(44) + " " + "scope".rjust(6) + "  "
              + "verdict".ljust(7) + "  " + "tools".rjust(4) + "   "
              + "corpus".rjust(6)))
    p("  " + "-" * 74)
    for ax in AXIS_ORDER:
        if ax not in selected:
            continue
        hits = by_axis.get(ax, [])
        ntools = len({h["tool"] for h in hits})
        if not hits:
            verdict = st.green("PASS   ")
        elif ax == "B_silent":
            verdict = st.yellow("WARN   ")
        else:
            verdict = st.red("FAIL   ")
        optin = "opt-in" if AXIS_OPTIN[ax] else "always"
        p(f"  {AXIS_LABEL[ax]:<44} {optin:>6}  {verdict}  {ntools:>4}   "
          + st.dim(f"{AXIS_RATE[ax]:>6}"))
    p("  " + "-" * 74)
    p(st.dim("  'corpus' = share of the 617 measured servers that fail that axis. "
             "'always'\n  means the axis applies whether or not you opt into strict "
             "mode."))

    amb = by_axis.get("AMB", [])

    # ---- detail ---------------------------------------------------------
    for ax in AXIS_ORDER:
        if ax not in selected:
            continue
        hits = by_axis.get(ax, [])
        if not hits:
            continue
        p()
        p(st.bold("=" * 78))
        head = f"{AXIS_LABEL[ax]}  —  {len(hits)} finding(s)"
        p(st.bold(st.red(head) if ax != "B_silent" else st.yellow(head)))
        p(st.bold("=" * 78))
        if ax == "B_silent":
            p(st.dim("  These do not reject the request. OpenAI strict mode accepts the\n"
                     "  schema and then does not enforce these keywords -- the constraint\n"
                     "  is gone and nothing tells you. Validate them in your handler."))
        by_code = {}
        for h in hits:
            by_code.setdefault(h["code"], []).append(h)
        for code, hs in sorted(by_code.items(), key=lambda kv: -len(kv[1])):
            h0 = hs[0]
            p()
            p("  " + st.bold(code) + st.dim(f"   ({len(hs)} occurrence(s))"))
            p(f"    {h0['message']}")
            p(f"    {st.dim('docs')}  " + st.cyan(f'"{h0["source_quote"]}"'))
            p(f"          {st.dim(h0['source'])}")
            if h0["fix"]:
                p(f"    {st.dim('fix')}   {st.green(h0['fix'])}")
            p()
            shown = hs if args.max_per_code <= 0 else hs[:args.max_per_code]
            for h in shown:
                loc = h["json_pointer"] or "#"
                tn = h["tool"] or st.dim("(whole request)")
                val = ""
                if h["value"] is not None:
                    v = json.dumps(h["value"])
                    val = "  = " + (v if len(v) <= 90 else v[:87] + "...")
                p(f"      {tn}  {st.dim(loc)}{val}")
            if len(hs) > len(shown):
                p(st.dim(f"      ... and {len(hs) - len(shown)} more "
                         f"(raise --max-per-code, or use --json for all of them)"))

    # ---- ambiguous ------------------------------------------------------
    if amb:
        if args.show_ambiguous:
            p()
            p(st.bold("=" * 78))
            p(st.bold("Documented ambiguities  —  not verdicts, never counted"))
            p(st.bold("=" * 78))
            p(st.dim("  The provider's docs do not settle these cases. They are reported\n"
                     "  so you can decide, and they never affect the exit code."))
            by_code = {}
            for h in amb:
                by_code.setdefault(h["code"].split(":")[0], []).append(h)
            for code, hs in sorted(by_code.items(), key=lambda kv: -len(kv[1])):
                p()
                p("  " + st.bold(code) + st.dim(f"   ({len(hs)} occurrence(s))"))
                p(f"    {st.dim('docs')}  " + st.cyan(f'"{hs[0]["source_quote"]}"'))
                p(f"    {st.dim('note')}  {hs[0]['fix']}")
        else:
            p()
            p(st.dim(f"  {len(amb)} documented ambiguity/ambiguities not shown "
                     f"(--show-ambiguous). They are not verdicts and never affect "
                     f"the exit code."))

    # ---- footer ---------------------------------------------------------
    hard = [f for f in findings if f["axis"] in selected and f["severity"] in HARD]
    soft = [f for f in findings if f["axis"] in selected and f["severity"] == "silent-loss"]
    p()
    if hard:
        p(st.red(st.bold(f"  {len(hard)} hard reject(s)")) +
          st.dim(f" — these axes would refuse your schema."))
    else:
        p(st.green(st.bold("  0 hard rejects on the selected axes.")))
    if soft:
        p(st.yellow(f"  {len(soft)} silently-dropped constraint(s)") +
          st.dim(" — accepted, then not enforced." +
                 ("" if args.fail_on == "silent" else " (--fail-on silent to gate CI on these)")))
    p()


# -------------------------------------------------------------- the SDK oracle

def run_sdk_oracle(tools):
    """Run the vendor's own transformer locally. Not a rule -- an oracle.

    Returns None-shaped dict with an `unavailable` reason rather than raising,
    so a missing optional dependency degrades to a printed explanation instead
    of a stack trace."""
    try:
        from rules import sdk_oracle
    except ImportError as e:
        return {"unavailable": f"cannot import the oracle module: {e}", "tools": []}
    if not sdk_oracle.available():
        return {"unavailable":
                "the `anthropic` package is not importable in this interpreter. "
                "`pip install anthropic` and re-run; it is a local transform, "
                "no API key and no network call.", "tools": []}
    out = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        r = sdk_oracle.run_one(t.get("inputSchema"))
        if r["raises"] or r["dropped"]:
            out.append({"tool": t.get("name"), **r})
    return {"unavailable": None,
            "sdk_version": sdk_oracle.sdk_version(),
            "measured_against": sdk_oracle.SDK_VERSION_MEASURED,
            "tools": out}


def render_sdk(sdk, st, out=sys.stdout):
    p = lambda s="": print(s, file=out)
    p()
    p(st.bold("=" * 78))
    p(st.bold("Anthropic Python SDK transformer  —  oracle, not a rule"))
    p(st.bold("=" * 78))
    if sdk["unavailable"]:
        p(st.yellow(f"  skipped: {sdk['unavailable']}"))
        p()
        return
    p(st.dim(f"  anthropic=={sdk['sdk_version']}  "
             f"(the corpus was measured against {sdk['measured_against']})\n"
             "  This runs the SDK's own transform_schema over your schemas, in this\n"
             "  process. What it refuses is not in any published constraint list --\n"
             "  it is what the shipped client actually does, defects included."))
    raises = [r for r in sdk["tools"] if r["raises"]]
    drops = [r for r in sdk["tools"] if r["dropped"]]
    p()
    if not raises and not drops:
        p(st.green("  the SDK transforms every schema cleanly and drops nothing."))
        p()
        return
    if raises:
        p(st.red(st.bold(f"  transform_schema RAISED on {len(raises)} tool(s)")) +
          st.dim(" — the SDK cannot even normalise these."))
        for r in raises[:20]:
            p(f"      {r['tool']}  {st.dim(r['raises'])}")
        if len(raises) > 20:
            p(st.dim(f"      ... and {len(raises) - 20} more"))
        p(st.dim("      An AssertionError here is an SDK DEFECT, not a documented\n"
                 "      constraint: see anthropics/anthropic-sdk-python#1876 for the\n"
                 '      ["string","null"] case.'))
        p()
    if drops:
        p(st.yellow(f"  the SDK silently dropped constraints on {len(drops)} tool(s)"))
        for r in drops[:20]:
            p(f"      {r['tool']}  {st.dim(', '.join(r['dropped']))}")
        if len(drops) > 20:
            p(st.dim(f"      ... and {len(drops) - 20} more"))
        p(st.dim("      Dropped keywords are moved into the description string; the\n"
                 "      model sees them as prose and nothing enforces them."))
        p()


# ------------------------------------------------------------------------ main

def parse_env(pairs):
    env = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--env expects KEY=VALUE, got {p!r}")
        k, v = p.split("=", 1)
        env[k] = v
    return env


def build_parser():
    ap = argparse.ArgumentParser(
        prog="mcp-schema-check",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  mcp-schema-check --cmd "npx -y @modelcontextprotocol/server-everything"
  mcp-schema-check --tools tools.json --axis anthropic
  mcp-schema-check --schema one-input-schema.json --json
  mcp-schema-check --cmd "python -m my_server" --axis openai --fail-on silent

exit codes:
  0  no hard reject on the selected axes (or --exit-zero)
  1  at least one hard reject
  2  the input could not be read, or the server did not start
""")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--cmd", metavar="CMDLINE",
                     help="start your MCP server as a LOCAL child process and call "
                          "tools/list over stdio. Not a network call.")
    src.add_argument("--tools", metavar="FILE",
                     help="a tools/list response as JSON (envelope, result, or bare array)")
    src.add_argument("--schema", metavar="FILE",
                     help="a single inputSchema as JSON")

    ap.add_argument("--axis", default="all",
                    choices=["anthropic", "openai", "mcp", "all"],
                    help="which provider axis to judge (default: all)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="machine-readable output on stdout")
    ap.add_argument("--exit-zero", action="store_true",
                    help="always exit 0 (report only; useful outside CI)")
    ap.add_argument("--fail-on", default="hard", choices=["hard", "silent"],
                    help="'hard' (default) fails only on rejects; 'silent' also fails "
                         "on constraints that are accepted then silently dropped")
    ap.add_argument("--sdk-oracle", action="store_true",
                    help="additionally run the real Anthropic Python SDK's own "
                         "schema transformer over each schema, locally, and report "
                         "what it refuses or silently drops. Needs `pip install "
                         "anthropic`; makes no API call and needs no key. Reports "
                         "SDK defects the published constraint docs do not cover.")
    ap.add_argument("--show-ambiguous", action="store_true",
                    help="also print cases the provider docs do not settle "
                         "(never affects the exit code)")
    ap.add_argument("--max-per-code", type=int, default=10, metavar="N",
                    help="occurrences printed per code, 0 for all (default 10). "
                         "Anything hidden is counted out loud.")
    ap.add_argument("--env", action="append", metavar="K=V",
                    help="environment variable for --cmd (repeatable)")
    ap.add_argument("--cwd", help="working directory for --cmd")
    ap.add_argument("--timeout", type=float, default=30.0, metavar="SEC",
                    help="per-request timeout for --cmd (default 30)")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--version", action="version", version=f"mcp-schema-check {VERSION}")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    st = Style(not args.no_color and sys.stdout.isatty() and not args.as_json)

    server_info = None
    if args.cmd:
        try:
            tools, si = tools_via_stdio(args.cmd, env=parse_env(args.env),
                                        cwd=args.cwd, timeout=args.timeout)
        except ServerError as e:
            sys.stderr.write(f"could not get tools/list from `{args.cmd}`: {e}\n")
            return 2
        server_info = " ".join(filter(None, [si.get("name"), si.get("version")])) or None
        label = args.cmd
    else:
        path = args.tools or args.schema
        try:
            tools = (tools_from_file(path) if args.tools
                     else tool_from_schema_file(path))
        except OSError as e:
            sys.stderr.write(f"cannot read {path}: {e.strerror}\n")
            return 2
        except BadInput as e:
            sys.stderr.write(f"{path}: {e}\n")
            return 2
        except ValueError as e:
            sys.stderr.write(f"{path} is not valid JSON: {e}\n")
            return 2
        label = path

    if not isinstance(tools, list):
        sys.stderr.write("the input did not yield a list of tools\n")
        return 2

    selected = {a for a in AXIS_ORDER
                if args.axis == "all" or AXIS_SELECTOR[a] == args.axis}
    selected.add("AMB")

    findings, extra = analyse(tools, label=label)
    findings = [f for f in findings if f["axis"] in selected]

    sdk = run_sdk_oracle(tools) if args.sdk_oracle else None

    meta = {"input_label": label, "n_tools": len(tools),
            "selected_axes": selected, "server_info": server_info,
            "corpus_n": 617}

    hard = [f for f in findings if f["severity"] in HARD]
    soft = [f for f in findings if f["severity"] == "silent-loss"]
    sdk_raises = [r for r in (sdk or {}).get("tools", []) if r["raises"]]
    code = 1 if (hard or sdk_raises or (args.fail_on == "silent" and soft)) else 0
    if args.exit_zero:
        code = 0

    if args.as_json:
        json.dump({
            "tool": "mcp-schema-check", "version": VERSION,
            "rules_engine": os.path.relpath(RULES_DIR, ROOT),
            "input": {"kind": "cmd" if args.cmd else ("tools" if args.tools else "schema"),
                      "value": label},
            "server_info": server_info,
            "n_tools": len(tools),
            "axes": {a: {"label": AXIS_LABEL[a], "opt_in": AXIS_OPTIN[a],
                         "selected": a in selected,
                         "n_findings": sum(1 for f in findings if f["axis"] == a),
                         "tools_affected": len({f["tool"] for f in findings
                                                if f["axis"] == a}),
                         "corpus_server_fail_rate": AXIS_RATE[a]}
                     for a in AXIS_ORDER},
            "complexity": extra["complexity"],
            "findings": [f for f in findings if f["axis"] != "AMB"],
            "ambiguous": [f for f in findings if f["axis"] == "AMB"],
            "sdk_oracle": sdk,
            "n_hard_rejects": len(hard), "n_silent_losses": len(soft),
            "exit_code": code,
        }, sys.stdout, indent=2)
        print()
    else:
        render(findings, meta, args, st)
        if sdk is not None:
            render_sdk(sdk, st)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
