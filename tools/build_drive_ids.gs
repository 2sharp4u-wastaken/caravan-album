/**
 * build_drive_ids.gs  -  Google Apps Script (run at https://script.google.com)
 *
 * Builds drive_ids.json: { "<filename>": {"id": "...", "size": N, "mime": "..."} }
 * for every original photo/video in the trip folder (top level only; _album is skipped).
 * The JSON is saved into the trip folder's _album subfolder on Drive (and synced to the PC).
 *
 * Run it AFTER Google Drive for Desktop has finished uploading.
 * Safe to re-run: it overwrites drive_ids.json.
 */

const FOLDER_ID = '17pCaZasqkkXreElzLwraxWKHeezRWx00'; // Caravan Trip in Germany, Austria & Czechia 8-2026
const OUT_NAME  = 'drive_ids.json';

function buildDriveIds() {
  const root = DriveApp.getFolderById(FOLDER_ID);
  const map = {};
  const dupes = [];
  let n = 0;

  const it = root.getFiles();
  while (it.hasNext()) {
    const f = it.next();
    const name = f.getName();
    const rec = { id: f.getId(), size: f.getSize(), mime: f.getMimeType() };
    if (map[name]) {            // same name twice: keep both, flag it
      if (!Array.isArray(map[name])) map[name] = [map[name]];
      map[name].push(rec);
      dupes.push(name);
    } else {
      map[name] = rec;
    }
    n++;
  }

  const out = {
    folderId: FOLDER_ID,
    generated: new Date().toISOString(),
    count: n,
    duplicates: dupes,
    files: map,
  };
  const json = JSON.stringify(out, null, 1);

  // write into _album (create/overwrite)
  const albums = root.getFoldersByName('_album');
  const target = albums.hasNext() ? albums.next() : root;
  const old = target.getFilesByName(OUT_NAME);
  while (old.hasNext()) old.next().setTrashed(true);
  target.createFile(OUT_NAME, json, 'application/json');

  Logger.log('Wrote %s: %s files, %s duplicate names %s', OUT_NAME, n, dupes.length, dupes.join(', '));
}
