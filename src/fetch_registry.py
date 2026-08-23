import json, urllib.request, time, sys

BASE="https://registry.modelcontextprotocol.io/v0/servers"
def get(url):
    req=urllib.request.Request(url, headers={"User-Agent":"mcp-schema-compat-poc/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

servers=[]; cursor=None; pages=0
while True:
    url=BASE+"?limit=100&version=latest"+(f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
    d=get(url)
    servers.extend(d.get("servers",[]))
    cursor=d.get("metadata",{}).get("nextCursor")
    pages+=1
    print(f"page {pages} total={len(servers)}", file=sys.stderr)
    if not cursor or pages>60: break
    time.sleep(0.1)

json.dump(servers, open("data/registry_servers.json","w"), indent=1)
print("saved", len(servers))
