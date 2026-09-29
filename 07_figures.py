"""Step 7 — Figures 1–3 and Supplementary Figure 1 (record flow) from data/results.json
(Okabe–Ito palette; PNG 600 dpi, SVG and PDF).

    python 07_figures.py
"""
import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as tk
import config as C

R = json.loads((C.DATA / "results.json").read_text())
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif"], "font.size": 9,
                     "svg.fonttype": "none", "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GREY = "#0072B2", "#E69F00", "#999999"
OUT = C.DATA / "figures"; OUT.mkdir(exist_ok=True)


def save(fig, name):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=600, bbox_inches="tight")
    plt.close(fig)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** .5 / d
    return (c - h) * 100, (c + h) * 100


# Figure 1 — annual volume, full calendar years 2015–2025, log scale
yrs = sorted(int(y) for y in R["annual_records"] if 2015 <= int(y) <= 2025); vals = [R["annual_records"][str(y)] for y in yrs]
fig, ax = plt.subplots(figsize=(6.2, 3.2))
ax.plot(yrs, vals, color=BLUE, marker="o", mec="black", mew=.5)
for y, v in zip(yrs, vals): ax.annotate(f"{v:,}", (y, v), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7)
ax.set_yscale("log"); ax.yaxis.set_major_formatter(tk.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.set_xticks(yrs); ax.set_xlabel("Year"); ax.set_ylabel("Posts and comments per year (log scale)")
save(fig, "Figure1_discussion_volume")

# Figure 2 — yes / no / mixed by peptide category, 95% CI
titles = {"believed_effective": "Believed effective", "would_use_again": "Would use again", "would_recommend": "Would recommend"}
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.8), sharey=True)
for ax, (field, groups) in zip(axs, R["figure2"].items()):
    for j, (g, d) in enumerate(groups.items()):
        y, n, c = len(groups) - 1 - j, d["n"], d["count"]
        if not n: continue                                   # no records in this category answered the question
        for k, col, mk, off, lab in [(c.get("yes", 0), BLUE, "o", .22, "Yes"), (c.get("no", 0), ORANGE, "s", 0, "No"),
                                     (n - c.get("yes", 0) - c.get("no", 0), GREY, "^", -.22, "Mixed / other")]:
            lo, hi = wilson(k, n); p = k / n * 100
            ax.errorbar(p, y + off, xerr=[[max(p - lo, 0)], [max(hi - p, 0)]], fmt=mk, color=col, mec="black", mew=.4, ms=5, capsize=2,
                        label=lab if (ax is axs[0] and j == 0) else None)
        ax.text(99, y + .4, f"n={n:,}", ha="right", fontsize=6.5)
    ax.set_title(titles[field]); ax.set_xlim(0, 100); ax.set_xlabel("Records (%)")
    ax.set_yticks(range(len(groups))); ax.set_yticklabels(list(groups)[::-1])
fig.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, -.08)); fig.tight_layout(rect=(0, .04, .97, 1))
save(fig, "Figure2_satisfaction")

# Figure 3 — 13 most frequent adverse-event groups, 95% CI
ae = R["adverse_events"]; top = ae["groups"][:13][::-1]
fig, ax = plt.subplots(figsize=(6.2, 4.2))
for i, g in enumerate(top):
    lo, hi = g["ci95"]
    ax.errorbar(g["pct"], i, xerr=[[max(g["pct"] - lo, 0)], [max(hi - g["pct"], 0)]], fmt="o", color=BLUE, mec="black", mew=.4, ms=5, capsize=2)
    ax.text(hi + .3, i, f"{g['pct']:.1f}% (n={g['records']:,})", va="center", fontsize=7)
ax.set_yticks(range(len(top))); ax.set_yticklabels([g["group"] for g in top])
ax.set_xlabel(f"Records reporting at least one side effect (%; n={ae['n']:,})")
save(fig, "Figure3_adverse_events")

# Supplementary Figure 1 — record flow from retrieval to the analytic sample (numbers from data/flow.json)
F = R["flow"]
LABELS = {"excluded_account": "Excluded: bot, moderator-team\nor deleted accounts",
          "duplicate_text": "Excluded: identical text reposted\nby the same account",
          "no_extraction": "Excluded: no extraction output",
          "not_own_use": "Excluded: not describing the\nauthor's own peptide use",
          "nonpeptide_substance": "Excluded: named substance\nnot a peptide",
          "repeat_user": "Excluded: additional records\nfrom repeat users"}
steps = [(s, F[s]) for s in LABELS if F.get(s)]
fig, ax = plt.subplots(figsize=(6.2, 1.6 + 0.8 * len(steps))); ax.set_axis_off()
top, bottom, x_main, x_side = 0.95, 0.06, 0.30, 0.78
box = dict(boxstyle="square,pad=0.5", fc="white", ec="black", lw=0.8)
ax.text(x_main, top, "Posts and comments retrieved from eight peptide-focused\nand biohacking communities, November 2014 – June 2026\n"
        f"n = {F['retrieved']:,} records", ha="center", va="center", fontsize=8.5, weight="bold", bbox=box, transform=ax.transAxes)
ax.text(x_main, bottom, f"Users analysed (one post or comment per user)\nn = {F['analysed']:,}", ha="center", va="center",
        fontsize=8.5, weight="bold", bbox=box, transform=ax.transAxes)
ax.annotate("", xy=(x_main, bottom + 0.045), xytext=(x_main, top - 0.055), xycoords="axes fraction",
            arrowprops=dict(arrowstyle="-|>", lw=1.2, color="black"))
for i, (s, n) in enumerate(steps):
    y = top - 0.15 - i * (top - bottom - 0.3) / max(len(steps) - 1, 1)
    ax.annotate("", xy=(x_side - 0.17, y), xytext=(x_main, y), xycoords="axes fraction", arrowprops=dict(arrowstyle="-|>", lw=0.9, color="black"))
    ax.text(x_side, y, f"{LABELS[s]}\nn = {n:,} records", ha="center", va="center", fontsize=7.5, bbox=box, transform=ax.transAxes)
ax.text(0.0, -0.02, "Unit of analysis: the user (the earliest eligible post or comment was kept for each user). "
        "Users were identified by Reddit username.", fontsize=7, style="italic", transform=ax.transAxes)
save(fig, "Supplementary_Figure1_flow")
print("figures written to", OUT)
