import json, os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from common import RES
S=json.load(open(RES+"/summary.json"))["rows"]
short={"Jev 1.14 (OpenRouter)":"Jev 1.14\n(hosted)","Arch-Router 1.5B (local CPU)":"Arch-Router 1.5B\n(local CPU)",
 "Llama-3.1-8B naive prompt (OpenRouter)":"Llama-3.1-8B\nnaive prompt","Llama-3.1-8B delimited prompt (OpenRouter)":"Llama-3.1-8B\ndelimited prompt",
 "RouteLLM BERT (local CPU)":"RouteLLM BERT\n(local CPU)"}
col={"Jev 1.14 (OpenRouter)":"#1f6feb"}; grey="#8b949e"
fig,(a,b)=plt.subplots(1,2,figsize=(13,5.6),gridspec_kw={"width_ratios":[1.25,1]})
for r in S:
  c=col.get(r["router"],grey); x=r["lat_p50_ms"]; y=r["acc_all"]*100
  a.scatter(x,y,s=160,color=c,zorder=3)
  cost="$0 API (local)" if r["router_cost_per_1k_usd"]==0 else f'${r["router_cost_per_1k_usd"]:.3f} / 1k decisions'
  a.annotate(short[r["router"]].replace("\n"," ")+f"\n{y:.0f}% · {cost}",(x,y),xytext=(8,-4 if "naive" not in r["router"] else -14),textcoords="offset points",fontsize=8.5,color=c if c!=grey else "#444")
a.set_xscale("log"); a.set_xlim(15,8000); a.set_ylim(25,90); a.axhline(33.3,ls=":",color=grey); a.text(2500,34.5,"random guess (33%)",fontsize=8,color=grey)
a.set_xlabel("Median latency per routing decision (ms, log scale)"); a.set_ylabel(os.environ.get("YLAB","Accuracy vs our labels (57 queries × 3 runs)"))
a.set_title("Accuracy vs speed and cost",fontsize=11,loc="left"); a.grid(alpha=.3)
order=sorted(S,key=lambda r:r["frontier_to_cheap"])
names=[short[r["router"]].replace("\n"," ") for r in order]
f2c=[r["frontier_to_cheap"]*100 for r in order]; miss=[r["frontier_missed"]*100 for r in order]
b.barh(names,miss,color="#f0d0d0",label="Hard task not sent to frontier (any downgrade)")
b.barh(names,f2c,color="#cf222e",label="Hard task sent to CHEAP tier (dangerous)")
for i,(m,f) in enumerate(zip(miss,f2c)): b.text(max(f,1)+1,i,f"{f:.0f}%",va="center",fontsize=9,color="#cf222e",fontweight="bold")
b.set_xlim(0,100); b.set_xlabel(os.environ.get("XLAB","% of the 19 frontier-labeled queries (× 3 runs)")); b.invert_yaxis()
b.set_title("Under-routing of hard tasks",fontsize=11,loc="left"); b.legend(fontsize=8,loc="upper right"); b.grid(axis="x",alpha=.3)
fig.suptitle(os.environ.get("TITLE","Jev routed coding tasks most accurately (76%), never sent a hard task to the cheap tier,\nand decided in ~150 ms for about 2 cents per 1,000 decisions"),fontsize=13,fontweight="bold",x=0.01,ha="left")
fig.text(0.01,0.01,os.environ.get("FOOT","Labels are our judgement, not measured task outcomes. n=57 queries; differences under ~10 points are within noise. Jev still downgrades 37% of hard tasks to mid."),fontsize=8,color="#555")
plt.tight_layout(rect=[0,0.03,1,0.9]); plt.savefig(RES+"/chart.png",dpi=150)
