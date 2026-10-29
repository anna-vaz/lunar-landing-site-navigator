"""Step 4a: global terrain checks, and the headline numbers for every curated site.

Checks
  * LDEM_64 (global, 474 m) is read with the right orientation: it must agree with the
    independent LDEM_16 product everywhere, and with the 40 m polar map where they overlap.
  * The composite terrain (polar map south of 80.2 S, global map elsewhere) gives the same
    horizon as the polar map alone for a site near the pole (where both are complete).
Then a table of 2027 sunlight / Earth visibility for every site in sites.py.
"""
import json
from pathlib import Path

import numpy as np

import moon_sky as ms
import ops
import sites
import terrain as tr

ROOT = Path(__file__).resolve().parent
rng = np.random.default_rng(3)
res = {}

g64 = tr.GlobalDEM("ldem_64")
g16 = tr.GlobalDEM("ldem_16")
pol = tr.PolarDEM()
comp = tr.CompositeDEM(pol, g64)

lat = rng.uniform(-75, 75, 20000)
lon = rng.uniform(0, 360, 20000)
a, b = g64.height(lat, lon), g16.height(lat, lon)
res["ldem64_vs_ldem16"] = dict(corr=float(np.corrcoef(a, b)[0, 1]),
                               rms_m=float(np.sqrt(np.mean((a - b) ** 2))))
lat = rng.uniform(-87, -80.5, 20000)
a, b = g64.height(lat, lon), pol.height(lat, lon)
res["ldem64_vs_polar40m"] = dict(corr=float(np.corrcoef(a, b)[0, 1]),
                                 rms_m=float(np.sqrt(np.mean((a - b) ** 2))))
print("global 474 m map vs global 1.9 km map:", res["ldem64_vs_ldem16"])
print("global 474 m map vs polar 40 m map (80.5-87 S):", res["ldem64_vs_polar40m"])

az, h1, _ = tr.horizon_profile(pol, -89.451, 222.81, 2.0)
az, h2, _ = tr.horizon_profile(comp, -89.451, 222.81, 2.0)
res["composite_vs_polar_near_pole_max_diff_deg"] = float(np.nanmax(np.abs(h1 - h2)))
print("composite vs polar-only horizon at the ridge: max diff",
      res["composite_vs_polar_near_pole_max_diff_deg"], "deg")
res["polar_only_nan_dirs_at_IM1"] = int(np.isnan(
    tr.horizon_profile(pol, -80.13, 1.44, 2.0)[1]).sum())
res["composite_nan_dirs_at_IM1"] = int(np.isnan(
    tr.horizon_profile(comp, -80.13, 1.44, 2.0)[1]).sum())
print("IM-1 site (80.13 S): directions with no terrain, polar-only:",
      res["polar_only_nan_dirs_at_IM1"], " composite:", res["composite_nan_dirs_at_IM1"])

ets = ms.time_grid("2027-01-01T00:00", "2027-12-31T23:00", 1.0)
vec = {t: ms.target_vectors_from_moon_center(t, ets) for t in ("SUN", "EARTH")}
table = []
for s in sites.SITES:
    tl = ops.SiteTimeline(s["lat"], s["lon"], "2027-01-01T00:00", "2027-12-31T23:00",
                          dem=comp, vectors=vec,
                          array=ops.SolarArray(mode="vertical_tracking" if s["lat"] < -60
                                               else "horizontal"))
    m = tl.summary()
    m.update(name=s["name"], horizon_max_deg=float(np.nanmax(tl.hor)))
    table.append(m)
    print(f"{s['name'][:44]:44s} ground {m['ground_height_m']:6.0f} m  Sun {m['sun_visible_pct']:5.1f}%  "
          f"Earth {m['earth_visible_pct']:5.1f}%  longest dark {m['longest_dark_h']:5.0f} h  "
          f"mean power {m['mean_power_w']:5.0f} W")
res["sites_2027"] = table
(ROOT / "results" / "step4a_global.json").write_text(json.dumps(res, indent=2))
