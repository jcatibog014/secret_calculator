import pytest

from secret_calculator import APP_NAME
from secret_calculator.gui.icon import ASSETS, ICON_SIZES

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_app_name():
    assert APP_NAME == "Count Me Out"


@pytest.mark.parametrize("name", ["logo.png", *(f"icon-{size}.png" for size in ICON_SIZES)])
def test_png_icons_present(name):
    assert (ASSETS / name).read_bytes().startswith(PNG_SIGNATURE)


def test_windows_icon_present():
    assert (ASSETS / "icon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
