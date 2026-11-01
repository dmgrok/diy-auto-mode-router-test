import os, json, time, requests
from common import *; from decision_common import *
URL="https://openrouter.ai/api/v1/systemone"; MODEL="typesafe/jev-1.14"
H={"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"}
out=writer("jev"); spend=0.0
for run in range(3):
  for q in load_queries():
    body={"model":MODEL,"state":state(q["query"]),"questions":QUESTIONS}
    r=None
    for attempt in range(4):
      try:
        t=time.perf_counter(); r=requests.post(URL,headers=H,json=body,timeout=60); lat=(time.perf_counter()-t)*1000
        if r.status_code in (429,500,502,503): time.sleep(2); continue
        break
      except requests.exceptions.RequestException: time.sleep(2)
    rec={"router":"jev","run":run,"id":q["id"],"latency_ms":round(lat,1),"status":r.status_code}
    if r.ok:
      d=r.json(); a=d["answers"]; c=d["usage"].get("cost",0) or 0; spend+=c
      rec.update(pred_norules=a["tier"]["choice"],probs=a["tier"].get("probabilities"),confidence=a["tier"].get("confidence"),
                 urgent=a["urgent"]["noul"],ripple=a["ripple"]["noul"],cost=c,input_tokens=d["usage"].get("input_tokens"))
      rec["pred_rules"]=apply_rules(rec["pred_norules"],rec["urgent"],rec["ripple"])
    else: rec["error"]=r.text[:300]
    out.write(json.dumps(rec)+"\n"); out.flush()
    if spend>0.3: raise SystemExit("cap")
print("jev done",round(spend,6))
