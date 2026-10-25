# Caravan Trip Album – project notes for Claude Code

Printed photo album of the family caravan trip, Germany / Austria / Czechia, 12–25 Aug 2026.
Owner: Eran. Chat in English; album text, maps and captions in Hebrew (RTL).

## Goal
- Print at wow.co.il (same engine as albume.co.il): flat/thick-page album ("אלבום שטוח"), 40x30 cm.
- Plan: ~800 photos on ~60 pages (13–14 per page), some hero pages. Captions on ~1/3 of pages, placed ON photos, never as bands.
- Chronological and fun. Brutal honesty when culling blurry/noisy/repetitive shots; don't oversize the album.
- Workflow: normalize (time + place) → order → group/position → captions/fun facts.
- Family: Eran ערן, Liat ליאת, Omer עומר, Zohar זוהר, Idan עידן. Others = Friends / Strangers.

## Hard rules
- **Never modify the originals** in the parent folder. They must keep EXIF/GPS: wow sorts uploads by geo + EXIF.
- Back up any file before editing it (e.g. `review.backup.html`).
- Paths contain Hebrew (`C:\Users\אני\...`) and spaces/ampersand – always quote them; use paths exactly as listed.
- After writing a file, verify it (re-read / diff). A save once silently didn't persist.
- For HTML with inline JS: extract the `<script>` and run `node --check` before saving.

## Layout
Parent folder `Caravan Trip in Germany, Austria & Czechia 8-2026\` = 1,555 originals downloaded from Google Photos
(HEIC/JPG/PNG photos, MOV/MP4 videos, Live Photo clips = `IMG_xxxx.MP4` next to `IMG_xxxx.HEIC`, ~70 `videoframe_*.png` snapshots).
Total ≈ 11.4 GB; originals ≈ 9.9 GB.

`_album\` (this folder) – working files:
- `review\review.html`, `review\data.js` – local review app (PC version, plays full videos). data.js = `window.DATA = {items, frames, notime}`.
  - item fields: n, id, name, kind (photo|video|map), t_local, t_src, lat, lon, loc_src, place, cc, dur, device, thumb, strip, sharp, tier (A hero / B strong / C maybe / X cut – Claude's suggestion), live (paired clip name), w, h
- `decisions.json` – Eran's choices: `{items:{n:{d:keep|maybe|cut, x:reviewed, p:[people], c:caption, pt:video second, pg:album page, qr, ql, qt}}, frames:{}, notime:{}}`
- `thumbs\` (~400 px), `strips\` (filmstrip per video), `film\` (≈1 frame/s per video for frame picking), `maps\` (Hebrew round minimaps per day + endpaper route map), `draft\`
- Scripts: `film.py` (filmstrips/frames), `picks.py` + `run_picks.bat` (export chosen video frames as full-res PNG), `make_wow.py` + `run_make_wow.bat` (build wow upload set), `album_index.py`, `probe_heic.py`, `run_film.bat`, `run_probe.bat`, `run_stage1.bat`; `page_plan.csv`, `qr_list.csv`, `index.json`, `film_list.json`, `samples.npz`
- `for_wow\` – output of make_wow.py (upload set for wow)
- `drive_ids.json` – filename → Google Drive file ID for every original (built by Apps Script `build_drive_ids.gs`, Drive folder id 17pCaZasqkkXreElzLwraxWKHeezRWx00). Re-run the script if originals are replaced.
- `.venv\` – Python env, machine-specific; don't sync/commit, recreate with `python -m venv .venv`.

## Cloud copy (claude.ai artifact "Caravan Album Review")
https://claude.ai/artifact/8A8ZwMeRZnKrPhwiFzhJkM – private, works on phone.
- Same UI as review.html plus Select mode, touch, sync via the artifact db (docs `days/<date>`, `extra/frames`, `extra/notime`).
- Thumbnails/frames packed per day into blobs referenced by `manifest.js`; `film.js` lists frames; `drive.js` = name → Drive ID for "Open full resolution in Drive" buttons.
- Until task 2 is done, **the cloud copy is the source of truth for decisions.** Move them to the PC with Import/Export → save `decisions.json` into `_album`, then run the .bat scripts.
- It can't play full videos (videos not uploaded); it uses the filmstrips.

## Where things live
- **Originals:** Google Drive, backed up from the Windows PC (Drive → Computers → My Computer → trip folder, id 17pCaZasqkkXreElzLwraxWKHeezRWx00).
  Read-only. Any machine that runs the scripts needs a local copy (download once); config.json points at it.
- **Code + small data:** private GitHub repo `caravan-album` (this folder's code, review app, data.js, decisions.json, drive_ids.json, maps, docs).
  NOT in git: originals, thumbs/, film/, strips/, for_wow/, draft/, .venv/, *.zip, samples.npz. Keep the git clone OUTSIDE any Drive-synced folder.
- **Itinerary & caption drafts:** `itinerary_and_captions.md` (moved here from the claude.ai project).
- Decisions in cloud and local decisions.json were verified identical on 2026-10-25 (127 reviewed).

## Open tasks (in order)
1. ~~Repo hygiene~~ – done 2026-10-25: `config.py` + `config.json` (`photos_dir`; default = parent folder, so the old Windows layout still works),
   `setup.sh` / `run_*.sh` for macOS, `requirements.txt`. Not yet run on a Mac – verify `./setup.sh` end to end on first use.
2. **Migrate the review app off claude.ai** so everything is maintained from Claude Code:
   - Host the app on GitHub Pages (code only, no photos – repo/page can be public or private-with-Pages).
   - Google sign-in (Google Identity Services, OAuth client for the Pages origin; scope `drive.file` or `drive.readonly` + app-data as needed).
   - Thumbnails + film frames: read from the Drive `_album/thumbs`, `_album/film` folders with the user's token (private). Or keep the per-day packs
     from the artifact (`manifest.js` + blobs) uploaded to Drive – fewer requests.
   - Decisions: one JSON file per day in Drive `_album/decisions/` (mirrors the artifact db docs `days/<date>`, `extra/frames`, `extra/notime`),
     read on load, write debounced per day, poll or re-read on focus for cross-device sync. Keep decisions.json export for the scripts.
   - Full-res: keep `drive_ids.json` → `https://drive.google.com/file/d/<id>/view`.
   - Must stay: mobile layout, Select mode, swipe, frame picker, people tags, captions, QR/page fields.
   - The user must create the Google Cloud project + OAuth Client ID (Web, authorized origin = the Pages URL). Walk them through it click by click.
   - Migration of data: seed the per-day files from decisions.json (current state of truth).
   - The current artifact source is in `cloud/` (index.html, data.js, film.js, manifest.js, drive.js). The per-day thumbnail pack blobs (~100 MB) are NOT in git – regenerate from thumbs/ + film/ or ask for them.
3. **Live Photos (434 items with `live`):** add frame picking. Extend `film.py` to make filmstrips for Live clips (~3 s, ~8 frames each),
   show the picker for photos with `live` with "original photo (full res)" as default, and make `picks.py` extract the chosen frame.
   Clip frames are ≤1440×1920 vs ~12 MP stills – fine for small slots only.
4. Continue the album: grouping/page layout (`page_plan.csv`), captions from `itinerary_and_captions.md`, then `make_wow.py` for upload.

## Known placements
#1019/#1020 Munich airport; #1026 Israel airport. Videoframes "0 (1)" and "1066 (1)" share time/place with videoframe_45721;
10853, 11339, 5666 share time/place with videoframe_3688 (Lipno slide).
