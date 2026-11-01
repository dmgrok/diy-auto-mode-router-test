"""Router accuracy vs cost per 1,000 decisions, with David's two rules (7 routers shown).
Styled after Artificial Analysis' 'Index vs Cost per Task' scatter.
Reads counts.json (raw integer counts from score_v3.py) next to this file, so every
percentage is rounded once from exact counts; writes chart_pareto.png (1080x1350, portrait)."""
import json, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/truetype/sand-box/google/Be Vietnam Pro"
for w in ("Regular", "Medium", "Bold"):
    p = os.path.join(FONT_DIR, f"BeVietnamPro-{w}.ttf")
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams["font.family"] = ["Be Vietnam Pro", "DejaVu Sans"]

DANGER = "#D7263D"
INK, MUTED, GRID = "#161616", "#666666", "#E6E6E6"
TYPE_COL = {"hosted": "#1F6FD1", "openrouter": "#7A3FC4", "cpu": "#3A3A3A"}
TYPE_LBL = {"hosted": "Hosted SaaS", "openrouter": "Open-weight via OpenRouter*", "cpu": "Local CPU"}

NAMES = {"Jev": "Jev (hosted)", "Qwen3": "Qwen3-235B*", "Mistral": "Mistral Small 3.2*",
         "gpt-oss-120b": "gpt-oss-120b*", "gpt-oss-20b": "gpt-oss-20b*", "Llama": "Llama-3.1-8B*",
         "GLiClass": "GLiClass (CPU)", "vela3": "vela3 (CPU)", "d3-lite": "d3-lite (CPU)",
         "NadirClaw": "NadirClaw (CPU)"}

rows = []
for r in json.load(open(os.path.join(HERE, "counts.json")))["rows"]:
    if not r["mode"].startswith("rules"):
        continue
    n = r["n_decisions"]
    name = next(v for k, v in NAMES.items() if r["router"].startswith(k))
    kind = "hosted" if r["group"] == "Hosted closed" else ("cpu" if "local CPU" in r["router"] else "openrouter")
    rows.append(dict(
        name=name, kind=kind,
        right=r["n_correct"] / n * 100,
        weak=r["n_under"] / n * 100,         # sent to a weaker tier than needed
        danger=r["n_hard_to_cheap"] / n * 100,     # hard task -> cheapest tier, per 100 requests
        cost=r["cost_sum_usd"] / n * 1000, lat=r["lat_p50_ms"]))
mx = max(r["cost"] for r in rows)   # most expensive router = 100%
for r in rows:
    r["rel"] = r["cost"] / mx * 100
SHOW = ["Qwen3-235B*", "Mistral Small 3.2*", "gpt-oss-120b*", "gpt-oss-20b*", "Jev (hosted)",
        "GLiClass (CPU)", "Llama-3.1-8B*"]
rows = [r for r in rows if r["name"] in SHOW]

# the dotted line: routers nobody else beats on both price and accuracy
def beaten(a):
    return any(b is not a and b["cost"] <= a["cost"] and b["right"] >= a["right"]
               and (b["cost"] < a["cost"] or b["right"] > a["right"]) for b in rows)
front = sorted([r for r in rows if not beaten(r)], key=lambda r: r["cost"])

# x mapping: log10(cost) for API routers; CPU ($0) gets its own band at the far left
XMIN, XMAX = math.log10(mx * 0.08), math.log10(mx * 3.6)
BAND_L, BAND_R = XMIN - 0.40, XMIN - 0.10      # local band, then a visible break
CPU_X = (BAND_L + BAND_R) / 2
def X(r):
    return CPU_X if r["cost"] == 0 else math.log10(r["cost"])

W, H = 1080, 1350
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0.105, 0.205, 0.865, 0.49])
YMIN, YMAX = 58, 91
ax.set_xlim(BAND_L - 0.02, XMAX); ax.set_ylim(YMIN, YMAX)

# local band
ax.add_patch(plt.Rectangle((BAND_L, YMIN), BAND_R - BAND_L, YMAX - YMIN, color="#EFEFEF", lw=0, zorder=0))
ax.text(CPU_X, YMAX - 1.0, "Runs\nlocally\n$0 API", fontsize=16, color="#444444", ha="center",
        va="top", linespacing=1.15, zorder=1)
for xb in (BAND_R + 0.02, BAND_R + 0.05):   # axis break marks
    ax.plot([xb - 0.012, xb + 0.012], [YMIN - 0.6, YMIN + 0.6], color=INK, lw=1.5, clip_on=False, zorder=5)

ticks_rel = [10, 25, 50, 100]
ax.set_xticks([CPU_X] + [math.log10(mx * t / 100) for t in ticks_rel])
ax.set_xticklabels(["$0"] + [f"${mx * t / 100:.3f}\n{t}%" for t in ticks_rel], fontsize=17)
ax.set_yticks(range(60, 91, 10))
ax.set_yticklabels([f"{v}%" for v in range(60, 91, 10)], fontsize=18)
ax.grid(axis="y", color=GRID, lw=1, zorder=0)
for v in [math.log10(mx * t / 100) for t in ticks_rel]:
    ax.axvline(v, color=GRID, lw=1, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.spines["bottom"].set_color("#BBBBBB"); ax.spines["left"].set_color("#BBBBBB")
ax.tick_params(colors=INK, length=0, pad=8)
ax.set_xlabel("Router cost per 1,000 decisions (USD, log scale)\nand % of the most expensive router",
              fontsize=17, color=INK, labelpad=10, linespacing=1.25)
ax.set_ylabel("Routed right (accuracy)", fontsize=18, color=INK, labelpad=8)

# dotted line
ax.plot([X(r) for r in front], [r["right"] for r in front], ls=(0, (1.2, 2.4)), lw=3,
        color=INK, zorder=2, dash_capstyle="round")

# one plain dot per router, coloured by type
for r in rows:
    ax.scatter(X(r), r["right"], s=220, color=TYPE_COL[r["kind"]], edgecolor="white", lw=2, zorder=4)

# labels (offsets in points): name + % right, red too-weak figure underneath
OFF = {"Qwen3-235B*": (10, 34, "left"), "Mistral Small 3.2*": (-30, 52, "right"),
       "gpt-oss-120b*": (12, -26, "left"), "gpt-oss-20b*": (-10, 40, "center"),
       "Jev (hosted)": (-16, -16, "right"), "Llama-3.1-8B*": (14, -12, "left"),
       "GLiClass (CPU)": (14, -16, "left")}
LEADER = {"Qwen3-235B*", "Mistral Small 3.2*"}
LS = 24   # gap between name line and red line, points
for r in rows:
    dx, dy, ha = OFF[r["name"]]
    ax.annotate(f"{r['name']}  {r['right']:.0f}%", (X(r), r["right"]), xytext=(dx, dy),
                textcoords="offset points", ha=ha, va="center", fontsize=18, fontweight="bold",
                color=INK, zorder=6)
    ax.annotate(f"{r['weak']:.0f}% too weak", (X(r), r["right"]), xytext=(dx, dy - LS),
                textcoords="offset points", ha=ha, va="center", fontsize=16, color=DANGER, zorder=6)
    if r["name"] in LEADER:  # short leader line from the dot to its label block
        ax.annotate("", (X(r), r["right"]), xytext=(dx, dy - LS - 10), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", color="#888888", lw=1.2, shrinkA=0, shrinkB=7), zorder=5)

# GLiClass note by the grey band
ax.text(BAND_L + 0.03, 62.6, "GLiClass is on the line only\nbecause hardware isn't counted", fontsize=14.5,
        color=MUTED, style="italic", linespacing=1.2, ha="left", va="top", zorder=6)

# Jev latency callout
jev = next(r for r in rows if r["kind"] == "hosted")
fastest = min(rows, key=lambda r: r["lat"])
if fastest is jev:
    nxt = sorted(r["lat"] for r in rows)[1]
    ax.annotate(f"{jev['lat']:.0f} ms, fastest\n({nxt / jev['lat']:.0f}× quicker than the next)",
                (X(jev), jev["right"]), xytext=(26, -92), textcoords="offset points",
                fontsize=15.5, color=TYPE_COL["hosted"], ha="left", va="center", linespacing=1.2,
                arrowprops=dict(arrowstyle="-", color=TYPE_COL["hosted"], lw=1.3, shrinkA=4, shrinkB=8), zorder=6)

# ---- headline, subtitle, legend, footer (figure coords) ----
fig.text(0.045, 0.972, "Paying more mostly buys fewer tasks\nsent to a model too weak for them.",
         fontsize=31, fontweight="bold", color=INK, va="top", linespacing=1.15)
fig.text(0.045, 0.868, "Each dot is a router. Higher = more coding tasks routed to the right\n"
         "model. Further right = higher router fee. Red = share of tasks sent\n"
         "to a model too weak for them.",
         fontsize=18, color="#333333", va="top", linespacing=1.3)
handles = [Line2D([], [], ls="", marker="o", ms=14, color=TYPE_COL[k], mec="white", label=TYPE_LBL[k])
           for k in ("hosted", "openrouter", "cpu")]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.035, 0.778), ncol=3, frameon=False,
           fontsize=16.5, handletextpad=0.3, columnspacing=1.2)
dl = fig.add_axes([0.047, 0.716, 0.9, 0.022]); dl.axis("off"); dl.set_xlim(0, 1); dl.set_ylim(0, 1)
dl.plot([0.0, 0.05], [0.5, 0.5], ls=(0, (1.2, 2.4)), lw=3, color=INK, dash_capstyle="round")
dl.text(0.065, 0.5, "routers nobody beats on both price and accuracy", fontsize=16.5, va="center", color=INK)

fig.text(0.045, 0.018,
         "67 one line coding requests, 3 runs each, my 2 rules. Labels are my judgement; gaps under about 10 points\n"
         f"are mostly noise. * open-weight, via OpenRouter as a stand in for self-hosting. 100% = ${mx:.4f} per 1,000.",
         fontsize=13.5, color=MUTED, va="bottom", linespacing=1.35)

fig.canvas.draw()
_r = fig.canvas.get_renderer()
texts = ax.texts + fig.texts + dl.texts
for _t in texts:
    _b = matplotlib.text.Text.get_window_extent(_t, _r)
    if _b.x0 < 0 or _b.x1 > W or _b.y0 < 0 or _b.y1 > H:
        print("CLIPPED:", _t.get_text()[:40], _b)
_bb = [(t.get_text()[:25], matplotlib.text.Text.get_window_extent(t, _r)) for t in texts if t.get_text()]
for i in range(len(_bb)):
    for j in range(i + 1, len(_bb)):
        if _bb[i][1].overlaps(_bb[j][1]):
            print("OVERLAP:", _bb[i][0], "|", _bb[j][0])
fig.savefig(os.path.join(HERE, "chart_pareto.png"), dpi=100, facecolor="white")
print("On the dotted line:", [r["name"] for r in front])
for r in sorted(rows, key=lambda r: -r["right"]):
    print(f"{r['name']:20s} acc {r['right']:.1f} weak {r['weak']:.1f} danger {r['danger']:.1f} "
          f"cost ${r['cost']:.4f} ({r['rel']:.0f}%) lat {r['lat']:.0f}ms")
