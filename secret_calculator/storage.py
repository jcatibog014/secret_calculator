"""Where the app keeps its files: %APPDATA%\\SecretCalculator (never inside the repo)."""

import json
import os
from pathlib import Path

APP_DIR_NAME = "SecretCalculator"
HOME_OVERRIDE_ENV = "SECRET_CALCULATOR_HOME"


def data_dir():
    """Folder for config, locker and history. Set SECRET_CALCULATOR_HOME to override."""
    override = os.environ.get(HOME_OVERRIDE_ENV)
    if override:
        folder = Path(override)
    elif os.environ.get("APPDATA"):
        folder = Path(os.environ["APPDATA"]) / APP_DIR_NAME
    else:
        folder = Path.home() / f".{APP_DIR_NAME.lower()}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def config_path():
    return data_dir() / "config.json"


def locker_path():
    return data_dir() / "locker.enc"


def history_path():
    return data_dir() / "history.json"


def is_first_run():
    return not config_path().exists()


def write_bytes_atomic(path, data):
    """Write to a temp file then swap it in, so a crash never leaves half a file."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def read_json(path, default=None):
    """Load JSON, returning `default` if the file is missing or unreadable."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return default


def write_json(path, data):
    write_bytes_atomic(path, json.dumps(data, indent=2).encode("utf-8"))
