"""Build the pitch deck (pitch/Lunar_Landing_Site_Navigator.pptx) with python-pptx.
Dark theme to match the app. Numbers come from results/*.json (computed by the steps)."""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
BG = RGBColor(0x0E, 0x11, 0x17)
CARD = RGBColor(0x1B, 0x1F, 0x2A)
WHITE = RGBColor(0xF2, 0xF2, 0xF2)
GREY = RGBColor(0xA9, 0xB1, 0xBD)
SUN = RGBColor(0xF5, 0xA6, 0x23)
EARTH = RGBColor(0x4A, 0x9B, 0xF0)
RED = RGBColor(0xE4, 0x57, 0x2E)
GREEN = RGBColor(0x5C, 0xC9, 0x8B)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide(notes=""):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def text(s, x, y, w, h, runs, size=20, color=WHITE, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, style)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    paras = [runs] if isinstance(runs, str) else runs
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(6)
        for chunk in ([(para, {})] if isinstance(para, str) else para):
            t, st = chunk
            r = p.add_run()
            r.text = t
            f = r.font
            f.size = Pt(st.get("size", size))
            f.bold = st.get("bold", bold)
            f.color.rgb = st.get("color", color)
            f.name = "Segoe UI"
    return tb


def card(s, x, y, w, h, fill=CARD):
    r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w),
                           Inches(h))
    r.adjustments[0] = 0.06
    r.fill.solid()
    r.fill.fore_color.rgb = fill
    r.line.fill.background()
    r.shadow.inherit = False
    return r


def picture(s, path, x, y, w=None, h=None):
    """Place an image inside the box (x, y, w, h) keeping its aspect ratio."""
    iw, ih = Image.open(path).size
    if w and h:
        if iw / ih > w / h:
            h2 = w * ih / iw
            y += (h - h2) / 2
            h = h2
        else:
            w2 = h * iw / ih
            x += (w - w2) / 2
            w = w2
    return s.shapes.add_picture(str(path), Inches(x), Inches(y),
                                Inches(w) if w else None, Inches(h) if h else None)


def footer(s, n):
    text(s, 0.5, 7.02, 11.4, 0.35, "Lunar Landing Site Navigator · NASA Space Apps 2026, "
         "Athens · Charts and screenshots made by code written with SI assistance (Claude)",
         size=10, color=GREY)
    text(s, 12.2, 7.02, 0.7, 0.35, str(n), size=11, color=GREY, align=PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- 1. title / hook
s = slide("""HOOK (20 s). Start with the question, not with us.
"Imagine you're a mission planner. Your lander is ready, the landing site at the Moon's south pole is chosen... and the launch slips two weeks. Is your site still good? Will the lander have sunlight for power, and Earth in view to talk home?"
"Today answering that means juggling JPL Horizons, LRO terrain maps and spreadsheets. We built a tool that answers it in seconds."
Then: "We're team Nokstella: I'm Anna, a mechanical engineer, with Georgios Anagnostopoulos..." (one line about the team).""")
picture(s, IMG / "sky.png", 6.3, 0.6, 6.6, 5.6)
text(s, 0.6, 1.3, 5.8, 1.6, "Lunar Landing Site Navigator", size=44, bold=True)
text(s, 0.6, 3.0, 5.6, 2.2, [
    [("Your launch just slipped two weeks.", {"size": 26, "color": SUN, "bold": True})],
    [("Will your lander still see the ", {"size": 24}), ("Sun", {"size": 24, "color": SUN,
                                                              "bold": True}),
     (" and ", {"size": 24}), ("Earth", {"size": 24, "color": EARTH, "bold": True}),
     ("?", {"size": 24})],
])
text(s, 0.6, 5.35, 5.6, 1.5, [[("Team: ", {}), ("Nokstella", {"bold": True})],
                             [("Members: ", {}), ("Anna Vazaiou, Georgios Anagnostopoulos", {"bold": True})],
                             "Challenge: Lunar Landing Site Navigator · NASA Space Apps 2026, "
                             "Athens"], size=15, color=GREY)
footer(s, 1)

# ---------------------------------------------------------------- 2. the problem
s = slide("""PROBLEM (40 s).
"The Moon's axis is tilted only 1.5 degrees. At the south pole the Sun never climbs more than about 1.5 degrees - it circles the horizon once a month, like a lamp held at floor level."
Point at the picture: "This is the real skyline at the IM-2 landing site, from NASA's laser altimeter. Grey is terrain. When the Sun's path dips behind it - the pale part - no power."
"So terrain decides everything: on a ridge near Shackleton crater the Sun is up 91 % of the year; on flat ground it would be 57 %. And 500 metres can change sunlight from 100 % to 50 %."
"Earth is the same story for radio: it bobs up and down every month and can disappear behind a hill for days.\"""")
text(s, 0.6, 0.45, 12, 0.9, "At the south pole, a hill decides the mission", size=34, bold=True)
picture(s, IMG / "sky_im2.png", 6.0, 1.45, 7.0, 4.9)
facts = [
    ("≤ 1.6°", "highest the Sun ever gets at the pole (the Moon is tilted only 1.5°)", SUN),
    ("57 % → 91 %", "sunlight on flat ground vs on the ridge by Shackleton crater (2027)", SUN),
    ("13 days", "longest radio silence at that same sunny ridge: Earth hides behind terrain",
     EARTH),
]
for i, (big, small, c) in enumerate(facts):
    y = 1.55 + i * 1.65
    card(s, 0.6, y, 5.1, 1.45)
    text(s, 0.85, y + 0.12, 4.7, 0.7, big, size=32, bold=True, color=c)
    text(s, 0.85, y + 0.78, 4.7, 0.65, small, size=15, color=GREY)
text(s, 6.0, 6.35, 7.0, 0.5, "Real skyline at the IM-2 site (LRO laser altimeter). Pale = Sun "
     "or Earth hidden behind terrain.", size=12, color=GREY)
footer(s, 2)

# ---------------------------------------------------------------- 3. the tool
s = slide("""SOLUTION (30 s), then switch to the LIVE DEMO (see demo_script.md).
"Pick up to four sites - Apollo, Chandrayaan-3, the commercial landers, or your own coordinates - and a landing date."
"For each site you get the answers a planner needs first: is the Sun up, is Earth up, and how long until sunset or Earthset. Then a comparison table: sunlight, Earth contact, the longest darkness and the battery you need to survive it."
"Everything is computed on this laptop from NASA's own data - no internet needed.\"""")
text(s, 0.6, 0.45, 12, 0.9, "Pick sites and a date. Get answers in seconds.", size=34, bold=True)
picture(s, IMG / "app_overview.png", 0.6, 1.4, 7.9, 5.4)
items = [
    ("☀️ 🌍", "Sun and Earth up or down, and time until sunset / Earthset"),
    ("📊", "Side-by-side: sunlight, Earth contact, power, battery for the longest night"),
    ("🔭", "The real skyline with the Sun's and Earth's paths"),
    ("📅", "Best landing dates for the next year"),
    ("🧭", "Move the site: what changes 200 m away?"),
    ("🌕", "16 real sites (Apollo, CLPS, Chandrayaan-3, Chang'e, SLIM) or any coordinates"),
]
for i, (ic, t) in enumerate(items):
    y = 1.45 + i * 0.88
    text(s, 8.8, y, 0.9, 0.7, ic, size=22)
    text(s, 9.7, y + 0.02, 3.3, 0.85, t, size=15)
footer(s, 3)

# ---------------------------------------------------------------- 4. the story
s = slide("""THE STORY (45 s) - this is the moment judges remember.
"Take the real IM-2 site on Mons Mouton, a 14-day mission. Planned landing: 7 November. The tool says: Sun visible only 45 % of the mission, and a 7.7-day night - you'd need a big battery."
"Launch slips two weeks to 21 November: better, 69 %. But the Best-dates tab shows something nobody would guess: land on 15 November and you get Sun AND Earth 100 % of the mission." Point at the chart: every landing day on the x-axis, the orange curve is how much of the mission is sunlit - the lunar day is a 29.5-day rhythm, so the date matters enormously.
"That's an answer a planner can act on in a meeting, instead of a week of analysis.\"""")
text(s, 0.6, 0.45, 12, 0.9, "\"The launch slipped.\" Good news or bad?", size=34, bold=True)
text(s, 0.6, 1.25, 12, 0.5, "IM-2 site, Mons Mouton (84.8°S) · 14-day mission · 1 m² solar "
     "panel", size=16, color=GREY)
rows = [
    ("Landing day", "Sun visible", "Earth visible", "Longest night", "Mean power"),
    ("7 Nov (planned)", "45 %", "65 %", "7.7 days", "180 W"),
    ("21 Nov (2-week slip)", "69 %", "93 %", "4.4 days", "280 W"),
    ("15 Nov (best day)", "100 %", "100 %", "none", "414 W"),
]
tbl = s.shapes.add_table(4, 5, Inches(0.6), Inches(1.9), Inches(7.5), Inches(2.6)).table
widths = [2.55, 1.2, 1.3, 1.3, 1.15]
for j, wd in enumerate(widths):
    tbl.columns[j].width = Inches(wd)
for i, row in enumerate(rows):
    for j, v in enumerate(row):
        c = tbl.cell(i, j)
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor(0x2A, 0x30, 0x3F) if i == 0 else (
            RGBColor(0x1E, 0x3A, 0x2B) if i == 3 else CARD)
        tf = c.text_frame
        tf.text = v
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        f = p.runs[0].font
        f.size = Pt(15 if i else 13)
        f.bold = i in (0, 3)
        f.name = "Segoe UI"
        f.color.rgb = GREY if i == 0 else (GREEN if i == 3 and j else WHITE)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
text(s, 0.6, 4.75, 7.4, 1.9, [
    [("A two-week slip ", {}), ("helps", {"color": GREEN, "bold": True}),
     (" here, but the best day is ", {}), ("6 days", {"bold": True}),
     (" before it.", {})],
    [("Moving the site 500 m can swing sunlight from 100 % to 50 %.", {"color": GREY,
                                                                        "size": 17})],
], size=20)
picture(s, IMG / "slip_chart.png", 8.35, 1.2, 4.75, 5.7)
footer(s, 4)

# ---------------------------------------------------------------- 5. trust + next
s = slide("""VALIDITY + IMPACT + CLOSE (35 s).
"Why trust it? Every part is checked against something independent. Sun and Earth positions agree with NASA JPL Horizons to 0.006 arcseconds. Our sunlight and Earth-visibility percentages agree with the NASA LOLA team's own south-pole maps - median difference half a percentage point over 142 sites. And for Chandrayaan-3 the tool puts sunrise on 21 August and sunset on 4 September 2023 - exactly the lunar day ISRO used."
"Who is it for: mission planners who need answers fast when schedules change, and teachers and the public who want to see why the south pole is so hard."
"Next: thermal model, rover traverses, relay satellites."
CLOSE: "The Moon's south pole is where the next missions are going. Our tool tells you, in seconds, if your lander will have light and a line home. Thank you.\"""")
text(s, 0.6, 0.45, 12, 0.9, "Built on NASA data, checked against NASA", size=34, bold=True)
checks = [
    ("0.006″", "Sun & Earth positions vs NASA JPL Horizons (52,560 checks)", SUN),
    ("0.5 pts", "sunlight % vs NASA LOLA team south-pole maps (142 sites, 18.6 years)",
     SUN),
    ("0.1 pts", "Earth-visibility % vs the same NASA maps", EARTH),
    ("✓ dates", "Chandrayaan-3: sunrise 21 Aug, sunset 4 Sep 2023, ISRO's lunar day", GREEN),
]
for i, (big, small, c) in enumerate(checks):
    y = 1.45 + i * 1.2
    card(s, 0.6, y, 6.4, 1.05)
    text(s, 0.8, y + 0.15, 1.9, 0.8, big, size=26, bold=True, color=c,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, 2.75, y + 0.12, 4.15, 0.85, small, size=15, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
card(s, 7.4, 1.45, 5.4, 2.25)
text(s, 7.65, 1.55, 5.0, 2.1, [
    [("Who it's for", {"bold": True, "size": 20})],
    "• Mission planners: re-plan in minutes when the date or site changes",
    "• Teachers and the public: see why the pole is so hard",
], size=16)
card(s, 7.4, 3.9, 5.4, 1.95)
text(s, 7.65, 4.0, 5.0, 1.8, [
    [("Next", {"bold": True, "size": 20})],
    "• Thermal model (how cold the night gets)",
    "• Rover routes that stay in sunlight · relay satellites",
], size=16)
text(s, 0.6, 6.3, 12.2, 0.6, "Data: NASA/JPL DE440 ephemeris (SPICE), LRO LOLA terrain, "
     "NASA LOLA illumination maps. Code: github.com/anna-vaz/lunar-landing-site-navigator",
     size=12, color=GREY)
footer(s, 5)

out = HERE / "Lunar_Landing_Site_Navigator.pptx"
prs.save(out)
print("saved", out)
