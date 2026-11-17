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

## Cloud copy
Old claude.ai artifact "Caravan Album Review": https://claude.ai/artifact/8A8ZwMeRZnKrPhwiFzhJkM – private, works on
phone, syncs via the artifact db. Being replaced by task 2 (GitHub Pages + Google Drive, code already in `cloud/`,
see above) – keep the artifact around as a fallback only until Eran finishes the one-time setup and re-imports
decisions.json there. Same UI either way: Select mode, touch, `film.js` lists frames, `drive.js` = name → Drive ID
for "Open full resolution in Drive" buttons. Neither version can play full videos (not uploaded); both use filmstrips.
- Until task 2's setup is done, **the claude.ai artifact is still the source of truth for decisions.** Move them to
  the PC with Import/Export → save `decisions.json` into `_album`, then run the .bat/.sh scripts.

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
2. **Migrate the review app off claude.ai** – code done 2026-10-25, needs Eran's one-time setup (see `cloud/README.md`):
   - `cloud/index.html` no longer calls `window.claude.use(...)`; sign-in and Drive I/O are in `cloud/drivesync.js`
     (Google Identity Services token client, scope = full `drive`, decided over `drive.file`/readonly for simplicity).
   - Thumbnails + film frames: fetched live from Drive `_album/thumbs`, `_album/film` per image (decided over the
     per-day-pack-blob approach to skip a manual 100 MB upload; revisit if Drive API quota becomes a problem).
     `manifest.js` (the old pack-offset map) is removed, no longer needed.
   - Decisions: one JSON file per day in Drive `_album/decisions/days/<date>.json` + `extra/frames.json` + `extra/notime.json`,
     written debounced per day via `cloud/drivesync.js`, re-read on tab focus for cross-device sync. decisions.json
     export/import (for the PC scripts) still works, now via a plain browser download instead of the artifact's downloads API.
   - Full-res: unchanged, `drive_ids.json` → `https://drive.google.com/file/d/<id>/view` via `drive.js`.
   - Still true: mobile layout, Select mode, swipe, frame picker, people tags, captions, QR/page fields – untouched.
   - **Eran still needs to, by hand** (walked through in `cloud/README.md`): make the repo public (Settings → Danger
     Zone) and turn on Settings → Pages → Source: GitHub Actions (workflow `.github/workflows/pages.yml` already
     added, deploys `cloud/` on push to `main`); create the Google Cloud project + OAuth Client ID (Web, authorized
     origin = the Pages URL) and paste it into `cloud/config.js`; then sign in once on the Pages URL and use
     Import/export → "Import into the cloud" with this repo's `decisions.json` to seed Drive.
   - Chose to make the repo public rather than pay for private Pages – data.js/decisions.json (times, GPS, device
     names, Hebrew captions, people tags) become world-readable at the Pages URL once that's done; thumbnails/film
     stay private since they're fetched per-viewer from Drive with their own Google sign-in.
3. **Live Photos (434 items with `live`):** add frame picking. Extend `film.py` to make filmstrips for Live clips (~3 s, ~8 frames each),
   show the picker for photos with `live` with "original photo (full res)" as default, and make `picks.py` extract the chosen frame.
   Clip frames are ≤1440×1920 vs ~12 MP stills – fine for small slots only.
4. Continue the album: grouping/page layout (`page_plan.csv`), captions from `itinerary_and_captions.md`, then `make_wow.py` for upload.

## Known placements
#1019/#1020 Munich airport; #1026 Israel airport. Videoframes "0 (1)" and "1066 (1)" share time/place with videoframe_45721;
10853, 11339, 5666 share time/place with videoframe_3688 (Lipno slide).
