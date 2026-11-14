"""Build the 30-second demo video (no voice: on-screen captions) from the running app.

  1. Playwright records/screenshots the app on http://localhost:8517 (start it first).
  2. PIL draws the title card, end card and caption bars (1920 x 1080).
  3. ffmpeg assembles the segments (slow zoom on stills, the recorded 3D rotation clip).
Output: pitch/video/nokstella_demo_30s.mp4 (must stay <= 30 s for Global Judging).

Run: python pitch/make_video.py [APP_LINK]
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "video"
WORK = OUT / "work"
WORK.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1920, 1080, 30
APP_LINK = sys.argv[1] if len(sys.argv) > 1 else "github.com/anna-vaz/lunar-landing-site-navigator"
FFMPEG = shutil.which("ffmpeg") or str(next(
    (Path.home() / "AppData/Local/hermes/tools").glob("ffmpeg-*/bin/ffmpeg.exe"), "ffmpeg"))
BG = (14, 17, 23)
WHITE, GREY = (242, 242, 242), (169, 177, 189)
SUN, EARTH, GREEN = (245, 166, 35), (74, 155, 240), (92, 201, 139)
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"
SI_NOTE = "App, figures and video made with code written with SI assistance (Claude)"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def si_mark(d):
    d.text((W - 24, H - 18), SI_NOTE, font=font(22), fill=GREY, anchor="rd")


def caption_png(lines, path):
    """Transparent 1920x1080 overlay: caption bar at the bottom + SI watermark.
    lines: list of [(text, colour), ...] runs."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bar_h = 70 + 62 * len(lines)
    d.rectangle([0, H - bar_h, W, H], fill=(10, 12, 18, 225))
    y = H - bar_h + 26
    for runs in lines:
        total = sum(d.textlength(t, font=font(50, True)) for t, _ in runs)
        x = (W - total) / 2
        for t, c in runs:
            d.text((x, y), t, font=font(50, True), fill=c)
            x += d.textlength(t, font=font(50, True))
        y += 62
    si_mark(d)
    im.save(path)


def card(path, draw_fn):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    draw_fn(d)
    si_mark(d)
    im.save(path)


def fit(src, dst, top_pad=40, bottom_pad=200):
    """Place a screenshot on a 1920x1080 dark frame, leaving room for the caption bar."""
    im = Image.open(src).convert("RGB")
    box_w, box_h = W - 80, H - top_pad - bottom_pad
    s = min(box_w / im.width, box_h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    frame = Image.new("RGB", (W, H), BG)
    frame.paste(im, ((W - im.width) // 2, top_pad + (box_h - im.height) // 2))
    frame.save(dst)


# ------------------------------------------------------------------ 1. capture the app
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    ctx = b.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.2,
                        record_video_dir=str(WORK / "rec"),
                        record_video_size={"width": 1600, "height": 900})
    pg = ctx.new_page()
    pg.goto("http://localhost:8517/", wait_until="networkidle")
    pg.wait_for_selector("text=Comparison over", timeout=120000)
    pg.wait_for_timeout(3000)
    main = pg.locator("[data-testid=stMain]").first.bounding_box()
    pg.screenshot(path=str(WORK / "overview.png"),
                  clip={"x": main["x"] + 10, "y": 50, "width": main["width"] - 20,
                        "height": 900 - 60})
    tp = lambda: pg.locator("[role=tabpanel]:visible").first  # noqa: E731
    pg.get_by_role("tab", name="🔭 Sky view").click()
    pg.wait_for_timeout(1500)
    tp().get_by_text("IM-2 Athena", exact=False).first.click()
    pg.wait_for_timeout(3000)
    tp().locator(".js-plotly-plot").first.screenshot(path=str(WORK / "sky.png"))
    # 3D terrain: pick IM-2, then rotate the scene with the mouse (recorded)
    pg.get_by_role("tab", name="🏔️ 3D terrain").click()
    pg.wait_for_timeout(1500)
    tp().get_by_text("IM-2 Athena", exact=False).first.click()
    pg.wait_for_timeout(9000)
    plot = tp().locator(".js-plotly-plot").first
    plot.scroll_into_view_if_needed()
    pg.wait_for_timeout(1500)
    bb = plot.bounding_box()
    t_start = pg.evaluate("performance.now()")
    cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] * 0.55
    pg.mouse.move(cx - 250, cy)
    pg.mouse.down()
    for i in range(120):                       # ~6 s of slow rotation
        pg.mouse.move(cx - 250 + i * 4.2, cy - i * 0.4)
        pg.wait_for_timeout(50)
    pg.mouse.up()
    t_end = pg.evaluate("performance.now()")
    clip_box = bb
    video_path = pg.video.path()
    ctx.close()
    b.close()
rec_start = None
# The recording starts when the page opened; estimate the rotation window from wall times.
# (performance.now() is ms since navigation; the recording began just before navigation.)
rot_from, rot_len = t_start / 1000.0, (t_end - t_start) / 1000.0
print("rotation window", round(rot_from, 1), round(rot_len, 1), "s; video", video_path)

# ------------------------------------------------------------------ 2. frames and captions
card(WORK / "title.png", lambda d: (
    d.text((W / 2, 330), "Lunar Landing Site Navigator", font=font(92, True), fill=WHITE,
           anchor="mm"),
    d.text((W / 2, 450), "Will your lander see the Sun and Earth?", font=font(52),
           fill=SUN, anchor="mm"),
    d.text((W / 2, 640), "Team Nokstella", font=font(56, True), fill=WHITE, anchor="mm"),
    d.text((W / 2, 720), "Anna Vazaiou · Georgios Anagnostopoulos", font=font(44),
           fill=GREY, anchor="mm"),
    d.text((W / 2, 820), "NASA Space Apps 2026 · Challenge: Lunar Landing Site Navigator",
           font=font(36), fill=GREY, anchor="mm")))
fit(WORK / "sky.png", WORK / "sky_f.png")
fit(WORK / "overview.png", WORK / "overview_f.png")
fit(HERE / "img" / "slip_chart.png", WORK / "slip_f.png")
fit(HERE / "render" / "slide5.png", WORK / "checks_f.png")
card(WORK / "end.png", lambda d: (
    d.text((W / 2, 250), "Re-plan in minutes when a launch slips.", font=font(64, True),
           fill=WHITE, anchor="mm"),
    d.text((W / 2, 350), "Show anyone why the lunar south pole is so hard.",
           font=font(54), fill=WHITE, anchor="mm"),
    d.text((W / 2, 480), "Next: thermal model · sunlit rover routes · relay satellites",
           font=font(42), fill=GREY, anchor="mm"),
    d.text((W / 2, 640), "Try it:", font=font(46), fill=GREY, anchor="mm"),
    d.text((W / 2, 720), APP_LINK, font=font(54, True), fill=EARTH, anchor="mm"),
    d.text((W / 2, 860), "Team Nokstella · NASA Space Apps 2026", font=font(40),
           fill=GREY, anchor="mm")))

caption_png([[("At the Moon's south pole the ", WHITE), ("Sun", SUN), (" barely rises.", WHITE)],
             [("One hill decides if a lander has power.", WHITE)]], WORK / "cap_sky.png")
caption_png([[("Pick any landing site and date: see when it has ", WHITE), ("Sun", SUN),
              (" and ", WHITE), ("Earth", EARTH), (",", WHITE)],
             [("and how long until sunset and Earthset.", WHITE)]], WORK / "cap_over.png")
caption_png([[("Launch slipped? At the IM-2 site, landing on 7 Nov: ", WHITE),
              ("45 % sunlight.", SUN)],
             [("Landing on 15 Nov: ", WHITE), ("100 % Sun and Earth.", GREEN)]],
            WORK / "cap_slip.png")
caption_png([[("Real terrain from NASA's LRO laser altimeter,", WHITE)],
             [("Sun and Earth from JPL's planetary ephemeris.", WHITE)]], WORK / "cap_3d.png")
caption_png([[("Checked against NASA's own data:", WHITE)],
             [("JPL Horizons and the LOLA team's sunlight maps.", WHITE)]],
            WORK / "cap_checks.png")


# ------------------------------------------------------------------ 3. ffmpeg segments
def run(args):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def still(img, dur, out, overlay=None, zoom=True):
    n = int(dur * FPS)
    z = (f"zoompan=z='1+0.04*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:"
         f"s={W}x{H}:fps={FPS}") if zoom else f"loop={n}:1:0,fps={FPS}"
    if overlay:
        run(["-loop", "1", "-i", str(img), "-i", str(overlay), "-filter_complex",
             f"[0:v]{z}[b];[b][1:v]overlay=0:0,format=yuv420p", "-t", f"{dur}", "-r",
             str(FPS), str(out)])
    else:
        run(["-loop", "1", "-i", str(img), "-vf", f"{z},format=yuv420p", "-t", f"{dur}",
             "-r", str(FPS), str(out)])


segs = []
for name, img, dur, ov, zoom in (("s1", WORK / "title.png", 2.5, None, False),
                                 ("s2", WORK / "sky_f.png", 3.5, WORK / "cap_sky.png", True),
                                 ("s3", WORK / "overview_f.png", 5.0, WORK / "cap_over.png", True),
                                 ("s4", WORK / "slip_f.png", 5.5, WORK / "cap_slip.png", True)):
    still(img, dur, WORK / f"{name}.mp4", ov, zoom)
    segs.append(WORK / f"{name}.mp4")

# s5: recorded 3D rotation, cropped to the plot, captioned (5 s)
crop = (f"crop={int(clip_box['width'])}:{int(clip_box['height'])}:{int(clip_box['x'])}:"
        f"{int(clip_box['y'])}")
run(["-ss", f"{rot_from + 0.3:.2f}", "-t", "5", "-i", str(video_path), "-i",
     str(WORK / "cap_3d.png"), "-filter_complex",
     f"[0:v]{crop},scale={W - 80}:{H - 240}:force_original_aspect_ratio=decrease,"
     f"pad={W}:{H}:(ow-iw)/2:40:color=0x0e1117,fps={FPS}[b];[b][1:v]overlay=0:0,format=yuv420p",
     "-t", "5", str(WORK / "s5.mp4")])
segs.append(WORK / "s5.mp4")
still(WORK / "checks_f.png", 4.0, WORK / "s6.mp4", WORK / "cap_checks.png", True)
still(WORK / "end.png", 4.0, WORK / "s7.mp4", None, False)
segs += [WORK / "s6.mp4", WORK / "s7.mp4"]

(WORK / "list.txt").write_text("".join(f"file '{s.as_posix()}'\n" for s in segs))
final = OUT / "nokstella_demo_30s.mp4"
run(["-f", "concat", "-safe", "0", "-i", str(WORK / "list.txt"), "-c:v", "libx264", "-crf",
     "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(final)])
dur = subprocess.run([str(Path(FFMPEG).with_name("ffprobe" + Path(FFMPEG).suffix)), "-v", "error", "-show_entries",
                      "format=duration", "-of", "csv=p=0", str(final)],
                     capture_output=True, text=True).stdout.strip()
print("saved", final, "duration", dur, "s")
