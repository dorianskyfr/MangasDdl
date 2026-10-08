"""Writable user data, independent of the launch directory."""
import json
import os
import sys
import tempfile
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("MANGASDDL_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return root / "MangasDdl"


def user_file(name: str) -> Path:
    path = data_dir() / name
    # Preserve existing installations. Never remove the original file.
    if not path.exists():
        legacy = Path(__file__).resolve().parent / name
        if legacy.exists() and legacy != path:
            try:
                atomic_json_write(path, json.loads(legacy.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    return path


def atomic_json_write(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
