#!/usr/bin/env python3
"""Launch public MCP servers locally over stdio and capture their real tools/list response.

$0: npm packages only, no LLM-provider API calls, no tools/call (discovery only).
Required secrets are filled with an obvious dummy so the process boots; servers that
build their tool list from a live backend will fail to launch and are recorded as such.
"""
import json, os, subprocess, sys, threading, queue, shutil, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMMY = "POC_DUMMY_NOT_A_REAL_KEY"
PROTO = "2025-06-18"
TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "75"))


def build_targets(limit=None, offset=0):
    servers = json.load(open(os.path.join(ROOT, "data/registry_servers.json")))
    out = []
    for x in servers:
        sv = x["server"]
        meta = x.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
        if meta.get("status") != "active":
            continue
        for p in (sv.get("packages") or []):
            if p.get("registryType") != "npm":
                continue
            if (p.get("transport") or {}).get("type") != "stdio":
                continue
            env = {}
            for e in (p.get("environmentVariables") or []):
                if e.get("default") is not None:
                    env[e["name"]] = str(e["default"])
                elif e.get("isRequired"):
                    env[e["name"]] = DUMMY
            args = []
            for a in (p.get("packageArguments") or []):
                if a.get("type") == "named":
                    v = a.get("value") or a.get("default")
                    args.append(a["name"])
                    if v is not None and not a.get("isRepeated"):
                        args.append(str(v))
                else:
                    v = a.get("value") or a.get("default")
                    if v is not None:
                        args.append(str(v))
            out.append({
                "server_name": sv["name"],
                "title": sv.get("title"),
                "version": sv.get("version"),
                "repository": (sv.get("repository") or {}).get("url"),
                "pkg": p["identifier"],
                "pkg_version": p.get("version"),
                "args": args,
                "env": env,
            })
            break
    out.sort(key=lambda t: t["server_name"])
    # Seeded shuffle: the registry is alphabetical and one publisher can own a
    # whole contiguous block (e.g. @agentutility/* = 8 of the first 12).
    import random
    random.Random(20260809).shuffle(out)
    out = out[offset:]
    return out[:limit] if limit else out


ENVVAR_RE = None


def guess_env_from_stderr(stderr):
    """Servers commonly require env vars the registry metadata never declares.
    Scrape plausible env var names out of the failure message and retry once."""
    import re
    global ENVVAR_RE
    if ENVVAR_RE is None:
        ENVVAR_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,5})\b")
    skip = {"FATAL", "ERROR", "WARNING", "MCP_SERVER", "JSON_RPC", "NOT_FOUND",
            "MODULE_NOT_FOUND", "ERR_MODULE_NOT_FOUND", "ERR_REQUIRE_ESM", "TODO"}
    found = []
    for m in ENVVAR_RE.findall(stderr or ""):
        if m in skip or m.startswith("ERR_") or m.startswith("NODE_"):
            continue
        if m not in found:
            found.append(m)
    return found[:12]


def probe(t, workdir):
    spec = t["pkg"] + ("@" + t["pkg_version"] if t.get("pkg_version") else "")
    cmd = ["npx", "-y", spec] + t["args"]
    env = {
        "PATH": os.environ["PATH"], "HOME": workdir, "TMPDIR": workdir,
        "npm_config_cache": os.path.join(os.path.expanduser("~"), ".npm"),
        "npm_config_yes": "true", "NO_UPDATE_NOTIFIER": "1", "CI": "1",
        "NODE_NO_WARNINGS": "1", "TERM": "dumb", "LANG": "C.UTF-8",
    }
    env.update(t["env"])
    rec = dict(t)
    try:
        # start_new_session: npx spawns a grandchild node process. Killing only npx
        # leaves the grandchild alive holding the stderr pipe, and stderr.read()
        # then blocks forever. Kill the whole process group instead.
        p = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             bufsize=1, start_new_session=True)
    except Exception as e:
        rec.update(status="spawn_error", error=str(e))
        return rec

    errbuf = []

    def errreader():
        try:
            for line in p.stderr:
                errbuf.append(line)
                if len(errbuf) > 400:
                    del errbuf[:200]
        except Exception:
            pass
    eth = threading.Thread(target=errreader, daemon=True)
    eth.start()

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
        except Exception:
            pass

    result = {"tools": None, "err": None}

    def reader():
        try:
            for line in p.stdout:
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("id") == 1 and "result" in m:
                    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                if m.get("id") == 1 and "error" in m:
                    result["err"] = "initialize_error: " + json.dumps(m["error"])[:300]
                    return
                if m.get("id") == 2:
                    if "result" in m:
                        result["tools"] = m["result"].get("tools", [])
                    else:
                        result["err"] = "tools_list_error: " + json.dumps(m.get("error"))[:300]
                    return
        except Exception as e:
            result["err"] = "read_error: " + str(e)

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": PROTO, "capabilities": {"roots": {}, "sampling": {}},
        "clientInfo": {"name": "mcp-schema-compat-poc", "version": "0.1"}}})
    th.join(TIMEOUT)
    try:
        os.killpg(os.getpgid(p.pid), 9)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    eth.join(3)
    stderr = ("".join(errbuf))[-1200:]

    if result["tools"] is not None:
        rec.update(status="ok", tools=result["tools"], n_tools=len(result["tools"]))
    elif result["err"]:
        rec.update(status="rpc_error", error=result["err"], stderr=stderr)
    else:
        rec.update(status="timeout_or_crash", stderr=stderr)
    return rec


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    outpath = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "data/tools_stdio.jsonl")
    targets = build_targets(limit, offset)
    print(f"targets={len(targets)}", file=sys.stderr)
    q = queue.Queue()
    for t in targets:
        q.put(t)
    lock = threading.Lock()
    fh = open(outpath, "a")
    done = [0]

    def worker(wid):
        wd = tempfile.mkdtemp(prefix=f"mcpscan{wid}_")
        while True:
            try:
                t = q.get_nowait()
            except queue.Empty:
                break
            try:
                rec = probe(t, wd)
                if rec["status"] != "ok":
                    extra = guess_env_from_stderr(
                        (rec.get("stderr") or "") + " " + (rec.get("error") or ""))
                    if extra:
                        t2 = dict(t)
                        t2["env"] = dict(t["env"])
                        for k in extra:
                            t2["env"].setdefault(k, DUMMY)
                        rec2 = probe(t2, wd)
                        rec2["retry_env"] = extra
                        if rec2["status"] == "ok":
                            rec = rec2
                        else:
                            rec["retry_env"] = extra
                            rec["retry_status"] = rec2["status"]
            except Exception as e:
                rec = dict(t); rec.update(status="harness_error", error=str(e))
            with lock:
                fh.write(json.dumps(rec) + "\n"); fh.flush()
                done[0] += 1
                if done[0] % 10 == 0:
                    print(f"  {done[0]}/{len(targets)}", file=sys.stderr)
            for f in os.listdir(wd):
                pass
        shutil.rmtree(wd, ignore_errors=True)

    ths = [threading.Thread(target=worker, args=(i,)) for i in range(int(os.environ.get("MCP_PAR", "12")))]
    t0 = time.time()
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    fh.close()
    print(f"done in {time.time()-t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
