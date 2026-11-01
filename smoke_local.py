import sys,time
from local_backends import BACKENDS
b=BACKENDS[sys.argv[1]](); 
for q in ["URGENT!!! Production is down!!! ...the error says `ModuleNotFoundError: No module named 'requests'`. Please fix ASAP.","Bump lodash from 4.17.20 to 4.17.21 in package.json.","Intermittent deadlock in our Go worker pool under load."]:
  t=time.perf_counter(); a=b.ask(q); print(b.name,round((time.perf_counter()-t)*1000),"ms",a,flush=True)
