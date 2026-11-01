import json, time, math, os
from llama_cpp import Llama
from common import *
llm=Llama(model_path=os.path.join(HERE,"models","Arch-Router-Q6_K.gguf"),n_ctx=4096,n_threads=8,logits_all=True,verbose=False)
TASK="""
You are a helpful assistant designed to find the best suited route.
You are provided with route description within <routes></routes> XML tags:
<routes>

{routes}

</routes>

<conversation>

{conversation}

</conversation>
"""
FMT="""
Your task is to decide which route is best suit with user intent on the conversation in <conversation></conversation> XML tags.  Follow the instruction:
1. If the latest intent from user is irrelevant or user intent is full filled, response with other route {"route": "other"}.
2. You must analyze the route descriptions and find the best match route for user latest intent. 
3. You only response the name of the route that best matches the user's request, use the exact name in the <routes></routes>.

Based on your analysis, provide your response in the following JSON formats if you decide to match any route:
{"route": "route_name"} 
"""
routes=[{"name":k,"description":v} for k,v in TIER_DESC.items()]
def prompt(q): return TASK.format(routes=json.dumps(routes),conversation=json.dumps([{"role":"user","content":q}]))+FMT
def chat_text(p): return f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n"
first={t:llm.tokenize(t.encode(),add_bos=False)[0] for t in TIERS}
out=writer("arch_router")
for run in range(3):
  for q in load_queries():
    p=chat_text(prompt(q["query"]))
    t=time.perf_counter(); r=llm.create_completion(p,max_tokens=32,temperature=0); lat=(time.perf_counter()-t)*1000
    txt=r["choices"][0]["text"]; pred=next((x for x in TIERS if f'"{x}"' in txt or f"'{x}'" in txt),None)
    rec={"router":"arch_router","run":run,"id":q["id"],"latency_ms":round(lat,1),"raw":txt[:100],"pred":pred or "mid","parse_ok":pred is not None,"cost":0.0,
         "prompt_tokens":r["usage"]["prompt_tokens"]}
    if run==0:  # route-token probabilities (not timed)
      llm.reset(); llm.eval(llm.tokenize((p+"{'route': '").encode(),special=True))
      lg=llm.scores[llm.n_tokens-1]; m=max(lg[i] for i in first.values()); e={k:math.exp(lg[i]-m) for k,i in first.items()}; s=sum(e.values())
      rec["probs"]={k:v/s for k,v in e.items()}
    out.write(json.dumps(rec)+"\n"); out.flush()
print("arch done")
