"""Step 2a: check the terrain map is read correctly and the two horizon methods agree.

Check 1, projection: the polar map's (lat, lon) -> pixel formula has sign conventions that
are easy to get wrong (a mirrored or rotated map would still "look" like the Moon). We sample
the polar map along 80-89 deg S at many longitudes and compare with the global cylindrical
map LDEM_16 (a separate product with a trivial lat/lon grid). Only the right convention
correlates well.

Check 2, horizon: ray-marching (horizon_profile) vs brute force over every pixel
(horizon_bruteforce) at three sites.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import terrain as tr

ROOT = Path(__file__).resolve().parent
out = {}

# ---------------- check 1: projection convention ----------------
cyl = np.memmap(tr.DATA / "ldem_16.img", dtype="<i2", mode="r", shape=(2880, 5760))


def cyl_height(lat, lon):
    row = (90.0 - lat) * 16 - 0.5
    col = (lon % 360.0) * 16 - 0.5
    r0, c0 = np.floor(row).astype(int), np.floor(col).astype(int)
    fr, fc = row - r0, col - c0
    c1 = (c0 + 1) % 5760
    c0 = c0 % 5760
    h = ((1 - fr) * ((1 - fc) * cyl[r0, c0] + fc * cyl[r0, c1])
         + fr * ((1 - fc) * cyl[r0 + 1, c0] + fc * cyl[r0 + 1, c1]))
    return h * 0.5


dem = tr.PolarDEM("ldem_80s_40m")
lats = np.linspace(-80.5, -89.0, 18)
lons = np.linspace(0, 359, 360)
LA, LO = np.meshgrid(lats, lons, indexing="ij")
h_cyl = cyl_height(LA.ravel(), LO.ravel())
conv = {}
for sx in (+1, -1):
    for sy in (+1, -1):
        tr.PolarDEM.SX, tr.PolarDEM.SY = sx, sy
        h_pol = dem.height(LA.ravel(), LO.ravel())
        ok = np.isfinite(h_pol)
        corr = np.corrcoef(h_pol[ok], h_cyl[ok])[0, 1]
        rms = float(np.sqrt(np.mean((h_pol[ok] - h_cyl[ok]) ** 2)))
        conv[f"SX={sx:+d},SY={sy:+d}"] = dict(corr=float(corr), rms_m=rms)
        print(f"SX={sx:+d} SY={sy:+d}: correlation {corr:.4f}, rms difference {rms:7.1f} m")
best = max(conv, key=lambda k: conv[k]["corr"])
print("best convention:", best)
tr.PolarDEM.SX, tr.PolarDEM.SY = +1, -1
assert best == "SX=+1,SY=-1", "terrain.PolarDEM.SX/SY must be updated"
out["projection_check"] = conv

# round trip
r, c = dem.latlon_to_pix(LA.ravel(), LO.ravel())
la2, lo2 = dem.pix_to_latlon(r, c)
out["roundtrip_max_err_deg"] = float(max(np.abs(la2 - LA.ravel()).max(),
                                         (np.abs((lo2 - LO.ravel() + 180) % 360 - 180)).max()))
print("lat/lon -> pixel -> lat/lon round trip, max error (deg):", out["roundtrip_max_err_deg"])

# ---------------- check 2: horizon methods ----------------
# 2a far field (> 5 km): ray marching vs brute force over every pixel. (Closer than ~5 km a
#    40 m pixel is wider than one 0.5 deg azimuth bin, so brute force under-samples there.)
# 2b near field (< 300 m): local slope vs the near-field horizon (rough check).
# 2c smooth sphere: with all terrain heights set to zero, the horizon must be the textbook
#    "dip" of the horizon from height h on a sphere, -acos(R / (R + h)).
SITES = {
    "Near Shackleton rim": (-89.9, 0.0),
    "Malapert massif (approx.)": (-86.0, 2.9),
    "Haworth crater floor (approx.)": (-87.4, 355.0),
}
fig, axes = plt.subplots(len(SITES), 1, figsize=(11, 8.5), sharex=True)
out["horizon_check"] = {}
for ax, (name, (la, lo)) in zip(axes, SITES.items()):
    az, hr, hs = tr.horizon_profile(dem, la, lo, obs_height_m=2.0, max_dist_m=100e3,
                                    min_dist_m=5000.0)
    az_b, hb, _ = tr.horizon_bruteforce(dem, la, lo, obs_height_m=2.0, radius_m=100e3,
                                        min_dist_m=5000.0)
    d = hr - hb
    slope, aspect = tr.local_slope(dem, la, lo)
    azn, hn, _ = tr.horizon_profile(dem, la, lo, obs_height_m=0.0, max_dist_m=300.0)
    az_full, h_full, _ = tr.horizon_profile(dem, la, lo, obs_height_m=2.0, max_dist_m=100e3)
    res = dict(site_height_m=hs,
               far_mean_diff_deg=float(d.mean()),
               far_p95_abs_diff_deg=float(np.percentile(np.abs(d), 95)),
               far_max_abs_diff_deg=float(np.abs(d).max()),
               slope_deg=float(slope), uphill_az_deg=float(aspect),
               near_max_horizon_deg=float(hn.max()), near_max_az_deg=float(azn[hn.argmax()]))
    out["horizon_check"][name] = res
    print(f"{name:31s} h={hs:6.0f} m | far field ray-brute: mean {d.mean():+.4f}, "
          f"95% within {res['far_p95_abs_diff_deg']:.4f}, max {res['far_max_abs_diff_deg']:.3f} deg"
          f" | slope {slope:5.2f} deg towards {aspect:5.1f}; near-field max {hn.max():5.2f} deg"
          f" at az {azn[hn.argmax()]:5.1f}")
    ax.plot(az_full, h_full, color="k", lw=1.4, label="full horizon (used in the app)")
    ax.plot(az, hr, lw=1.0, label="ray marching, terrain > 5 km away")
    ax.plot(az_b, hb, lw=0.8, ls="--", label="brute force, every pixel 5-100 km away")
    ax.axhspan(-1.6, 1.6, color="orange", alpha=0.15, label="range of Sun elevations")
    ax.set_ylabel("horizon (deg)")
    ax.set_title(f"{name}: ground {hs:.0f} m, local slope {slope:.1f} deg", fontsize=9)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=7, loc="upper right")
axes[-1].set_xlabel("azimuth (deg from north, towards east)")
axes[-1].set_xticks(range(0, 361, 45))
fig.tight_layout()

# 2c smooth sphere
flat = object.__new__(tr.PolarDEM)
flat.__dict__.update({k: v for k, v in dem.__dict__.items() if k != "dn"})
flat.dn = np.zeros((dem.n_lines, dem.n_samples), dtype="<i2")
out["smooth_sphere_check"] = {}
for h_obs in (2.0, 100.0, 1000.0):
    _, hz, _ = tr.horizon_profile(flat, -88.0, 45.0, obs_height_m=h_obs, n_az=72)
    exact = -np.degrees(np.arccos(tr.R_MOON_M / (tr.R_MOON_M + h_obs)))
    err = float(np.abs(hz - exact).max())
    out["smooth_sphere_check"][f"{h_obs:g} m"] = dict(exact_deg=float(exact), max_err_deg=err)
    print(f"smooth sphere, eye at {h_obs:6g} m: exact dip {exact:+.4f} deg, "
          f"max error {err:.5f} deg")
del flat
(ROOT / "figures").mkdir(exist_ok=True)
fig.savefig(ROOT / "figures" / "step2a_horizon_methods.png", dpi=130)
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "step2a_checks.json").write_text(json.dumps(out, indent=2))
print("saved")
