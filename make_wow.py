"""Builds _album\\for_wow: your Keeps as print-ready JPEGs whose FILE NAMES give the album order.
Sort by name in wow = page order.  Originals are never changed.
Usage:  make_wow.py [--per 6] [--size 4000] [--start 2]
"""
import sys, json, re, csv, shutil, datetime as dt, math, collections, unicodedata, argparse
from pathlib import Path
from PIL import Image, ImageOps
try:
    import pillow_heif; pillow_heif.register_heif_opener()
except Exception as e:
    print("note: pillow-heif unavailable:", e)
import av

ap = argparse.ArgumentParser()
ap.add_argument("--per", type=float, default=6.0)      # target images per page
ap.add_argument("--size", type=int, default=4000)      # max long edge (px)
ap.add_argument("--start", type=int, default=2)        # first auto page number (1 = map page)
a = ap.parse_args()

HERE = Path(__file__).resolve().parent
from config import photos_root
ROOT = photos_root()
OUT = HERE / "for_wow"
dec = json.loads((HERE / "decisions.json").read_text(encoding="utf-8"))
raw = (HERE / "review" / "data.js").read_text(encoding="utf-8")
DATA = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
I = dec.get("items", {}); F = dec.get("frames", {})

def slug(s):
    s = unicodedata.normalize("NFKD", s or "x").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "", s)[:14] or "x"

# ---- collect keeps
K = []
for r in DATA["items"]:
    s = I.get(str(r["n"]), {})
    if s.get("d") != "keep" or r.get("dup_of"): continue
    K.append(dict(key="n%d" % r["n"], n=r["n"], kind=r["kind"], id=r["id"], t=r["t_local"][:19], place=r.get("place"),
                  tier=r["tier"], dur=r.get("dur"), pt=s.get("pt"), pg=s.get("pg"), qr=bool(s.get("qr")),
                  ql=s.get("ql", ""), qt=s.get("qt", "")))
for f in DATA["frames"]:
    s = F.get(f["id"], {})
    if s.get("d") == "keep" and f.get("t_local"):
        K.append(dict(key="f" + f["id"], n="F" + re.sub(r"\D", "", f["id"])[:6], kind="frame", id=f["id"], t=f["t_local"][:19],
                      place=f.get("place"), tier="F", dur=None, pt=None, pg=None, qr=False, ql="", qt=""))
K.sort(key=lambda r: r["t"])
# fill missing place from neighbours
last = None
for r in K:
    if r["place"]: last = r["place"]
    else: r["place"] = last or "x"

# ---- group into pages
pinned = collections.defaultdict(list); auto = []
for r in K:
    (pinned[int(r["pg"])] if r["pg"] else auto).append(r)
days = collections.OrderedDict()
for r in auto: days.setdefault(r["t"][:10], []).append(r)
pages = []   # list of lists
for day, L in days.items():
    sc = [[L[0]]]
    for r in L[1:]:
        g = (dt.datetime.fromisoformat(r["t"]) - dt.datetime.fromisoformat(sc[-1][-1]["t"])).total_seconds() / 60
        if g > 45 or (r["place"] != sc[-1][-1]["place"] and g > 15): sc.append([r])
        else: sc[-1].append(r)
    out = []
    for s in sc:
        if out and len(s) < 3: out[-1] += s
        else: out.append(s)
    for s in out:
        npg = max(1, round(len(s) / a.per)); base, extra = divmod(len(s), npg); pos = 0
        for i in range(npg):
            sz = base + (1 if i < extra else 0)
            if s[pos:pos + sz]: pages.append(s[pos:pos + sz])
            pos += sz
plan = []   # (page, slot, item)
pno = a.start
for p in pages:
    while pno in pinned: pno += 1
    for k, r in enumerate(p, 1): plan.append((pno, k, r))
    pno += 1
for pg, L in pinned.items():
    for k, r in enumerate(sorted(L, key=lambda r: r["t"]), 1): plan.append((pg, k, r))
plan.sort(key=lambda x: (x[0], x[1]))

# ---- image export
def video_frame(path, t_sec, sharpest=False):
    import numpy as np, cv2
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        c.seek(int(max(0, t_sec - (0.6 if sharpest else 0)) / vs.time_base), stream=vs, backward=True)
        best = None; bs = -1
        for fr in c.decode(vs):
            ft = float(fr.pts * vs.time_base) if fr.pts is not None else 0
            if sharpest:
                if ft < t_sec - 0.4: continue
                g = cv2.cvtColor(fr.to_ndarray(format="bgr24"), cv2.COLOR_BGR2GRAY)
                g = cv2.resize(g, (g.shape[1] // 2, g.shape[0] // 2))
                sc = cv2.Laplacian(g, cv2.CV_64F).var()
                if sc > bs: bs = sc; best = fr
                if ft > t_sec + 0.4: break
                continue
            best = fr
            if ft >= t_sec - 0.02: break
        rot = getattr(best, "rotation", 0) or 0
        if not rot:
            try: rot = int(vs.metadata.get("rotate", 0))
            except Exception: rot = 0
        im = best.to_image()
        k = (int(round(rot / 90.0))) % 4
        if k: im = im.rotate(90 * k, expand=True)
        return im

def exif_for(im, t):
    ex = Image.Exif()   # clean EXIF: source EXIF of some files has out-of-range values
    stamp = t.replace("-", ":").replace("T", " ")
    ex[0x0132] = stamp
    try: ex.get_ifd(0x8769)[0x9003] = stamp
    except Exception: pass
    return ex

if OUT.exists():
    for f in OUT.iterdir():
        try: f.unlink()
        except Exception: pass
OUT.mkdir(exist_ok=True)
rows = []; qrrows = []; fail = 0
for pg, slot, r in plan:
    src = ROOT / r["id"]
    name = "P%03d_%02d_%s_%s_%s%s.jpg" % (pg, slot, r["t"][5:10].replace("-", ""), slug(r["place"]), r["n"], "_VIDEO" if r["kind"] == "video" else "")
    try:
        if r["kind"] == "map":   # pre-rendered transparent PNG: copy as is
            name = name[:-4] + ".png"
            shutil.copy(src, OUT / name)
            rows.append([pg, slot, name, r["n"], "map", r["t"], "MAP", r["tier"], "", "", ""])
            continue
        if r["kind"] == "video":
            manual = r["pt"] not in (None, "")
            t = float(r["pt"]) if manual else (r["dur"] or 3) / 3.0
            im = video_frame(src, t, sharpest=not manual)   # auto frames: sharpest within +-0.4s
        else:
            im = Image.open(src); im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        ow, oh = im.size
        ex = exif_for(im, r["t"])
        if max(im.size) > a.size: im.thumbnail((a.size, a.size), Image.LANCZOS)
        try: im.save(OUT / name, "JPEG", quality=92, exif=ex)
        except Exception: im.save(OUT / name, "JPEG", quality=92)
        rows.append([pg, slot, name, r["n"], r["kind"], r["t"], r["place"], r["tier"], "QR" if r["qr"] else "", "%dx%d" % (ow, oh), "LOW-RES" if max(ow, oh) < 1800 else ("small-only" if max(ow, oh) < 2600 else "")])
        if r["qr"]: qrrows.append([pg, name, r["id"], r["ql"], r["qt"]])
    except Exception as e:
        fail += 1; print("FAILED", r["id"], e)
with open(HERE / "page_plan.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["page", "slot", "file", "n", "kind", "time", "place", "tier", "qr", "pixels", "resolution_flag"]); w.writerows(rows)
with open(HERE / "qr_list.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["page", "frame_file", "video", "google_photos_link", "label"]); w.writerows(qrrows)
npages = len({x[0] for x in plan})
print("DONE: %d images on %d pages (target %.1f per page); failures: %d" % (len(rows), npages, a.per, fail))
print("Folder:", OUT)
