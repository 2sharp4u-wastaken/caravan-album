# Cloud review app – setup (task 2)

Static site in this folder: `index.html` + `data.js`/`film.js`/`drive.js` (committed data) +
`config.js` (your OAuth Client ID) + `drivesync.js` (Google sign-in + Drive read/write, no server).
No `window.claude` runtime calls left – it runs on any static host.

What it does once signed in with your Google account:
- Reads thumbnails and film frames directly from your Drive `_album/thumbs` and `_album/film` folders
  (one Drive API request per image the first time it's shown; the Drive file id then stays cached in
  this browser's `localStorage`, so repeat visits are fast).
- Reads/writes your choices as one JSON file per day in Drive `_album/decisions/days/<date>.json`,
  plus `_album/decisions/extra/frames.json` and `.../notime.json`. Re-reads the current day on tab
  focus so a second device's edits show up without a hard refresh.
- "Import / export" still saves/loads a plain `decisions.json` for the PC scripts, like before.

## One-time setup

### 1. Make the repo public, turn on Pages
GitHub Settings → General → Danger Zone → **Change visibility → Make public** (type the repo name to confirm).
Then Settings → Pages → **Source: GitHub Actions**. `.github/workflows/pages.yml` (already in this repo)
then deploys this `cloud/` folder to `https://<you>.github.io/caravan-album/` on every push to `main`
that touches `cloud/**`. The photo *originals* are never touched by any of this – only the code and the
metadata already in `data.js`/`decisions.json` (times, places, captions, people tags) becomes world-readable
at that URL. Thumbnails/film frames are fetched live from your Drive with your own sign-in, so they stay
private even though the page is public.

### 2. Create the Google OAuth Client ID
1. https://console.cloud.google.com/ → create a new project (e.g. "Caravan Album").
2. **APIs & Services → Library** → enable **Google Drive API**.
3. **APIs & Services → OAuth consent screen**: User type **External**, app name "Caravan Album Review",
   your email as support + developer contact. Scopes: add `https://www.googleapis.com/auth/drive`
   (full Drive access – simplest way for the app to read your existing `_album` folder and write
   `_album/decisions/`). Add yourself (and Liat, if she'll use it) under **Test users**. Leave the app
   in "Testing" status – that's fine for a private family tool; you'll just see a one-time
   "Google hasn't verified this app" click-through the first time each person signs in.
4. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**:
   - Application type: **Web application**.
   - Authorized JavaScript origins: `https://<you>.github.io` (no path, no trailing slash).
   - Create. Copy the Client ID (ends `.apps.googleusercontent.com`).
5. Paste it into `cloud/config.js` here (`clientId: "..."`) and push to `main`.

### 3. Seed Drive from the current decisions.json
In Drive, make sure your `_album` folder (the one with `thumbs/`, `film/`, etc.) is there; a `decisions/`
subfolder will be created automatically on first write. Open the Pages URL, tap **Sign in with Google**,
then open **Import / export → Import from the PC**, pick this repo's `decisions.json`, and press
**Import into the cloud** – that writes everything into `_album/decisions/*.json` in one go. After that,
decisions made on the Pages site sync straight to Drive; export `decisions.json` from there whenever you
want to run `run_picks.sh` / `run_make_wow.sh` on the PC.

## Still open
- Live Photo frame picking (task 3) still needs filmstrips generated for the 434 `live` items.
- If Drive API quota ever gets ugly on a big scrolling session, revisit the day-pack-blob approach
  noted in `CLAUDE.md` task 2 – it was skipped for now in favor of simplicity.
