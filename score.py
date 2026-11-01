import json, os, numpy as np, csv
from collections import defaultdict, Counter
from common import *
R=os.path.join(HERE,RES); qs={q["id"]:q for q in load_queries()}; calib=split(); test=[i for i in qs if i not in calib]
IDX={t:i for i,t in enumerate(TIERS)}
def load(n): return [json.loads(l) for l in open(os.path.join(R,"raw",n+".jsonl"))]
recs={"Jev 1.14 (OpenRouter)":load("jev"),"Arch-Router 1.5B (local CPU)":load("arch_router"),
      "Llama-3.1-8B naive prompt (OpenRouter)":load("llm_baseline"),"Llama-3.1-8B delimited prompt (OpenRouter)":load("llm_baseline_v2")}
# RouteLLM BERT: thresholds on calibration split
b=load("routellm_bert_scores"); w0={r["id"]:r["win_rate"] for r in b if r["run"]==0}
cs=sorted(set(w0[i] for i in calib)); cand=[0]+[(a+c)/2 for a,c in zip(cs,cs[1:])]+[1.01]
def tier(w,t1,t2): return "cheap" if w<t1 else ("mid" if w<t2 else "frontier")
best=None
for i,t1 in enumerate(cand):
  for t2 in cand[i:]:
    p={k:tier(w0[k],t1,t2) for k in calib}
    acc=sum(p[k]==qs[k]["label"] for k in calib); under=sum(IDX[p[k]]<IDX[qs[k]["label"]] for k in calib)
    key=(acc,-under)
    if best is None or key>best[0]: best=(key,t1,t2)
T1,T2=best[1],best[2]
for r in b: r["pred"]=tier(r["win_rate"],T1,T2)
recs[f"RouteLLM BERT (local CPU)"]=b
ASSUMED={"cheap":0.002,"mid":0.02,"frontier":0.20}
rows=[]; conf={}
def ece(confs,correct,nb=5):
  confs=np.array(confs); correct=np.array(correct,float); e=0
  for lo in np.linspace(0,1,nb,endpoint=False):
    m=(confs>lo)&(confs<=lo+1/nb) if lo>0 else (confs<=1/nb)
    if m.sum(): e+=m.sum()/len(confs)*abs(confs[m].mean()-correct[m].mean())
  return e
for name,rs in recs.items():
  rs=[r for r in rs if r.get("pred")]
  def sub(ids): return [r for r in rs if r["id"] in ids]
  def acc(ids): x=sub(ids); return np.mean([r["pred"]==qs[r["id"]]["label"] for r in x])
  allr=rs; lab=[qs[r["id"]]["label"] for r in allr]
  over=np.mean([IDX[r["pred"]]>IDX[l] for r,l in zip(allr,lab)]); under=np.mean([IDX[r["pred"]]<IDX[l] for r,l in zip(allr,lab)])
  f2c=np.mean([r["pred"]=="cheap" for r,l in zip(allr,lab) if l=="frontier"])
  c2f=np.mean([r["pred"]=="frontier" for r,l in zip(allr,lab) if l=="cheap"])
  fmiss=np.mean([r["pred"]!="frontier" for r,l in zip(allr,lab) if l=="frontier"])
  cm=np.zeros((3,3),int)
  for r,l in zip(allr,lab): cm[IDX[l],IDX[r["pred"]]]+=1
  conf[name]=cm
  lat=[r["latency_ms"] for r in allr]
  cost1k=np.mean([r.get("cost",0) or 0 for r in allr])*1000
  by=defaultdict(list)
  for r in allr: by[r["id"]].append(r["pred"])
  consist=np.mean([len(set(v))==1 for v in by.values()])
  routed=np.mean([ASSUMED[r["pred"]] for r in allr]); ideal=np.mean([ASSUMED[l] for l in lab])
  # calibration
  cal=[(max(r["probs"].values()),r["pred"]==qs[r["id"]]["label"],r["probs"]) for r in allr if r.get("probs")]
  if not cal: cal=[(r["confidence"],r["pred"]==qs[r["id"]]["label"],None) for r in allr if r.get("confidence") is not None]
  brier=np.mean([sum((p.get(t,0)-(t==qs_l))**2 for t in TIERS) for (_,_,p),qs_l in zip(cal,[None]*len(cal)) ]) if False else None
  if cal and cal[0][2] is not None:
    lab_c=[qs[r["id"]]["label"] for r in allr if r.get("probs")]
    brier=np.mean([sum((p[t]-(t==l))**2 for t in TIERS) for (_,_,p),l in zip(cal,lab_c)])
  E=ece([c for c,_,_ in cal],[k for _,k,_ in cal]) if cal else None
  hi=[k for c,k,_ in cal if c>=0.8]
  rows.append({"router":name,"n_decisions":len(allr),"acc_test_split":round(acc(set(test)),3),"acc_all":round(acc(set(qs)),3),
    "over_routing":round(over,3),"under_routing":round(under,3),"frontier_to_cheap":round(f2c,3),"frontier_missed":round(fmiss,3),"cheap_to_frontier":round(c2f,3),
    "lat_p50_ms":round(float(np.percentile(lat,50)),1),"lat_p95_ms":round(float(np.percentile(lat,95)),1),
    "router_cost_per_1k_usd":round(cost1k,4),"routed_task_cost_vs_ideal":round(routed/ideal,3),
    "consistency_3runs":round(consist,3),"ece":None if E is None else round(E,3),"brier":None if brier is None else round(brier,3),
    "acc_at_conf>=0.8":round(np.mean(hi),3) if hi else None,"coverage_conf>=0.8":round(len(hi)/len(cal),3) if cal else None,
    "parse_fail_rate":round(np.mean([r.get("parse_ok",True)==False for r in allr]),3),"calibration_source":("route probabilities" if cal and cal[0][2] is not None else ("self-reported confidence" if cal else "none"))})
with open(os.path.join(R,"summary.csv"),"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump({"rows":rows,"confusion":{k:v.tolist() for k,v in conf.items()},"bert_thresholds":[T1,T2],"calib_ids":sorted(calib)},open(os.path.join(R,"summary.json"),"w"),indent=1)
# per-query majority preds
maj={}
for name,rs in recs.items():
  by=defaultdict(list)
  for r in rs:
    if r.get("pred"): by[r["id"]].append(r["pred"])
  maj[name]={k:Counter(v).most_common(1)[0][0] for k,v in by.items()}
json.dump(maj,open(os.path.join(R,"per_query_majority.json"),"w"),indent=1)
for r in rows: print(r)
print("BERT thresholds",T1,T2); print({k:v.tolist() for k,v in conf.items()})
