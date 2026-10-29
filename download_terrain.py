"""Download the LOLA terrain maps and NASA's reference illumination maps into data/ (~1.1 GB)."""
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
PDS = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/"
ILL = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/"
FILES = {
    "data/lola": [PDS + f"polar/img/ldem_80s_40m.{e}" for e in ("lbl", "img")]      # 462 MB
                 + [PDS + f"cylindrical/img/ldem_16.{e}" for e in ("lbl", "img")]   # 33 MB
                 + [PDS + f"cylindrical/img/ldem_64.{e}" for e in ("lbl", "img")],  # 531 MB
    "data/nasa_illum": [ILL + f"AVGVISIB_85S_060M_201608{s}.{e}"                     # 2 x 51 MB
                        for s in ("", "_EARTH") for e in ("LBL", "IMG")],
}
for folder, urls in FILES.items():
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
    for u in urls:
        dest = ROOT / folder / u.rsplit("/", 1)[1]
        if dest.exists():
            print("have", dest.name)
            continue
        print("downloading", dest.name)
        urllib.request.urlretrieve(u, dest)
print("done")
