"""Step 3: checks of the power and communication model (ops.py), and a demo timeline.

Checks
  3a  Partial disc: segment-area formula vs counting 400,000 random points inside the disc.
  3b  Solar energy, analytic: a flat panel at the Apollo 11 site over exactly 12 lunar days
      (synodic months; a partial lunar day would bias the average), flat horizon. Near the equator the Sun's elevation follows sin(el) ~ cos(lat) cos(H), so
      the average of max(0, sin el) over a day is cos(lat)/pi, and
      mean power = (1361 W/m^2 x <(1 AU / r)^2>) x area x efficiency x cos(lat) / pi.
  3c  Link budget: dB arithmetic vs the same link computed in plain SI units (Friis).
  3d  Time until sunset: the refined answer vs brute-force sampling every minute.
  3e  Consistency with block 2: the ridge site's sunlit fraction.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import moon_sky as ms
import ops
import terrain as tr

ROOT = Path(__file__).resolve().parent
res = {}
rng = np.random.default_rng(1)

# ---- 3a partial disc ----
pts = rng.uniform(-1, 1, (2_000_000, 2))
pts = pts[(pts ** 2).sum(1) <= 1][:400_000]
errs = []
for u in np.linspace(-1, 1, 21):
    mc = float((pts[:, 1] > u).mean())
    f = float(ops.disc_fraction_above(0.0, 1.0, u))
    errs.append(abs(mc - f))
res["3a_disc_fraction_max_err"] = max(errs)
print(f"3a disc fraction vs Monte Carlo: max error {max(errs):.4f} (MC noise ~0.001)")

# ---- 3b analytic energy, Apollo 11, flat horizon, horizontal panel ----
LAT11, LON11 = 0.67408, 23.47297
flat = (np.arange(720) * 0.5, np.zeros(720), 0.0)
arr = ops.SolarArray(area_m2=1.0, efficiency=0.30, mode="horizontal")
SYNODIC_S = 29.530589 * 86400
t_end = ms.et_to_utc([ms.utc_to_et("2027-01-01T00:00") + 12 * SYNODIC_S])[0]
tl = ops.SiteTimeline(LAT11, LON11, "2027-01-01T00:00", t_end, step_h=1 / 6,
                      mast_m=0.0, array=arr, horizon=flat)
tl.power_w, tl.ets = tl.power_w[:-1], tl.ets[:-1]   # drop the duplicated end point
tl.sun = {k: v[:-1] for k, v in tl.sun.items()}
sim = float(tl.power_w.mean())
inv_r2 = float(((ops.AU_KM / tl.sun["range_km"]) ** 2).mean())
analytic = ops.SOLAR_CONSTANT * inv_r2 * 1.0 * 0.30 * np.cos(np.radians(LAT11)) / np.pi
res["3b"] = dict(simulated_mean_W=sim, analytic_mean_W=float(analytic),
                 rel_diff=float(sim / analytic - 1))
print(f"3b Apollo 11 flat panel, 12 lunar days, mean power: simulated {sim:.3f} W, "
      f"analytic {analytic:.3f} W ({100 * (sim / analytic - 1):+.3f} %)")

# ---- 3c link budget ----
link = ops.RadioLink()
d_km = 384400.0
b = link.budget(d_km)
lam = ops.C_LIGHT / link.freq_hz
g_tx = 10 ** (link.tx_gain_dbi / 10)
p_rx_over_t = (link.tx_power_w * g_tx / 10 ** (link.tx_losses_db / 10)
               * (lam / (4 * np.pi * d_km * 1e3)) ** 2 / 10 ** (link.other_losses_db / 10)
               * 10 ** (link.ground_g_over_t_dbk / 10))
c_n0_si = p_rx_over_t / 1.380649e-23
rate_si = c_n0_si / 10 ** ((link.required_ebn0_db + link.margin_db) / 10)
res["3c"] = dict(db_rate_bps=float(b["max_rate_bps"]), si_rate_bps=float(rate_si),
                 eirp_dbw=float(b["eirp_dbw"]), fspl_db=float(b["free_space_loss_db"]),
                 c_n0_dbhz=float(b["c_over_n0_dbhz"]), tx_gain_dbi=link.tx_gain_dbi)
print(f"3c link at 384,400 km: EIRP {b['eirp_dbw']:.1f} dBW, path loss "
      f"{b['free_space_loss_db']:.1f} dB, C/N0 {b['c_over_n0_dbhz']:.1f} dBHz -> "
      f"{b['max_rate_bps'] / 1e6:.1f} Mbit/s (SI units: {rate_si / 1e6:.1f} Mbit/s)")

# ---- 3d/3e ridge site ----
LAT, LON = -89.451, 222.81
dem = tr.PolarDEM()
tl = ops.SiteTimeline(LAT, LON, "2027-01-01T00:00", "2027-12-31T23:00", step_h=1.0,
                      mast_m=2.0, dem=dem)
s = tl.summary()
res["ridge_2027"] = s
print("3e ridge 2027 summary:", json.dumps({k: round(v, 2) for k, v in s.items()}))

# 3d: at a site sunlit ~45 % of the time (one of step 2b's random test sites), pick 8 random
#     moments and compare the refined time until the Sun's state changes with a 1-minute scan
tlm = ops.SiteTimeline(-89.509, 86.75, "2027-01-01T00:00", "2027-12-31T23:00", step_h=1.0,
                       mast_m=2.0, dem=dem)
errs = []
cases = []
for i in rng.choice(np.arange(len(tlm.ets) - 24 * 40), 8, replace=False):
    et0 = tlm.ets[i] + 600.0
    now, hrs = tlm.time_until_change(et0, "sun")
    if hrs is None:
        continue
    t_scan = np.arange(et0, et0 + (hrs + 2) * 3600, 60.0)
    az, el, rr, rad, h = tlm._sky("SUN", t_scan)
    vis = ops.disc_fraction_above(el, rad, h) > 0
    k = int(np.argmax(vis != now))
    scan_h = (t_scan[k] - et0) / 3600
    errs.append(abs(scan_h - hrs) * 60)
    cases.append(dict(utc=ms.et_to_utc([et0])[0], sun_up=now, refined_h=float(hrs),
                      scan_h=float(scan_h)))
res["3d_time_to_sunset"] = dict(max_err_min=max(errs), cases=cases)
print(f"3d time until sunset/sunrise, refined vs 1-minute scan: max difference "
      f"{max(errs):.1f} min over {len(errs)} cases")
for c in cases:
    print(f"   {c['utc']}  Sun {'up  ' if c['sun_up'] else 'down'} -> changes in "
          f"{c['refined_h']:7.2f} h (scan {c['scan_h']:7.2f} h)")
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "step3_checks.json").write_text(json.dumps(res, indent=2, default=float))

# ---- demo figure: the darkest lunar day of 2027 at the ridge ----
n = int(29.5 * 24)
starts = np.arange(0, len(tl.ets) - n, 24)
k0 = int(starts[np.argmin([tl.sun["visible"][k:k + n].mean() for k in starts])])
sl = slice(k0, k0 + n)
days = (tl.ets[sl] - tl.ets[k0]) / 86400
t0_utc = ms.et_to_utc([tl.ets[k0]])[0][:10]
fig, ax = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True)
ax[0].plot(days, tl.sun["el"][sl], color="tab:orange", lw=1, label="Sun elevation")
ax[0].plot(days, tl.sun["horizon"][sl], color="0.4", lw=1, label="terrain in the Sun's direction")
ax[0].plot(days, tl.earth["el"][sl], color="tab:blue", lw=1, label="Earth elevation")
ax[0].plot(days, tl.earth["horizon"][sl], color="0.4", lw=1, ls=":",
           label="terrain in Earth's direction")
ax[0].set_ylabel("deg")
ax[0].legend(fontsize=7, ncol=2, loc="upper right")
ax[0].grid(alpha=0.3)
ax[1].fill_between(days, 0, tl.power_w[sl], color="tab:orange", alpha=0.6)
ax[1].set_ylabel("array power (W)\n1 m², 30 %, sun-tracking")
ax[1].grid(alpha=0.3)
ax[2].fill_between(days, 0, tl.rate_bps[sl] / 1e6, color="tab:blue", alpha=0.6)
ax[2].set_ylabel("max downlink\n(Mbit/s)")
ax[2].set_xlabel(f"days from {t0_utc}")
ax[2].grid(alpha=0.3)
seg = {"sun": tl.sun["visible"][sl].mean(), "earth": tl.comm[sl].mean()}
ax[0].set_title(f"Shackleton–de Gerlache ridge, darkest lunar day of 2027: Sun visible "
                f"{100 * seg['sun']:.0f} %, Earth link {100 * seg['earth']:.0f} %", fontsize=10)
fig.tight_layout()
fig.savefig(ROOT / "figures" / "step3_ridge_timeline.png", dpi=130)
print("saved")
