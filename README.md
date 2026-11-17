# Caravan Trip Album (Aug 2026)

Tools and review app for the printed album of the Germany/Austria/Czechia caravan trip.
Start with **CLAUDE.md** – full project notes, rules and open tasks.

## Setup on a new machine
1. Get the originals (read-only) – Google Drive → Computers → My Computer → trip folder (1,555 files).
2. `cp config.example.json config.json` and set `photos_dir` to that folder.
3. macOS/Linux: `./setup.sh` (creates `.venv`, installs `requirements.txt`, indexes the originals → thumbs/strips).
   Windows: `run_stage1.bat` (old layout: this folder inside the photo folder works without config.json).
4. Then `./run_film.sh`, `./run_picks.sh`, `./run_make_wow.sh` (or the `.bat` versions).

## Folders
- `review/` – local PC review app (`review.html` + `data.js`, `items_min.json`)
- `cloud/` – GitHub Pages review app (Google sign-in + Drive sync, no claude.ai runtime needed). See `cloud/README.md` for one-time setup (OAuth client, enabling Pages).
- `maps/` – Hebrew day minimaps + endpaper route map
- `tools/build_drive_ids.gs` – Apps Script that builds `drive_ids.json`
- generated, not in git: `thumbs/ film/ strips/ for_wow/ picks/ draft/`
