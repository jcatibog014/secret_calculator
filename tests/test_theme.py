import re

from secret_calculator.gui import theme
from secret_calculator.locker import CATEGORIES

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_every_category_has_a_colour_and_label():
    assert set(theme.CATEGORY_COLORS) == set(CATEGORIES)
    assert set(theme.CATEGORY_LABELS) == set(CATEGORIES)


def test_category_colours_are_distinct_hex():
    colours = [theme.CATEGORY_COLORS[c] for c in CATEGORIES]
    assert all(HEX.match(c) for c in colours)
    assert len(set(colours)) == len(colours)


def test_spec_colours():
    assert theme.BG == "#1B1F27"
    assert theme.AMBER == "#F2B33D"
    assert theme.BUTTON_HEIGHT >= 44 and theme.KEY_HEIGHT >= 44
