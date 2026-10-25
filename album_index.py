#!/usr/bin/env python3
"""
album_index.py  -  stage 1 of the trip-album pipeline.

Reads every photo / video / video-frame snapshot in a folder and writes, into
<folder>/_album/:
    index.json      one record per file (time, GPS, device, size, quality metrics, hashes)
    thumbs/         480px previews (photos, frames, one poster per video)
    strips/         4-up keyframe strip per video (to judge content without playing it)
    samples.npz     tiny 32x32 grey keyframes per video + per snapshot (for frame->video matching)
    album_pack.zip  everything above, packed small enough to hand to Claude (no originals!)

Originals are only READ. Nothing in the source folder is modified or uploaded.
Resumable: re-running skips files already processed (same name + size).
"""
import argparse, json, os, re, sys, time, zipfile, traceback, datetime as dt
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageOps
import av
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as _e:  # some PCs block this native library; JPEG-in-.HEIC still opens via Pillow
    print("note: pillow-heif unavailable (%s); real HEIC files will be reported as errors" % _e)
av.logging.set_level(av.logging.FATAL)

PHOTO_EXT = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".avi", ".mkv"}
THUMB = 480
TRIP_UTC_OFFSET_H = 2   # CEST (Germany/Austria/Czechia in August). Used only for UTC-stamped videos.


# ----------------------------------------------------------------- helpers
def rat(x):
    try:
        return float(x)
    except Exception:
        try:
            return x[0] / x[1]
        except Exception:
            return None


def dms(v, ref):
    if not v or len(v) < 3:
        return None
    d, m, s = (rat(i) for i in v[:3])
    if None in (d, m, s):
        return None
    out = d + m / 60 + s / 3600
    return -out if ref in ("S", "W") else out


def parse_exif_dt(s, off=None):
    if not s:
        return None
    s = str(s).strip().replace("\x00", "")
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s[:19], fmt)
        except ValueError:
            pass
    return None


def name_time(name):
    m = re.search(r"(?:IMG|VID|PXL|PANO|MVIMG)[_-](\d{8})[_-](\d{6})", name)
    if m:
        try:
            return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        except ValueError:
            pass
    m = re.search(r"VIDEO-(\d{4})-(\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d)", name)
    if m:
        return dt.datetime(*map(int, m.groups()))
    m = re.search(r"-(\d{8})-WA\d+", name)  # WhatsApp: date only
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%Y%m%d")
        except ValueError:
            pass
    return None


def parse_iso6709(s):
    if not s:
        return None, None
    m = re.match(r"\s*([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)", s)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def gray32(rgb):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    return cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA)


def dhash(rgb, n=8):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (n + 1, n), interpolation=cv2.INTER_AREA)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return "%016x" % int("".join("1" if b else "0" for b in bits), 2)


def metrics(rgb):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (320, int(320 * g.shape[0] / g.shape[1]) or 1), interpolation=cv2.INTER_AREA)
    return round(float(cv2.Laplacian(g, cv2.CV_64F).var()), 1), round(float(g.mean()), 1)


def save_thumb(img, path, size=THUMB, q=72):
    img = img.convert("RGB")
    img.thumbnail((size, size))
    img.save(path, "JPEG", quality=q, optimize=True)


# ----------------------------------------------------------------- photos
def do_photo(path, out):
    rec = {}
    img = Image.open(path)
    rec["w"], rec["h"] = img.size
    ex = img.getexif()
    sub = ex.get_ifd(0x8769) if ex else {}
    gps = ex.get_ifd(0x8825) if ex else {}
    rec["device"] = " ".join(str(ex.get(k, "")).strip() for k in (271, 272)).strip() or None
    t = parse_exif_dt(sub.get(36867) or sub.get(36868) or ex.get(306))
    if t:
        rec["t_local"] = t.isoformat()
        rec["t_src"] = "exif"
        off = sub.get(36881)
        if off:
            rec["tz"] = str(off)
    lat = lon = None
    if gps:
        lat = dms(gps.get(2), gps.get(1))
        lon = dms(gps.get(4), gps.get(3))
        alt = rat(gps.get(6))
        if alt is not None:
            rec["alt"] = round(alt, 1)
    if lat is not None and lon is not None and (abs(lat) > 1e-6 or abs(lon) > 1e-6):
        rec["lat"], rec["lon"] = round(lat, 6), round(lon, 6)
    img = ImageOps.exif_transpose(img)
    rgb = np.array(img.convert("RGB"))
    save_thumb(img, out / "thumbs" / (path.name + ".jpg"))
    rec["dhash"] = dhash(rgb)
    rec["sharp"], rec["bright"] = metrics(rgb)
    small = np.array(img.convert("RGB").resize((64, 64)))
    return rec, gray32(rgb)[None], None


# ----------------------------------------------------------------- videos
def do_video(path, out):
    rec = {}
    samples, times, imgs = [], [], []
    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        md = {k.lower(): v for k, v in dict(c.metadata).items()}
        md.update({k.lower(): v for k, v in dict(vs.metadata).items() if k.lower() not in md})
        dur = float(c.duration / av.time_base) if c.duration else None
        rec["dur"] = round(dur, 1) if dur else None
        rec["has_audio"] = len(c.streams.audio) > 0
        rec["device"] = md.get("com.apple.quicktime.model") or md.get("com.android.manufacturer") or None
        if md.get("com.apple.quicktime.make") and md.get("com.apple.quicktime.model"):
            rec["device"] = md["com.apple.quicktime.make"] + " " + md["com.apple.quicktime.model"]
        # ---- time
        t = None
        cd = md.get("com.apple.quicktime.creationdate")  # local time with offset, best source
        if cd:
            m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)([+-]\d\d:?\d\d)?", cd)
            if m:
                t = dt.datetime.fromisoformat(m.group(1))
                rec["t_src"], rec["tz"] = "qt-creationdate", m.group(2)
        if t is None and md.get("creation_time"):
            try:
                u = dt.datetime.fromisoformat(md["creation_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                if u.year > 2000:
                    t = u + dt.timedelta(hours=TRIP_UTC_OFFSET_H)
                    rec["t_src"], rec["tz"] = "container-utc+%dh(assumed)" % TRIP_UTC_OFFSET_H, None
            except ValueError:
                pass
        if t is None:
            t = name_time(path.name)
            if t:
                rec["t_src"] = "filename"
        if t:
            rec["t_local"] = t.isoformat()
        # ---- gps
        lat, lon = parse_iso6709(md.get("com.apple.quicktime.location.iso6709") or md.get("location") or md.get("location-eng"))
        if lat is not None:
            rec["lat"], rec["lon"] = lat, lon
        # ---- keyframes
        vs.thread_type = "AUTO"
        vs.codec_context.skip_frame = "NONKEY"
        min_gap = max(1.0, (dur or 0) / 48.0)
        last = -1e9
        W = 320
        for fr in c.decode(vs):
            ft = float(fr.pts * vs.time_base) if fr.pts is not None else (len(times) * 1.0)
            if ft - last < min_gap * 0.9 and times:
                continue
            h = max(2, int(round(W * fr.height / fr.width / 2)) * 2)
            rgb = fr.reformat(width=W, height=h, format="rgb24").to_ndarray()
            rot = getattr(fr, "rotation", 0) or 0
            if not rot:
                try:
                    rot = int(vs.metadata.get("rotate", 0))
                except Exception:
                    rot = 0
            k = (int(round(rot / 90.0))) % 4
            if k:
                rgb = np.rot90(rgb, k)
            rgb = np.ascontiguousarray(rgb)
            times.append(round(ft, 2))
            samples.append(gray32(rgb))
            imgs.append(rgb)
            last = ft
            if len(times) >= 64:
                break
    if not imgs:
        raise RuntimeError("no keyframes decoded")
    rec["w"], rec["h"] = (imgs[0].shape[1], imgs[0].shape[0])  # displayed aspect at thumb scale
    mid = imgs[len(imgs) // 3]
    Image.fromarray(mid).save(out / "thumbs" / (path.name + ".jpg"), "JPEG", quality=72, optimize=True)
    pick = [imgs[int(i)] for i in np.linspace(0, len(imgs) - 1, min(4, len(imgs)))]
    hh = 200
    row = [cv2.resize(p, (int(p.shape[1] * hh / p.shape[0]), hh)) for p in pick]
    Image.fromarray(np.hstack(row)).save(out / "strips" / (path.name + ".jpg"), "JPEG", quality=65, optimize=True)
    rec["dhash"] = dhash(mid)
    rec["sharp"], rec["bright"] = metrics(mid)
    rec["n_samples"] = len(times)
    return rec, np.stack(samples), np.array(times, dtype=np.float32)


# ----------------------------------------------------------------- worker
def work(args):
    path, out = Path(args[0]), Path(args[1])
    rel = args[2]
    ext = path.suffix.lower()
    rec = {"id": rel, "name": path.name, "size": path.stat().st_size, "ext": ext.lstrip(".")}
    try:
        if ext in VIDEO_EXT:
            rec["kind"] = "video"
            r, smp, tms = do_video(path, out)
        else:
            m = re.match(r"videoframe[_ ]?(\d+)", path.stem, re.I)
            rec["kind"] = "frame" if m else "photo"
            if m:
                rec["frame_hint_ms"] = int(m.group(1))
            r, smp, tms = do_photo(path, out)
        rec.update(r)
        nt = name_time(path.name)
        if nt:
            rec["t_name"] = nt.isoformat()
            if "t_local" not in rec:
                rec["t_local"], rec["t_src"] = rec["t_name"], "filename"
        rec["thumb"] = "thumbs/" + path.name + ".jpg"
        if rec["kind"] == "video":
            rec["strip"] = "strips/" + path.name + ".jpg"
        if "lat" not in rec:
            rec.pop("lon", None)
    except Exception as e:
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        smp = tms = None
    return rec, smp, tms


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--no-pack", action="store_true")
    a = ap.parse_args()
    root = Path(a.folder).resolve()
    out = root / "_album"
    for d in ("thumbs", "strips"):
        (out / d).mkdir(parents=True, exist_ok=True)

    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part.startswith("_") for part in p.relative_to(root).parts[:-1]):
            if p.suffix.lower() in PHOTO_EXT | VIDEO_EXT:
                files.append(p)
    print("found %d media files in %s" % (len(files), root))

    idx_path, smp_path = out / "index.json", out / "samples.npz"
    old = {}
    samples = {}
    if idx_path.exists() and smp_path.exists():
        try:
            old = {r["id"]: r for r in json.loads(idx_path.read_text(encoding="utf-8"))}
            z = np.load(smp_path)
            samples = {k: z[k] for k in z.files}
        except Exception:
            old, samples = {}, {}

    todo, recs = [], {}
    for p in files:
        rel = p.relative_to(root).as_posix()
        o = old.get(rel)
        if o and o.get("size") == p.stat().st_size and "error" not in o and (rel + "|s" in samples):
            recs[rel] = o
        else:
            todo.append((str(p), str(out), rel))
    print("already done: %d   to process: %d   workers: %d" % (len(recs), len(todo), a.workers))

    def flush():
        ordered = [recs[k] for k in sorted(recs)]
        idx_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=0), encoding="utf-8")
        np.savez(smp_path, **samples)

    t0, n = time.time(), 0
    if todo:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(work, t): t for t in todo}
            for f in as_completed(futs):
                rec, smp, tms = f.result()
                recs[rec["id"]] = rec
                if smp is not None:
                    samples[rec["id"] + "|s"] = smp
                    if tms is not None:
                        samples[rec["id"] + "|t"] = tms
                n += 1
                if n % 25 == 0 or n == len(todo):
                    el = time.time() - t0
                    print("  %d/%d  (%.0fs elapsed, ~%.0fs left)" % (n, len(todo), el, el / n * (len(todo) - n)))
                    sys.stdout.flush()
                if n % 100 == 0:
                    flush()
    # ---- pair Live-Photo motion clips (same file stem as a still, short video)
    stills = {Path(r["name"]).stem.lower(): r["id"] for r in recs.values() if r["kind"] in ("photo",)}
    n_live = 0
    for r in recs.values():
        if r["kind"] == "video" and (r.get("dur") or 99) <= 6:
            k = Path(r["name"]).stem.lower()
            if k in stills:
                r["live_of"] = stills[k]
                recs[stills[k]]["live_clip"] = r["id"]
                n_live += 1
    print("live-photo clips paired with stills:", n_live)
    flush()

    errs = [r for r in recs.values() if "error" in r]
    print("\n=== SUMMARY ===")
    kinds = {}
    for r in recs.values():
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("items:", kinds, " errors:", len(errs))
    for r in errs[:15]:
        print("  ERR", r["name"], r["error"])
    print("with time: %d   with GPS: %d" % (sum("t_local" in r for r in recs.values()), sum("lat" in r for r in recs.values())))

    if not a.no_pack:
        pack = out / "album_pack.zip"
        with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as z:
            z.write(idx_path, "index.json")
            z.write(smp_path, "samples.npz")
            for d in ("thumbs", "strips"):
                for f in sorted((out / d).iterdir()):
                    z.write(f, d + "/" + f.name)
        print("pack: %s  (%.0f MB)" % (pack, pack.stat().st_size / 1e6))
    print("DONE. Tell Claude: 'stage 1 finished'.")


if __name__ == "__main__":
    main()
