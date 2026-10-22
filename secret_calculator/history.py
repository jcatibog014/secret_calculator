"""Calculation history: newest first, capped, saved as JSON."""

from . import storage

MAX_ITEMS = 50


class History:
    def __init__(self, items=None):
        self.items = []
        for item in items or []:
            if self._is_valid(item):
                self.items.append({"expression": item["expression"], "result": item["result"]})
        del self.items[MAX_ITEMS:]

    @staticmethod
    def _is_valid(item):
        return (
            isinstance(item, dict)
            and isinstance(item.get("expression"), str)
            and isinstance(item.get("result"), str)
        )

    def add(self, expression, result):
        self.items.insert(0, {"expression": expression, "result": result})
        del self.items[MAX_ITEMS:]

    def clear(self):
        self.items.clear()

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


def load_history(path=None):
    data = storage.read_json(path or storage.history_path(), default=[])
    return History(data if isinstance(data, list) else [])


def save_history(history, path=None):
    storage.write_json(path or storage.history_path(), history.items)
