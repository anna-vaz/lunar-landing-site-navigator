"""Cut the compact terrain layers of the web edition (data_web/) from the full LOLA maps.
Needs the full data/ folder (download_terrain.py). Run: python build_web_data.py"""
import json
from pathlib import Path

import numpy as np

import sites
import terrain as tr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data_web"
OUT.mkdir(exist_ok=True)
PATCH_KM = 15.0          # radius of the full-detail patch around each curated site
CYL_DEG = 1.5            # half-size (latitude) of the 474 m patch around non-polar sites

pol = tr.PolarDEM()
meta = {"polar_patches": [], "cyl_patches": []}

# 3. whole polar map at 120 m (3 x 3 block mean of the 40 m map)
n = (pol.n_lines // 3) * 3
a = np.asarray(pol.dn[:n, :n], dtype=np.float32).reshape(n // 3, 3, n // 3, 3).mean((1, 3))
np.savez_compressed(OUT / "polar_120m.npz", dn=np.round(a).astype("<i2"),
                    l0=(pol.l0 - 1) / 3, s0=(pol.s0 - 1) / 3)

# 4. global 1.9 km map
g16 = tr.GlobalDEM("ldem_16")
np.savez_compressed(OUT / "global_16.npz", dn=np.asarray(g16.dn))

g64 = tr.GlobalDEM("ldem_64")
for k, s in enumerate(sites.SITES):
    if s["lat"] <= -80.2:                      # 1. 40 m polar patch
        r, c = pol.latlon_to_pix(s["lat"], s["lon"])
        h = int(PATCH_KM * 1000 / pol.scale)
        r0, c0 = int(round(r)) - h, int(round(c)) - h
        dn = np.asarray(pol.dn[r0:r0 + 2 * h + 1, c0:c0 + 2 * h + 1])
        f = f"polar_patch_{k:02d}.npz"
        np.savez_compressed(OUT / f, dn=dn, l0=pol.l0 - r0, s0=pol.s0 - c0)
        meta["polar_patches"].append(dict(site=s["name"], file=f))
    else:                                       # 2. 474 m cylindrical patch
        dlon = min(60.0, CYL_DEG / max(np.cos(np.radians(s["lat"])), 0.05))
        lat_top = min(90.0, np.ceil((s["lat"] + CYL_DEG) * 64) / 64)
        lat_bot = max(-90.0, np.floor((s["lat"] - CYL_DEG) * 64) / 64)
        lon_left = np.floor(((s["lon"] - dlon) % 360) * 64) / 64
        rows = np.arange(int(round((90 - lat_top) * 64)), int(round((90 - lat_bot) * 64)))
        ncol = int(np.ceil(2 * dlon * 64)) + 1
        cols = (int(round(lon_left * 64)) + np.arange(ncol)) % g64.n_samples
        dn = np.asarray(g64.dn[rows[0]:rows[-1] + 1][:, cols])
        f = f"cyl_patch_{k:02d}.npz"
        np.savez_compressed(OUT / f, dn=dn, lat_top=lat_top, lon_left=lon_left)
        meta["cyl_patches"].append(dict(site=s["name"], file=f))
(OUT / "meta.json").write_text(json.dumps(meta, indent=1))
total = sum(p.stat().st_size for p in OUT.iterdir())
print(f"data_web: {total / 1e6:.1f} MB in {len(list(OUT.iterdir()))} files")
