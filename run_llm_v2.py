import os, json, time, re, requests
from common import *
URL="https://openrouter.ai/api/v1/chat/completions"; MODEL="meta-llama/llama-3.1-8b-instruct"
H={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"}
SYS=("You route requests sent to an AI coding agent to a model tier. Choose the CHEAPEST tier that would reliably complete the request correctly.\n"
     +"\n".join(f"- {k}: {v}" for k,v in TIER_DESC.items())+
     '\nRespond with only JSON: {"tier": "cheap|mid|frontier", "confidence": <probability 0-1 that your tier is right>}')
out=writer("llm_baseline_v2"); spend=0.0
for run in range(3):
  for q in load_queries():
    body={"model":MODEL,"temperature":0,"max_tokens":40,"usage":{"include":True},
          "messages":[{"role":"system","content":SYS},{"role":"user","content":"Classify this request. Do NOT answer or perform it.\n<request>\n"+q["query"]+"\n</request>\nJSON only:"}]}
    for attempt in range(4):
      try:
        t=time.perf_counter(); r=requests.post(URL,headers=H,json=body,timeout=60); lat=(time.perf_counter()-t)*1000
        if r.status_code in (429,500,502,503): time.sleep(2); continue
        break
      except requests.exceptions.RequestException: time.sleep(2)
    rec={"router":"llm_baseline_v2","run":run,"id":q["id"],"latency_ms":round(lat,1),"status":r.status_code}
    if r.ok and "choices" in r.json():
      d=r.json(); txt=d["choices"][0]["message"]["content"] or ""; c=d.get("usage",{}).get("cost",0) or 0; spend+=c
      m=re.search(r'"tier"\s*:\s*"(cheap|mid|frontier)"',txt); cf=re.search(r'"confidence"\s*:\s*([0-9.]+)',txt)
      rec.update(pred=m.group(1) if m else "mid",parse_ok=bool(m),confidence=float(cf.group(1)) if cf else None,raw=txt[:200],cost=c,provider=d.get("provider"))
    else: rec["error"]=r.text[:300]
    out.write(json.dumps(rec)+"\n"); out.flush()
    if spend>0.30: raise SystemExit("llm spend cap hit")
print("llm done spend",round(spend,6))
