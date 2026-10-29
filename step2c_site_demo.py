"""Step 2c: what the terrain horizon means at a real site (demo figure for the pitch).

Site: the brightest spot on NASA's 60 m south-pole sunlight map (86 % over 18.6 years),
on the ridge connecting Shackleton and de Gerlache craters (89.451 S, 222.81 E).
  Panel 1: the skyline seen from a 2 m mast, with the Sun's and Earth's paths over one
           lunar day (Jan 2027): above the terrain = usable, below = blocked.
  Panel 2: sunlight and Earth time in 2027 vs mast height, and vs a flat Moon (block 1).
"""
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import moon_sky as ms
import terrain as tr

ROOT = Path(__file__).resolve().parent
LAT, LON = -89.451, 222.81
NAME = "Shackleton–de Gerlache ridge (89.45°S, 222.81°E)"

dem = tr.PolarDEM()
ets = ms.time_grid("2027-01-01T00:00", "2027-12-31T23:00", 1.0)
vec = {t: ms.target_vectors_from_moon_center(t, ets) for t in ("SUN", "EARTH")}
sky = {t: ms.sky_from_vectors(vec[t], LAT, LON) for t in vec}


def visible(t, az, hz):
    a, e, d = sky[t]
    rad = np.degrees(np.arcsin(ms.TARGET_RADIUS_KM[t] / d))
    return (e + rad) > tr.horizon_at(az, hz, a)


heights = [0.5, 2, 5, 10, 20]
res = {"site": NAME, "lat": LAT, "lon": LON, "year": 2027, "by_mast_height_m": {}}
for h in heights:
    az, hz, hs = tr.horizon_profile(dem, LAT, LON, obs_height_m=h)
    res["by_mast_height_m"][str(h)] = {t.lower(): float(visible(t, az, hz).mean()) for t in sky}
res["flat_moon"] = {t.lower(): float((sky[t][1] + np.degrees(np.arcsin(
    ms.TARGET_RADIUS_KM[t] / sky[t][2])) > 0).mean()) for t in sky}
res["ground_height_m"] = hs

az, hz, _ = tr.horizon_profile(dem, LAT, LON, obs_height_m=2.0)
fig = plt.figure(figsize=(12, 7.5))
ax = fig.add_subplot(2, 1, 1)
ax.fill_between(az, -8, hz, color="0.55", label="terrain (seen from a 2 m mast)")
# Show the lunar day of 2027 with the LEAST sunlight (the hardest month for a lander)
n = int(29.5 * 24)
vs = visible("SUN", az, hz)
starts = np.arange(0, len(ets) - n, 24)
k0 = int(starts[np.argmin([vs[k:k + n].mean() for k in starts])])
month = ms.et_to_utc([ets[k0]])[0][:10]
res["worst_lunar_day_start"] = month
res["worst_lunar_day_sun"] = float(vs[k0:k0 + n].mean())
for t, col in (("SUN", "tab:orange"), ("EARTH", "tab:blue")):
    a, e, _ = sky[t]
    v = visible(t, az, hz)
    a, e, v = a[k0:k0 + n], e[k0:k0 + n], v[k0:k0 + n]
    ax.scatter(a[v], e[v], s=4, color=col, label=f"{t.title()}: visible", zorder=3)
    ax.scatter(a[~v], e[~v], s=4, color="white", edgecolors=col, linewidths=0.4,
               label=f"{t.title()}: behind terrain", zorder=3)
ax.set_xlim(0, 360)
ax.set_ylim(-4, 8)
ax.set_xticks(range(0, 361, 45))
ax.set_xlabel("azimuth (deg from north, towards east)")
ax.set_ylabel("elevation (deg)")
ax.set_title(f"{NAME}: skyline, and Sun/Earth paths over the darkest lunar day of 2027 "
             f"(from {month}; Sun visible {100 * res['worst_lunar_day_sun']:.0f}% of it)",
             fontsize=9)
ax.legend(fontsize=7, ncol=3, loc="upper right")
ax.grid(alpha=0.3)

ax2 = fig.add_subplot(2, 1, 2)
labels = ["flat Moon\n(no terrain)"] + [f"mast {h:g} m" for h in heights]
sun = [res["flat_moon"]["sun"]] + [res["by_mast_height_m"][str(h)]["sun"] for h in heights]
earth = [res["flat_moon"]["earth"]] + [res["by_mast_height_m"][str(h)]["earth"] for h in heights]
x = np.arange(len(labels))
b1 = ax2.bar(x - 0.2, np.array(sun) * 100, 0.4, color="tab:orange", label="Sun visible")
b2 = ax2.bar(x + 0.2, np.array(earth) * 100, 0.4, color="tab:blue", label="Earth visible")
ax2.bar_label(b1, fmt="%.0f%%", fontsize=8)
ax2.bar_label(b2, fmt="%.0f%%", fontsize=8)
ax2.set_xticks(x, labels)
ax2.set_ylabel("% of 2027")
ax2.set_ylim(0, 105)
ax2.set_title("Terrain matters more than latitude, and a few metres of mast change the answer",
              fontsize=10)
ax2.legend(fontsize=8, loc="upper left")
ax2.grid(alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(ROOT / "figures" / "step2c_ridge_site.png", dpi=130)
print(json.dumps(res, indent=1))
(ROOT / "results" / "step2c_ridge_site.json").write_text(json.dumps(res, indent=2))
print("saved")
