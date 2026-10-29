"""Block 2: the local horizon of a lunar site, from LRO/LOLA laser-altimeter terrain.

On the Moon there is no atmosphere, so what you can see is decided by geometry alone: the
terrain around you and the curvature of the Moon. For a site and every compass direction
(azimuth) we find the highest elevation angle at which terrain blocks the sky. The Sun or
Earth is visible only when it is above that terrain horizon.

Data: LOLA south-polar elevation map LDEM_80S_40M (NASA PDS), 40 m pixels, 80°S to the pole,
polar stereographic projection on the 1737.4 km sphere, MOON_ME frame (same as block 1).

Method (horizon_profile):
  1. For each azimuth, walk outward from the site along the great circle (the "straight
     line" on a sphere), at distances from 20 m up to the edge of the map.
  2. Read the terrain height at each point (bilinear interpolation of the map).
  3. Put the site and every terrain point in 3-D Moon-fixed coordinates and compute the
     elevation angle of the point as seen from the site:  asin( (Q - P) . up / |Q - P| ).
     Doing this in 3-D handles the Moon's curvature automatically: distant terrain sinks
     below the local horizontal plane.
  4. The horizon in that direction is the largest of those angles.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

R_MOON_M = 1737400.0
DATA = Path(__file__).resolve().parent / "data" / "lola"


def read_pds_label(path: Path) -> dict:
    """Minimal PDS3 label reader: KEY = VALUE pairs (numbers parsed, units dropped)."""
    out = {}
    for line in path.read_text(errors="ignore").splitlines():
        m = re.match(r"\s*([A-Z_^]+)\s*=\s*(.+?)\s*$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        val = re.sub(r"<.*?>", "", val).strip().strip('"')
        try:
            val = float(val)
        except ValueError:
            pass
        out.setdefault(key, val)  # first occurrence wins
    return out


class PolarDEM:
    """South-polar LOLA elevation map (polar stereographic, pixel-registered, int16)."""

    # Projection sign convention (verified in step2_validate.py against the independent
    # global cylindrical map LDEM_16): column grows with x, row DEcreases with y, where
    #   x = rho * sin(lon),  y = rho * cos(lon),  rho = 2 R tan(pi/4 + lat/2)   (lat < 0)
    # i.e. longitude 0 points up the image and 90E points right. Correlation with LDEM_16:
    # 0.9994 for this choice, below 0.31 for the other three.
    SX, SY = +1, -1

    def __init__(self, name: str = "ldem_80s_40m"):
        lbl = read_pds_label(DATA / f"{name}.lbl")
        self.name = name
        self.n_lines = int(lbl["LINES"])
        self.n_samples = int(lbl["LINE_SAMPLES"])
        self.scale = float(lbl["MAP_SCALE"])          # m / pixel
        self.dn_scale = float(lbl["SCALING_FACTOR"])  # m / DN
        self.l0 = float(lbl["LINE_PROJECTION_OFFSET"])
        self.s0 = float(lbl["SAMPLE_PROJECTION_OFFSET"])
        self.max_lat = float(lbl["MAXIMUM_LATITUDE"])
        self.dn = np.memmap(DATA / f"{name}.img", dtype="<i2", mode="r",
                            shape=(self.n_lines, self.n_samples))

    # ---- projection ----
    def latlon_to_pix(self, lat_deg, lon_deg):
        """(lat, lon) in degrees -> fractional (row, col), 0-based, pixel centres at integers."""
        lat = np.radians(lat_deg)
        lon = np.radians(lon_deg)
        rho = 2.0 * R_MOON_M * np.tan(np.pi / 4 + lat / 2)
        x = rho * np.sin(lon)
        y = rho * np.cos(lon)
        col = self.s0 + self.SX * x / self.scale
        row = self.l0 + self.SY * y / self.scale
        return row, col

    def pix_to_latlon(self, row, col):
        x = self.SX * (np.asarray(col, float) - self.s0) * self.scale
        y = self.SY * (np.asarray(row, float) - self.l0) * self.scale
        rho = np.hypot(x, y)
        lat = 2.0 * np.arctan(rho / (2.0 * R_MOON_M)) - np.pi / 2
        lon = np.arctan2(x, y)
        return np.degrees(lat), np.degrees(lon) % 360.0

    # ---- heights ----
    def height_pix(self, row, col):
        """Bilinear terrain height (m above 1737.4 km) at fractional pixel positions.
        NaN outside the map."""
        row = np.asarray(row, float)
        col = np.asarray(col, float)
        r0 = np.floor(row).astype(np.int64)
        c0 = np.floor(col).astype(np.int64)
        ok = (r0 >= 0) & (c0 >= 0) & (r0 < self.n_lines - 1) & (c0 < self.n_samples - 1)
        out = np.full(row.shape, np.nan)
        r0o, c0o = r0[ok], c0[ok]
        fr, fc = row[ok] - r0o, col[ok] - c0o
        d = self.dn
        h00 = d[r0o, c0o].astype(float)
        h01 = d[r0o, c0o + 1].astype(float)
        h10 = d[r0o + 1, c0o].astype(float)
        h11 = d[r0o + 1, c0o + 1].astype(float)
        out[ok] = ((1 - fr) * ((1 - fc) * h00 + fc * h01) + fr * ((1 - fc) * h10 + fc * h11))
        return out * self.dn_scale

    def height(self, lat_deg, lon_deg):
        r, c = self.latlon_to_pix(lat_deg, lon_deg)
        return self.height_pix(r, c)


class GlobalDEM:
    """Global LOLA elevation map in simple cylindrical projection (e.g. LDEM_64: 64 pixels
    per degree, ~474 m). Rows run from 90N down, columns from 0E eastward; pixel centres at
    (90 - lat) * res - 0.5 and lon * res - 0.5 (checked against LDEM_16 in step4a)."""

    def __init__(self, name: str = "ldem_64"):
        lbl = read_pds_label(DATA / f"{name}.lbl")
        self.name = name
        self.n_lines = int(lbl["LINES"])
        self.n_samples = int(lbl["LINE_SAMPLES"])
        self.res = float(lbl["MAP_RESOLUTION"])       # pixels per degree
        self.scale = float(lbl["MAP_SCALE"])          # m / pixel at the equator
        self.dn_scale = float(lbl["SCALING_FACTOR"])
        self.dn = np.memmap(DATA / f"{name}.img", dtype="<i2", mode="r",
                            shape=(self.n_lines, self.n_samples))

    def height(self, lat_deg, lon_deg):
        lat = np.asarray(lat_deg, float)
        lon = np.asarray(lon_deg, float) % 360.0
        row = np.clip((90.0 - lat) * self.res - 0.5, 0, self.n_lines - 1.001)
        col = lon * self.res - 0.5
        r0 = np.floor(row).astype(np.int64)
        c0 = np.floor(col).astype(np.int64)
        fr, fc = row - r0, col - c0
        c1 = (c0 + 1) % self.n_samples
        c0 = c0 % self.n_samples
        d = self.dn
        h = ((1 - fr) * ((1 - fc) * d[r0, c0] + fc * d[r0, c1])
             + fr * ((1 - fc) * d[r0 + 1, c0] + fc * d[r0 + 1, c1]))
        return h * self.dn_scale

    def scale_at(self, lat_deg):
        return self.scale


class CompositeDEM:
    """Best available terrain everywhere: the 40 m south-polar map south of 80.2 S, the
    global 474 m map elsewhere. This lets rays from a site at 82 S, say, run north off the
    polar map without losing terrain."""

    def __init__(self, polar: PolarDEM | None = None, glob: GlobalDEM | None = None):
        self.polar = polar or PolarDEM()
        self.glob = glob or GlobalDEM()
        self.scale = self.polar.scale

    def height(self, lat_deg, lon_deg):
        lat = np.asarray(lat_deg, float)
        lon = np.asarray(lon_deg, float)
        out = np.full(np.broadcast(lat, lon).shape, np.nan)
        lat_b, lon_b = np.broadcast_arrays(lat, lon)
        polar = lat_b <= -80.2
        if polar.any():
            out[polar] = self.polar.height(lat_b[polar], lon_b[polar])
        rest = ~np.isfinite(out)
        if rest.any():
            out[rest] = self.glob.height(lat_b[rest], lon_b[rest])
        return out

    def scale_at(self, lat_deg):
        return self.polar.scale if lat_deg <= -80.5 else self.glob.scale


def unit_vector(lat_deg, lon_deg):
    la, lo = np.radians(lat_deg), np.radians(lon_deg)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)


def destination(lat_deg, lon_deg, az_deg, dist_m):
    """Point reached by walking dist_m from (lat, lon) along the great circle with initial
    azimuth az (deg from north towards east). Broadcasts az against dist."""
    la1, lo1 = np.radians(lat_deg), np.radians(lon_deg)
    az = np.radians(np.asarray(az_deg, float))[:, None]
    dl = np.asarray(dist_m, float)[None, :] / R_MOON_M
    la2 = np.arcsin(np.sin(la1) * np.cos(dl) + np.cos(la1) * np.sin(dl) * np.cos(az))
    lo2 = lo1 + np.arctan2(np.sin(az) * np.sin(dl) * np.cos(la1),
                           np.cos(dl) - np.sin(la1) * np.sin(la2))
    return np.degrees(la2), np.degrees(lo2) % 360.0


def ray_distances(pixel_m: float, max_m: float) -> np.ndarray:
    """Sample distances along each ray: every half pixel out to 4 km, then growing by 0.5 %
    per step (far terrain needs less detail: 0.5 % of 100 km is 500 m)."""
    near = np.arange(pixel_m / 2, 4000.0, pixel_m / 2)
    far = [4000.0]
    while far[-1] < max_m:
        far.append(far[-1] * 1.005)
    return np.concatenate([near, np.array(far)])


def horizon_profile(dem, lat_deg, lon_deg, obs_height_m=2.0, n_az=720,
                    max_dist_m=350e3, min_dist_m=0.0):
    """Terrain horizon elevation (deg) for n_az azimuths 0..360 (deg from north, eastward).

    obs_height_m: eye height above the ground, e.g. a lander's solar panel or antenna.
    Returns (az_deg, horizon_deg, site_height_m).
    """
    az = np.arange(n_az) * 360.0 / n_az
    h_site = float(np.asarray(dem.height(lat_deg, lon_deg)).item())
    up = unit_vector(lat_deg, lon_deg)
    P = (R_MOON_M + h_site + obs_height_m) * up
    pixel = dem.scale_at(lat_deg) if hasattr(dem, "scale_at") else dem.scale
    d = ray_distances(pixel, max_dist_m)
    d = d[d >= min_dist_m]
    lat2, lon2 = destination(lat_deg, lon_deg, az, d)            # (n_az, n_d)
    h = dem.height(lat2, lon2)
    Q = (R_MOON_M + h)[..., None] * unit_vector(lat2, lon2)       # (n_az, n_d, 3)
    v = Q - P
    elev = np.degrees(np.arcsin((v @ up) / np.linalg.norm(v, axis=-1)))
    horizon = np.nanmax(elev, axis=1)
    return az, horizon, h_site


def horizon_bruteforce(dem: PolarDEM, lat_deg, lon_deg, obs_height_m=2.0, n_az=720,
                       radius_m=100e3, min_dist_m=1000.0, chunk_rows=400):
    """Independent check of horizon_profile: no rays and no interpolation. Take EVERY map
    pixel within radius_m, compute its exact azimuth and elevation from the site, and keep
    the highest elevation in each azimuth bin.

    Only valid beyond ~1 km (min_dist_m): a pixel very close to the site covers many azimuth
    bins but is counted in one, so the near field is under-sampled here. The near field is
    checked separately against the local slope."""
    h_site = float(dem.height(lat_deg, lon_deg))
    up = unit_vector(lat_deg, lon_deg)
    la, lo = np.radians(lat_deg), np.radians(lon_deg)
    east = np.array([-np.sin(lo), np.cos(lo), 0.0])
    north = np.cross(up, east)
    P = (R_MOON_M + h_site + obs_height_m) * up
    r0, c0 = dem.latlon_to_pix(lat_deg, lon_deg)
    rad_px = radius_m / dem.scale
    rlo, rhi = int(max(0, r0 - rad_px)), int(min(dem.n_lines, r0 + rad_px + 1))
    clo, chi = int(max(0, c0 - rad_px)), int(min(dem.n_samples, c0 + rad_px + 1))
    best = np.full(n_az, -90.0)
    cols = np.arange(clo, chi)
    for rs in range(rlo, rhi, chunk_rows):
        rows = np.arange(rs, min(rs + chunk_rows, rhi))
        RR, CC = np.meshgrid(rows, cols, indexing="ij")
        near = np.hypot(RR - r0, CC - c0)
        m = (near <= rad_px) & (near >= min_dist_m / dem.scale)
        if not m.any():
            continue
        lat2, lon2 = dem.pix_to_latlon(RR[m], CC[m])
        h = dem.dn[RR[m], CC[m]].astype(float) * dem.dn_scale
        v = (R_MOON_M + h)[:, None] * unit_vector(lat2, lon2) - P
        nv = np.linalg.norm(v, axis=1)
        el = np.degrees(np.arcsin((v @ up) / nv))
        a = np.degrees(np.arctan2(v @ east, v @ north)) % 360.0
        b = np.floor(a / (360.0 / n_az) + 0.5).astype(int) % n_az
        np.maximum.at(best, b, el)
    az = np.arange(n_az) * 360.0 / n_az
    return az, best, h_site


def horizon_at(az_profile, hor_profile, az_query):
    """Horizon elevation at arbitrary azimuths (periodic linear interpolation)."""
    azp = np.concatenate([az_profile, [360.0]])
    hp = np.concatenate([hor_profile, [hor_profile[0]]])
    return np.interp(np.asarray(az_query) % 360.0, azp, hp)


def local_slope(dem: PolarDEM, lat_deg, lon_deg, half_width_m=60.0):
    """Ground slope (deg) and the azimuth it rises towards (deg), from height differences
    half_width_m to the north/south/east/west of the site."""
    hN, hS, hE, hW = (dem.height(*destination(lat_deg, lon_deg, [a], [half_width_m])).item()
                      for a in (0.0, 180.0, 90.0, 270.0))
    dzn = (hN - hS) / (2 * half_width_m)
    dze = (hE - hW) / (2 * half_width_m)
    return np.degrees(np.arctan(np.hypot(dzn, dze))), np.degrees(np.arctan2(dze, dzn)) % 360
