from decimal import Decimal

import pytest

from secret_calculator.calculator import (
    MAX_DIGITS, Calculator, CalculatorError, apply_percent, calculate, display_entry, format_number,
    parse_number,
)


def press(calc, keys):
    """Feed a string of keys: digits, '.', operators, '=' and 'C'."""
    for key in keys:
        if key.isdigit():
            calc.press_digit(key)
        elif key == ".":
            calc.press_decimal()
        elif key == "=":
            calc.press_equals()
        elif key == "C":
            calc.clear()
        else:
            calc.press_operator(key)
    return calc.display


# ----- pure functions -------------------------------------------------------
@pytest.mark.parametrize("a, op, b, expected", [
    ("2", "+", "3", "5"), ("2", "-", "3", "-1"), ("4", "*", "2.5", "10"), ("9", "/", "4", "2.25"),
    ("0.1", "+", "0.2", "0.3"),
])
def test_calculate(a, op, b, expected):
    assert calculate(Decimal(a), op, Decimal(b)) == Decimal(expected)


def test_divide_by_zero():
    with pytest.raises(CalculatorError):
        calculate(Decimal(5), "÷", Decimal(0))
    with pytest.raises(CalculatorError):
        calculate(Decimal(0), "/", Decimal(0))


def test_unknown_operator():
    with pytest.raises(ValueError):
        calculate(Decimal(1), "^", Decimal(2))


@pytest.mark.parametrize("value, expected", [
    ("0", "0"), ("-0", "0"), ("2.50", "2.5"), ("100", "100"), ("1E+2", "100"),
    ("0.3333333333333333", "0.333333333333"), ("12345678901234567", "1.2345678901e+16"),
    ("0.00000000001", "1e-11"), ("-5", "-5"),
])
def test_format_number(value, expected):
    assert format_number(Decimal(value)) == expected


def test_display_entry_strips_leading_zeros():
    assert display_entry("007") == "7"
    assert display_entry("00.5") == "0.5"
    assert display_entry("-0012") == "-12"
    assert display_entry("0") == "0"


@pytest.mark.parametrize("text, expected", [
    ("42", "42"), (" 1,234.5 \n", "1234.5"), ("−7", "-7"), ("-0.25", "-0.25"), ("1e3", "1000"),
])
def test_parse_number(text, expected):
    assert parse_number(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "   ", "abc", "1+1", "NaN", "Infinity", "1" * (MAX_DIGITS + 1)])
def test_parse_number_rejects(text):
    assert parse_number(text) is None


def test_apply_percent():
    assert apply_percent(Decimal(10), Decimal(50), "+") == Decimal(5)
    assert apply_percent(Decimal(10), Decimal(50), "×") == Decimal("0.1")
    assert apply_percent(Decimal(25)) == Decimal("0.25")


# ----- state machine ---------------------------------------------------------
def test_basic_and_chained_operations():
    assert press(Calculator(), "12+3=") == "15"
    assert press(Calculator(), "2+3*4=") == "20"  # left to right, like a pocket calculator


def test_float_rounding_is_hidden():
    assert press(Calculator(), "0.1+0.2=") == "0.3"
    assert press(Calculator(), "1/3*3=") == "1"


def test_divide_by_zero_shows_error_and_recovers():
    calc = Calculator()
    assert press(calc, "5/0=") == "Error"
    assert calc.expression == "Cannot divide by zero"
    calc.press_digit("7")
    assert calc.display == "7"


def test_second_decimal_point_ignored():
    assert press(Calculator(), "1.2.3") == "1.23"


def test_operator_replaced_when_pressed_twice():
    calc = Calculator()
    press(calc, "8+-")
    assert calc.expression == "8 −"
    assert press(calc, "3=") == "5"


def test_repeated_equals_repeats_last_operation():
    calc = Calculator()
    press(calc, "2+3=")
    assert press(calc, "=") == "8"
    assert press(calc, "=") == "11"


def test_equals_with_nothing_to_do():
    calc = Calculator()
    assert calc.press_equals() is None
    press(calc, "5")
    assert calc.press_equals() is None
    assert calc.display == "5"


def test_equals_returns_history_pair():
    calc = Calculator()
    press(calc, "6*7")
    assert calc.press_equals() == ("6 × 7", "42")


def test_digit_limit():
    calc = Calculator()
    press(calc, "9" * (MAX_DIGITS + 5))
    assert len(calc.display) == MAX_DIGITS


def test_typing_after_result_starts_new_number():
    calc = Calculator()
    press(calc, "2+2=")
    assert press(calc, "9") == "9"


def test_operator_after_result_continues():
    assert press(Calculator(), "2+2=*5=") == "20"


def test_backspace_and_clear_entry():
    calc = Calculator()
    press(calc, "123")
    calc.backspace()
    assert calc.display == "12"
    calc.backspace()
    calc.backspace()
    assert calc.display == "0"
    press(calc, "9+4")
    calc.clear_entry()
    assert press(calc, "1=") == "10"


def test_toggle_sign_and_percent():
    calc = Calculator()
    press(calc, "5")
    calc.toggle_sign()
    assert calc.display == "-5"
    calc = Calculator()
    press(calc, "50+10")
    calc.press_percent()
    assert press(calc, "=") == "55"


def test_toggle_sign_on_zero_does_nothing():
    calc = Calculator()
    calc.toggle_sign()
    assert calc.display == "0"


def test_typed_digits_keeps_leading_zeros():
    calc = Calculator()
    press(calc, "00123456")
    assert calc.typed_digits == "00123456"
    assert calc.display == "123456"


def test_typed_digits_empty_for_results_and_decimals():
    calc = Calculator()
    press(calc, "1.5")
    assert calc.typed_digits == ""
    press(calc, "C12345678+1=")
    assert calc.typed_digits == ""


def test_typed_digits_for_second_operand():
    calc = Calculator()
    press(calc, "5+87654320")
    assert calc.typed_digits == "87654320"


def test_load_value_from_history():
    calc = Calculator()
    calc.load_value("42")
    assert press(calc, "+1=") == "43"
