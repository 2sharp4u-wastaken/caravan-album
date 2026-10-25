import sys, json, re, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import av, numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
from config import photos_root
ROOT = photos_root()
FILM = HERE / "film"

def safe(i): return re.sub(r"[^\w.\-]", "_", i)

def rot_of(fr, vs):
    rot = getattr(fr, "rotation", 0) or 0
    if not rot:
        try: rot = int(vs.metadata.get("rotate", 0))
        except Exception: rot = 0
    return (int(round(rot / 90.0))) % 4

def grab(c, vs, t, W):
    c.seek(int(t / vs.time_base), stream=vs, backward=True, any_frame=False)
    best = None
    for fr in c.decode(vs):
        ft = float(fr.pts * vs.time_base) if fr.pts is not None else 0
        best = fr
        if ft >= t - 0.02: break
    if best is None: return None
    h = max(2, int(round(W * best.height / best.width / 2)) * 2)
    rgb = best.reformat(width=W, height=h, format="rgb24").to_ndarray()
    k = rot_of(best, vs)
    if k: rgb = np.rot90(rgb, k)
    return np.ascontiguousarray(rgb)

def one(job):
    vid, nmax = job
    out = FILM / safe(vid); meta = out / "meta.json"
    if meta.exists(): return vid, True
    p = ROOT / vid
    try:
        out.mkdir(parents=True, exist_ok=True)
        with av.open(str(p)) as c:
            vs = c.streams.video[0]
            dur = float(c.duration / av.time_base) if c.duration else 10.0
            n = int(min(nmax, max(6, dur / 1.5)))
            ts = list(np.linspace(0.15, max(0.3, dur - 0.25), n))
            fr = []
            for k, t in enumerate(ts):
                try: a = grab(c, vs, t, 300)
                except Exception: a = None
                if a is None: continue
                fn = "%02d.jpg" % k
                Image.fromarray(a).save(out / fn, "JPEG", quality=72)
                fr.append({"t": round(t, 2), "f": fn})
        meta.write_text(json.dumps({"dur": round(dur, 1), "frames": fr}))
        return vid, True
    except Exception as e:
        return vid, str(e)

def build_js():
    d = {}
    for m in FILM.glob("*/meta.json"):
        d[m.parent.name] = json.loads(m.read_text())
    (FILM / "film.js").write_text("window.FILM=" + json.dumps(d) + ";", encoding="utf-8")
    return len(d)

if __name__ == "__main__":
    FILM.mkdir(exist_ok=True)
    lst = json.loads((HERE / "film_list.json").read_text(encoding="utf-8"))
    jobs = [(v, 16) for v in lst]
    done = 0
    with ProcessPoolExecutor(max_workers=4) as ex:
        for vid, r in ex.map(one, jobs):
            done += 1
            if r is not True: print("skip", vid, r)
            if done % 10 == 0:
                print(done, "/", len(jobs)); build_js()
    print("videos with filmstrips:", build_js())
