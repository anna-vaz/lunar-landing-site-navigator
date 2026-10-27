"""Step 1: check our Sun/Earth sky positions against NASA JPL Horizons.

Horizons is JPL's official ephemeris service; it can compute azimuth/elevation as seen from any
point on the Moon. It is a completely separate implementation from ours (different software,
DE441 instead of DE440, plus tiny effects we ignore such as gravitational light bending), so
agreement is a strong check.

We compare three things for every hour of 2027, for 3 sites and 2 targets:
  A  moon_sky.sky_positions        our code: SPICE vector -> our own East/North/Up rotation
  B  moon_sky.sky_positions_spice_azl  SPICE's built-in az/el routine (checks our rotation)
  C  JPL Horizons                  independent reference (checks everything)

Outputs: results/step1_validation.json, figures/step1_*.png
"""
import json
import time
from pathlib import Path

import numpy as np
import requests
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import moon_sky as ms

ROOT = Path(__file__).resolve().parent
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "figures").mkdir(exist_ok=True)
CACHE = ROOT / "data" / "horizons"
CACHE.mkdir(parents=True, exist_ok=True)

# Approximate coordinates (MOON_ME, deg). Good enough for a validation test; the real
# candidate sites come with the challenge data on 28 Oct.
SITES = {
    "shackleton_rim": dict(name="Near Shackleton rim", lat=-89.9, lon=0.0),
    "malapert": dict(name="Malapert massif (approx.)", lat=-86.0, lon=2.9),
    "apollo11": dict(name="Apollo 11 (equatorial check)", lat=0.67408, lon=23.47297),
}
TARGETS = {"SUN": "10", "EARTH": "399"}
START, STOP, STEP_H = "2027-01-01T00:00", "2027-12-31T23:00", 1.0


def horizons(target_id, lat, lon, start, stop, step="1 h"):
    """Fetch apparent airless az/el table from the Horizons API (cached on disk)."""
    key = f"{target_id}_{lat}_{lon}_{start}_{stop}_{step}".replace(":", "").replace(" ", "")
    f = CACHE / f"{key}.txt"
    if not f.exists():
        p = dict(format="text", COMMAND=f"'{target_id}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
                 EPHEM_TYPE="'OBSERVER'", CENTER="'coord@301'", COORD_TYPE="'GEODETIC'",
                 SITE_COORD=f"'{lon},{lat},0'", START_TIME=f"'{start.replace('T', ' ')}'",
                 STOP_TIME=f"'{stop.replace('T', ' ')}'", STEP_SIZE=f"'{step}'",
                 QUANTITIES="'4,20'", ANG_FORMAT="'DEG'", CSV_FORMAT="'YES'",
                 APPARENT="'AIRLESS'", TIME_DIGITS="'MINUTES'")
        r = requests.get("https://ssd.jpl.nasa.gov/api/horizons.api", params=p, timeout=120)
        r.raise_for_status()
        f.write_text(r.text, encoding="utf-8")
        time.sleep(1)
    txt = f.read_text(encoding="utf-8")
    body = txt.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    t, az, el, rng = [], [], [], []
    for line in body:
        c = [x.strip() for x in line.split(",")]
        t.append(c[0])
        az.append(float(c[3]))
        el.append(float(c[4]))
        rng.append(float(c[5]) * 149597870.7)  # au -> km
    return t, np.array(az), np.array(el), np.array(rng)


def ang_sep(az1, el1, az2, el2):
    """Angle between two sky directions (deg); immune to the azimuth wrap at the zenith."""
    a1, e1, a2, e2 = map(np.radians, (az1, el1, az2, el2))
    v1 = np.stack([np.cos(e1) * np.sin(a1), np.cos(e1) * np.cos(a1), np.sin(e1)])
    v2 = np.stack([np.cos(e2) * np.sin(a2), np.cos(e2) * np.cos(a2), np.sin(e2)])
    return np.degrees(np.arccos(np.clip((v1 * v2).sum(0), -1, 1)))


def main():
    ets = ms.time_grid(START, STOP, STEP_H)
    summary = {}
    series = {}
    for sk, s in SITES.items():
        for tname, tid in TARGETS.items():
            azA, elA, rA = ms.sky_positions(tname, s["lat"], s["lon"], ets)
            azB, elB, rB = ms.sky_positions_spice_azl(tname, s["lat"], s["lon"], ets)
            tC, azC, elC, rC = horizons(tid, s["lat"], s["lon"], START, STOP)
            assert len(tC) == len(ets), (len(tC), len(ets))
            sepAB = ang_sep(azA, elA, azB, elB) * 3600  # arcsec
            sepAC = ang_sep(azA, elA, azC, elC) * 3600
            res = {
                "n_times": int(len(ets)),
                "A_vs_B_max_direction_diff_arcsec": float(sepAB.max()),
                "A_vs_Horizons_max_direction_diff_arcsec": float(sepAC.max()),
                "A_vs_Horizons_max_elevation_diff_arcsec": float(np.abs(elA - elC).max() * 3600),
                "A_vs_Horizons_max_range_diff_km": float(np.abs(rA - rC).max()),
                "elevation_min_deg": float(elA.min()),
                "elevation_max_deg": float(elA.max()),
                "fraction_above_flat_horizon": float((elA > 0).mean()),
            }
            summary[f"{sk}/{tname}"] = res
            series[(sk, tname)] = (elA, azA, elC)
            print(f"{s['name']:32s} {tname:5s}  "
                  f"ours vs SPICE-azl {res['A_vs_B_max_direction_diff_arcsec']:.2e}\"  "
                  f"ours vs Horizons {res['A_vs_Horizons_max_direction_diff_arcsec']:.2f}\" "
                  f"(range {res['A_vs_Horizons_max_range_diff_km']:.3f} km)  "
                  f"elev {res['elevation_min_deg']:+.2f}..{res['elevation_max_deg']:+.2f} deg")

    (ROOT / "results" / "step1_validation.json").write_text(json.dumps(summary, indent=2))

    # ---- Figure 1: a year of Sun and Earth elevation at the Shackleton-rim site ----
    days = (ets - ets[0]) / 86400.0
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    for a, tname, col in ((ax[0], "SUN", "tab:orange"), (ax[1], "EARTH", "tab:blue")):
        elA, _, elC = series[("shackleton_rim", tname)]
        a.plot(days, elA, color=col, lw=0.9, label="our code (SPICE)")
        a.plot(days[::48], elC[::48], "k.", ms=2.5, label="JPL Horizons (every 2 days)")
        a.axhline(0, color="gray", lw=0.8)
        a.set_ylabel(f"{tname.title()} elevation (deg)")
        a.legend(loc="upper right", fontsize=8)
        a.grid(alpha=0.3)
    ax[0].set_title("Near Shackleton rim (89.9°S): elevation above a flat horizon, 2027")
    ax[1].set_xlabel("day of 2027")
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "step1_shackleton_year.png", dpi=130)

    # ---- Figure 2: sky plot (azimuth vs elevation) for one lunar day ----
    n = int(29.5 * 24 / STEP_H)  # one synodic month = one full lunar day/night cycle
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for tname, col in (("SUN", "tab:orange"), ("EARTH", "tab:blue")):
        elA, azA, _ = series[("shackleton_rim", tname)]
        ax.scatter(azA[:n], elA[:n], s=2, color=col,
                   label=f"{tname.title()} (hourly, 1 Jan + 29.5 days)")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlim(0, 360)
    ax.set_xticks(range(0, 361, 45))
    ax.set_xlabel("azimuth (deg from north, towards east)")
    ax.set_ylabel("elevation (deg)")
    ax.set_title("Shackleton-rim sky over one lunar day: the Sun circles the horizon, "
                 "Earth bobs up and down near north")
    ax.legend(fontsize=8, loc="lower center")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "step1_shackleton_sky.png", dpi=130)

    # ---- Figure 3: worst-case difference vs Horizons, every site and target ----
    labels, worst = [], []
    for key, r in summary.items():
        sk, tname = key.split("/")
        labels.append(f"{SITES[sk]['name']}\n{tname.title()}")
        worst.append(r["A_vs_Horizons_max_direction_diff_arcsec"])
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(range(len(worst)), worst, color="tab:green")
    # Horizons prints angles to 6 decimals of a degree: rounding is up to 0.0018" per angle,
    # i.e. up to ~0.0025" in direction. The rest (a few thousandths of an arcsec) comes from
    # DE441 vs DE440 and tiny effects Horizons includes (gravitational light bending).
    ax.axhline(0.0018 * 2 ** 0.5, color="k", ls="--", lw=1,
               label="largest error from Horizons rounding its printed values")
    ax.set_xticks(range(len(worst)), labels, fontsize=7)
    ax.set_ylabel("worst direction difference (arcsec)")
    ax.set_title("Ours vs JPL Horizons, every hour of 2027 (8,760 times per bar)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "step1_vs_horizons.png", dpi=130)
    print("saved figures and results/step1_validation.json")


if __name__ == "__main__":
    main()
