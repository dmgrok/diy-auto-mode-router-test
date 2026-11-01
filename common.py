import json, random, os, time
HERE=os.path.dirname(os.path.abspath(__file__))
TIERS=["cheap","mid","frontier"]
TIER_DESC={
 "cheap":"Mechanical or trivial coding work: typos, renames, one-line config/version edits, formatting, simple factual docs questions, small well-known scripts. A small cheap model handles it reliably.",
 "mid":"Moderate coding work: localized bug fixes with a clear error, pattern-based multi-file refactors, well-known feature setups (CI, OAuth), structured design write-ups. Needs a capable mid-tier model.",
 "frontier":"Hard coding work: open-ended architecture, concurrency/performance/production debugging, large behavior-preserving migrations, correctness-critical code (payments, money, sync), long-horizon features. Needs the strongest frontier model.",
}
QFILE=os.environ.get("QUERIES","queries.jsonl"); RES=os.environ.get("RESULTS","results"); ONLY=set(filter(None,os.environ.get("ONLY","").split(",")))
def load_queries(all_=False):
    qs=[json.loads(l) for l in open(os.path.join(HERE,QFILE))]
    return qs if (all_ or not ONLY) else [q for q in qs if q["id"] in ONLY]
def split():
    qs=load_queries(True); rnd=random.Random(42); calib=set()
    for t in TIERS:
        ids=[q["id"] for q in qs if q["label"]==t]; rnd.shuffle(ids); calib|=set(ids[:5])
    return calib
def writer(name):
    d=os.path.join(HERE,RES,"raw"); os.makedirs(d,exist_ok=True); return open(os.path.join(d,f"{name}.jsonl"),"w")
