import json,os,subprocess,threading,queue,sys,re
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repos=set()
for f in ("data/tools_stdio.jsonl","data/tools_pypi.jsonl"):
    p=os.path.join(ROOT,f)
    if not os.path.exists(p): continue
    for l in open(p):
        r=json.loads(l)
        u=r.get("repository") or ""
        m=re.match(r"https?://github\.com/([^/]+)/([^/#?]+)",u)
        if m: repos.add(m.group(1)+"/"+m.group(2).replace(".git",""))
repos=sorted(repos); print("repos",len(repos),file=sys.stderr)
out={}; lock=threading.Lock(); q=queue.Queue()
[q.put(r) for r in repos]
def w():
    while True:
        try: r=q.get_nowait()
        except queue.Empty: return
        try:
            o=subprocess.run(["gh","api","repos/"+r,"--jq",
                "{stars:.stargazers_count,pushed:.pushed_at,forks:.forks_count,fork:.fork,archived:.archived,created:.created_at}"],
                capture_output=True,text=True,timeout=40)
            d=json.loads(o.stdout) if o.returncode==0 and o.stdout.strip() else {"error":o.stderr[:120]}
        except Exception as e: d={"error":str(e)}
        with lock: out[r]=d
ths=[threading.Thread(target=w) for _ in range(10)]
[t.start() for t in ths]; [t.join() for t in ths]
json.dump(out,open(os.path.join(ROOT,"data/repo_activity.json"),"w"))
ok=[v for v in out.values() if "stars" in v]
print("resolved",len(ok),"/",len(out))
import statistics
if ok: print("median stars",statistics.median(x["stars"] for x in ok),"max",max(x["stars"] for x in ok))
