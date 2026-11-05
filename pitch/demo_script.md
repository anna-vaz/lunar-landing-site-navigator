# Pitch and demo script: Lunar Landing Site Navigator

Total: about **4 minutes** (slides 2 min + live demo 2 min). Ask the Athens organisers (Libre Space Foundation) how
long pitches are; if it's 3 minutes, skip slide 3 and shorten the demo to steps 1, 3 and 4.

Speaker notes for each slide are also inside the .pptx (View → Notes).

## Before you go on stage
- [ ] Start the app with `run_app.bat` **5 minutes early** (first load takes a few seconds).
- [ ] Use a browser **without Dark Reader** (or switch it off for localhost).
- [ ] Wi-Fi off once, to be sure it works offline.
- [ ] Sidebar ready: sites **Ridge**, **IM-2 Athena**, **Chandrayaan-3**; landing date
      **7 Nov 2026, 10:00**; look-ahead **1 lunar day**; mast **2 m**.
- [ ] Have the deck open in a second window; switch with Alt+Tab.
- [ ] Zoom the browser to 110–125 % so the back row can read it.

## Slides 1–2 (≈ 1 min): the hook and the problem
Say the slide notes. Key lines:
- "Your launch just slipped two weeks. Will your lander still see the Sun and Earth?"
- "At the south pole the Sun never climbs more than about 1.5°. A hill decides the mission."

## Slide 3 (≈ 20 s): what the tool does
"Pick sites and a date, get answers in seconds, all from NASA data, offline." → **Alt+Tab to
the app.**

## Live demo (≈ 2 min)
1. **Top of the page (20 s).** "Three real sites, landing on 7 November. For each one: is the
   Sun up, is Earth up, and how long until that changes." Point at IM-2: *"Sun down, rises in
   about 7 days: a lander here would wait a week in the dark."*
2. **Comparison table (15 s).** "The ridge near Shackleton: Sun 100 % of this lunar day, but
   Earth only 46 %, so it's sunny but often can't call home."
3. **Sky view, IM-2 (25 s).** "This grey line is the real skyline from NASA's laser
   altimeter. The orange curve is the Sun's path over the month. Where it's pale, it's behind
   the hills. That's why the Sun is down."
4. **Best landing dates (30 s): the story.** "Now the launch slips. This chart shows every
   landing day for the next year. For IM-2, 7 November gives 45 % sunlight. Two weeks later,
   69 %. But 15 November gives 100 % Sun and 100 % Earth." Point at the table below.
5. **Move the site (20 s).** Pick the ridge, spacing 200 m, click Compute (takes ~20 s:
   **talk while it runs**: "now we ask: what if the lander misses by a few hundred metres?").
   "Sunlight drops from 100 % to 50 % within 400 m, and on the Earth map many cells are zero."
6. Alt+Tab back to the slides.

## Slides 4–5 (≈ 1 min): the story in numbers, why trust it, close
- Slide 4: repeat the IM-2 numbers (for judges who missed the demo).
- Slide 5: "Every part is checked against NASA itself" (Horizons 0.006″, LOLA maps 0.5 points,
  Chandrayaan-3 dates).
- Close: **"The Moon's south pole is where the next missions are going. Our tool tells you, in
  seconds, whether your lander will have light and a line home. Thank you."**

## If something goes wrong
- App slow or frozen: stay on slide 4. It has the same story as the demo.
- "Move the site" too slow: skip it, show `pitch/img/move_site.png` instead.
- No laptop at all: the PDF (`Lunar_Landing_Site_Navigator.pdf`) runs anywhere.

## Likely judge questions (short answers)
- **How accurate is it?** Sun/Earth positions agree with JPL Horizons to 0.006 arcsec;
  sunlight % agrees with NASA's own LOLA maps to a median 0.5 percentage points.
- **Where does the data come from?** NASA/JPL DE440 ephemeris through SPICE; LRO LOLA laser
  altimeter terrain (40 m at the pole, 474 m elsewhere); NASA LOLA illumination maps for checks.
- **What's "visible"?** Any part of the Sun's disc above the skyline (power scales with how
  much); for radio, Earth's centre above the skyline.
- **Why 2 m mast?** Solar panels and antennas sit above the ground; at the pole even 1 m
  matters (slider in the app).
- **Limits?** No thermal model yet, hourly or 15-min steps, typical (not real) panel and radio
  values, assumes a ground station on Earth can see the Moon.
- **Is the rest real?** Yes: the landing sites are real LRO-measured coordinates, and for
  Chandrayaan-3 the tool reproduces the actual lunar day (sunrise 21 Aug, sunset 4 Sep 2023).
- **What did you do vs a library?** We wrote the horizon ray tracing, power, link budget,
  windows and the app; SPICE only gives the Sun/Earth vectors.
