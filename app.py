"""Lunar Landing Site Navigator: Streamlit app (block 4).

Run:  streamlit run app.py
Everything is computed locally from NASA data (works offline once data/ and kernels/ exist).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import moon_sky as ms
import ops
import sites as site_db
import terrain as tr

ROOT = Path(__file__).resolve().parent
SUN_C, EARTH_C, TERRAIN_C = "#f5a623", "#2f7fd8", "#6b6b6b"
SITE_COLORS = ["#e4572e", "#b388eb", "#17bebb", "#f2c14e"]

st.set_page_config(page_title="Lunar Landing Site Navigator", page_icon="🌘", layout="wide")

# The app has its own dark theme; ask the Dark Reader browser extension not to recolour it
# (it turned the plot legends into white text on a light box).
import streamlit.components.v1 as components
components.html("""<script>
const d = window.parent.document;
if (!d.querySelector('meta[name="darkreader-lock"]')) {
  const m = d.createElement('meta'); m.name = 'darkreader-lock'; d.head.appendChild(m);
}
</script>""", height=0)


# ======================================================================================
# Cached computations
# ======================================================================================
@st.cache_resource
def get_dem():
    return tr.CompositeDEM()


@st.cache_data(show_spinner=False)
def get_horizon(lat, lon, mast_m, n_az=720):
    az, hor, ground = tr.horizon_profile(get_dem(), lat, lon, mast_m, n_az=n_az)
    return az, hor, ground


@st.cache_data(show_spinner=False)
def get_vectors(start_utc, stop_utc, step_h):
    ets = ms.time_grid(start_utc, stop_utc, step_h)
    return ets, {t: ms.target_vectors_from_moon_center(t, ets) for t in ("SUN", "EARTH")}


def make_timeline(site, start_utc, stop_utc, step_h, mast_m, array, link):
    ets, vec = get_vectors(start_utc, stop_utc, step_h)
    hz = get_horizon(site["lat"], site["lon"], mast_m)
    tl = ops.SiteTimeline(site["lat"], site["lon"], start_utc, stop_utc, step_h, mast_m,
                          array=array, link=link, horizon=hz, vectors=vec)
    return tl


@st.cache_data(show_spinner=False)
def polar_relief():
    """Shaded relief of the south-polar map, 400 m pixels (computed once)."""
    d = get_dem().polar
    z = np.asarray(d.dn[::10, ::10], dtype=float) * d.dn_scale
    gy, gx = np.gradient(z, 400.0)
    shade = np.clip(0.5 + 1.5 * (-gx * 0.7 + gy * 0.7) / np.sqrt(1 + gx ** 2 + gy ** 2), 0, 1)
    return shade, z


@st.cache_data(show_spinner=False)
def global_relief():
    """Elevation (km) at 2 px/deg, plus a light hillshade, for the whole-Moon map."""
    g = tr.GlobalDEM("ldem_16")
    z = np.asarray(g.dn[::8, ::8], dtype=float) * g.dn_scale / 1000.0     # 2 px/deg
    gy, gx = np.gradient(z * 1000.0, 15160.0)
    shade = (-gx + gy) / np.sqrt(1 + gx ** 2 + gy ** 2)
    return z + 4.0 * shade


@st.cache_data(show_spinner=False)
def neighbourhood_scan(lat, lon, mast_m, start_utc, stop_utc, step_h, spacing_m, n):
    """Sunlit and Earth-visible % on an n x n grid around a site (n_az reduced for speed)."""
    ets, vec = get_vectors(start_utc, stop_utc, step_h)
    offs = (np.arange(n) - n // 2) * spacing_m
    sun = np.zeros((n, n))
    earth = np.zeros((n, n))
    for i, dy in enumerate(offs[::-1]):           # rows: north at top
        for j, dx in enumerate(offs):
            dist = float(np.hypot(dx, dy))
            az = float(np.degrees(np.arctan2(dx, dy)))
            la, lo = tr.destination(lat, lon, [az], [dist])
            la, lo = float(la.item()), float(lo.item())
            hz = tr.horizon_profile(get_dem(), la, lo, mast_m, n_az=360)
            tl = ops.SiteTimeline(la, lo, start_utc, stop_utc, step_h, mast_m, horizon=hz,
                                  vectors=vec)
            sun[i, j] = 100 * tl.sun["visible"].mean()
            earth[i, j] = 100 * tl.comm.mean()
    return offs, sun, earth


# ======================================================================================
# Helpers
# ======================================================================================
def fmt_hours(h):
    if h is None:
        return "—"
    if h <= 0:
        return "none"
    if h < 1:
        return f"{h * 60:.0f} min"
    d, hh = divmod(h, 24)
    return f"{int(d)} d {hh:.0f} h" if d >= 1 else f"{hh:.1f} h"


def et_to_dt(ets):
    base = dt.datetime(2000, 1, 1, 12, 0, 0)       # J2000 (TDB); UTC differs by ~69 s
    return [base + dt.timedelta(seconds=float(e) - 69.184) for e in np.atleast_1d(ets)]


def show_chart(fig, **kw):
    """Plot with a legend readable in light and dark themes and in every browser: a dark
    box with light text (Firefox can force legend text white, so a light box fails)."""
    fig.update_layout(legend=dict(bgcolor="rgba(25,28,36,0.92)", bordercolor="#888",
                                  borderwidth=1, font=dict(color="#f2f2f2", size=12)))
    st.plotly_chart(fig, **kw)


def short(name, n=28):
    return name if len(name) <= n else name[: n - 1] + "…"


# ======================================================================================
# Sidebar: inputs
# ======================================================================================
st.sidebar.title("🌘 Site & date")
names = [s["name"] for s in site_db.SITES]
if "custom_sites" not in st.session_state:
    st.session_state.custom_sites = []
all_sites = site_db.SITES + st.session_state.custom_sites
choice = st.sidebar.multiselect(
    "Landing sites to compare (up to 4)", [s["name"] for s in all_sites],
    default=[names[0], names[1], names[3]], max_selections=4)

with st.sidebar.expander("➕ Add your own coordinates"):
    c_name = st.text_input("Name", "My site")
    c_lat = st.number_input("Latitude (°N, negative = south)", -90.0, 90.0, -89.30, 0.01,
                            format="%.4f")
    c_lon = st.number_input("Longitude (°E, 0-360)", 0.0, 360.0, 220.0, 0.01, format="%.4f")
    if st.button("Add site"):
        st.session_state.custom_sites.append(dict(name=c_name, group="Custom", lat=c_lat,
                                                  lon=c_lon, note="Custom coordinates.",
                                                  source="user"))
        st.rerun()

today = dt.date(2026, 11, 7)
d0 = st.sidebar.date_input("Landing date (UTC)", today)
t0 = st.sidebar.time_input("Landing time (UTC)", dt.time(10, 0))
span_opt = {"3 days": 3, "1 lunar day (29.5 days)": 29.53, "3 months": 91.3, "1 year": 365.25}
span_label = st.sidebar.selectbox("Look ahead", list(span_opt), index=1)
span_days = span_opt[span_label]
step_h = 0.25 if span_days <= 31 else (1.0 if span_days <= 100 else 2.0)
start = dt.datetime.combine(d0, t0)
stop = start + dt.timedelta(days=span_days)
START, STOP = start.strftime("%Y-%m-%dT%H:%M"), stop.strftime("%Y-%m-%dT%H:%M")

mast = st.sidebar.slider("Height of solar panel / antenna above ground (m)", 0.5, 20.0,
                         2.0, 0.5)
with st.sidebar.expander("⚙️ Lander assumptions"):
    mode_lbl = {"Vertical, turns to face the Sun (polar landers)": "vertical_tracking",
                "Flat on the deck (equatorial landers)": "horizontal",
                "Always pointed at the Sun (best case)": "two_axis"}
    mode = mode_lbl[st.selectbox("Solar panel", list(mode_lbl))]
    area = st.number_input("Panel area (m²)", 0.1, 50.0, 1.0, 0.1)
    eff = st.slider("Cell efficiency", 0.10, 0.35, 0.30, 0.01)
    load = st.number_input("Power needed to survive the dark (W)", 5.0, 2000.0, 50.0, 5.0)
    st.markdown("**Radio (X-band, 8.45 GHz)**")
    ptx = st.number_input("Transmitter power (W)", 0.5, 200.0, 10.0, 0.5)
    dish = st.number_input("Lander dish diameter (m)", 0.05, 3.0, 0.3, 0.05)
    gs = {"Commercial 12 m station (G/T 37 dB/K)": 37.0,
          "NASA Deep Space Network 34 m (G/T 53 dB/K)": 53.0}
    gt = gs[st.selectbox("Ground station on Earth", list(gs))]
array = ops.SolarArray(area_m2=area, efficiency=eff, mode=mode)
link = ops.RadioLink(tx_power_w=ptx, tx_gain_dbi=float(ops.dish_gain_dbi(dish, 8.45e9)),
                     ground_g_over_t_dbk=gt)

st.sidebar.caption("Data: NASA/JPL DE440 ephemeris (SPICE), LRO LOLA terrain. "
                   "Times are UTC.")

# ======================================================================================
# Main page
# ======================================================================================
st.title("Lunar Landing Site Navigator")
st.markdown(
    "When will a lander **see the Sun** (power) and **see Earth** (talk to home)? "
    "Pick sites and a landing date. Everything is computed from NASA's own data: "
    "the Sun and Earth from JPL's ephemeris, the skyline from the LRO laser altimeter.")

sel = [s for s in all_sites if s["name"] in choice]
if not sel:
    st.info("Pick at least one site in the sidebar.")
    st.stop()

with st.spinner("Computing skylines and Sun/Earth paths…"):
    tls = [make_timeline(s, START, STOP, step_h, mast, array, link) for s in sel]

# ---------------- "right now" cards ----------------
st.subheader(f"At landing: {start:%d %b %Y %H:%M} UTC")
cols = st.columns(len(sel))
et0 = tls[0].ets[0]
for col, s, tl, c in zip(cols, sel, tls, SITE_COLORS):
    with col:
        st.markdown(f"<div style='border-left:6px solid {c};padding-left:8px'>"
                    f"<b>{s['name']}</b><br><small>{s['lat']:.3f}°, {s['lon']:.3f}°E · "
                    f"ground {tl.ground_m:,.0f} m</small></div>", unsafe_allow_html=True)
        up, h = tl.time_until_change(et0, "sun")
        st.metric("☀️ Sun", "Up" if up else "Down",
                  (f"{'sets' if up else 'rises'} in {fmt_hours(h)}" if h is not None else
                   f"{'stays up' if up else 'stays down'} all {span_label.split(' (')[0]}"),
                  delta_color="off")
        up, h = tl.time_until_change(et0, "earth")
        st.metric("🌍 Earth (radio)", "In view" if up else "Hidden",
                  (f"{'Earthset' if up else 'Earthrise'} in {fmt_hours(h)}" if h is not None
                   else f"{'stays in view' if up else 'stays hidden'} all "
                        f"{span_label.split(' (')[0]}"),
                  delta_color="off")
        st.caption(f"Sun at {tl.sun['el'][0]:+.2f}° (skyline in that direction "
                   f"{tl.sun['horizon'][0]:+.2f}°) · power now {tl.power_w[0]:.0f} W")

# ---------------- comparison table ----------------
st.subheader(f"Comparison over {span_label.lower()}")
rows = []
for s, tl in zip(sel, tls):
    m = tl.summary(battery_load_w=load)
    rows.append({
        "Site": s["name"],
        "Sun visible": f"{m['sun_visible_pct']:.0f} %",
        "Earth visible": f"{m['earth_visible_pct']:.0f} %",
        "Sun AND Earth": f"{m['sun_and_earth_pct']:.0f} %",
        "Highest Sun": f"{m['max_sun_el_deg']:.1f}°",
        "Mean power": f"{m['mean_power_w']:.0f} W",
        "Longest darkness": fmt_hours(m["longest_dark_h"]),
        "Battery to survive it": f"{m['battery_kwh_for_load']:.1f} kWh",
        "Longest radio silence": fmt_hours(m["longest_no_earth_h"]),
    })
st.dataframe(pd.DataFrame(rows).set_index("Site"), width="stretch")

tab_sky, tab_time, tab_dates, tab_move, tab_map, tab_about = st.tabs(
    ["🔭 Sky view", "📈 Timeline", "📅 Best landing dates", "🧭 Move the site", "🗺️ Map",
     "ℹ️ How it works"])

# ---------------- sky view ----------------
with tab_sky:
    k = st.radio("Site", range(len(sel)), format_func=lambda i: sel[i]["name"],
                 horizontal=True, key="sky_site")
    tl = tls[k]
    fig = go.Figure()
    az = np.concatenate([tl.az_h, [360.0]])
    hz = np.concatenate([tl.hor, [tl.hor[0]]])
    lo_y = max(-10.0, min(-3.0, float(np.nanmin(hz)) - 1,
                          float(np.nanmin(tl.earth["el"])) - 0.5,
                          float(np.nanmin(tl.sun["el"])) - 0.5))
    fig.add_trace(go.Scatter(x=az, y=np.full_like(az, lo_y), mode="lines",
                             line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=az, y=hz, fill="tonexty", mode="lines", name="terrain",
                             line=dict(color=TERRAIN_C), fillcolor="rgba(110,110,110,0.75)",
                             hovertemplate="az %{x:.1f}°<br>skyline %{y:.2f}°"))
    every = max(1, len(tl.ets) // 3000)
    times = et_to_dt(tl.ets[::every])
    for name, d, c in (("Sun", tl.sun, SUN_C), ("Earth", tl.earth, EARTH_C)):
        vis = (d["visible"] if name == "Sun" else tl.comm)[::every]
        a_, e_ = d["az"][::every], d["el"][::every]
        tt = np.array([t.strftime("%d %b %H:%M") for t in times])
        fig.add_trace(go.Scatter(x=a_[vis], y=e_[vis], mode="markers", name=f"{name}: visible",
                                 marker=dict(size=4, color=c), text=tt[vis],
                                 hovertemplate="%{text}<br>az %{x:.1f}°, el %{y:.2f}°"))
        fig.add_trace(go.Scatter(x=a_[~vis], y=e_[~vis], mode="markers",
                                 name=f"{name}: behind terrain",
                                 marker=dict(size=4, color="#a9b1bd"),
                                 text=tt[~vis], hovertemplate="%{text}<br>az %{x:.1f}°, el %{y:.2f}°"))
        fig.add_trace(go.Scatter(x=[d["az"][0]], y=[d["el"][0]], mode="markers+text",
                                 marker=dict(size=16, color=c, symbol="star",
                                             line=dict(color="black", width=1)),
                                 text=[f"{name} at landing"], textposition="top center",
                                 name=f"{name} at landing"))
    top = max(8.0, float(np.nanmax(tl.sun["el"])) + 2, float(np.nanmax(hz)) + 2)
    top = min(top, 90)
    fig.update_layout(height=480, xaxis=dict(title="direction (azimuth, ° from north)",
                                             range=[0, 360], tickvals=list(range(0, 361, 45)),
                                             ticktext=["N", "NE", "E", "SE", "S", "SW", "W",
                                                       "NW", "N"]),
                      yaxis=dict(title="height above horizontal (°)", range=[lo_y, top]),
                      legend=dict(orientation="h", y=-0.2), margin=dict(t=30))
    show_chart(fig, width="stretch")
    st.caption("Grey = the skyline seen from the lander, from LRO laser-altimeter terrain. "
               "Dots = where the Sun and Earth are over the chosen period; pale dots are "
               "hidden behind terrain. At the poles the Sun skims the horizon, so a few "
               "metres of terrain decide everything.")

# ---------------- timeline ----------------
with tab_time:
    t = et_to_dt(tls[0].ets)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.36, 0.32, 0.32],
                        subplot_titles=("When is the Sun / Earth visible?",
                                        "Solar array power (W)", "Max downlink rate (Mbit/s)"))
    for i, (s, tl, c) in enumerate(zip(sel, tls, SITE_COLORS)):
        y0 = len(sel) - i
        fig.add_trace(go.Scatter(x=t, y=np.where(tl.sun["visible"], y0 + 0.15, None),
                                 mode="lines", line=dict(color=SUN_C, width=9),
                                 name=f"Sun · {short(s['name'])}", legendgroup=str(i),
                                 showlegend=False, connectgaps=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=np.where(tl.comm, y0 - 0.15, None),
                                 mode="lines", line=dict(color=EARTH_C, width=9),
                                 name=f"Earth · {short(s['name'])}", legendgroup=str(i),
                                 showlegend=False, connectgaps=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=tl.power_w, mode="lines", line=dict(color=c),
                                 name=short(s["name"], 40), legendgroup=str(i)), row=2, col=1)
        fig.add_trace(go.Scatter(x=t, y=tl.rate_bps / 1e6, mode="lines", line=dict(color=c),
                                 showlegend=False, legendgroup=str(i)), row=3, col=1)
    fig.update_yaxes(tickvals=[len(sel) - i for i in range(len(sel))],
                     ticktext=[short(s["name"], 22) for s in sel], range=[0.4, len(sel) + 0.6],
                     row=1, col=1)
    fig.update_layout(height=640, legend=dict(orientation="h", y=-0.08), margin=dict(t=40))
    show_chart(fig, width="stretch")
    st.caption("Top: orange = Sun visible, blue = Earth visible (radio contact possible).")

# ---------------- best landing dates ----------------
with tab_dates:
    st.markdown("**What if the launch slips?** For every possible landing day in the next "
                "year, how much sunlight and Earth contact would a mission of a given length get?")
    mission_days = st.slider("Mission length on the surface (days)", 1, 60, 14)
    y_start = START
    y_stop = (start + dt.timedelta(days=365 + mission_days)).strftime("%Y-%m-%dT%H:%M")
    with st.spinner("Scanning a year of landing dates…"):
        ets_y, vec_y = get_vectors(y_start, y_stop, 2.0)
        n_m = int(mission_days * 12)
        days_idx = np.arange(0, len(ets_y) - n_m, 12)
        figd = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                             subplot_titles=("Sun visible during the mission (%)",
                                             "Earth visible during the mission (%)"))
        best_rows = []
        for i, (s, c) in enumerate(zip(sel, SITE_COLORS)):
            hz = get_horizon(s["lat"], s["lon"], mast)
            tly = ops.SiteTimeline(s["lat"], s["lon"], y_start, y_stop, 2.0, mast,
                                   array=array, link=link, horizon=hz, vectors=vec_y)
            cs = np.concatenate([[0], np.cumsum(tly.sun["visible"])])
            ce = np.concatenate([[0], np.cumsum(tly.comm)])
            sun_pct = 100 * (cs[days_idx + n_m] - cs[days_idx]) / n_m
            earth_pct = 100 * (ce[days_idx + n_m] - ce[days_idx]) / n_m
            dd = et_to_dt(ets_y[days_idx])
            figd.add_trace(go.Scatter(x=dd, y=sun_pct, line=dict(color=c),
                                      name=short(s["name"], 40), legendgroup=str(i)), 1, 1)
            figd.add_trace(go.Scatter(x=dd, y=earth_pct, line=dict(color=c), showlegend=False,
                                      legendgroup=str(i)), 2, 1)
            score = sun_pct + 0.5 * earth_pct
            b = int(np.argmax(score))
            best_rows.append({"Site": s["name"], "Best landing day": dd[b].strftime("%d %b %Y"),
                              "Sun": f"{sun_pct[b]:.0f} %", "Earth": f"{earth_pct[b]:.0f} %",
                              "Worst day": dd[int(np.argmin(score))].strftime("%d %b %Y"),
                              "Sun (worst)": f"{sun_pct[int(np.argmin(score))]:.0f} %"})
        figd.update_yaxes(range=[0, 105])
        figd.update_layout(height=520, legend=dict(orientation="h", y=-0.12), margin=dict(t=40))
    show_chart(figd, width="stretch")
    st.dataframe(pd.DataFrame(best_rows).set_index("Site"), width="stretch")
    st.caption("'Best' = most sunlight, with Earth contact counted half. Starts at the landing "
               "date in the sidebar.")

# ---------------- move the site ----------------
with tab_move:
    st.markdown("**Small moves, big changes.** Sunlight and Earth visibility on a grid around "
                "a site, over the look-ahead period. At the pole a few hundred metres can turn a "
                "sunny ridge into a shadowed slope.")
    k2 = st.radio("Site", range(len(sel)), format_func=lambda i: sel[i]["name"],
                  horizontal=True, key="move_site")
    spacing = st.select_slider("Grid spacing (m)", [100, 200, 500, 1000, 2000], value=500)
    if st.button("Compute 9 × 9 grid (about 20-40 s)"):
        s = sel[k2]
        with st.spinner("Computing 81 skylines…"):
            offs, sun, earth = neighbourhood_scan(s["lat"], s["lon"], mast, START, STOP,
                                                  step_h, spacing, 9)
        c1, c2 = st.columns(2)
        for colw, z, title, scale in ((c1, sun, "Sun visible (%)", "YlOrBr_r"),
                                      (c2, earth, "Earth visible (%)", "Blues_r")):
            fh = go.Figure(go.Heatmap(z=z, x=offs, y=offs[::-1], colorscale=scale,
                                      zmin=0, zmax=100, text=np.round(z).astype(int),
                                      texttemplate="%{text}", colorbar=dict(title="%")))
            fh.add_trace(go.Scatter(x=[0], y=[0], mode="markers",
                                    marker=dict(symbol="x", size=14, color="red"),
                                    name="site", showlegend=False))
            fh.update_layout(title=title, height=430, xaxis_title="metres east",
                             yaxis_title="metres north", yaxis_scaleanchor="x")
            colw.plotly_chart(fh, width="stretch")

# ---------------- map ----------------
with tab_map:
    polar_sel = [(s, c) for s, c in zip(sel, SITE_COLORS) if s["lat"] < -80.2]
    other_sel = [(s, c) for s, c in zip(sel, SITE_COLORS) if s["lat"] >= -80.2]
    if polar_sel:
        shade, z = polar_relief()
        d = get_dem().polar
        n = shade.shape[0]
        half = n / 2 * 0.4      # km
        far = max(np.hypot(*[(v - o) * d.scale / 1000 for v, o in
                             zip(d.latlon_to_pix(s["lat"], s["lon"]), (d.l0, d.s0))])
                  for s, _ in polar_sel)
        ext = st.slider("Zoom: half-width of map (km)", 20, 300,
                        int(min(300, max(40, np.ceil((far + 25) / 10) * 10))), 10)
        fm = go.Figure(go.Heatmap(z=shade[::-1], x=np.linspace(-half, half, n),
                                  y=np.linspace(-half, half, n), colorscale="gray",
                                  showscale=False, hoverinfo="skip"))
        for s, c in polar_sel:
            r, cc = d.latlon_to_pix(s["lat"], s["lon"])
            xk = (cc - d.s0) * d.scale / 1000
            yk = -(r - d.l0) * d.scale / 1000
            fm.add_trace(go.Scatter(x=[xk], y=[yk], mode="markers+text", text=[short(s["name"], 30)],
                                    textposition="top center", textfont=dict(color=c, size=13),
                                    marker=dict(size=13, color=c, line=dict(color="white", width=2)),
                                    showlegend=False))
        fm.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["South pole"],
                                marker=dict(symbol="cross", size=10, color="white"),
                                textfont=dict(color="white"), showlegend=False))
        fm.update_layout(height=700, width=760, xaxis=dict(range=[-ext, ext], title="km"),
                         yaxis=dict(range=[-ext, ext], title="km"),
                         title="South pole (LRO LOLA terrain, polar view; 0° E is up)")
        show_chart(fm, width="content")
    if other_sel or not polar_sel:
        g = global_relief()
        fg = go.Figure(go.Heatmap(z=g, x=np.linspace(0, 360, g.shape[1]),
                                  y=np.linspace(90, -90, g.shape[0]), colorscale="gray",
                                  zmin=-6, zmax=6, showscale=False, hoverinfo="skip"))
        for s, c in (other_sel or [(s, c) for s, c in zip(sel, SITE_COLORS)]):
            fg.add_trace(go.Scatter(x=[s["lon"]], y=[s["lat"]], mode="markers+text",
                                    text=[short(s["name"], 30)], textposition="top center",
                                    textfont=dict(color=c, size=13),
                                    marker=dict(size=12, color=c, line=dict(color="white", width=2)),
                                    showlegend=False))
        fg.add_vline(x=90, line=dict(color="white", dash="dot"))
        fg.add_vline(x=270, line=dict(color="white", dash="dot"))
        fg.update_layout(height=560, width=1050,
                         xaxis=dict(title="longitude (°E)", range=[0, 360],
                                    tickvals=list(range(0, 361, 30))),
                         yaxis=dict(title="latitude (°)", range=[-90, 90]),
                         title="Whole Moon (LOLA elevation). Near side faces Earth: 270°E → 0° → 90°E; "
                               "between the dotted lines is the far side")
        show_chart(fg, width="content")
    for s in sel:
        st.markdown(f"**{s['name']}**: {s.get('note', '')}  \n<small>Coordinates: "
                    f"{s.get('source', '')}</small>", unsafe_allow_html=True)

# ---------------- about ----------------
with tab_about:
    st.markdown("""
### How it works
1. **Sun and Earth positions** from NASA/JPL's DE440 planetary ephemeris and the Moon's
   orientation (SPICE), including the Moon's wobble (libration). Checked against JPL Horizons:
   **0.006 arcsec**.
2. **The skyline**: from the lander, rays are traced outward in 720 directions over NASA's LRO
   laser-altimeter terrain (40 m pixels near the south pole, 474 m elsewhere), including the
   Moon's curvature. Checked against NASA's own south-pole sunlight and Earth-visibility maps:
   **median difference 0.5 percentage points (Sun) and 0.1 (Earth)** over 142 sites.
3. **Visible** means any part of the Sun's disc above the skyline (power is scaled by how much
   of it). For radio, Earth's centre must be above the skyline.
4. **Power** = sunlight (1361 W/m² at 1 AU) × area × efficiency × panel angle × visible part
   of the disc. **Radio** = a standard link budget (transmitter, dishes, 380 000 km of space).

### Why the south pole is so different
The Moon's axis is tilted only 1.5°, so at the pole the Sun never climbs more than about
1.5° above the horizontal and circles the sky once a month. A crater wall a few hundred metres
high can hide it for weeks, while a ridge can see it 90 % of the time. Earth sits low on the
horizon and bobs up and down by about 7° every month as the Moon nods, so radio contact comes
and goes too.

### Limits
Hourly (or finer) steps; no thermal model; assumes a ground station on Earth can always see
the Moon; panel and radio values are typical assumptions, not those of a real mission.
""")
