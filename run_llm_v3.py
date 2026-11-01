import os, sys, json, time, re, requests
from common import *
MODEL=sys.argv[1]; TAG=sys.argv[2]; RULES=sys.argv[3]=="rules"; RUNS=int(sys.argv[4]) if len(sys.argv)>4 else 3
URL="https://openrouter.ai/api/v1/chat/completions"
H={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"}
POLICY=("\nPolicy rules (they override difficulty):\n"
 "1. If the user signals urgency or production impact (e.g. 'urgent', 'ASAP', production down, outage, customers blocked), choose frontier.\n"
 "2. If the change could ripple across the codebase (e.g. a major dependency or framework upgrade, a wide migration touching many files), choose frontier.\n")
SYS=("You route requests sent to an AI coding agent to a model tier. Choose the CHEAPEST tier that would reliably complete the request correctly.\n"
     +"\n".join(f"- {k}: {v}" for k,v in TIER_DESC.items())+(POLICY if RULES else "")+
     '\nRespond with only JSON: {"tier": "cheap|mid|frontier", "confidence": <probability 0-1 that your tier is right>}')
reasoning="gpt-oss" in MODEL
name=f"{TAG}_{'rules' if RULES else 'norules'}"; out=writer(name); spend=0.0
for run in range(RUNS):
  for q in load_queries():
    body={"model":MODEL,"temperature":0,"max_tokens":1500 if reasoning else 60,"usage":{"include":True},
          "messages":[{"role":"system","content":SYS},{"role":"user","content":"Classify this request. Do NOT answer or perform it.\n<request>\n"+q["query"]+"\n</request>\nJSON only:"}]}
    if reasoning: body["reasoning"]={"effort":"low"}
    r=None; lat=None
    for attempt in range(4):
      try:
        t=time.perf_counter(); r=requests.post(URL,headers=H,json=body,timeout=90); lat=(time.perf_counter()-t)*1000
        if r.status_code in (429,500,502,503): time.sleep(3); continue
        break
      except requests.exceptions.RequestException: time.sleep(3)
    rec={"router":name,"model":MODEL,"rules":RULES,"run":run,"id":q["id"],"latency_ms":round(lat or 0,1),"status":getattr(r,"status_code",None)}
    try: d=r.json()
    except Exception: d={}
    if r is not None and r.ok and "choices" in d:
      txt=d["choices"][0]["message"].get("content") or ""; c=d.get("usage",{}).get("cost",0) or 0; spend+=c
      m=re.search(r'"tier"\s*:\s*"(cheap|mid|frontier)"',txt); cf=re.search(r'"confidence"\s*:\s*([0-9.]+)',txt)
      rec.update(pred=m.group(1) if m else "mid",parse_ok=bool(m),confidence=float(cf.group(1)) if cf else None,raw=txt[:200],cost=c,
                 provider=d.get("provider"),completion_tokens=d.get("usage",{}).get("completion_tokens"))
    else: rec["error"]=(r.text[:300] if r is not None else "no response")
    out.write(json.dumps(rec)+"\n"); out.flush()
    if spend>0.25: raise SystemExit(f"{name} spend cap hit")
print(name,"done spend",round(spend,6))
