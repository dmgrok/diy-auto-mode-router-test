import json, time, numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from common import *
torch.set_num_threads(8)
CK="routellm/bert_gpt4_augmented"
model=AutoModelForSequenceClassification.from_pretrained(CK,num_labels=3).eval(); tok=AutoTokenizer.from_pretrained(CK)
def win_rate(p):  # identical to RouteLLM BERTRouter.calculate_strong_win_rate
  inp=tok(p,return_tensors="pt",padding=True,truncation=True)
  with torch.no_grad(): lg=model(**inp).logits.numpy()[0]
  s=np.exp(lg-lg.max()); s/=s.sum(); return float(1-s[-2:].sum())
out=writer("routellm_bert_scores")
for run in range(3):
  for q in load_queries():
    t=time.perf_counter(); w=win_rate(q["query"]); lat=(time.perf_counter()-t)*1000
    out.write(json.dumps({"router":"routellm_bert","run":run,"id":q["id"],"latency_ms":round(lat,1),"win_rate":w,"cost":0.0})+"\n")
print("bert done")
