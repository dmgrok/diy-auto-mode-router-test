import json, os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, numpy as np
rows=json.load(open("results_v3/summary.json"))["rows"]
by={}
for r in rows:
  if r["group"]=="Appendix": continue
  by.setdefault((r["group"],r["router"]),{})["rules" if r["mode"].startswith("rules") else "none"]=r
short=lambda n:n.replace(" (OpenRouter)","").replace(" (via OpenRouter)","*").replace(" (local CPU)"," · CPU").replace("Llama-3.1-8B delimited","Llama-3.1-8B")
hosted=[k for k in by if k[0]=="Hosted closed"]
openw=sorted([k for k in by if k[0]=="Open weights"],key=lambda k:-by[k].get("rules",by[k]["none"])["accuracy"])
order=hosted+[None]+openw
fig,axes=plt.subplots(1,2,figsize=(14,7.2),sharey=True)
y=[];labels=[];ypos=0;ys={}
for k in order:
  if k is None: ypos+=0.6; continue
  ys[k]=ypos; ypos+=1
H=0.38; c_no="#c9d1d9"; c_ru={"Hosted closed":"#1f6feb","Open weights":"#2da44e"}; c_bad_no="#f4c4c4"; c_bad="#cf222e"
for k,yy in ys.items():
  d=by[k]; n=d["none"]; ru=d.get("rules")
  axes[0].barh(yy-H/2,n["accuracy"]*100,H,color=c_no)
  axes[0].text(n["accuracy"]*100+1,yy-H/2,f'{n["accuracy"]*100:.0f}',va="center",fontsize=8,color="#57606a")
  if ru:
    axes[0].barh(yy+H/2,ru["accuracy"]*100,H,color=c_ru[k[0]])
    axes[0].text(ru["accuracy"]*100+1,yy+H/2,f'{ru["accuracy"]*100:.0f}%',va="center",fontsize=9,fontweight="bold",color=c_ru[k[0]])
  axes[1].barh(yy-H/2,n["hard_to_cheap"]*100,H,color=c_bad_no)
  axes[1].text(n["hard_to_cheap"]*100+0.4,yy-H/2,f'{n["hard_to_cheap"]*100:.0f}',va="center",fontsize=8,color="#57606a")
  if ru:
    axes[1].barh(yy+H/2,ru["hard_to_cheap"]*100,H,color=c_bad)
    axes[1].text(ru["hard_to_cheap"]*100+0.4,yy+H/2,f'{ru["hard_to_cheap"]*100:.0f}%',va="center",fontsize=9,fontweight="bold",color=c_bad)
axes[0].set_yticks(list(ys.values())); axes[0].set_yticklabels([short(k[1]) for k in ys]); axes[0].invert_yaxis()
axes[0].set_xlim(0,100); axes[1].set_xlim(0,30)
axes[0].set_title("Accuracy vs David's labels (67 queries)",loc="left",fontsize=11)
axes[1].set_title("Dangerous: hard task sent to the CHEAP tier",loc="left",fontsize=11)
axes[0].set_xlabel("% correct   (grey = without rules, colour = with David's 2 rules)")
axes[1].set_xlabel("% of 22 frontier-labelled queries   (pink = without rules, red = with)")
sep=(ys[hosted[-1]]+ys[openw[0]])/2
for a in axes: a.axhline(sep,color="#8b949e",lw=1,ls="--"); a.grid(axis="x",alpha=.3)
axes[0].text(99,ys[hosted[0]]-0.45,"HOSTED CLOSED",ha="right",fontsize=9,color="#1f6feb",fontweight="bold")
axes[0].text(99,ys[openw[0]]-0.45,"OPEN WEIGHTS (self-hostable)",ha="right",fontsize=9,color="#2da44e",fontweight="bold")
fig.suptitle(os.environ["TITLE"],fontsize=13,fontweight="bold",x=0.01,ha="left")
fig.text(0.01,0.01,os.environ["FOOT"],fontsize=8,color="#555")
plt.tight_layout(rect=[0,0.04,1,0.9]); plt.savefig("results_v3/chart.png",dpi=150)
