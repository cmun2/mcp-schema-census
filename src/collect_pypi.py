#!/usr/bin/env python3
"""Second, independent population: PyPI-published MCP servers, launched locally with uvx.

Motivation (self-attack): every npm MCP server is built on the official TypeScript SDK,
which *generates* `type: "object"` for it. Measuring MCP-spec conformance on npm alone
can only ever return ~0% -- the SDK makes the violation unrepresentable. A different
language ecosystem is required before the 0% means anything.
"""
import json, os, sys, subprocess, threading, queue, tempfile, shutil, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DUMMY = "POC_DUMMY_NOT_A_REAL_KEY"
PROTO = "2025-06-18"
TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "90"))
UVX = os.path.expanduser("~/.local/bin/uvx")


def build_targets(limit=None, offset=0):
    servers = json.load(open(os.path.join(ROOT, "data/registry_servers.json")))
    out = []
    for x in servers:
        sv = x["server"]
        meta = x.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
        if meta.get("status") != "active":
            continue
        for p in (sv.get("packages") or []):
            if p.get("registryType") != "pypi":
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
                v = a.get("value") or a.get("default")
                if a.get("type") == "named":
                    args.append(a["name"])
                    if v is not None and not a.get("isRepeated"):
                        args.append(str(v))
                elif v is not None:
                    args.append(str(v))
            out.append({"server_name": sv["name"], "title": sv.get("title"),
                        "version": sv.get("version"),
                        "repository": (sv.get("repository") or {}).get("url"),
                        "pkg": p["identifier"], "pkg_version": p.get("version"),
                        "args": args, "env": env, "ecosystem": "pypi"})
            break
    out.sort(key=lambda t: t["server_name"])
    import random
    random.Random(20260809).shuffle(out)
    out = out[offset:]
    return out[:limit] if limit else out


def run_once(cmd, t, workdir):
    env = {"PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ["PATH"],
           "HOME": workdir, "TMPDIR": workdir, "UV_CACHE_DIR": os.path.expanduser("~/.cache/uv"),
           "UV_PYTHON_INSTALL_DIR": os.path.expanduser("~/.local/share/uv/python"),
           "UV_CONSTRAINT": os.path.join(ROOT, "data/uv_constraints.txt"),
           "TERM": "dumb", "LANG": "C.UTF-8", "NO_COLOR": "1"}
    env.update(t["env"])
    try:
        p = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             bufsize=1, start_new_session=True)
    except Exception as e:
        return {"status": "spawn_error", "error": str(e)}
    errbuf = []

    def errreader():
        try:
            for line in p.stderr:
                errbuf.append(line)
                if len(errbuf) > 400:
                    del errbuf[:200]
        except Exception:
            pass
    eth = threading.Thread(target=errreader, daemon=True); eth.start()

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
        except Exception:
            pass
    res = {"tools": None, "err": None}

    def reader():
        try:
            for line in p.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("id") == 1 and "result" in m:
                    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                if m.get("id") == 1 and "error" in m:
                    res["err"] = "initialize_error: " + json.dumps(m["error"])[:300]; return
                if m.get("id") == 2:
                    if "result" in m:
                        res["tools"] = m["result"].get("tools", [])
                    else:
                        res["err"] = "tools_list_error: " + json.dumps(m.get("error"))[:300]
                    return
        except Exception as e:
            res["err"] = "read_error: " + str(e)
    th = threading.Thread(target=reader, daemon=True); th.start()
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": PROTO, "capabilities": {"roots": {}, "sampling": {}},
        "clientInfo": {"name": "mcp-schema-compat-poc", "version": "0.1"}}})
    th.join(TIMEOUT)
    try:
        os.killpg(os.getpgid(p.pid), 9)
    except Exception:
        pass
    eth.join(3)
    stderr = ("".join(errbuf))[-1200:]
    if res["tools"] is not None:
        return {"status": "ok", "tools": res["tools"], "n_tools": len(res["tools"])}
    if res["err"]:
        return {"status": "rpc_error", "error": res["err"], "stderr": stderr}
    return {"status": "timeout_or_crash", "stderr": stderr}


def probe(t, workdir):
    spec = t["pkg"] + ("==" + t["pkg_version"] if t.get("pkg_version") else "")
    base = ["--python", "3.12", "--no-progress", "-q"]
    attempts = [
        [UVX] + base + [spec] + t["args"],
        [UVX] + base + ["--from", spec, t["pkg"].split("/")[-1]] + t["args"],
        [UVX] + base + ["--from", spec, t["pkg"].replace("_", "-")] + t["args"],
    ]
    rec = dict(t)
    last = None
    for cmd in attempts:
        r = run_once(cmd, t, workdir)
        last = r
        if r["status"] == "ok":
            rec.update(r); return rec
        # only retry a different entrypoint if it looks like an entrypoint problem
        blob = (r.get("stderr") or "") + (r.get("error") or "")
        if "executable" not in blob and "not found" not in blob.lower():
            break
    rec.update(last or {"status": "harness_error"})
    return rec


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    outpath = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "data/tools_pypi.jsonl")
    targets = build_targets(limit, offset)
    print(f"pypi targets={len(targets)}", file=sys.stderr)
    q = queue.Queue()
    for t in targets:
        q.put(t)
    lock = threading.Lock(); fh = open(outpath, "a"); done = [0]

    def worker(wid):
        wd = tempfile.mkdtemp(prefix=f"pyscan{wid}_")
        while True:
            try:
                t = q.get_nowait()
            except queue.Empty:
                break
            try:
                rec = probe(t, wd)
            except Exception as e:
                rec = dict(t); rec.update(status="harness_error", error=str(e))
            with lock:
                fh.write(json.dumps(rec) + "\n"); fh.flush(); done[0] += 1
                if done[0] % 10 == 0:
                    print(f"  {done[0]}/{len(targets)}", file=sys.stderr)
        shutil.rmtree(wd, ignore_errors=True)
    ths = [threading.Thread(target=worker, args=(i,)) for i in range(int(os.environ.get("MCP_PAR", "8")))]
    t0 = time.time()
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    fh.close(); print(f"done in {time.time()-t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
