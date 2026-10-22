import pytest

from secret_calculator import security
from secret_calculator.locker import Locker, load_locker, save_locker


@pytest.fixture
def keys():
    config = security.create_credentials("48201937", "secret1", iterations=1_000)
    return security.unlock_keys(config, "48201937", "secret1")


def test_add_update_delete():
    locker = Locker()
    entry = locker.add("  Gmail ", "Account", "me@example.com", "pa55", "main email")
    assert entry.title == "Gmail"
    locker.update(entry.id, "Gmail (work)", "Account", "me@work.com", "new", "")
    assert locker.get(entry.id).username == "me@work.com"
    locker.delete(entry.id)
    assert locker.entries == []


@pytest.mark.parametrize("title, category", [("", "Account"), ("   ", "Note"), ("x" * 81, "Note"), ("ok", "Nope")])
def test_invalid_entries_rejected(title, category):
    with pytest.raises(ValueError):
        Locker().add(title, category)


def test_missing_entry():
    with pytest.raises(KeyError):
        Locker().delete("nope")


def test_search():
    locker = Locker()
    locker.add("Bank", "PIN / Card", notes="ATM card")
    locker.add("Netflix", "Account", username="family")
    locker.add("Passport", "ID")
    assert [e.title for e in locker.search("atm")] == ["Bank"]
    assert [e.title for e in locker.search("FAMILY")] == ["Netflix"]
    assert [e.title for e in locker.search(category="ID")] == ["Passport"]
    assert [e.title for e in locker.search()] == ["Bank", "Netflix", "Passport"]


def test_save_and_load_round_trip(tmp_path, keys):
    path = tmp_path / "locker.enc"
    locker = Locker()
    locker.add("Bank", "PIN / Card", secret="4321")
    save_locker(locker, keys, path)
    assert b"Bank" not in path.read_bytes()
    loaded = load_locker(keys, path)
    assert loaded.entries[0].title == "Bank"
    assert loaded.entries[0].secret == "4321"


def test_missing_file_is_empty_locker(tmp_path, keys):
    assert load_locker(keys, tmp_path / "none.enc").entries == []
