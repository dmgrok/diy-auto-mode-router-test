import sys, json, time
from common import *; from decision_common import apply_rules
from local_backends import BACKENDS
b=BACKENDS[sys.argv[1]](); RUNS=int(sys.argv[2]); out=writer(b.name)
b.ask("warmup")
for run in range(RUNS):
  for q in load_queries():
    t=time.perf_counter(); a=b.ask(q["query"]); lat=(time.perf_counter()-t)*1000
    rec={"router":b.name,"run":run,"id":q["id"],"latency_ms":round(lat,1),"pred_norules":a["tier"],"probs":a["probs"],"urgent":a["urgent"],"ripple":a["ripple"],"cost":0.0}
    rec["pred_rules"]=apply_rules(a["tier"],a["urgent"],a["ripple"]) if a["urgent"] is not None else None
    out.write(json.dumps(rec)+"\n"); out.flush()
print(b.name,"done")
