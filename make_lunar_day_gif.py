"""Animated GIF: one lunar day (29.5 days) in the sky of a site, from 7 Nov 2026.
Output: figures/lunar_day_<site>.gif (for the README and as a backup visual for the pitch)."""
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

import ops
import sites
import terrain as tr
from app_time import et_to_dt

ROOT = Path(__file__).resolve().parent
name = sys.argv[1] if len(sys.argv) > 1 else "IM-2 Athena (Mons Mouton), landed 2025"
s = sites.BY_NAME[name]
tl = ops.SiteTimeline(s["lat"], s["lon"], "2026-11-07T10:00", "2026-12-07T00:00", 1.0, 2.0,
                      dem=tr.CompositeDEM())
times = et_to_dt(tl.ets)
step = 6                                # one frame every 6 h -> ~118 frames
frames = range(0, len(tl.ets), step)

plt.rcParams.update({"font.family": "Segoe UI", "font.size": 12})
fig, (ax, axp) = plt.subplots(2, 1, figsize=(9, 5.6), height_ratios=[3, 1],
                              facecolor="#0e1117")
for a in (ax, axp):
    a.set_facecolor("#0e1117")
    a.tick_params(colors="#a9b1bd")
    for sp in a.spines.values():
        sp.set_color("#3a4150")
lo = max(-10, min(-3, np.nanmin(tl.hor) - 0.5, np.nanmin(tl.sun["el"]) - 0.5,
                  np.nanmin(tl.earth["el"]) - 0.5))
hi = max(8, np.nanmax(tl.sun["el"]) + 1, np.nanmax(tl.earth["el"]) + 1)
ax.fill_between(tl.az_h, lo, tl.hor, color="#6b6b6b")
ax.set_xlim(0, 360)
ax.set_ylim(lo, hi)
ax.set_xticks(range(0, 361, 45), ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
ax.set_ylabel("height (°)", color="#a9b1bd")
title = ax.set_title("", color="#f2f2f2", fontsize=13)
sun_trail, = ax.plot([], [], ".", color="#f5a623", ms=2, alpha=0.5)
earth_trail, = ax.plot([], [], ".", color="#4a9bf0", ms=2, alpha=0.5)
sun_dot, = ax.plot([], [], "o", ms=16, mec="black")
earth_dot, = ax.plot([], [], "o", ms=11, mec="black")
status = ax.text(0.01, 0.95, "", transform=ax.transAxes, color="#f2f2f2", va="top",
                 fontsize=12, bbox=dict(fc="#1b1f2a", ec="#3a4150", boxstyle="round"))
days = (tl.ets - tl.ets[0]) / 86400
axp.fill_between(days, 0, tl.power_w, color="#f5a623", alpha=0.35)
axp.set_xlim(0, days[-1])
axp.set_ylabel("power (W)", color="#a9b1bd")
axp.set_xlabel("days after landing", color="#a9b1bd")
cursor = axp.axvline(0, color="#f2f2f2", lw=1.5)
fig.tight_layout(rect=(0, 0, 1, 0.96))


def draw(i):
    sv, ev = tl.sun["visible"][i], tl.comm[i]
    sun_trail.set_data(tl.sun["az"][:i + 1], tl.sun["el"][:i + 1])
    earth_trail.set_data(tl.earth["az"][:i + 1], tl.earth["el"][:i + 1])
    sun_dot.set_data([tl.sun["az"][i]], [tl.sun["el"][i]])
    sun_dot.set_color("#f5a623" if sv else "#5a4a2a")
    earth_dot.set_data([tl.earth["az"][i]], [tl.earth["el"][i]])
    earth_dot.set_color("#4a9bf0" if ev else "#2a3a55")
    status.set_text(f"Sun: {'visible' if sv else 'behind terrain'}\n"
                    f"Earth: {'visible' if ev else 'behind terrain'}\n"
                    f"power {tl.power_w[i]:.0f} W")
    title.set_text(f"{name.split(',')[0]}: {times[i]:%d %b %Y %H:%M} UTC")
    cursor.set_xdata([days[i]])
    return sun_trail, earth_trail, sun_dot, earth_dot, status, title, cursor


out = ROOT / "figures" / f"lunar_day_{name.split(' ')[0].lower()}.gif"
FuncAnimation(fig, draw, frames=frames, blit=False).save(out, writer=PillowWriter(fps=12),
                                                        dpi=90)
print("saved", out, out.stat().st_size // 1024, "kB")
