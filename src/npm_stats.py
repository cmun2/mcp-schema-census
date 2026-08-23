import json, urllib.request, threading, queue, os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
servers=json.load(open(ROOT+"/data/registry_servers.json"))
pkgs=set()
for x in servers:
    for p in (x["server"].get("packages") or []):
        if p.get("registryType")=="npm": pkgs.add(p["identifier"])
pkgs=sorted(pkgs); print(len(pkgs),file=sys.stderr)
q=queue.Queue(); [q.put(p) for p in pkgs]
res={}; lock=threading.Lock()
def w():
    while True:
        try: p=q.get_nowait()
        except queue.Empty: return
        try:
            req=urllib.request.Request("https://api.npmjs.org/downloads/point/last-week/"+urllib.parse.quote(p,safe='@/'),headers={"User-Agent":"mcp-poc"})
            with urllib.request.urlopen(req,timeout=20) as r: d=json.loads(r.read())
            v=d.get("downloads")
        except Exception as e: v=None
        with lock: res[p]=v
ths=[threading.Thread(target=w) for _ in range(20)]
[t.start() for t in ths]; [t.join() for t in ths]
json.dump(res,open(ROOT+"/data/npm_downloads.json","w"))
import statistics
vals=[v for v in res.values() if v is not None]
print("got",len(vals),"median",statistics.median(vals),"max",max(vals))
for th in (10,50,100,500,1000,5000,10000):
    print(f">={th}: {sum(1 for v in vals if v>=th)}")
