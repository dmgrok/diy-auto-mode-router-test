"""Router mistakes per 100 requests, with David's two rules.
Reads summary.csv next to this file; writes chart_errors.png (1080x1350)."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/truetype/sand-box/google/Be Vietnam Pro"
for w in ("Regular", "Medium", "Bold"):
    p = os.path.join(FONT_DIR, f"BeVietnamPro-{w}.ttf")
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams["font.family"] = ["Be Vietnam Pro", "DejaVu Sans"]

N_HARD = 22  # frontier-labelled queries (REPORT.md: 23 cheap / 22 mid / 22 frontier)
DANGER, DANGER_DARK = "#D7263D", "#6E0D1B"
WASTE, WASTE_TXT = "#EBA937", "#A9670A"
GREY, INK, MUTED = "#9A9A9A", "#161616", "#666666"

NAMES = {"Jev": "Jev (hosted)", "Qwen3": "Qwen3-235B*", "Mistral": "Mistral Small 3.2*",
         "gpt-oss-120b": "gpt-oss-120b*", "gpt-oss-20b": "gpt-oss-20b*", "Llama": "Llama-3.1-8B*",
         "GLiClass": "GLiClass (CPU)", "vela3": "vela3 (CPU)", "d3-lite": "d3-lite (CPU)",
         "NadirClaw": "NadirClaw (CPU)"}

rows = []
for r in csv.DictReader(open(os.path.join(HERE, "summary.csv"))):
    if r["group"] == "Appendix" or not r["mode"].startswith("rules"):
        continue
    n, runs = int(r["n_decisions"]), int(r["runs"])
    rows.append(dict(
        name=next(v for k, v in NAMES.items() if r["router"].startswith(k)),
        right=float(r["accuracy"]) * 100,
        weak=float(r["under_routing"]) * 100,      # sent to a weaker tier than needed
        strong=float(r["over_routing"]) * 100,     # sent to a pricier tier than needed
        # hard_to_cheap is a share of hard decisions -> count -> per 100 requests
        danger=round(float(r["hard_to_cheap"]) * N_HARD * runs) / n * 100,
        cost=float(r["cost_per_1k_usd"]), lat=float(r["lat_p50_ms"])))
mx = max(r["cost"] for r in rows)
for r in rows:
    r["rel"] = r["cost"] / mx * 100
rows.sort(key=lambda r: (-r["right"], r["weak"]))

W, H = 1080, 1350
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
# everything below is in pixels, y grows downwards
LM, RM = 54, W - 54

def t(x, y, s, **kw):
    kw.setdefault("va", "top"); kw.setdefault("color", INK)
    ax.text(x, y, s, **kw)

def box(x, y, w, h, col):
    ax.add_patch(plt.Rectangle((x, y), w, h, color=col, lw=0))

# headline + subhead
t(LM, 40, "Qwen3, Mistral and Jev rarely pick a model\nthat's too weak. Their misses mostly waste money.",
  fontsize=28, fontweight="bold", linespacing=1.15)
t(LM, 160, f"Qwen3-235B gets 85 of 100 right. Its fee is the highest, yet only\n"
           f"${mx:.3f} per 1,000 decisions. Cheaper routers save cents, but send\n"
           "up to 36 in 100 tasks to a model that is too weak.",
  fontsize=17, color="#333333", linespacing=1.3)

# legend in plain words
def key(x, y, col, title, tcol, body):
    box(x, y + 4, 24, 24, col)
    t(x + 36, y, title, fontsize=19, fontweight="bold", color=tcol)
    t(x + 36, y + 34, body, fontsize=15, linespacing=1.2)
key(LM, 290, DANGER, "Too weak", DANGER, "a hard task gets a cheap model\n(bad code, rework)")
key(560, 290, WASTE, "Too strong", WASTE_TXT, "an easy task gets an expensive\nmodel (wasted money)")
box(LM, 398, 24, 24, DANGER_DARK)
t(LM + 36, 396, "Darkest red = worst case: a hard task sent to the CHEAP model", fontsize=15)

# scale: units (per 100 requests) -> px around a centre line
CX, U = 520, 9.6
X = lambda v: CX + v * U
HDR = 456
t(LM, HDR, "right", fontsize=14, color=MUTED)
t(CX, HDR, "mistakes per 100 requests, with the 2 rules", fontsize=14, color=MUTED, ha="center")
t(RM, HDR, "cost · time", fontsize=14, color=MUTED, ha="right")

TOP, ROW, BH = 494, 68, 22
for i, r in enumerate(rows):
    y0 = TOP + i * ROW                # name line top
    yb = y0 + 46                      # bar centre
    t(LM, y0, r["name"], fontsize=17, fontweight="bold")
    t(LM, yb, f"{r['right']:.0f}", fontsize=21, fontweight="bold", color=GREY, va="center")
    cost_lbl = "0%" if r["cost"] == 0 else f"{r['rel']:.0f}%"
    lat_lbl = f"{r['lat']/1000:.1f} s" if r["lat"] >= 1000 else f"{r['lat']:.0f} ms"
    t(RM, yb, f"{cost_lbl} · {lat_lbl}", fontsize=15, color=MUTED, va="center", ha="right")
    box(X(-r["weak"]), yb - BH / 2, r["weak"] * U, BH, DANGER)
    box(X(-r["weak"]), yb - BH / 2, r["danger"] * U, BH, DANGER_DARK)
    t(X(-r["weak"]) - 7, yb, f"{r['weak']:.0f}", fontsize=17, fontweight="bold", color=DANGER, va="center", ha="right")
    box(CX, yb - BH / 2, r["strong"] * U, BH, WASTE)
    t(X(r["strong"]) + 7, yb, f"{r['strong']:.0f}", fontsize=17, fontweight="bold", color=WASTE_TXT, va="center")
ax.plot([CX, CX], [TOP + 22, TOP + ROW * len(rows) - 4], color=INK, lw=1.3)

# notes + footer
fy = TOP + ROW * len(rows) + 12
t(LM, fy, f"Cost = router fee per decision, most expensive = 100% (${mx:.4f} per 1,000).\n"
          "CPU = runs locally: 0% API cost, hardware not counted. Time = median latency.",
  fontsize=13.5, color=MUTED, linespacing=1.3)
t(LM, fy + 64, "67 one-line coding requests, 3 runs each. Labels are my judgement; gaps under ~10\n"
               "points are mostly noise. * open-weight model called via OpenRouter as a stand-in\n"
               "for self-hosting.", fontsize=13.5, color=MUTED, linespacing=1.3)

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
