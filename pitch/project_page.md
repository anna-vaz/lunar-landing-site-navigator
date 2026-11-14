# Project page draft (fill in on 14 Nov from 09:00, Athens time)

Fields follow the 2026 Project Submission Guide. Replace [brackets]. All text must be English.

## Project Name
Lunar Landing Site Navigator  *(optional: a distinct name, since it equals the challenge title)*

## High-Level Project Summary
We built a free web app that tells mission planners, teachers and the public, in seconds,
whether a lunar landing site will see the Sun (power) and Earth (direct communication) on a
chosen date, and for how long. It traces the real skyline of any site from NASA's LRO laser-
altimeter terrain and moves the Sun and Earth across it using JPL's planetary ephemeris. It
answers the challenge's key questions: time until sunset and Earthset, sunlight and Earth
visibility, power, battery for the longest night, the best landing date if a launch slips,
and how much moving the site a few hundred metres changes. Every part is checked against an
independent NASA source.

## Link to Project Demo
[YouTube/Drive link to the ≤30 s video]  *or*  [public link to the 5-slide PDF]

## Link to Final Project
[https://….streamlit.app]  (live app) · code: https://github.com/anna-vaz/lunar-landing-site-navigator

## Detailed Project Description
**What it does.** Pick up to four sites (16 curated: Apollo 11–17, IM-1, IM-2, Chandrayaan-3,
SLIM, Blue Ghost 1, Chang'e 4/5/6, a Shackleton ridge, Shackleton's shadowed floor) or any
coordinates, a landing date and a look-ahead period. The app shows: whether the Sun and Earth are
up and the time until sunset/Earthset; a comparison table (sunlight %, Earth %, both, mean
power, longest darkness and the battery to survive it, longest radio silence); a sky view of
the skyline with the Sun's and Earth's paths; a 3D terrain view with a time slider; a timeline
of power and downlink rate; a "best landing dates" scan for the next year; and a 9 × 9 grid
showing how sunlight and Earth visibility change around the site.

**How it works.**
1. Sun and Earth directions from the site: JPL DE440 ephemeris and the Moon's orientation
   (including libration) via NASA NAIF SPICE, rotated into local east/north/up axes.
2. Skyline: rays traced outward in 720 directions over LOLA terrain (40 m near the south
   pole, 474 m elsewhere), in 3-D so the Moon's curvature is included.
3. Visible = any part of the disc above the skyline (power scales with the visible part); for
   radio, Earth's centre above the skyline.
4. Power = 1361 W/m² × (1 AU/r)² × area × efficiency × panel angle; radio = standard X-band link
   budget. Panel and radio values are editable assumptions.

**Validation.** Sun/Earth positions agree with JPL Horizons to 0.006 arcsec (52,560 checks);
sunlight and Earth-visibility percentages agree with the NASA LOLA team's 18.6-year south-pole
maps to a median 0.5 and 0.1 percentage points (142 sites); for Chandrayaan-3 the tool gives
sunrise 21 Aug and sunset 4 Sep 2023, matching the lunar day ISRO operated in.

**Benefits.** Re-plan in minutes when a launch slips or a site changes; explains visually why
the south pole is so hard; free, open source, runs offline on a laptop.

**Tools.** Python, SpiceyPy (NASA NAIF SPICE), NumPy, Streamlit, Plotly, Matplotlib,
python-pptx; hosted on Streamlit Community Cloud.

**Next.** Thermal model, sunlit rover routes, relay-satellite coverage.

## Use of Super Intelligence (SI)  *(not shown to judges; be accurate)*
[Edit so it is true for your team.] Yes. Anthropic's Claude (via the Hermes agent) wrote most of
the code, ran the validation checks, and drafted the slides, scripts and this text, working
step by step under [Anna]'s direction; [Anna] chose the challenge, reviewed each step and the
results, and made the decisions. The code is marked as SI-assisted in the repository README
("Use of SI"), and the slides/video carry a visible note.

## NASA Data
- LRO LOLA gridded elevation maps LDEM_80S_40M, LDEM_64, LDEM_16 (NASA PDS Geosciences Node)
- NASA LOLA team average Sun and Earth visibility maps AVGVISIB_85S_060M_201608 (+ _EARTH),
  Mazarico et al. 2011 (validation)
- JPL planetary ephemeris DE440 and lunar orientation kernels via NASA NAIF SPICE
- JPL Horizons System (validation)
- Landing-site coordinates from NASA NSSDC (Apollo, Wagner et al. 2017) and LROC

## Space Agency Partner Data and Other References
- ISRO Chandrayaan-3 landing site (USGS Gazetteer of Planetary Nomenclature, Statio Shiv Shakti)
- JAXA SLIM landing site; CNSA Chang'e 4/5/6 sites (LROC, published coordinates)
- Mazarico, E. et al. (2011), Illumination conditions of the lunar polar regions using LOLA
  topography, Icarus 211, 1066–1081
- Wagner, R.V. et al. (2017), Icarus 283, 92–103 (Apollo coordinates)
- Software: SpiceyPy, NumPy, pandas, Streamlit, Plotly, Matplotlib, python-pptx (open source)
- Full list with links: README.md and sites.py in the repository
