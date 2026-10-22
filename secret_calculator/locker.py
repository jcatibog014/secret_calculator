"""The hidden Info Locker: entries kept in memory, saved double-encrypted."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from . import security, storage

CATEGORIES = ("Account", "PIN / Card", "ID", "Contact", "Note", "Other")
TITLE_MAX = 80


def _now():
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class LockerEntry:
    title: str
    category: str = "Other"
    username: str = ""
    secret: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)


def validate_entry(title, category):
    """Return an error message, or None if the entry can be saved."""
    title = title.strip()
    if not title:
        return "Title is required"
    if len(title) > TITLE_MAX:
        return f"Title must be at most {TITLE_MAX} characters"
    if category not in CATEGORIES:
        return "Pick a category from the list"
    return None


class Locker:
    def __init__(self, entries=None):
        self.entries = list(entries or [])

    def get(self, entry_id):
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        raise KeyError(entry_id)

    def add(self, title, category="Other", username="", secret="", notes=""):
        error = validate_entry(title, category)
        if error:
            raise ValueError(error)
        entry = LockerEntry(title.strip(), category, username, secret, notes)
        self.entries.append(entry)
        return entry

    def update(self, entry_id, title, category, username="", secret="", notes=""):
        error = validate_entry(title, category)
        if error:
            raise ValueError(error)
        entry = self.get(entry_id)
        entry.title = title.strip()
        entry.category = category
        entry.username = username
        entry.secret = secret
        entry.notes = notes
        entry.updated = _now()
        return entry

    def delete(self, entry_id):
        self.entries.remove(self.get(entry_id))

    def search(self, query="", category=None):
        """Entries whose title, username or notes contain `query` (case-insensitive)."""
        query = query.strip().lower()
        results = []
        for entry in self.entries:
            if category and entry.category != category:
                continue
            haystack = f"{entry.title}\n{entry.username}\n{entry.notes}".lower()
            if query and query not in haystack:
                continue
            results.append(entry)
        return sorted(results, key=lambda e: e.title.lower())

    def to_bytes(self):
        return json.dumps([asdict(e) for e in self.entries]).encode("utf-8")

    @classmethod
    def from_bytes(cls, data):
        known = set(LockerEntry.__dataclass_fields__)
        entries = [LockerEntry(**{k: v for k, v in item.items() if k in known})
                   for item in json.loads(data.decode("utf-8"))]
        return cls(entries)


def save_locker(locker, keys, path=None):
    storage.write_bytes_atomic(path or storage.locker_path(), security.double_encrypt(locker.to_bytes(), keys))


def load_locker(keys, path=None):
    """Decrypt the locker file. A missing file means an empty locker."""
    path = path or storage.locker_path()
    try:
        token = path.read_bytes()
    except FileNotFoundError:
        return Locker()
    return Locker.from_bytes(security.double_decrypt(token, keys))
