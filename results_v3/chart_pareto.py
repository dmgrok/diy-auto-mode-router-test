"""Router accuracy vs cost per 1,000 decisions, with David's two rules.
Styled after Artificial Analysis' 'Index vs Cost per Task' scatter.
Reads summary.csv next to this file; writes chart_pareto.png (1200x1000)."""
import csv, os, math
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

N_HARD = 22  # frontier-labelled queries (REPORT.md: 23 cheap / 22 mid / 22 frontier)
DANGER = "#D7263D"
INK, MUTED, GRID = "#161616", "#666666", "#E6E6E6"
TYPE_COL = {"hosted": "#1F6FD1", "openrouter": "#7A3FC4", "cpu": "#3A3A3A"}
TYPE_LBL = {"hosted": "Hosted SaaS", "openrouter": "Open-weight via OpenRouter*", "cpu": "Local CPU"}

NAMES = {"Jev": "Jev (hosted)", "Qwen3": "Qwen3-235B*", "Mistral": "Mistral Small 3.2*",
         "gpt-oss-120b": "gpt-oss-120b*", "gpt-oss-20b": "gpt-oss-20b*", "Llama": "Llama-3.1-8B*",
         "GLiClass": "GLiClass (CPU)", "vela3": "vela3 (CPU)", "d3-lite": "d3-lite (CPU)",
         "NadirClaw": "NadirClaw (CPU)"}

rows = []
for r in csv.DictReader(open(os.path.join(HERE, "summary.csv"))):
    if r["group"] == "Appendix" or not r["mode"].startswith("rules"):
        continue
    n, runs = int(r["n_decisions"]), int(r["runs"])
    name = next(v for k, v in NAMES.items() if r["router"].startswith(k))
    kind = "hosted" if r["group"] == "Hosted closed" else ("cpu" if "local CPU" in r["router"] else "openrouter")
    rows.append(dict(
        name=name, kind=kind,
        right=float(r["accuracy"]) * 100,
        weak=float(r["under_routing"]) * 100,      # sent to a weaker tier than needed
        danger=round(float(r["hard_to_cheap"]) * N_HARD * runs) / n * 100,
        cost=float(r["cost_per_1k_usd"]), lat=float(r["lat_p50_ms"])))
mx = max(r["cost"] for r in rows)
for r in rows:
    r["rel"] = r["cost"] / mx * 100

# Pareto front: nobody else is at least as cheap AND at least as accurate (and better on one)
def dominated(a):
    return any(b is not a and b["cost"] <= a["cost"] and b["right"] >= a["right"]
               and (b["cost"] < a["cost"] or b["right"] > a["right"]) for b in rows)
front = sorted([r for r in rows if not dominated(r)], key=lambda r: r["cost"])

# x mapping: log10(cost) for API routers; CPU ($0) gets its own band at the far left
XMIN, XMAX = math.log10(mx * 0.07), math.log10(mx * 2.1)
BAND_L, BAND_R = XMIN - 0.42, XMIN - 0.12      # local band, then a visible break
CPU_X = (BAND_L + BAND_R) / 2
def X(r):
    return CPU_X if r["cost"] == 0 else math.log10(r["cost"])

W, H = 1200, 1000
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0.085, 0.195, 0.865, 0.53])
YMIN, YMAX = 45, 92
ax.set_xlim(BAND_L - 0.03, XMAX); ax.set_ylim(YMIN, YMAX)

# sweet-spot quadrant: >= 75% right, <= half the top router's cost (incl. the local band)
Q_ACC, Q_REL = 75, 50
ax.add_patch(plt.Rectangle((BAND_L, YMIN), BAND_R - BAND_L, YMAX - YMIN, color="#EFEFEF", lw=0, zorder=0))
ax.add_patch(plt.Rectangle((BAND_L - 0.03, Q_ACC), math.log10(mx * Q_REL / 100) - BAND_L + 0.03,
                           YMAX - Q_ACC, color="#BFE6B3", alpha=0.6, lw=0, zorder=0.5))
ax.text(BAND_R + 0.08, YMAX - 1.2, "Most attractive: ≥75% right, ≤50% of the cost",
        fontsize=14, color="#2E7D32", fontweight="bold", va="top", zorder=1)
# local band
ax.text(CPU_X, YMAX - 1.8, "Runs locally\n$0 API\n(hardware\nnot counted)", fontsize=12,
        color="#444444", ha="center", va="top", linespacing=1.1, zorder=1)
# axis break marks
for xb in (BAND_R + 0.02, BAND_R + 0.05):
    ax.plot([xb - 0.012, xb + 0.012], [YMIN - 0.9, YMIN + 0.9], color=INK, lw=1.4, clip_on=False, zorder=5)

ticks_rel = [10, 25, 50, 100]
ax.set_xticks([CPU_X] + [math.log10(mx * t / 100) for t in ticks_rel])
ax.set_xticklabels(["$0"] + [f"${mx * t / 100:.3f}\n{t}%" for t in ticks_rel], fontsize=13.5)
ax.set_yticks(range(50, 91, 10))
ax.set_yticklabels([f"{v}%" for v in range(50, 91, 10)], fontsize=14)
ax.grid(axis="y", color=GRID, lw=1, zorder=0)
for v in [math.log10(mx * t / 100) for t in ticks_rel]:
    ax.axvline(v, color=GRID, lw=1, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.spines["bottom"].set_color("#BBBBBB"); ax.spines["left"].set_color("#BBBBBB")
ax.tick_params(colors=INK, length=0, pad=8)
ax.set_xlabel("Router cost per 1,000 routing decisions (USD, log scale) · % of the most expensive",
              fontsize=14.5, color=INK, labelpad=10)
ax.set_ylabel("Routed right (accuracy)", fontsize=15, color=INK, labelpad=8)

# Pareto line
ax.plot([X(r) for r in front], [r["right"] for r in front], ls=(0, (1.2, 2.2)), lw=2.6,
        color=INK, zorder=2, dash_capstyle="round")

# markers: one plain dot per router, coloured by type
for r in rows:
    x, y = X(r), r["right"]
    ax.scatter(x, y, s=130, color=TYPE_COL[r["kind"]], edgecolor="white", lw=1.5, zorder=4)

# labels (offsets in points)
OFF = {"Qwen3-235B*": (14, 30, "left"), "Mistral Small 3.2*": (-26, 40, "right"),
       "gpt-oss-120b*": (14, -20, "left"), "gpt-oss-20b*": (-12, 24, "right"),
       "Jev (hosted)": (-16, -26, "right"), "Llama-3.1-8B*": (18, -14, "left"),
       "GLiClass (CPU)": (16, -10, "left"), "vela3 (CPU)": (16, 4, "left"),
       "d3-lite (CPU)": (16, -6, "left"), "NadirClaw (CPU)": (16, 0, "left")}
LEADER = {"Qwen3-235B*", "Mistral Small 3.2*"}
for r in rows:
    dx, dy, ha = OFF[r["name"]]
    lbl = f"{r['name']}  {r['right']:.0f}%"
    ax.annotate(lbl, (X(r), r["right"]), xytext=(dx, dy), textcoords="offset points",
                ha=ha, va="center", fontsize=14.5, fontweight="bold", color=INK, zorder=6)
    if r["name"] in LEADER:  # short leader line from dot to the label block
        ax.annotate("", (X(r), r["right"]), xytext=(dx, dy - 26),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", color="#888888", lw=1, shrinkA=0, shrinkB=5), zorder=5)
    ax.annotate(f"{r['weak']:.0f}% too weak", (X(r), r["right"]), xytext=(dx, dy - 17),
                textcoords="offset points", ha=ha, va="center", fontsize=12, color=DANGER, zorder=6)

# Jev latency callout
jev = next(r for r in rows if r["kind"] == "hosted")
fastest = min(rows, key=lambda r: r["lat"])
if fastest is jev:
    nxt = sorted(r["lat"] for r in rows)[1]
    ax.annotate(f"{jev['lat']:.0f} ms, fastest\n({nxt / jev['lat']:.0f}× quicker than the next)",
                (X(jev), jev["right"]), xytext=(14, -150), textcoords="offset points",
                fontsize=12.5, color=TYPE_COL["hosted"], ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=TYPE_COL["hosted"], lw=1.2), zorder=6)

# ---- headline, subtitle, legend, footnote (figure coords) ----
best = max(rows, key=lambda r: r["right"])
sweet = [r for r in rows if r["right"] >= Q_ACC and r["rel"] <= Q_REL]
s = sweet[0] if sweet else front[1]
fig.text(0.035, 0.975, f"{s['name'].rstrip('*')} is the sweet spot: {s['right']:.0f}% right for "
         f"{s['rel']:.0f}% of the cost.\nThe catch: it sends {s['weak']:.0f}% of tasks to a model too weak for them.",
         fontsize=24, fontweight="bold", color=INK, va="top", linespacing=1.15)
front_names = ", ".join(r["name"].rstrip("*").replace(" (CPU)", "") for r in front)
fig.text(0.035, 0.872, f"Up and left is better. The dotted line links the routers nobody beats on both price\nand accuracy: {front_names}.\n"
         "Paying more mostly buys fewer tasks sent to a model too weak for them (red figures).",
         fontsize=15.5, color="#333333", va="top", linespacing=1.25)

# legend row
handles = [Line2D([], [], ls="", marker="o", ms=11, color=TYPE_COL[k], mec="white", label=TYPE_LBL[k])
           for k in ("hosted", "openrouter", "cpu")]
handles += [plt.Rectangle((0, 0), 1, 1, color="#D6F0CF", label="Most attractive"),
            Line2D([], [], ls=(0, (1.2, 2.2)), lw=2.6, color=INK, label="Pareto line")]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.03, 0.768), ncol=5, frameon=False,
           fontsize=13.5, handletextpad=0.4, columnspacing=1.3)

fig.text(0.035, 0.022,
         f"67 one-line coding requests, 3 runs each, with my 2 routing rules. Labels are my judgement; gaps under ~10 points are\n"
         f"mostly noise. * open-weight model called via OpenRouter as a stand-in for self-hosting. 100% = ${mx:.4f} per 1,000 decisions.",
         fontsize=12, color=MUTED, va="bottom", linespacing=1.35)

fig.canvas.draw()
_r = fig.canvas.get_renderer()
for _t in fig.texts + ax.texts:
    _b = _t.get_window_extent(_r)
    if _b.x0 < 0 or _b.x1 > W or _b.y0 < 0 or _b.y1 > H:
        print("CLIPPED:", _t.get_text()[:40], _b)
_bb = [(t.get_text()[:25], matplotlib.text.Text.get_window_extent(t, _r)) for t in ax.texts + fig.texts]  # text only, no arrows
for i in range(len(_bb)):
    for j in range(i + 1, len(_bb)):
        if _bb[i][1].overlaps(_bb[j][1]):
            print("OVERLAP:", _bb[i][0], "|", _bb[j][0])
fig.savefig(os.path.join(HERE, "chart_pareto.png"), dpi=100, facecolor="white")
print("Pareto:", [r["name"] for r in front])
for r in sorted(rows, key=lambda r: -r["right"]):
    print(f"{r['name']:20s} acc {r['right']:.1f} weak {r['weak']:.1f} danger {r['danger']:.1f} "
          f"cost ${r['cost']:.4f} ({r['rel']:.0f}%) lat {r['lat']:.0f}ms")
