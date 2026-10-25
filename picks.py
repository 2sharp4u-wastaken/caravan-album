"""Reads decisions.json, saves full-resolution PNGs of the frames you picked from videos."""
import json, re
from pathlib import Path
import av, numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
from config import photos_root
ROOT = photos_root()
OUT = HERE / "picks"; OUT.mkdir(exist_ok=True)
dec = json.loads((HERE / "decisions.json").read_text(encoding="utf-8"))
items = {str(r["n"]): r for r in json.loads((HERE / "review" / "items_min.json").read_text(encoding="utf-8"))}
cnt = 0
for n, s in dec.get("items", {}).items():
    pt = s.get("pt")
    if pt in (None, ""): continue
    r = items.get(n)
    if not r: continue
    t = float(pt)
    p = ROOT / r["id"]
    try:
        with av.open(str(p)) as c:
            vs = c.streams.video[0]
            c.seek(int(t / vs.time_base), stream=vs, backward=True)
            best = None
            for fr in c.decode(vs):
                ft = float(fr.pts * vs.time_base) if fr.pts is not None else 0
                best = fr
                if ft >= t - 0.02: break
            rot = getattr(best, "rotation", 0) or 0
            if not rot:
                try: rot = int(vs.metadata.get("rotate", 0))
                except Exception: rot = 0
            a = best.to_ndarray(format="rgb24")
            k = (int(round(rot / 90.0))) % 4
            if k: a = np.rot90(a, k)
            name = "%04d_%s_%ss.png" % (int(n), re.sub(r"[^\w\-]", "_", Path(r["id"]).stem), str(t).replace(".", "_"))
            Image.fromarray(np.ascontiguousarray(a)).save(OUT / name)
            cnt += 1
    except Exception as e:
        print("failed", n, e)
print("saved", cnt, "frames to", OUT)
