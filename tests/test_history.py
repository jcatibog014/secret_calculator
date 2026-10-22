from secret_calculator.history import MAX_ITEMS, History, load_history, save_history


def test_newest_first_and_capped():
    history = History()
    for n in range(MAX_ITEMS + 5):
        history.add(f"{n} + 0", str(n))
    assert len(history) == MAX_ITEMS
    assert history.items[0]["result"] == str(MAX_ITEMS + 4)


def test_clear():
    history = History()
    history.add("1 + 1", "2")
    history.clear()
    assert len(history) == 0


def test_bad_items_are_skipped():
    history = History([{"expression": "1 + 1", "result": "2"}, {"oops": 1}, "junk"])
    assert len(history) == 1


def test_save_and_load(tmp_path):
    path = tmp_path / "history.json"
    history = History()
    history.add("2 × 3", "6")
    save_history(history, path)
    assert load_history(path).items == [{"expression": "2 × 3", "result": "6"}]


def test_corrupt_file_gives_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json", encoding="utf-8")
    assert len(load_history(path)) == 0
