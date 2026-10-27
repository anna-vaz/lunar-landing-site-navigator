"""Download the NASA/JPL SPICE files used by moon_sky.py (about 45 MB) into kernels/."""
from pathlib import Path
import urllib.request

BASE = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
FILES = [
    "lsk/naif0012.tls",
    "pck/pck00011.tpc",
    "pck/moon_pa_de440_200625.bpc",
    "fk/satellites/moon_de440_250416.tf",
    "spk/planets/de440s.bsp",
]

out = Path(__file__).resolve().parent / "kernels"
out.mkdir(exist_ok=True)
for f in FILES:
    dest = out / Path(f).name
    if dest.exists():
        print("have", dest.name)
        continue
    print("downloading", f)
    urllib.request.urlretrieve(BASE + f, dest)
print("done")
