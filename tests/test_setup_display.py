from secret_calculator.gui.calculator_window import pin_counter, pin_slots


def test_empty_pin_shows_all_blanks():
    assert pin_slots("") == "_ _ _ _ _ _ _ _"
    assert pin_counter("") == "0 of 8 digits"


def test_leading_zero_is_visible():
    # A first 0 must show up, unlike the normal calculator display which drops it.
    assert pin_slots("0") == "0 _ _ _ _ _ _ _"
    assert pin_slots("05") == "0 5 _ _ _ _ _ _"
    assert pin_counter("05") == "2 of 8 digits"


def test_full_pin():
    assert pin_slots("05918273") == "0 5 9 1 8 2 7 3"
    assert pin_counter("05918273") == "8 of 8 digits"
