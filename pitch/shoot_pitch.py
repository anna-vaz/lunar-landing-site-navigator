"""Screenshots of the app for the pitch deck (app must run on :8517)."""
from playwright.sync_api import sync_playwright

OUT = "pitch/img/"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)
    pg.goto("http://localhost:8517/", wait_until="networkidle")
    pg.wait_for_selector("text=Comparison over", timeout=120000)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=OUT + "app_overview.png")
    main = pg.locator("section.main, [data-testid=stMain]").first

    def panel(name, wait, path, before=None):
        pg.get_by_role("tab", name=name).click()
        pg.wait_for_timeout(1500)
        if before:
            before()
        pg.wait_for_timeout(wait)
        pg.locator("[role=tabpanel]:visible").first.screenshot(path=OUT + path)

    panel("🔭 Sky view", 2500, "sky.png")
    pg.locator("[role=tabpanel]:visible").get_by_text("IM-2 Athena", exact=False).first.click()
    pg.wait_for_timeout(3000)
    pg.locator("[role=tabpanel]:visible").first.screenshot(path=OUT + "sky_im2.png")
    panel("📈 Timeline", 2500, "timeline.png")
    panel("📅 Best landing dates", 8000, "best_dates.png")

    def grid():
        tp = pg.locator("[role=tabpanel]:visible")
        pg.get_by_role("button", name="Compute 9 × 9 grid").click()
        pg.wait_for_selector("text=Sun visible (%)", timeout=240000)
    panel("🧭 Move the site", 3000, "move_site.png", before=grid)
    b.close()
print("ok")
