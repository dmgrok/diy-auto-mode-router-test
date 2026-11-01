import csv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=[r for r in csv.DictReader(open("summary.csv")) if r["group"]!="Appendix" and r["mode"].startswith("rules")]
def name(r):
    n=r["router"].replace(" (OpenRouter)","").replace(" (via OpenRouter)","*").replace(" delimited","")
    return n.replace(" (local CPU)"," · CPU")
rows.sort(key=lambda r:-float(r["accuracy"]))
mx=max(float(r["cost_per_1k_usd"]) for r in rows)
names=[name(r) for r in rows]; acc=[float(r["accuracy"])*100 for r in rows]
h2c=[float(r["hard_to_cheap"])*100 for r in rows]; cost=[float(r["cost_per_1k_usd"])/mx*100 for r in rows]
jev=["Jev" in n for n in names]
fig,ax=plt.subplots(1,3,figsize=(15,6.2),sharey=True)
y=range(len(rows))
for a,vals,title,col,fmt in [(ax[0],acc,"Routed right (with your 2 rules)","#2a9d4b","{:.0f}%"),
                             (ax[1],h2c,"Hard task sent to CHEAP model","#d62839","{:.0f}%"),
                             (ax[2],cost,"Router cost per decision\n(most expensive = 100%)","#555555","{:.0f}%")]:
    cols=["#1f6fd1" if j else col for j in jev]
    a.barh(list(y),vals,color=cols)
    for i,v in enumerate(vals):
        lab=fmt.format(v) if not (a is ax[2] and v==0) else "0% API (your own CPU)"
        a.text(v+1,i,lab,va="center",fontsize=10)
    a.set_title(title,fontsize=12,loc="left"); a.spines[["top","right"]].set_visible(False)
ax[0].set_xlim(0,100); ax[1].set_xlim(0,30); ax[2].set_xlim(0,135)
ax[0].set_yticks(list(y)); ax[0].set_yticklabels(names); ax[0].invert_yaxis()
fig.suptitle("Qwen3-235B is the most accurate router and the most expensive. Jev does 74% for 62% of the price,\nand gpt-oss-20b does 77% for 12%.",x=0.01,ha="left",fontsize=13,fontweight="bold")
fig.text(0.01,0.01,"Blue = Jev (hosted, closed). * = open-weight model called via OpenRouter as a stand-in for self-hosting. 100% = $0.039 per 1,000 decisions.\nCPU models cost $0 in API fees, but you pay for the hardware, which isn't counted. 67 queries, labels are David's; gaps under ~10 points are mostly noise.",fontsize=8.5,color="#555")
plt.tight_layout(rect=(0,0.06,1,0.9)); plt.savefig("chart_cost.png",dpi=130)
for n,c in zip(names,cost): print(n, round(c))
