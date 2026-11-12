"""Check the web edition's compact terrain against the full edition.

  A. the 16 curated sites: Sun and Earth visibility over 2027 (2 m mast)
  B. 60 random custom points near the south pole (85-89.8 S), where the web edition only has
     the 120 m map: how much does reduced detail change the answer?
"""
import json
import time
from pathlib import Path

import numpy as np

import moon_sky as ms
import ops
import sites
import terrain as tr
import web_terrain as wt

ROOT = Path(__file__).resolve().parent
full = tr.CompositeDEM()
t = time.time()
web = wt.WebDEM()
print(f"web terrain loaded in {time.time() - t:.1f} s")
ets = ms.time_grid("2027-01-01T00:00", "2027-12-31T23:00", 1.0)
vec = {k: ms.target_vectors_from_moon_center(k, ets) for k in ("SUN", "EARTH")}


def pct(dem, la, lo):
    tl = ops.SiteTimeline(la, lo, "2027-01-01T00:00", "2027-12-31T23:00", 1.0, 2.0, dem=dem,
                          vectors=vec)
    return 100 * tl.sun["visible"].mean(), 100 * tl.comm.mean()


res = {"curated": [], "random_polar": []}
for s in sites.SITES:
    f, w = pct(full, s["lat"], s["lon"]), pct(web, s["lat"], s["lon"])
    res["curated"].append(dict(site=s["name"], full=f, web=w))
    print(f"{s['name'][:44]:44s} Sun {f[0]:5.1f} / {w[0]:5.1f}   Earth {f[1]:5.1f} / {w[1]:5.1f}")
rng = np.random.default_rng(7)
for _ in range(60):
    la, lo = -rng.uniform(85.0, 89.8), rng.uniform(0, 360)
    f, w = pct(full, la, lo), pct(web, la, lo)
    res["random_polar"].append(dict(lat=la, lon=lo, full=f, web=w))
for k in ("curated", "random_polar"):
    d = np.array([[r["web"][0] - r["full"][0], r["web"][1] - r["full"][1]] for r in res[k]])
    res[k + "_summary"] = dict(sun_median_abs=float(np.median(np.abs(d[:, 0]))),
                               sun_max_abs=float(np.abs(d[:, 0]).max()),
                               earth_median_abs=float(np.median(np.abs(d[:, 1]))),
                               earth_max_abs=float(np.abs(d[:, 1]).max()))
    print(k, res[k + "_summary"])
(ROOT / "results" / "step_web_check.json").write_text(json.dumps(res, indent=1))
