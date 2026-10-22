"""Calculator logic: pure arithmetic functions plus a key-press state machine.

Nothing here knows about Tkinter, so every rule can be unit tested.
"""

from decimal import Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_UP, localcontext

MAX_DIGITS = 16
OPERATORS = ("+", "−", "×", "÷")

# Keyboard / ASCII spellings mapped to the symbols shown on the buttons.
OPERATOR_ALIASES = {"+": "+", "-": "−", "−": "−", "*": "×", "x": "×", "×": "×", "/": "÷", "÷": "÷"}

SCIENTIFIC_ABOVE = Decimal("1e16")
SCIENTIFIC_BELOW = Decimal("1e-10")
DECIMAL_PLACES = Decimal("1e-12")


class CalculatorError(Exception):
    """Raised when a calculation cannot produce a number (e.g. divide by zero)."""


def normalize_operator(op):
    """Return the display symbol for an operator, or raise ValueError if unknown."""
    if op not in OPERATOR_ALIASES:
        raise ValueError(f"Unknown operator: {op!r}")
    return OPERATOR_ALIASES[op]


def calculate(a, op, b):
    """Apply one arithmetic operation to two Decimals and return a Decimal."""
    op = normalize_operator(op)
    try:
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.traps[DivisionByZero] = True
            ctx.traps[InvalidOperation] = True
            ctx.traps[Overflow] = True
            if op == "+":
                return a + b
            if op == "−":
                return a - b
            if op == "×":
                return a * b
            if b == 0:
                raise CalculatorError("Cannot divide by zero")
            return a / b
    except (DivisionByZero, InvalidOperation):
        raise CalculatorError("Cannot divide by zero")
    except Overflow:
        raise CalculatorError("Number too large")


def apply_percent(value, base=None, op=None):
    """Percent key: '50 + 10 %' means 10% of 50; otherwise value / 100."""
    if base is not None and op in ("+", "−"):
        return base * value / 100
    return value / 100


def format_number(value):
    """Turn a Decimal into display text: no trailing zeros, scientific when extreme."""
    if not value.is_finite():
        raise CalculatorError("Invalid result")
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= SCIENTIFIC_ABOVE or magnitude < SCIENTIFIC_BELOW:
        mantissa, exponent = f"{value:.10e}".split("e")
        if "." in mantissa:
            mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent):+d}"
    with localcontext() as ctx:
        ctx.prec = 40
        rounded = value.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def parse_number(text):
    """Read a pasted number like ' 1,234.5 ' or '−7'. Returns a Decimal, or None if invalid."""
    cleaned = text.strip().replace(",", "").replace(" ", "").replace("−", "-")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not value.is_finite() or count_digits(cleaned) > MAX_DIGITS:
        return None
    return value


def count_digits(entry):
    """How many digits an entry contains (sign and decimal point don't count)."""
    return sum(ch.isdigit() for ch in entry)


def display_entry(entry):
    """Strip extra leading zeros from what the user typed ('007' -> '7', '00.5' -> '0.5')."""
    sign = "-" if entry.startswith("-") else ""
    body = entry.lstrip("-")
    whole, dot, fraction = body.partition(".")
    whole = whole.lstrip("0") or "0"
    return f"{sign}{whole}{dot}{fraction}"


class Calculator:
    """Tracks what has been typed and turns key presses into results."""

    def __init__(self):
        self.clear()

    # ----- state helpers -------------------------------------------------
    def clear(self):
        self.entry = "0"
        self.fresh = True          # next digit starts a new number
        self.accumulator = None    # left-hand side of a pending operation
        self.operator = None
        self.last_operator = None  # remembered for repeated '='
        self.last_operand = None
        self.after_equals = False
        self.expression = ""
        self.error = None

    def _value(self):
        return Decimal(self.entry)

    def _set_error(self, message):
        self.error = message
        self.expression = message

    @property
    def display(self):
        if self.error:
            return "Error"
        if self.fresh:
            return format_number(self._value())  # results keep full precision, shown rounded
        return display_entry(self.entry)

    @property
    def typed_digits(self):
        """The raw digits of the number being typed, or '' if it isn't plain digits."""
        if self.fresh or self.error or not self.entry.isdigit():
            return ""
        return self.entry

    # ----- keys ------------------------------------------------------------
    def press_digit(self, digit):
        if digit not in "0123456789" or len(digit) != 1:
            raise ValueError(f"Not a digit: {digit!r}")
        if self.error or self.after_equals:
            self.clear()
        if self.fresh:
            self.entry = digit
            self.fresh = False
        elif count_digits(self.entry) < MAX_DIGITS:
            self.entry += digit

    def press_decimal(self):
        if self.error or self.after_equals:
            self.clear()
        if self.fresh:
            self.entry = "0."
            self.fresh = False
        elif "." not in self.entry:
            self.entry += "."

    def backspace(self):
        if self.error:
            self.clear()
            return
        if self.fresh:
            return  # results can't be edited digit by digit
        self.entry = self.entry[:-1]
        if self.entry in ("", "-"):
            self.entry = "0"
            self.fresh = True

    def clear_entry(self):
        if self.error:
            self.clear()
            return
        self.entry = "0"
        self.fresh = True

    def toggle_sign(self):
        if self.error or self._value() == 0:
            return
        self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry

    def press_percent(self):
        if self.error:
            return
        value = apply_percent(self._value(), self.accumulator, self.operator)
        self.entry = str(value)
        self.fresh = True

    def press_operator(self, op):
        op = normalize_operator(op)
        if self.error:
            return
        if self.operator is not None and self.fresh:
            self.operator = op  # pressed two operators in a row: keep the last one
            self.expression = f"{format_number(self.accumulator)} {op}"
            return
        value = self._value()
        if self.operator is not None:
            try:
                value = calculate(self.accumulator, self.operator, value)
            except CalculatorError as exc:
                self._set_error(str(exc))
                return
        self.accumulator = value
        self.operator = op
        self.entry = str(value)
        self.fresh = True
        self.after_equals = False
        self.expression = f"{format_number(value)} {op}"

    def press_equals(self):
        """Finish the calculation. Returns (expression, result) for history, or None."""
        if self.error:
            return None
        if self.operator is not None:
            a, op, b = self.accumulator, self.operator, self._value()
        elif self.after_equals and self.last_operator is not None:
            a, op, b = self._value(), self.last_operator, self.last_operand
        else:
            return None  # nothing to calculate
        expression = f"{format_number(a)} {op} {format_number(b)}"
        try:
            value = calculate(a, op, b)
            result = format_number(value)
        except CalculatorError as exc:
            self.accumulator = None
            self.operator = None
            self._set_error(str(exc))
            return None
        self.last_operator, self.last_operand = op, b
        self.accumulator = None
        self.operator = None
        self.entry = str(value)
        self.fresh = True
        self.after_equals = True
        self.expression = f"{expression} ="
        return expression, result

    def load_value(self, text):
        """Put a number (e.g. picked from history) into the display."""
        value = Decimal(text)
        if self.error or self.after_equals:
            self.clear()
        self.entry = str(value)
        self.fresh = True
