"""Sun and Earth positions in the sky of a point on the Moon.

Block 1 of the Lunar Landing Site Navigator.

Everything comes from NASA/JPL SPICE data (kernels/):
  de440s.bsp              where the Sun, Earth and Moon are (JPL planetary ephemeris DE440)
  moon_pa_de440_200625.bpc how the Moon is rotating, including its small wobbles (libration)
  moon_de440_250416.tf    defines MOON_ME, the "mean Earth" lunar frame that LRO/LOLA maps use
  pck00011.tpc            Moon radius (1737.4 km sphere)
  naif0012.tls            leap seconds (UTC <-> TDB conversion)

A site is given by latitude, east longitude (degrees, MOON_ME frame) and height above the
1737.4 km reference sphere (km). For each time we return, for the Sun and the Earth:
  azimuth   degrees, measured from local north towards east (same convention as JPL Horizons)
  elevation degrees above the local horizontal plane (ignoring terrain; that's block 2)
  range     km
Positions are "apparent": corrected for light travel time and stellar aberration, i.e. where
you would actually see the object from that spot.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import spiceypy as sp

KERNEL_DIR = Path(__file__).resolve().parent / "kernels"
KERNELS = [
    "naif0012.tls",
    "pck00011.tpc",
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
    "de440s.bsp",
]
FRAME = "MOON_ME"
MOON_RADIUS_KM = 1737.4

_loaded = False


def load_kernels() -> None:
    """Load the SPICE files once per Python session."""
    global _loaded
    if _loaded:
        return
    for k in KERNELS:
        path = KERNEL_DIR / k
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run download_kernels.py")
        sp.furnsh(str(path))
    _loaded = True


def utc_to_et(utc: str) -> float:
    """'2027-01-01T00:00' -> SPICE ephemeris time (seconds past J2000 TDB)."""
    load_kernels()
    return sp.str2et(utc)


def time_grid(start_utc: str, stop_utc: str, step_hours: float) -> np.ndarray:
    """Evenly spaced ephemeris times from start to stop (inclusive)."""
    t0, t1 = utc_to_et(start_utc), utc_to_et(stop_utc)
    dt = step_hours * 3600.0
    n = int(round((t1 - t0) / dt)) + 1
    return t0 + dt * np.arange(n)


def site_position(lat_deg: float, lon_deg: float, height_km: float = 0.0) -> np.ndarray:
    """Site position vector in MOON_ME (km). On a sphere, latitude is simply geocentric."""
    return sp.latrec(MOON_RADIUS_KM + height_km, np.radians(lon_deg), np.radians(lat_deg))


def enu_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Rows are the local East, North, Up unit vectors in MOON_ME.

    Multiplying a MOON_ME vector by this matrix gives its (east, north, up) components.
    """
    la, lo = np.radians(lat_deg), np.radians(lon_deg)
    east = np.array([-np.sin(lo), np.cos(lo), 0.0])
    north = np.array([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)])
    up = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    return np.vstack([east, north, up])


def sky_positions(target: str, lat_deg: float, lon_deg: float, ets, height_km: float = 0.0):
    """Azimuth, elevation (deg) and range (km) of `target` ('SUN' or 'EARTH') from the site.

    Method: SPICE gives the apparent vector from the fixed site to the target, expressed in
    MOON_ME. We rotate it into local East-North-Up axes and read off the two angles:
        elevation = asin(up / |v|),  azimuth = atan2(east, north)
    """
    load_kernels()
    ets = np.atleast_1d(np.asarray(ets, dtype=float))
    r_site = site_position(lat_deg, lon_deg, height_km)
    R = enu_matrix(lat_deg, lon_deg)
    az = np.empty(ets.size)
    el = np.empty(ets.size)
    rng = np.empty(ets.size)
    for i, et in enumerate(ets):
        # spkcpo: observer at a Constant POsition on the Moon, frame rotates with the Moon.
        # 'OBSERVER' = the frame orientation is evaluated at the observation time.
        state, _lt = sp.spkcpo(target, et, FRAME, "OBSERVER", "LT+S", r_site, "MOON", FRAME)
        e, n, u = R @ np.asarray(state[:3])
        d = np.sqrt(e * e + n * n + u * u)
        rng[i] = d
        el[i] = np.degrees(np.arcsin(u / d))
        az[i] = np.degrees(np.arctan2(e, n)) % 360.0
    return az, el, rng


def sky_positions_spice_azl(target: str, lat_deg: float, lon_deg: float, ets, height_km=0.0):
    """Same quantity computed by SPICE's own azimuth/elevation routine (azlcpo).

    Used only as an independent check of sky_positions() (different code path inside SPICE:
    it builds the local frame itself from the reference ellipsoid).
    """
    load_kernels()
    ets = np.atleast_1d(np.asarray(ets, dtype=float))
    r_site = site_position(lat_deg, lon_deg, height_km)
    out = np.empty((ets.size, 3))
    for i, et in enumerate(ets):
        azlsta, _lt = sp.azlcpo("ELLIPSOID", target, et, "LT+S", False, True,
                                r_site, "MOON", FRAME)
        rng, az, el = azlsta[0], azlsta[1], azlsta[2]
        out[i] = (np.degrees(az) % 360.0, np.degrees(el), rng)
    return out[:, 0], out[:, 1], out[:, 2]


TARGET_RADIUS_KM = {"SUN": 695700.0, "EARTH": 6371.0}


def target_vectors_from_moon_center(target: str, ets) -> np.ndarray:
    """Apparent target position seen from the Moon's centre, MOON_ME frame, km (n, 3).
    Computed once and reused for many sites (fast path for long time spans)."""
    load_kernels()
    ets = np.atleast_1d(np.asarray(ets, dtype=float))
    pos, _lt = sp.spkpos(target, ets, FRAME, "LT+S", "MOON")
    return np.asarray(pos)


def sky_from_vectors(target_vecs: np.ndarray, lat_deg, lon_deg, height_km=0.0):
    """Azimuth, elevation (deg), range (km) for one site from precomputed centre vectors.

    The site sits ~1737 km from the Moon's centre, so we subtract its position (this is the
    parallax: up to 0.26 deg for Earth, negligible for the Sun). The tiny difference in
    light time between the centre and the site (~6 ms) is ignored; step2_validate.py checks
    that this agrees with the exact sky_positions().
    """
    v = target_vecs - site_position(lat_deg, lon_deg, height_km)[None, :]
    enu = v @ enu_matrix(lat_deg, lon_deg).T
    rng = np.linalg.norm(enu, axis=1)
    el = np.degrees(np.arcsin(enu[:, 2] / rng))
    az = np.degrees(np.arctan2(enu[:, 0], enu[:, 1])) % 360.0
    return az, el, rng


def et_to_utc(ets, prec: int = 0):
    load_kernels()
    return [sp.et2utc(float(e), "ISOC", prec) for e in np.atleast_1d(ets)]
