"""Compact terrain for the online ("web") edition of the app.

The full edition reads 1.1 GB of LOLA maps. Free app hosting can't hold that, so
build_web_data.py cuts a small set of layers (about 100 MB) from the same maps:

  1. 40 m south-polar patches, 15 km around each curated polar site   (full detail)
  2. 474 m global-map patches, ~1.5 deg around each other curated site (full detail)
  3. the whole 80-90 S polar map at 120 m (3 x 3 block average of the 40 m map)
  4. the global map LDEM_16 at 1.9 km, everywhere

WebDEM.height() uses the finest layer that covers a point. So curated sites get the same
near-field detail as the full edition, and distant terrain (which only needs coarse detail,
because far away a 120 m pixel is a tiny angle) comes from the coarser layers.
Custom coordinates near the pole use the 120 m map. step_web_check.py compares the two
editions.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import terrain as tr

WEB = Path(__file__).resolve().parent / "data_web"


def polar_from_array(dn, l0, s0, scale, dn_scale=0.5, name="polar"):
    d = object.__new__(tr.PolarDEM)
    d.name, d.dn, d.l0, d.s0, d.scale, d.dn_scale = name, dn, l0, s0, scale, dn_scale
    d.n_lines, d.n_samples = dn.shape
    d.max_lat = -80.0
    return d


class CylPatch:
    """A rectangle of a global cylindrical map (pixel centres like GlobalDEM). NaN outside."""

    def __init__(self, dn, lat_top, lon_left, res, dn_scale=0.5, scale_m=473.802):
        self.dn, self.lat_top, self.lon_left, self.res = dn, lat_top, lon_left, res
        self.dn_scale, self.scale = dn_scale, scale_m

    def height(self, lat, lon):
        lat = np.asarray(lat, float)
        lon = np.asarray(lon, float)
        row = (self.lat_top - lat) * self.res - 0.5
        col = ((lon - self.lon_left) % 360.0) * self.res - 0.5
        n, m = self.dn.shape
        out = np.full(np.broadcast(row, col).shape, np.nan)
        row, col = np.broadcast_arrays(row, col)
        ok = (row >= 0) & (col >= 0) & (row < n - 1) & (col < m - 1)
        r0 = np.floor(row[ok]).astype(int)
        c0 = np.floor(col[ok]).astype(int)
        fr, fc = row[ok] - r0, col[ok] - c0
        d = self.dn
        out[ok] = ((1 - fr) * ((1 - fc) * d[r0, c0] + fc * d[r0, c0 + 1])
                   + fr * ((1 - fc) * d[r0 + 1, c0] + fc * d[r0 + 1, c0 + 1])) * self.dn_scale
        return out


class WebDEM:
    def __init__(self, folder: Path = WEB):
        meta = json.loads((folder / "meta.json").read_text())
        z = np.load(folder / "polar_120m.npz")
        self.polar = polar_from_array(z["dn"], float(z["l0"]), float(z["s0"]), 120.0,
                                      name="polar_120m")
        g = np.load(folder / "global_16.npz")["dn"]
        self.glob = CylPatch(g, 90.0, 0.0, 16.0, scale_m=1895.21)
        self.glob_dn = g
        self.polar_patches, self.cyl_patches = [], []
        for p in meta["polar_patches"]:
            a = np.load(folder / p["file"])
            self.polar_patches.append((p, polar_from_array(a["dn"], float(a["l0"]),
                                                           float(a["s0"]), 40.0)))
        for p in meta["cyl_patches"]:
            a = np.load(folder / p["file"])
            self.cyl_patches.append((p, CylPatch(a["dn"], float(a["lat_top"]),
                                                 float(a["lon_left"]), 64.0)))
        self.scale = 40.0

    def height(self, lat, lon):
        lat = np.asarray(lat, float)
        lon = np.asarray(lon, float)
        lat_b, lon_b = np.broadcast_arrays(lat, lon)
        out = np.full(lat_b.shape, np.nan)
        polar = lat_b <= -80.2
        for _, d in self.polar_patches:
            m = polar & ~np.isfinite(out)
            if m.any():
                out[m] = d.height(lat_b[m], lon_b[m])
        for _, d in self.cyl_patches:
            m = ~np.isfinite(out)
            if m.any():
                out[m] = d.height(lat_b[m], lon_b[m])
        m = polar & ~np.isfinite(out)
        if m.any():
            out[m] = self.polar.height(lat_b[m], lon_b[m])
        m = ~np.isfinite(out)
        if m.any():
            out[m] = self.glob.height(lat_b[m], np.asarray(lon_b[m]) % 360.0)
        return out

    def scale_at(self, lat, lon=None):
        """Pixel size at the site (sets the ray step near the site)."""
        if lon is not None:
            for p, d in self.polar_patches:
                if lat <= -80.2 and np.isfinite(d.height(lat, lon)):
                    return 40.0
            for p, d in self.cyl_patches:
                if np.isfinite(d.height(lat, lon)):
                    return 473.8
        return 120.0 if lat <= -80.2 else 1895.0

    def detail_note(self, lat, lon):
        s = self.scale_at(lat, lon)
        return {40.0: "full detail (40 m)", 473.8: "full detail (474 m)",
                120.0: "reduced detail (120 m)", 1895.0: "reduced detail (1.9 km)"}[s]
