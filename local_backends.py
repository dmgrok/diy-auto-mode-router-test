import sys, time, torch, numpy as np
from common import TIERS
from decision_common import QUESTIONS, state, state_text
torch.set_num_threads(8)
HF="/home/box/.cache/huggingface/hub/"
V=HF+"models--vllm-sr--vela3-fast/snapshots/fa60e3aa41132c60bf05a84cabfdced39cb6d4f7"
D=HF+"models--vllm-sr--d3-lite/snapshots/03560c26f5199c3c04129a2ccb38960c913635e0"
def norm_answers(a):
  return {"tier":a["tier"].get("choice"),"probs":a["tier"].get("probabilities"),"urgent":a["urgent"].get("noul"),"ripple":a["ripple"].get("noul")}
class Vela:
  name="vela3_fast"
  def __init__(s):
    sys.path.insert(0,V); from vela3_encoder import DecisionEncoder; s.m=DecisionEncoder.load(V)
  def ask(s,q):
    if hasattr(s.m,"system_one"): out=s.m.system_one(state(q),QUESTIONS)["answers"]
    else: out=s.m.predict(state(q),QUESTIONS)[0]
    return norm_answers(out)
class D3:
  name="d3_lite"
  def __init__(s):
    from transformers import AutoModel; s.m=AutoModel.from_pretrained(D,trust_remote_code=True).eval()
  def ask(s,q):
    with torch.no_grad(): return norm_answers(s.m.system_one(state=state(q),questions=QUESTIONS)["answers"])
class GLi:
  name="gliclass_v4_edge"
  def __init__(s):
    from gliclass import GLiClassModel, ZeroShotClassificationPipeline
    mid="knowledgator/gliclass-v4-edge"; m=GLiClassModel.from_pretrained(mid)
    s.p=ZeroShotClassificationPipeline(m,mid,classification_type="single-label",max_length=2048,device="cpu")
    s.keys=list(QUESTIONS["tier"]["criteria"]); s.descs=[QUESTIONS["tier"]["criteria"][k] for k in s.keys]
  def _single(s,text,labels,prompt):
    r=s.p(text,labels,prompt=prompt,classification_type="single-label",threshold=0.0)[0]
    return {x["label"]:x["score"] for x in r}
  def ask(s,q):
    t=state_text(q)
    sc=s._single(t,s.descs,QUESTIONS["tier"]["instructions"]); probs={k:float(sc.get(d,0)) for k,d in zip(s.keys,s.descs)}
    tot=sum(probs.values()) or 1; probs={k:v/tot for k,v in probs.items()}
    u=s._single(t,["yes","no"],QUESTIONS["urgent"]["instructions"]); r=s._single(t,["yes","no"],QUESTIONS["ripple"]["instructions"])
    nu=lambda d: d.get("yes",0)/((d.get("yes",0)+d.get("no",0)) or 1)
    return {"tier":max(probs,key=probs.get),"probs":probs,"urgent":nu(u),"ripple":nu(r)}
class Nadir:
  name="nadirclaw_distilbert"
  def __init__(s):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    r="nadirclaw/nadirclaw-distilbert"; s.t=AutoTokenizer.from_pretrained(r); s.m=AutoModelForSequenceClassification.from_pretrained(r).eval()
  def ask(s,q):
    i=s.t(q,return_tensors="pt",truncation=True,max_length=256)
    with torch.no_grad(): p=torch.softmax(s.m(**i).logits[0],-1).tolist()
    probs=dict(zip(TIERS,p))  # simple->cheap, medium->mid, complex->frontier
    return {"tier":max(probs,key=probs.get),"probs":probs,"urgent":None,"ripple":None}
BACKENDS={"vela":Vela,"d3":D3,"gli":GLi,"nadir":Nadir}
