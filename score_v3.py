import json, os, csv, numpy as np
from collections import defaultdict, Counter
from common import *; from decision_common import apply_rules
R=os.path.join(HERE,"results_v3"); qs={q["id"]:q for q in load_queries(True)}; IDX={t:i for i,t in enumerate(TIERS)}
def L(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def raw(n): return L(os.path.join(R,"raw",n+".jsonl"))
def dec(recs,mode):  # decision-model records -> pred for mode
  out=[]
  for r in recs:
    p=r.get("pred_rules" if mode=="rules" else "pred_norules")
    if p: out.append({**r,"pred":p})
  return out
E=[]  # (group, name, mode, recs, has_probs)
jev=raw("jev")
E+= [("Hosted closed","Jev 1.14 (OpenRouter)","no rules",dec(jev,"no"),"probs"),("Hosted closed","Jev 1.14 (OpenRouter)","rules",dec(jev,"rules"),None)]
LLM=[("gptoss120b","gpt-oss-120b (via OpenRouter)"),("gptoss20b","gpt-oss-20b (via OpenRouter)"),("qwen3_235b","Qwen3-235B-A22B-2507 (via OpenRouter)"),
     ("mistral_small32","Mistral Small 3.2 24B (via OpenRouter)"),("llama8b","Llama-3.1-8B delimited (via OpenRouter)")]
for tag,nm in LLM:
  nr=raw(f"{tag}_norules") or [ {**r} for r in L(os.path.join(HERE,"results_v2","raw","llm_baseline_v2.jsonl"))]
  E+=[("Open weights",nm,"no rules",[r for r in nr if r.get("pred")],"conf"),("Open weights",nm,"rules",[r for r in raw(f"{tag}_rules") if r.get("pred")],None)]
LOC=[("vela3_fast","vela3-fast 0.4B (local CPU)"),("d3_lite","d3-lite 0.8B (local CPU)"),("gliclass_v4_edge","GLiClass v4 edge 0.4B (local CPU)")]
for tag,nm in LOC:
  rs=raw(tag)
  if rs: E+=[("Open weights",nm,"no rules",dec(rs,"no"),"probs"),("Open weights",nm,"rules",dec(rs,"rules"),None)]
nad=raw("nadirclaw_distilbert"); gli={(r["run"],r["id"]):r for r in raw("gliclass_v4_edge")}
if nad:
  E.append(("Open weights","NadirClaw DistilBERT (local CPU)","no rules",dec(nad,"no"),"probs"))
  if gli:
    hy=[{**r,"pred":apply_rules(r["pred_norules"],gli[(r["run"],r["id"])]["urgent"],gli[(r["run"],r["id"])]["ripple"]),
         "latency_ms":r["latency_ms"]+gli[(r["run"],r["id"])]["latency_ms"]} for r in nad if (r["run"],r["id"]) in gli]
    E.append(("Open weights","NadirClaw DistilBERT (local CPU)","rules (via GLiClass rule checks)",hy,None))
# appendix from v2 (no rules)
v2=json.load(open(os.path.join(HERE,"results_v2","per_query_majority.json")))
def ece(c,k,nb=5):
  c=np.array(c);k=np.array(k,float);e=0
  for lo in np.linspace(0,1,nb,endpoint=False):
    m=(c>lo)&(c<=lo+1/nb) if lo>0 else (c<=1/nb)
    if m.sum(): e+=m.sum()/len(c)*abs(c[m].mean()-k[m].mean())
  return float(e)
rows=[];maj={};counts=[]  # counts: raw integers, so charts/report can round once from exact values
for g,nm,mode,rs,cal in E:
  lab=[qs[r["id"]]["label"] for r in rs]; pr=[r["pred"] for r in rs]
  acc=np.mean([p==l for p,l in zip(pr,lab)])
  f2c=np.mean([p=="cheap" for p,l in zip(pr,lab) if l=="frontier"]); fm=np.mean([p!="frontier" for p,l in zip(pr,lab) if l=="frontier"])
  c2f=np.mean([p=="frontier" for p,l in zip(pr,lab) if l=="cheap"])
  over=np.mean([IDX[p]>IDX[l] for p,l in zip(pr,lab)]); under=np.mean([IDX[p]<IDX[l] for p,l in zip(pr,lab)])
  lat=[r["latency_ms"] for r in rs]; cost=np.mean([r.get("cost",0) or 0 for r in rs])*1000
  by=defaultdict(list)
  for r in rs: by[r["id"]].append(r["pred"])
  cons=np.mean([len(set(v))==1 for v in by.values()]); runs=len(set(r["run"] for r in rs))
  E_=None
  if cal=="probs": E_=ece([max(r["probs"].values()) for r in rs],[p==l for p,l in zip(pr,lab)])
  elif cal=="conf":
    cc=[(r["confidence"],p==l) for r,p,l in zip(rs,pr,lab) if r.get("confidence") is not None]
    if cc: E_=ece([min(c,1) for c,_ in cc],[k for _,k in cc])
  pf=np.mean([r.get("parse_ok",True)==False for r in rs])
  m={k:Counter(v).most_common(1)[0][0] for k,v in by.items()}; maj[f"{nm} | {mode}"]=m
  counts.append({"group":g,"router":nm,"mode":mode,"runs":runs,"n_decisions":len(rs),
    "n_correct":int(sum(p==l for p,l in zip(pr,lab))),"n_hard":int(sum(l=="frontier" for l in lab)),
    "n_hard_to_cheap":int(sum(p=="cheap" for p,l in zip(pr,lab) if l=="frontier")),
    "n_hard_not_frontier":int(sum(p!="frontier" for p,l in zip(pr,lab) if l=="frontier")),
    "n_easy":int(sum(l=="cheap" for l in lab)),"n_cheap_to_frontier":int(sum(p=="frontier" for p,l in zip(pr,lab) if l=="cheap")),
    "n_over":int(sum(IDX[p]>IDX[l] for p,l in zip(pr,lab))),"n_under":int(sum(IDX[p]<IDX[l] for p,l in zip(pr,lab))),
    "cost_sum_usd":float(sum(r.get("cost",0) or 0 for r in rs)),"lat_p50_ms":float(np.percentile(lat,50)),
    "lat_p95_ms":float(np.percentile(lat,95)),"n_queries":len(by),"n_consistent":int(sum(len(set(v))==1 for v in by.values()))})
  rows.append({"group":g,"router":nm,"mode":mode,"runs":runs,"n_decisions":len(rs),"accuracy":round(acc,3),"hard_to_cheap":round(f2c,3),"hard_not_frontier":round(fm,3),
    "cheap_to_frontier":round(c2f,3),"over_routing":round(over,3),"under_routing":round(under,3),"lat_p50_ms":round(float(np.percentile(lat,50)),1),"lat_p95_ms":round(float(np.percentile(lat,95)),1),
    "cost_per_1k_usd":round(cost,4),"consistency":round(cons,3),"ece":None if E_ is None else round(E_,3),"parse_fail":round(pf,3),
    "q07":m.get("q07"),"q48":m.get("q48")})
for nm,k in [("Arch-Router 1.5B (appendix; licence)","Arch-Router 1.5B (local CPU)"),("RouteLLM BERT (appendix; below chance)","RouteLLM BERT (local CPU)")]:
  p=v2[k]; lab={i:qs[i]["label"] for i in qs}
  rows.append({"group":"Appendix","router":nm,"mode":"no rules (v2, majority vote)","runs":3,"n_decisions":len(p),"accuracy":round(np.mean([p[i]==lab[i] for i in p]),3),
    "hard_to_cheap":round(np.mean([p[i]=="cheap" for i in p if lab[i]=="frontier"]),3),"hard_not_frontier":round(np.mean([p[i]!="frontier" for i in p if lab[i]=="frontier"]),3),
    "q07":p["q07"],"q48":p["q48"]})
keys=list(rows[0]); 
with open(os.path.join(R,"summary.csv"),"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); [w.writerow({k:r.get(k) for k in keys}) for r in rows]
json.dump({"rows":rows},open(os.path.join(R,"summary.json"),"w"),indent=1); json.dump({"rows":counts},open(os.path.join(R,"counts.json"),"w"),indent=1); json.dump(maj,open(os.path.join(R,"per_query_majority.json"),"w"),indent=1)
for r in rows: print(f"{r['group'][:6]:6} {r['router'][:40]:40} {r['mode'][:12]:12} acc {r['accuracy']:.2f} h2c {r['hard_to_cheap']:.2f} hnf {r['hard_not_frontier']:.2f} c2f {r.get('cheap_to_frontier')} p50 {r.get('lat_p50_ms')} $1k {r.get('cost_per_1k_usd')} cons {r.get('consistency')} ece {r.get('ece')} q07 {r['q07']} q48 {r['q48']} runs {r['runs']}")
