"""Router mistakes per 100 requests, with David's two rules (7 routers shown).
Reads counts.json (raw integer counts from score_v3.py) next to this file, so every
percentage is rounded once from exact counts; writes chart_errors.png (1080x1350)."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
# Be Vietnam Pro if you have it (point CHART_FONT_DIR at its .ttf files, or install it
# system-wide); otherwise fall back to DejaVu Sans, which ships with matplotlib.
FONT_DIR = os.environ.get("CHART_FONT_DIR", "")
for w in ("Regular", "Medium", "Bold"):
    p = os.path.join(FONT_DIR, f"BeVietnamPro-{w}.ttf")
    if FONT_DIR and os.path.exists(p):
        fm.fontManager.addfont(p)
_have = {f.name for f in fm.fontManager.ttflist}
plt.rcParams["font.family"] = (["Be Vietnam Pro"] if "Be Vietnam Pro" in _have else []) + ["DejaVu Sans"]

DANGER, DANGER_DARK = "#D7263D", "#6E0D1B"
WASTE, WASTE_TXT = "#EBA937", "#A9670A"
GREY, INK, MUTED, COLTXT = "#8A8A8A", "#161616", "#5E5E5E", "#333333"

NAMES = {"Jev": "Jev (hosted)", "Qwen3": "Qwen3-235B*", "Mistral": "Mistral Small 3.2*",
         "gpt-oss-120b": "gpt-oss-120b*", "gpt-oss-20b": "gpt-oss-20b*", "Llama": "Llama-3.1-8B*",
         "GLiClass": "GLiClass (CPU)", "vela3": "vela3 (CPU)", "d3-lite": "d3-lite (CPU)",
         "NadirClaw": "NadirClaw (CPU)"}

rows = []
for r in json.load(open(os.path.join(HERE, "counts.json")))["rows"]:
    if not r["mode"].startswith("rules"):
        continue
    n = r["n_decisions"]
    rows.append(dict(
        name=next(v for k, v in NAMES.items() if r["router"].startswith(k)),
        right=r["n_correct"] / n * 100,
        weak=r["n_under"] / n * 100,         # sent to a weaker tier than needed
        strong=r["n_over"] / n * 100,        # sent to a pricier tier than needed
        danger=r["n_hard_to_cheap"] / n * 100,     # hard task -> cheapest tier, per 100 requests
        cost=r["cost_sum_usd"] / n * 1000, lat=r["lat_p50_ms"]))
mx = max(r["cost"] for r in rows)   # most expensive router = 100% (taken over all 10)
for r in rows:
    r["rel"] = r["cost"] / mx * 100
SHOW = ["Qwen3-235B*", "Mistral Small 3.2*", "gpt-oss-120b*", "gpt-oss-20b*", "Jev (hosted)",
        "GLiClass (CPU)", "Llama-3.1-8B*"]
hidden = [r for r in rows if r["name"] not in SHOW]          # vela3, d3-lite, NadirClaw
rows = sorted([r for r in rows if r["name"] in SHOW], key=lambda r: SHOW.index(r["name"]))
max_weak = max(r["weak"] for r in rows)

W, H = 1080, 1350
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
# everything below is in pixels, y grows downwards
LM, RM = 50, W - 50

def t(x, y, s, **kw):
    kw.setdefault("va", "top"); kw.setdefault("color", INK)
    ax.text(x, y, s, **kw)

def box(x, y, w, h, col):
    ax.add_patch(plt.Rectangle((x, y), w, h, color=col, lw=0))

# headline + subhead
t(LM, 36, "Qwen3, Mistral and Jev rarely pick a model\nthat's too weak. Their misses mostly waste money.",
  fontsize=29, fontweight="bold", linespacing=1.15)
t(LM, 158, f"Qwen3-235B gets 85 of 100 right. Its fee is the highest, yet only\n"
           f"${mx:.3f} per 1,000 decisions. Cheaper routers save cents, but send\n"
           f"up to {max_weak:.0f} in 100 tasks to a model that is too weak.",
  fontsize=19, color="#333333", linespacing=1.3)

# legend in plain words
def key(x, y, col, title, tcol, body):
    box(x, y + 5, 26, 26, col)
    t(x + 38, y, title, fontsize=21, fontweight="bold", color=tcol)
    t(x + 38, y + 36, body, fontsize=17, linespacing=1.2)
key(LM, 300, DANGER, "Too weak", DANGER, "a hard task gets a cheap\nmodel (bad code, rework)")
key(560, 300, WASTE, "Too strong", WASTE_TXT, "an easy task gets an expensive\nmodel (wasted money)")
box(LM, 414, 26, 26, DANGER_DARK)
t(LM + 38, 412, "dark tip = hard task sent to the cheapest model", fontsize=17)

# scale: units (per 100 requests) -> px around a centre line
CX, U = 500, 10.5
X = lambda v: CX + v * U
HDR = 474
t(LM, HDR, "% right", fontsize=16, color=COLTXT)
t(CX, HDR, "mistakes per 100 requests, with the 2 rules", fontsize=16, color=COLTXT, ha="center")
t(RM, HDR, "cost · time", fontsize=16, color=COLTXT, ha="right")

TOP, ROW, BH = 516, 92, 28
for i, r in enumerate(rows):
    y0 = TOP + i * ROW                # name line top
    yb = y0 + 56                      # bar centre
    t(LM, y0, r["name"], fontsize=20, fontweight="bold")
    t(LM, yb, f"{r['right']:.0f}", fontsize=25, fontweight="bold", color=GREY, va="center")
    cost_lbl = "0%" if r["cost"] == 0 else f"{r['rel']:.0f}%"
    lat_lbl = f"{r['lat']/1000:.1f} s" if r["lat"] >= 1000 else f"{r['lat']:.0f} ms"
    t(RM, yb, f"{cost_lbl} · {lat_lbl}", fontsize=18, color=COLTXT, va="center", ha="right")
    box(X(-r["weak"]), yb - BH / 2, r["weak"] * U, BH, DANGER)
    box(X(-r["weak"]), yb - BH / 2, r["danger"] * U, BH, DANGER_DARK)
    t(X(-r["weak"]) - 8, yb, f"{r['weak']:.0f}", fontsize=20, fontweight="bold", color=DANGER, va="center", ha="right")
    box(CX, yb - BH / 2, r["strong"] * U, BH, WASTE)
    t(X(r["strong"]) + 8, yb, f"{r['strong']:.0f}", fontsize=20, fontweight="bold", color=WASTE_TXT, va="center")
ax.plot([CX, CX], [TOP + 26, TOP + ROW * len(rows) - 4], color=INK, lw=1.4)

# hidden routers + notes + footer
fy = TOP + ROW * len(rows) + 6
lo, hi = min(r["right"] for r in hidden), max(r["right"] for r in hidden)
t(LM, fy, f"Three other CPU classifiers: {lo:.0f} to {hi:.0f}% right", fontsize=17, color=MUTED)
t(LM, fy + 36, f"Cost: priciest router = 100% (${mx:.4f} per 1,000). CPU: hardware not counted. Time: median.",
  fontsize=15, color=MUTED)
t(LM, H - 28, "67 one line coding requests, 3 runs each. Labels are my judgement; gaps under about 10 points are\n"
              "mostly noise. * open-weight model via OpenRouter, as a stand in for self-hosting.",
  fontsize=14.5, color=MUTED, linespacing=1.35, va="bottom")

fig.canvas.draw()
_r = fig.canvas.get_renderer()
for _t in ax.texts:  # sanity check: nothing outside the canvas
    _b = _t.get_window_extent(_r)
    if _b.x0 < 0 or _b.x1 > W or _b.y0 < 0 or _b.y1 > H:
        print("CLIPPED:", _t.get_text()[:40], _b)
fig.savefig(os.path.join(HERE, "chart_errors.png"), dpi=100, facecolor="white")
for r in rows:
    print(f"{r['name']:20s} right {r['right']:.1f} weak {r['weak']:.1f} strong {r['strong']:.1f} "
          f"danger {r['danger']:.1f} cost {r['rel']:.0f}% lat {r['lat']:.0f}ms")
