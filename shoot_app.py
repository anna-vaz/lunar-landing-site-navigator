"""Take screenshots of the running app (streamlit on :8517) with the installed Edge browser.
Run: python shoot_app.py"""
import sys
from playwright.sync_api import sync_playwright

OUT = "figures/app/"
TABS = ["🔭 Sky view", "📈 Timeline", "📅 Best landing dates", "🗺️ Map"]
import sys as _s
if len(_s.argv) > 1:
    TABS = [t for t in TABS if any(a in t for a in _s.argv[1:])]
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto("http://localhost:8517/", wait_until="networkidle")
    pg.wait_for_selector("text=Comparison over", timeout=120000)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=OUT + "01_top.png", full_page=False)
    for i, t in enumerate(TABS):
        pg.get_by_role("tab", name=t).click()
        pg.wait_for_timeout(6000 if ("dates" in t or "Map" in t) else 2500)
        tab = pg.get_by_role("tabpanel").first
        pg.locator("[role=tabpanel]:visible").first.scroll_into_view_if_needed()
        pg.wait_for_timeout(1000)
        pg.locator("[role=tabpanel]:visible").first.screenshot(path=OUT + f"0{i + 2}_tab.png")
    b.close()
print("ok")
