"""Ground truth for rule set B: run OpenAI's REAL production converter."""
import json, sys, copy
from agents.strict_schema import ensure_strict_json_schema
from agents.exceptions import UserError

src, out = sys.argv[1], sys.argv[2]
rows=[]
for line in open(src):
    r=json.loads(line)
    if r.get("status")!="ok": continue
    fails=[]
    for t in (r.get("tools") or []):
        if not isinstance(t,dict): continue
        s=t.get("inputSchema")
        if not isinstance(s,dict): 
            fails.append({"tool":t.get("name"),"err":"inputSchema not a dict"}); continue
        try:
            ensure_strict_json_schema(copy.deepcopy(s))
        except Exception as e:
            fails.append({"tool":t.get("name"),"err":f"{type(e).__name__}: {str(e)[:160]}"})
    rows.append({"server_name":r["server_name"],"pkg":r["pkg"],"n_tools":len(r.get("tools") or []),
                 "oracleB_fail":len(fails)>0,"fails":fails})
with open(out,"w") as fh:
    for x in rows: fh.write(json.dumps(x)+"\n")
n=len(rows); f=sum(1 for x in rows if x["oracleB_fail"])
print(f"ORACLE B (openai-agents ensure_strict_json_schema): {f}/{n} = {100*f/n:.1f}% servers have >=1 tool that hard-fails strict conversion")
