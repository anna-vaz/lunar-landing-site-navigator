"""Numbers for the pitch story: 'the launch slipped two weeks'. Prints a small table."""
import json
import numpy as np
import ops, terrain as tr, sites

dem = tr.CompositeDEM()
out = {}
MISSION_D = 14
for key in ["Ridge between Shackleton and de Gerlache craters", "IM-2 Athena (Mons Mouton), landed 2025"]:
    s = sites.BY_NAME[key]
    for label, start in (("planned 7 Nov 2026", "2026-11-07T10:00"),
                         ("best day 15 Nov 2026", "2026-11-15T10:00"),
                         ("slipped to 21 Nov 2026", "2026-11-21T10:00")):
        y, m, d = start[:10].split("-")
        stop = f"2026-{int(m) + (1 if int(d) + MISSION_D > 30 else 0):02d}-" \
               f"{(int(d) + MISSION_D - 1) % 30 + 1:02d}T10:00"
        tl = ops.SiteTimeline(s["lat"], s["lon"], start, stop, 0.25, 2.0, dem=dem)
        sm = tl.summary()
        r = {k: round(sm[k], 1) for k in ("sun_visible_pct", "earth_visible_pct",
                                          "sun_and_earth_pct", "longest_dark_h",
                                          "longest_no_earth_h", "mean_power_w")}
        out[f"{key} | {label} ({start}..{stop})"] = r
        print(key[:30], label, r)
json.dump(out, open("results/pitch_story.json", "w"), indent=1)
