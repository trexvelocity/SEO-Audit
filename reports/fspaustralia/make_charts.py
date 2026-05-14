"""Generate charts for the FSP Australia SEO audit report (200 DPI)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)

# Brand palette per CLAUDE.md
NAVY = "#1e3a5f"
GOLD = "#b8860b"
GREEN = "#2d6a4f"
AMBER = "#d4740e"
RED = "#c53030"
CREAM = "#faf9f7"
LIGHT_GREY = "#e6e1d8"

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": 10,
    "axes.edgecolor": NAVY,
    "axes.labelcolor": NAVY,
    "xtick.color": "#333",
    "ytick.color": "#333",
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "savefig.facecolor": "white",
    "savefig.dpi": 200,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# -------------------------------------------------------------------------
# 1. Technical SEO scorecard — horizontal bar chart
# -------------------------------------------------------------------------
cats = [
    "Crawlability", "Indexability", "Security", "URL Structure",
    "Mobile", "Core Web Vitals", "Structured Data", "JS Rendering",
]
scores = [70, 45, 60, 88, 78, 70, 40, 95]


def colour(s):
    if s >= 80:
        return GREEN
    if s >= 60:
        return AMBER
    return RED


colours = [colour(s) for s in scores]
fig, ax = plt.subplots(figsize=(8, 4.2))
bars = ax.barh(cats[::-1], scores[::-1], color=colours[::-1], edgecolor=NAVY, linewidth=0.6)
ax.axvline(80, color=GREEN, linestyle="--", linewidth=0.8, alpha=0.7)
ax.axvline(60, color=AMBER, linestyle="--", linewidth=0.8, alpha=0.7)
ax.set_xlim(0, 100)
ax.set_xlabel("Score (0–100)")
ax.set_title("Pillar 1 — Technical SEO Scorecard  (Overall 68/100)", color=NAVY)
for bar, score in zip(bars, scores[::-1]):
    ax.text(score + 1.5, bar.get_y() + bar.get_height() / 2,
            str(score), va="center", color=NAVY, fontsize=9, fontweight="bold")
ax.set_facecolor(CREAM)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
save(fig, "01_technical_scorecard.png")

# -------------------------------------------------------------------------
# 2. Keyword opportunity — current vs target clicks (top 10)
# -------------------------------------------------------------------------
kws = [
    "plastic lockers AU", "plastic lockers", "wheel chocks AU", "fire hose reel cab",
    "post & rail fencing", "caravan wheel chocks", "fire ext. cabinet",
    "school lockers AU", "hdpe lockers", "wheel chocks trucks",
]
current = [70, 95, 120, 65, 55, 35, 25, 30, 80, 45]
opportunity = [110, 220, 145, 180, 115, 140, 110, 85, 35, 75]

x = np.arange(len(kws))
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(x, current, color=NAVY, label="Current clicks/mo (est.)", edgecolor="white")
ax.bar(x, opportunity, bottom=current, color=GOLD, label="Opportunity (+clicks/mo)", edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(kws, rotation=35, ha="right", fontsize=8)
ax.set_ylabel("Monthly clicks")
ax.set_title("Pillar 2 — Top 10 Keyword Opportunity (Current vs. Capturable)", color=NAVY)
ax.legend(loc="upper right", frameon=False)
ax.set_facecolor(CREAM)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
save(fig, "02_keyword_opportunity.png")

# -------------------------------------------------------------------------
# 3. Content gap — FSP vs competitor average
# -------------------------------------------------------------------------
content_cats = [
    "Buying guides", "Comparison\npages", "Case studies",
    "Vertical hubs", "Compliance\ncontent", "FAQ pages",
    "Location pages", "Calculators", "Videos", "Glossary",
]
fsp = [4, 1, 3, 4, 0, 10, 6, 0, 2, 0]
comp = [22, 12, 18, 11, 9, 45, 14, 4, 25, 30]

x = np.arange(len(content_cats))
w = 0.38
fig, ax = plt.subplots(figsize=(9.5, 4.5))
ax.bar(x - w / 2, fsp, w, color=RED, label="FSP Australia", edgecolor="white")
ax.bar(x + w / 2, comp, w, color=GREEN, label="Competitor avg", edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(content_cats, fontsize=8.5)
ax.set_ylabel("Pages")
ax.set_title("Pillar 3 — Content Inventory vs. Competitor Average", color=NAVY)
ax.legend(frameon=False)
ax.set_facecolor(CREAM)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
save(fig, "03_content_gap.png")

# -------------------------------------------------------------------------
# 4. Backlink link-source quality breakdown — donut
# -------------------------------------------------------------------------
labels = ["High-authority\n(.edu/.gov)", "Industry authority",
          "Medium quality", "Low quality", "Toxic / spam"]
sizes = [4, 12, 34, 42, 8]
clrs = [GREEN, NAVY, GOLD, AMBER, RED]

fig, ax = plt.subplots(figsize=(6.5, 4.8))
wedges, texts, autotexts = ax.pie(
    sizes, labels=labels, autopct="%1.0f%%",
    colors=clrs, startangle=90, pctdistance=0.78,
    wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
    textprops=dict(fontsize=9, color=NAVY),
)
for t in autotexts:
    t.set_color("white")
    t.set_fontweight("bold")
    t.set_fontsize(9)
ax.set_title("Pillar 4 — Backlink Source Quality Distribution (est.)", color=NAVY)
save(fig, "04_backlink_quality.png")

# -------------------------------------------------------------------------
# 5. 12-Month traffic growth forecast
# -------------------------------------------------------------------------
months = np.arange(0, 13)
clicks = [5000, 5200, 5500, 6000, 6500, 7200, 8200, 9000, 9700, 10300, 10800, 11200, 11500]
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.fill_between(months, clicks, color=GOLD, alpha=0.25)
ax.plot(months, clicks, color=NAVY, linewidth=2.5, marker="o", markersize=5,
        markerfacecolor=GOLD, markeredgecolor=NAVY)
ax.axhline(5000, color="#999", linestyle=":", linewidth=0.8)
ax.text(0.2, 5050, "Baseline 5,000", color="#666", fontsize=8)
ax.annotate("Phase 1\nFoundation", xy=(1.5, 5350), color=NAVY, fontsize=8.5,
            ha="center", fontweight="bold")
ax.annotate("Phase 2\nContent expansion", xy=(4.5, 6500), color=NAVY, fontsize=8.5,
            ha="center", fontweight="bold")
ax.annotate("Phase 3\nAuthority & scale", xy=(9.5, 9700), color=NAVY, fontsize=8.5,
            ha="center", fontweight="bold")
ax.set_xticks(months)
ax.set_xticklabels(["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"])
ax.set_ylabel("Organic clicks / month")
ax.set_title("12-Month Organic Traffic Forecast  (+130% by Month 12)", color=NAVY)
ax.set_facecolor(CREAM)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
save(fig, "05_traffic_forecast.png")

# -------------------------------------------------------------------------
# 6. AEO/GEO radar — 10 dimensions current vs target
# -------------------------------------------------------------------------
geo_cats = [
    "AI Crawler\nAccess", "E-E-A-T", "Entity SEO",
    "Answer-first\ncontent", "AI Citations", "Voice/\nSpeakable",
    "Brand Entity", "AI Overview", "Trust Signals", "Schema:\nFAQ/HowTo",
]
current_geo = [10, 45, 25, 30, 5, 10, 40, 5, 45, 30]
target_geo = [85, 80, 70, 80, 65, 75, 78, 70, 85, 90]

angles = np.linspace(0, 2 * np.pi, len(geo_cats), endpoint=False).tolist()
current_geo += current_geo[:1]
target_geo += target_geo[:1]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(7.5, 6.5), subplot_kw=dict(polar=True))
ax.plot(angles, current_geo, color=RED, linewidth=2, label="Current (est.)")
ax.fill(angles, current_geo, color=RED, alpha=0.18)
ax.plot(angles, target_geo, color=GREEN, linewidth=2, label="Month-12 target")
ax.fill(angles, target_geo, color=GREEN, alpha=0.15)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(geo_cats, fontsize=8.5, color=NAVY)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#666", fontsize=8)
ax.set_ylim(0, 100)
ax.set_title("Pillar 7 — AEO/GEO Score: 32 → 78 (10 dimensions)",
             color=NAVY, pad=22)
ax.legend(loc="lower right", bbox_to_anchor=(1.18, -0.05), frameon=False, fontsize=9)
ax.grid(color="#ccc", alpha=0.6)
save(fig, "06_aeo_geo_radar.png")

# -------------------------------------------------------------------------
# 7. Roadmap Gantt — Phase 1/2/3
# -------------------------------------------------------------------------
tasks = [
    ("WAF + llms.txt + sitemaps",                 0,  1, GREEN),
    ("Domain consolidation 301s",                 0,  2, GREEN),
    ("Schema deployment (Org/Prod/FAQ)",          0,  2, GREEN),
    ("Quick-win FAQ + buying guides (12 pgs)",    0,  2, GREEN),
    ("Citation cleanup + reseller badges",        0,  2, GREEN),
    ("12 buying guides + 6 vertical hubs",        2,  6, GOLD),
    ("10 case studies",                           3,  6, GOLD),
    ("Trade-press PR (Australian Mining etc.)",   3,  6, GOLD),
    ("Industry × Product matrix (25 pgs)",        4,  8, NAVY),
    ("12 location hubs (LocalBusiness schema)",   5,  9, NAVY),
    ("Compliance / glossary / calculators",       6, 11, NAVY),
    ("Full programmatic matrix completion",       7, 12, NAVY),
]

fig, ax = plt.subplots(figsize=(9.5, 5.2))
for i, (task, start, end, clr) in enumerate(tasks):
    ax.barh(i, end - start, left=start, color=clr, edgecolor="white", height=0.6)
    ax.text(end + 0.15, i, f"M{start}–M{end}", va="center", fontsize=8, color="#444")
ax.set_yticks(range(len(tasks)))
ax.set_yticklabels([t[0] for t in tasks], fontsize=8.5)
ax.invert_yaxis()
ax.set_xlim(0, 13)
ax.set_xticks(range(0, 13))
ax.set_xticklabels([f"M{m}" for m in range(13)])
ax.set_xlabel("Month")
ax.set_title("12-Month Implementation Roadmap (Gantt)", color=NAVY)
ax.axvspan(0, 2, color=GREEN, alpha=0.05)
ax.axvspan(2, 6, color=GOLD, alpha=0.05)
ax.axvspan(6, 12, color=NAVY, alpha=0.05)
ax.text(1, -0.7, "Phase 1: Foundation", color=GREEN, fontweight="bold",
        fontsize=9, ha="center")
ax.text(4, -0.7, "Phase 2: Content Expansion", color=GOLD, fontweight="bold",
        fontsize=9, ha="center")
ax.text(9, -0.7, "Phase 3: Authority & Scale", color=NAVY, fontweight="bold",
        fontsize=9, ha="center")
ax.set_facecolor(CREAM)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
save(fig, "07_roadmap_gantt.png")

print("Charts generated:", sorted(p.name for p in OUT.iterdir()))
