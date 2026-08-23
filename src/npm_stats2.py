import json, urllib.request, urllib.parse, urllib.error, threading, queue, os, sys, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res=json.load(open(ROOT+"/data/npm_downloads.json"))
todo=[p for p,v in res.items() if v is None]
print("todo",len(todo),file=sys.stderr)
q=queue.Queue(); [q.put(p) for p in todo]
lock=threading.Lock(); n=[0]
def w():
    while True:
        try: p=q.get_nowait()
        except queue.Empty: return
        v=None
        for attempt in range(4):
            try:
                req=urllib.request.Request("https://api.npmjs.org/downloads/point/last-week/"+urllib.parse.quote(p,safe='@/'),headers={"User-Agent":"mcp-schema-compat-poc"})
                with urllib.request.urlopen(req,timeout=25) as r: d=json.loads(r.read())
                v=d.get("downloads"); break
            except urllib.error.HTTPError as e:
                if e.code==404: v=0; break
                time.sleep(1.5*(attempt+1))
            except Exception: time.sleep(1.5*(attempt+1))
        with lock:
            res[p]=v; n[0]+=1
            if n[0]%150==0: print(n[0],file=sys.stderr)
ths=[threading.Thread(target=w) for _ in range(6)]
[t.start() for t in ths]; [t.join() for t in ths]
json.dump(res,open(ROOT+"/data/npm_downloads.json","w"))
vals=[v for v in res.values() if v is not None]
import statistics
print("resolved",len(vals),"/",len(res),"median",statistics.median(vals))
for th in (0,1,10,50,100,500,1000,5000,50000):
    print(f">={th}: {sum(1 for v in vals if v>=th)}")
