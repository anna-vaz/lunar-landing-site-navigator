"""Block 3: power and communications for a lunar site.

Builds on block 1 (Sun/Earth positions) and block 2 (terrain horizon) and turns them into
the numbers a mission planner needs:

  * how much of the Sun's disc is above the terrain, and the resulting solar-array power
  * sunlight / Earth-visibility windows, and "time until sunset / Earthset" from any moment
  * the longest dark period (which sizes the battery)
  * a direct-to-Earth radio link budget: the maximum data rate the link supports

All physical inputs (panel area, efficiency, antenna sizes, ...) are explicit parameters
with stated default assumptions, so the user can change them in the app.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import moon_sky as ms
import terrain as tr

AU_KM = 149597870.7
SOLAR_CONSTANT = 1361.0          # W/m^2 at 1 AU (total solar irradiance)
C_LIGHT = 299792458.0
K_BOLTZMANN_DB = -228.6          # 10 log10(1.380649e-23 J/K)


# ----------------------------------------------------------------------------------------
# Partial visibility of a disc behind a horizon
# ----------------------------------------------------------------------------------------
def disc_fraction_above(center_el, radius, horizon_el):
    """Fraction of a disc (Sun or Earth) that is above the horizon line.

    Treats the horizon as a straight line across the disc (the Sun is only 0.53 deg wide).
    u = position of the horizon line relative to the disc centre, in disc radii; the area of
    the circular segment above a chord at u is  (acos(u) - u sqrt(1 - u^2)) / pi.
    """
    u = np.clip((np.asarray(horizon_el) - np.asarray(center_el)) / np.asarray(radius), -1, 1)
    return (np.arccos(u) - u * np.sqrt(1 - u * u)) / np.pi


# ----------------------------------------------------------------------------------------
# Solar power
# ----------------------------------------------------------------------------------------
@dataclass
class SolarArray:
    """Solar array assumptions (defaults: a small CLPS-class lander).

    mode: 'vertical_tracking' : vertical panel turned to face the Sun's azimuth (typical at the
                                poles, where the Sun is always near the horizon)
          'vertical_fixed'    : vertical panel facing a fixed azimuth `azimuth_deg`
          'horizontal'        : flat panel on the deck (typical for equatorial landers)
          'two_axis'          : always pointed at the Sun (upper bound)
    """
    area_m2: float = 1.0
    efficiency: float = 0.30          # triple-junction GaAs cells, beginning of life
    mode: str = "vertical_tracking"
    azimuth_deg: float = 0.0

    def cos_incidence(self, sun_az, sun_el):
        el = np.radians(sun_el)
        if self.mode == "vertical_tracking":
            return np.clip(np.cos(el), 0, None)
        if self.mode == "vertical_fixed":
            return np.clip(np.cos(el) * np.cos(np.radians(sun_az - self.azimuth_deg)), 0, None)
        if self.mode == "horizontal":
            return np.clip(np.sin(el), 0, None)
        if self.mode == "two_axis":
            return np.ones_like(el)
        raise ValueError(self.mode)

    def power_w(self, sun_az, sun_el, sun_range_km, disc_fraction):
        flux = SOLAR_CONSTANT * (AU_KM / np.asarray(sun_range_km)) ** 2
        return flux * self.area_m2 * self.efficiency * self.cos_incidence(sun_az, sun_el) \
            * disc_fraction


# ----------------------------------------------------------------------------------------
# Direct-to-Earth link budget
# ----------------------------------------------------------------------------------------
def dish_gain_dbi(diameter_m, freq_hz, efficiency=0.55):
    lam = C_LIGHT / freq_hz
    return 10 * np.log10(efficiency * (np.pi * diameter_m / lam) ** 2)


@dataclass
class RadioLink:
    """Downlink assumptions. Defaults: X-band, 10 W, 0.3 m dish on the lander, received by a
    commercial 12 m class ground station (G/T ~37 dB/K). For a NASA Deep Space Network 34 m
    antenna use G/T ~53 dB/K. All values are typical, not mission-specific."""
    freq_hz: float = 8.45e9
    tx_power_w: float = 10.0
    tx_gain_dbi: float = field(default_factory=lambda: float(dish_gain_dbi(0.3, 8.45e9)))
    tx_losses_db: float = 2.0         # cables, pointing error
    ground_g_over_t_dbk: float = 37.0  # 12 m class station at X-band (DSN 34 m: ~53)
    other_losses_db: float = 1.0      # polarisation, etc. (no atmosphere on the Moon side)
    required_ebn0_db: float = 2.5     # coded BPSK (e.g. rate-1/2 turbo/LDPC + margin for loss)
    margin_db: float = 3.0
    earth_mask_deg: float = 0.0       # Earth's centre must be this far above the terrain

    def budget(self, range_km):
        """Return the budget terms (dB) and the maximum supported data rate (bit/s)."""
        lam = C_LIGHT / self.freq_hz
        d = np.asarray(range_km) * 1e3
        fspl = 20 * np.log10(4 * np.pi * d / lam)
        eirp = 10 * np.log10(self.tx_power_w) + self.tx_gain_dbi - self.tx_losses_db
        c_n0 = eirp - fspl - self.other_losses_db + self.ground_g_over_t_dbk - K_BOLTZMANN_DB
        rate_db = c_n0 - self.required_ebn0_db - self.margin_db
        return dict(eirp_dbw=eirp, free_space_loss_db=fspl, c_over_n0_dbhz=c_n0,
                    max_rate_bps=10 ** (rate_db / 10))


# ----------------------------------------------------------------------------------------
# Windows ("when is it sunny / when can we talk") and time until sunset / Earthset
# ----------------------------------------------------------------------------------------
def windows(ets, mask):
    """List of (start_et, end_et) intervals where mask is True (edges at sample times)."""
    mask = np.asarray(mask, bool)
    if not mask.any():
        return []
    d = np.diff(mask.astype(int))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0])
    if mask[0]:
        starts = [0] + starts
    if mask[-1]:
        ends = ends + [len(mask) - 1]
    return [(float(ets[s]), float(ets[e])) for s, e in zip(starts, ends)]


def longest_run_hours(ets, mask):
    """Longest continuous stretch where mask is True, in hours."""
    w = windows(ets, mask)
    return max((e - s) / 3600.0 for s, e in w) if w else 0.0


# ----------------------------------------------------------------------------------------
# Everything for one site and date range
# ----------------------------------------------------------------------------------------
class SiteTimeline:
    """Sun/Earth visibility, power and link rate for one site over a time span."""

    def __init__(self, lat, lon, start_utc, stop_utc, step_h=1.0, mast_m=2.0, dem=None,
                 array: SolarArray | None = None, link: RadioLink | None = None,
                 horizon=None):
        self.lat, self.lon, self.mast_m = lat, lon, mast_m
        self.array = array or SolarArray()
        self.link = link or RadioLink()
        self.ets = ms.time_grid(start_utc, stop_utc, step_h)
        if horizon is None:
            dem = dem or tr.PolarDEM()
            self.az_h, self.hor, self.ground_m = tr.horizon_profile(dem, lat, lon, mast_m)
        else:
            self.az_h, self.hor, self.ground_m = horizon
        self._compute()

    def _sky(self, target, ets):
        v = ms.target_vectors_from_moon_center(target, ets)
        az, el, rng = ms.sky_from_vectors(v, self.lat, self.lon, (self.ground_m + self.mast_m) / 1e3)
        rad = np.degrees(np.arcsin(ms.TARGET_RADIUS_KM[target] / rng))
        h = tr.horizon_at(self.az_h, self.hor, az)
        return az, el, rng, rad, h

    def _compute(self):
        az, el, rng, rad, h = self._sky("SUN", self.ets)
        self.sun = dict(az=az, el=el, range_km=rng, horizon=h,
                        fraction=disc_fraction_above(el, rad, h))
        self.sun["visible"] = self.sun["fraction"] > 0
        self.power_w = self.array.power_w(az, el, rng, self.sun["fraction"])
        az, el, rng, rad, h = self._sky("EARTH", self.ets)
        self.earth = dict(az=az, el=el, range_km=rng, horizon=h,
                          fraction=disc_fraction_above(el, rad, h))
        self.earth["visible"] = self.earth["fraction"] > 0
        self.comm = el > h + self.link.earth_mask_deg     # Earth's centre clear of terrain
        self.rate_bps = np.where(self.comm, self.link.budget(rng)["max_rate_bps"], 0.0)

    # ---- metrics ----
    def summary(self, battery_load_w=50.0):
        dt_h = np.diff(self.ets).mean() / 3600.0
        dark_h = longest_run_hours(self.ets, ~self.sun["visible"])
        silent_h = longest_run_hours(self.ets, ~self.comm)
        return dict(
            ground_height_m=float(self.ground_m),
            sun_visible_pct=100 * float(self.sun["visible"].mean()),
            earth_visible_pct=100 * float(self.comm.mean()),
            sun_and_earth_pct=100 * float((self.sun["visible"] & self.comm).mean()),
            mean_power_w=float(self.power_w.mean()),
            energy_kwh=float(self.power_w.sum() * dt_h / 1000),
            longest_dark_h=dark_h,
            battery_kwh_for_load=battery_load_w * dark_h / 1000,
            longest_no_earth_h=silent_h,
            data_gb=float(self.rate_bps.sum() * dt_h * 3600 / 8e9),   # if used whenever possible
            max_sun_el_deg=float(self.sun["el"].max()),
        )

    def time_until_change(self, et_query, which="sun", refine_s=60.0):
        """From et_query: is the Sun (or Earth link) up now, and how long until that changes?
        The change time is refined to `refine_s` seconds by re-sampling within the step."""
        mask = self.sun["visible"] if which == "sun" else self.comm
        i = int(np.clip(np.searchsorted(self.ets, et_query), 0, len(self.ets) - 1))
        now = bool(mask[i])
        j = i + np.argmax(mask[i:] != now) if (mask[i:] != now).any() else None
        if j is None:
            return now, None
        # refine between samples j-1 and j
        t_fine = np.arange(self.ets[j - 1], self.ets[j] + refine_s, refine_s)
        target = "SUN" if which == "sun" else "EARTH"
        az, el, rng, rad, h = self._sky(target, t_fine)
        m = disc_fraction_above(el, rad, h) > 0 if which == "sun" \
            else el > h + self.link.earth_mask_deg
        k = int(np.argmax(m != now)) if (m != now).any() else len(t_fine) - 1
        return now, (t_fine[k] - et_query) / 3600.0
