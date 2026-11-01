"""Slide-4 chart: sunlight and Earth contact during a 14-day mission at the IM-2 site,
for every landing day from 1 Nov to 31 Dec 2026."""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ops, sites, terrain as tr  # noqa: E402
from app_time import et_to_dt     # noqa: E402

s = sites.BY_NAME["IM-2 Athena (Mons Mouton), landed 2025"]
tl = ops.SiteTimeline(s["lat"], s["lon"], "2026-11-01T10:00", "2027-01-14T10:00", 1.0, 2.0,
                      dem=tr.CompositeDEM())
n = 14 * 24
starts = np.arange(0, len(tl.ets) - n, 24)
cs = np.concatenate([[0], np.cumsum(tl.sun["visible"])])
ce = np.concatenate([[0], np.cumsum(tl.comm)])
sun = 100 * (cs[starts + n] - cs[starts]) / n
earth = 100 * (ce[starts + n] - ce[starts]) / n
days = et_to_dt(tl.ets[starts])

plt.rcParams.update({"font.family": "Segoe UI", "font.size": 13})
fig, ax = plt.subplots(figsize=(6.2, 5.6), facecolor="#0e1117")
ax.set_facecolor("#0e1117")
ax.plot(days, sun, color="#f5a623", lw=3, label="Sun visible")
ax.plot(days, earth, color="#4a9bf0", lw=2.2, ls="--", label="Earth visible")
marks = [("7 Nov planned", 6, "#e4572e", (14, -14), "left"),
         ("15 Nov best", 14, "#5cc98b", (0, 12), "center"),
         ("21 Nov slipped", 20, "#f2f2f2", (12, 0), "left")]
for lab, i, c, off, ha in marks:
    ax.scatter([days[i]], [sun[i]], s=160, color=c, zorder=5, edgecolor="black")
    ax.annotate(f"{lab}: {sun[i]:.0f} %", (days[i], sun[i]), textcoords="offset points",
                xytext=off, ha=ha, va=("top" if off[1] < 0 else "center") if ha != "center" else "bottom", color=c,
                fontsize=14, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="#0e1117", ec="none", alpha=0.85))
ax.set_ylim(-5, 115)
ax.set_xlim(days[0], days[44])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 15]))
ax.set_ylabel("% of the 14-day mission", color="#a9b1bd")
ax.set_xlabel("landing day (2026)", color="#a9b1bd")
ax.set_title("IM-2 site: pick the landing day", color="#f2f2f2", fontsize=15, pad=10)
ax.tick_params(colors="#a9b1bd")
for sp in ax.spines.values():
    sp.set_color("#3a4150")
ax.grid(alpha=0.15)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, facecolor="#1b1f2a", edgecolor="#3a4150", labelcolor="#f2f2f2")
fig.tight_layout()
fig.savefig(Path(__file__).parent / "img" / "slip_chart.png", dpi=180, facecolor="#0e1117")
print([(d.strftime("%d %b"), round(a), round(b)) for d, a, b in zip(days[:25], sun, earth)])
