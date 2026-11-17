/* Minimal Google Drive REST client used by index.html for sign-in + decisions sync + image loading.
   All paths are relative to the user's "_album" folder in Drive, e.g. "thumbs/IMG_3091.MOV.jpg"
   or "decisions/days/2026-08-12.json". Folder/file ids are resolved by name and cached in localStorage
   (safe to do: ids are stable, and the cache is only ever widened, never trusted blindly for writes). */
(function () {
  const SCOPE = "https://www.googleapis.com/auth/drive";
  const API = "https://www.googleapis.com/drive/v3";
  const UPLOAD = "https://www.googleapis.com/upload/drive/v3";
  const CACHE_KEY = "caravan_drive_ids_v1";

  let tokenClient = null, accessToken = null, tokenExpiry = 0, refreshTimer = null;
  const authCbs = [];
  let idCache = {};
  try { idCache = JSON.parse(localStorage.getItem(CACHE_KEY) || "{}"); } catch (e) { idCache = {}; }
  function saveCache() { try { localStorage.setItem(CACHE_KEY, JSON.stringify(idCache)); } catch (e) {} }
  function qEsc(s) { return String(s).replace(/\\/g, "\\\\").replace(/'/g, "\\'"); }

  async function authFetch(url, opts) {
    if (!accessToken) throw new Error("not signed in");
    opts = opts || {};
    opts.headers = Object.assign({}, opts.headers, { Authorization: "Bearer " + accessToken });
    const r = await fetch(url, opts);
    if (r.status === 401) { accessToken = null; throw new Error("Drive sign-in expired - tap Sign in again"); }
    return r;
  }

  async function findChild(parentId, name, folderOnly) {
    const key = parentId + "/" + name;
    if (idCache[key] !== undefined) return idCache[key];
    let q = `name = '${qEsc(name)}' and trashed = false and '${parentId}' in parents`;
    if (folderOnly) q += " and mimeType = 'application/vnd.google-apps.folder'";
    const url = `${API}/files?q=${encodeURIComponent(q)}&fields=files(id)&pageSize=10`;
    const r = await authFetch(url);
    if (!r.ok) throw new Error("Drive lookup failed: HTTP " + r.status);
    const j = await r.json();
    const id = (j.files && j.files[0]) ? j.files[0].id : null;
    idCache[key] = id; saveCache();
    return id;
  }

  async function findAlbumRoot() {
    const key = "__album_root__";
    if (idCache[key]) return idCache[key];
    const q = "name = '_album' and mimeType = 'application/vnd.google-apps.folder' and trashed = false";
    const url = `${API}/files?q=${encodeURIComponent(q)}&fields=files(id)&pageSize=10`;
    const r = await authFetch(url);
    if (!r.ok) throw new Error("Drive lookup failed: HTTP " + r.status);
    const j = await r.json();
    if (!j.files || !j.files.length) throw new Error("No '_album' folder found in this Google account's Drive");
    idCache[key] = j.files[0].id; saveCache();
    return j.files[0].id;
  }

  async function ensureFolder(parentId, name) {
    const id = await findChild(parentId, name, true);
    if (id) return id;
    const r = await authFetch(`${API}/files`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, mimeType: "application/vnd.google-apps.folder", parents: [parentId] })
    });
    if (!r.ok) throw new Error("Could not create Drive folder '" + name + "': HTTP " + r.status);
    const j = await r.json();
    idCache[parentId + "/" + name] = j.id; saveCache();
    return j.id;
  }

  // Resolves pathParts under _album. create=true makes missing intermediate folders.
  async function resolveFileId(pathParts, create) {
    let parent = await findAlbumRoot();
    for (let i = 0; i < pathParts.length - 1; i++) {
      parent = create ? await ensureFolder(parent, pathParts[i]) : await findChild(parent, pathParts[i], true);
      if (!parent) return { parent: null, id: null };
    }
    const name = pathParts[pathParts.length - 1];
    const id = await findChild(parent, name, false);
    return { parent, id };
  }

  async function getBlobURL(key) {
    const res = await resolveFileId(key.split("/"), false);
    if (!res.id) throw new Error("not in Drive: " + key);
    const r = await authFetch(`${API}/files/${res.id}?alt=media`);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return URL.createObjectURL(await r.blob());
  }

  async function readJSON(key) {
    const res = await resolveFileId(key.split("/"), false);
    if (!res.id) return null;
    const r = await authFetch(`${API}/files/${res.id}?alt=media`);
    if (!r.ok) return null;
    try { return await r.json(); } catch (e) { return null; }
  }

  const writeChains = {};
  function writeJSON(key, obj) {
    writeChains[key] = (writeChains[key] || Promise.resolve()).then(async () => {
      const parts = key.split("/");
      const res = await resolveFileId(parts, true);
      const body = JSON.stringify(obj);
      if (res.id) {
        const r = await authFetch(`${UPLOAD}/files/${res.id}?uploadType=media`, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body
        });
        if (!r.ok) throw new Error("Drive save failed: HTTP " + r.status);
      } else {
        const name = parts[parts.length - 1];
        const form = new FormData();
        form.append("metadata", new Blob([JSON.stringify({ name, parents: [res.parent] })], { type: "application/json" }));
        form.append("file", new Blob([body], { type: "application/json" }));
        const r = await authFetch(`${UPLOAD}/files?uploadType=multipart`, { method: "POST", body: form });
        if (!r.ok) throw new Error("Drive save failed: HTTP " + r.status);
        const j = await r.json();
        idCache[res.parent + "/" + name] = j.id; saveCache();
      }
    });
    return writeChains[key];
  }

  async function waitForGIS() {
    let i = 0;
    while (!(window.google && window.google.accounts && window.google.accounts.oauth2) && i < 100) {
      await new Promise(r => setTimeout(r, 50)); i++;
    }
    if (!(window.google && window.google.accounts && window.google.accounts.oauth2)) {
      throw new Error("Google sign-in script failed to load");
    }
  }

  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => tokenClient.requestAccessToken({ prompt: "" }), Math.max(5000, tokenExpiry - Date.now()));
  }

  async function init(clientId) {
    await waitForGIS();
    tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPE,
      callback: (resp) => {
        if (resp.error) { authCbs.forEach(cb => cb({ signedIn: false, error: resp.error })); return; }
        accessToken = resp.access_token;
        tokenExpiry = Date.now() + (resp.expires_in - 60) * 1000;
        scheduleRefresh();
        authCbs.forEach(cb => cb({ signedIn: true }));
      }
    });
  }

  function signIn(interactive) {
    if (!tokenClient) return;
    tokenClient.requestAccessToken(interactive === false ? { prompt: "" } : {});
  }
  function isSignedIn() { return !!accessToken && Date.now() < tokenExpiry; }
  function onAuth(cb) { authCbs.push(cb); }

  window.DriveSync = { init, signIn, isSignedIn, onAuth, getBlobURL, readJSON, writeJSON };
})();
