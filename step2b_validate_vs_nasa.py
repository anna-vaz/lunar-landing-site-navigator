"""Step 2b: validate sunlight and Earth-visibility fractions against NASA's own maps.

NASA's LOLA team (Mazarico et al. 2011, updated 2016) computed, for every 60 m pixel near
the south pole, the fraction of time the Sun (and Earth) is visible, averaged over 18.6 years
(one full cycle of the Moon's orbit-plane precession). Those maps (AVGVISIB_85S_060M_201608
and ..._EARTH) are an independent reference: different software, a different elevation map
(60 m vs our 40 m), and hourly steps.

We pick test sites, compute their horizon (block 2) and the Sun/Earth sky track (block 1)
every 3 hours over 18.6 years, and count how often each body's disc clears the horizon.
"Visible" = any part of the disc above the terrain, the same definition NASA used.

Matching NASA's setup: their surface is a 60 m grid and each pixel's horizon is formed by the
other pixels, so we put the eye at ground level and ignore terrain closer than 60 m. (With a
0 m eye and no exclusion, our interpolated ground "shades itself": when the Sun is at 1 deg, a
bump of 1 m at 40 m distance is enough to hide it. The app uses a 2 m eye height, a lander's
solar panel, which removes that artefact; see step2c.)
"""
import json
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import moon_sky as ms
import terrain as tr

ROOT = Path(__file__).resolve().parent
ILL = ROOT / "data" / "nasa_illum"
rng = np.random.default_rng(42)

# ---------- NASA reference maps (same polar stereographic layout, 60 m pixels) ----------
N60, S60, L60 = 5058, 2528.5, 2528.5
sun_map = np.memmap(ILL / "AVGVISIB_85S_060M_201608.IMG", dtype="<i2", mode="r",
                    shape=(N60, N60))
earth_map = np.memmap(ILL / "AVGVISIB_85S_060M_201608_EARTH.IMG", dtype="<i2", mode="r",
                      shape=(N60, N60))


def nasa_pix(lat, lon):
    rho = 2 * tr.R_MOON_M * np.tan(np.pi / 4 + np.radians(lat) / 2)
    x, y = rho * np.sin(np.radians(lon)), rho * np.cos(np.radians(lon))
    return int(round(L60 - y / 60.0)), int(round(S60 + x / 60.0))


def nasa_value(m, lat, lon):
    r, c = nasa_pix(lat, lon)
    return float(m[r, c]) * 4e-5


# ---------- test sites ----------
# (a) random points 85-89.8 S; (b) the brightest spots on NASA's map (the candidate
# "peaks of eternal light", where an error would matter most for a landing-site tool).
sites = []
while len(sites) < 120:
    la = -rng.uniform(85.2, 89.8)
    lo = rng.uniform(0, 360)
    sites.append(("random", la, lo))
sub = np.asarray(sun_map[::4, ::4]).astype(float)
for idx in np.argsort(sub.ravel())[::-1][:4000:100]:   # 40 bright spots, spread out
    r, c = np.unravel_index(idx, sub.shape)
    r, c = r * 4, c * 4
    x = (c - S60) * 60.0
    y = -(r - L60) * 60.0
    rho = np.hypot(x, y)
    la = np.degrees(2 * np.arctan(rho / (2 * tr.R_MOON_M)) - np.pi / 2)
    lo = np.degrees(np.arctan2(x, y)) % 360
    if la < -85.2:
        sites.append(("bright", la, lo))
print(len(sites), "test sites")

# ---------- 18.6 years of Sun and Earth directions ----------
ets = ms.time_grid("2009-01-01T00:00", "2027-08-07T00:00", 3.0)
print(len(ets), "times")
vec = {t: ms.target_vectors_from_moon_center(t, ets) for t in ("SUN", "EARTH")}

# fast path vs exact path (block 1) on one site, one year
chk_et = ets[:2920]
a1, e1, _ = ms.sky_from_vectors(vec["EARTH"][:2920], -89.0, 30.0)
a2, e2, _ = ms.sky_positions("EARTH", -89.0, 30.0, chk_et)
fast_err_arcsec = float(np.abs(e1 - e2).max() * 3600)
print(f"fast sky path vs exact: max Earth elevation difference {fast_err_arcsec:.3f} arcsec")

dem = tr.PolarDEM("ldem_80s_40m")
rows = []
t0 = time.time()
for kind, la, lo in sites:
    az, hz, hs = tr.horizon_profile(dem, la, lo, obs_height_m=0.0, min_dist_m=60.0)
    rec = dict(kind=kind, lat=la, lon=lo, ground_m=hs)
    for t, m in (("SUN", sun_map), ("EARTH", earth_map)):
        a, e, d = ms.sky_from_vectors(vec[t], la, lo)
        radius = np.degrees(np.arcsin(ms.TARGET_RADIUS_KM[t] / d))
        visible = (e + radius) > tr.horizon_at(az, hz, a)
        rec[f"{t.lower()}_ours"] = float(visible.mean())
        rec[f"{t.lower()}_nasa"] = nasa_value(m, la, lo)
    rows.append(rec)
print(f"horizons + visibility for {len(rows)} sites in {time.time() - t0:.0f} s")

summary = {"n_sites": len(rows), "n_times": int(len(ets)), "years": 18.6,
           "fast_vs_exact_sky_arcsec": fast_err_arcsec}
for t in ("sun", "earth"):
    o = np.array([r[f"{t}_ours"] for r in rows])
    n = np.array([r[f"{t}_nasa"] for r in rows])
    d = (o - n) * 100
    summary[t] = dict(mean_diff_pct_points=float(d.mean()),
                      median_abs_diff_pct_points=float(np.median(np.abs(d))),
                      p90_abs_diff_pct_points=float(np.percentile(np.abs(d), 90)),
                      correlation=float(np.corrcoef(o, n)[0, 1]))
    b = np.array([r["kind"] == "bright" for r in rows])
    summary[t]["bright_sites_median_abs_diff_pct_points"] = float(np.median(np.abs(d[b])))
    print(t, summary[t])

(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "step2b_vs_nasa.json").write_text(
    json.dumps({"summary": summary, "sites": rows}, indent=2))

fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
for ax, t, title in ((axes[0], "sun", "Sunlight"), (axes[1], "earth", "Earth in view")):
    for kind, col, lab in (("random", "tab:blue", "random sites 85-90°S"),
                           ("bright", "tab:orange", "brightest spots on NASA's map")):
        o = [r[f"{t}_ours"] * 100 for r in rows if r["kind"] == kind]
        n = [r[f"{t}_nasa"] * 100 for r in rows if r["kind"] == kind]
        ax.scatter(n, o, s=14, color=col, label=lab, alpha=0.8)
    ax.plot([0, 100], [0, 100], "k--", lw=0.8)
    s = summary[t]
    ax.set_title(f"{title}: % of time over 18.6 years\n"
                 f"median difference {s['median_abs_diff_pct_points']:.1f} points, "
                 f"correlation {s['correlation']:.3f}", fontsize=10)
    ax.set_xlabel("NASA LOLA team map (%)")
    ax.set_ylabel("our tool (%)")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(ROOT / "figures" / "step2b_vs_nasa.png", dpi=130)
print("saved")
