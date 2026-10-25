"""Shared path config. Photos folder = config.json "photos_dir", or env CARAVAN_PHOTOS,
or (default, old layout) the parent of this folder."""
import json, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
def photos_root() -> Path:
    p = os.environ.get("CARAVAN_PHOTOS")
    cfg = HERE / "config.json"
    if not p and cfg.exists():
        p = json.loads(cfg.read_text(encoding="utf-8")).get("photos_dir")
    return Path(p).expanduser().resolve() if p else (HERE / "..").resolve()
