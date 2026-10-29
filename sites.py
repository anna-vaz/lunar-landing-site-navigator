"""Curated landing sites (latitude deg N, longitude deg E, MOON_ME frame).

Sources are given per site. Where a mission landed, the coordinates are the measured lander
position (mostly from LRO camera images); "target" sites are candidate locations.
"""

SITES = [
    # --- south pole: CLPS, commercial and international --------------------------------
    dict(name="Ridge between Shackleton and de Gerlache craters", group="South pole",
         lat=-89.451, lon=222.81,
         note="Brightest spot on NASA's LOLA south-pole sunlight map (86 % over 18.6 years); "
              "the Artemis 'connecting ridge' area. Found in this project (step 2b).",
         source="NASA LOLA team AVGVISIB_85S_060M map (Mazarico et al. 2011, 2016 update)"),
    dict(name="IM-2 Athena (Mons Mouton), landed 2025", group="South pole",
         lat=-84.7906, lon=29.1957,
         note="Intuitive Machines, NASA CLPS. Landed on its side in a small crater.",
         source="LROC (Arizona State Univ.) IM-2 featured site, 2025"),
    dict(name="IM-1 Odysseus (Malapert A), landed 2024", group="South pole",
         lat=-80.13, lon=1.44,
         note="Intuitive Machines, NASA CLPS. First US landing since Apollo 17; tipped over.",
         source="Wikipedia / EGU25-20315 (80.13 S, 1.44 E)"),
    dict(name="Chandrayaan-3 Vikram (Statio Shiv Shakti), landed 2023", group="South pole",
         lat=-69.37345, lon=32.31985,
         note="ISRO. First landing at high southern latitude.",
         source="USGS Gazetteer of Planetary Nomenclature, feature 16272"),
    dict(name="Shackleton crater floor (permanent shadow)", group="South pole",
         lat=-89.655, lon=129.174,
         note="Crater centre: a 'cold trap' where the Sun never shines. For contrast.",
         source="NASA NTRS 20120009640 (Shackleton rim centre -89.655, 129.174 E)"),
    # --- far side ----------------------------------------------------------------------
    dict(name="Chang'e 4 (Von Kármán crater), landed 2019", group="Far side",
         lat=-45.444, lon=177.599,
         note="CNSA. First far-side landing: Earth is never visible; it needs a relay "
              "satellite (Queqiao).",
         source="Wikipedia (Spatio Tianhe, 45.444 S, 177.599 E)"),
    dict(name="Chang'e 6 (Apollo basin), landed 2024", group="Far side",
         lat=-41.6385, lon=206.0148,
         note="CNSA. First far-side sample return.",
         source="LROC image 1374 (-41.6385 N, 206.0148 E)"),
    # --- near side ---------------------------------------------------------------------
    dict(name="SLIM (near Shioli crater), landed 2024", group="Near side",
         lat=-13.3160, lon=25.2510,
         note="JAXA. Pinpoint landing; landed upside down, solar panels facing west.",
         source="Wikipedia (13.3160 S, 25.2510 E)"),
    dict(name="Blue Ghost Mission 1 (Mare Crisium), landed 2025", group="Near side",
         lat=18.56, lon=61.81,
         note="Firefly Aerospace, NASA CLPS. Fully successful commercial landing.",
         source="Wikipedia (18.56 N, 61.81 E)"),
    dict(name="Chang'e 5 (Mons Rümker), landed 2020", group="Near side",
         lat=43.0576, lon=-51.9161 % 360,
         note="CNSA sample return.", source="Wikipedia (43.0576 N, 51.9161 W)"),
    dict(name="Apollo 11 (Mare Tranquillitatis), 1969", group="Apollo",
         lat=0.67416, lon=23.47314, note="First crewed landing.",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
    dict(name="Apollo 12 (Oceanus Procellarum), 1969", group="Apollo",
         lat=-3.0128, lon=-23.4219 % 360, note="Landed next to Surveyor 3.",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
    dict(name="Apollo 14 (Fra Mauro), 1971", group="Apollo",
         lat=-3.64589, lon=-17.47194 % 360, note="",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
    dict(name="Apollo 15 (Hadley-Apennine), 1971", group="Apollo",
         lat=26.13239, lon=3.63330, note="Between the Apennine mountains and Hadley Rille.",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
    dict(name="Apollo 16 (Descartes highlands), 1972", group="Apollo",
         lat=-8.9734, lon=15.5011, note="",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
    dict(name="Apollo 17 (Taurus-Littrow), 1972", group="Apollo",
         lat=20.1911, lon=30.7723, note="Deep valley: high mountains on both sides.",
         source="NASA NSSDC, LRO-derived (Wagner et al. 2017)"),
]

BY_NAME = {s["name"]: s for s in SITES}
