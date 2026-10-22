"""PIN / password rules, hashing, and the two-layer encryption of the locker.

Layer 1 (inner) is encrypted with a key derived from the password.
Layer 2 (outer) is encrypted with a key derived from the 8-digit PIN.
Both secrets are needed to read the locker file.
"""

import base64
import hashlib
import hmac
import os
from collections import namedtuple

from cryptography.fernet import Fernet, InvalidToken

PIN_LENGTH = 8
PASSWORD_MIN = 6
PASSWORD_MAX = 32
ITERATIONS = 300_000
SALT_BYTES = 16

Keys = namedtuple("Keys", "pin_key password_key")

__all__ = [
    "InvalidToken", "Keys", "validate_pin", "validate_password", "hash_secret", "verify_secret",
    "derive_key", "create_credentials", "verify_pin", "verify_password", "unlock_keys",
    "change_pin", "change_password", "double_encrypt", "double_decrypt",
]


# ----- rules ---------------------------------------------------------------
def _is_sequence(pin):
    steps = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
    return steps == {1} or steps == {-1}


def validate_pin(pin):
    """Return an error message, or None if the PIN is acceptable."""
    if not pin:
        return "Enter a PIN"
    if not pin.isdigit():
        return "PIN must be numbers only"
    if len(pin) != PIN_LENGTH:
        return f"PIN must be exactly {PIN_LENGTH} digits"
    if len(set(pin)) == 1:
        return "PIN can't be all the same digit"
    if _is_sequence(pin):
        return "PIN can't be a straight sequence"
    return None


def validate_password(password, pin=None):
    """Return an error message, or None if the password is acceptable."""
    if not password:
        return "Enter a password"
    if password != password.strip():
        return "Password can't start or end with a space"
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters"
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters"
    if not any(ch.isalpha() for ch in password):
        return "Password needs at least one letter"
    if not any(ch.isdigit() for ch in password):
        return "Password needs at least one number"
    if pin is not None and password == pin:
        return "Password must be different from the PIN"
    return None


# ----- hashing & keys --------------------------------------------------------
def _pbkdf2(secret, salt, iterations):
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)


def _new_salt():
    return os.urandom(SALT_BYTES)


def hash_secret(secret, salt=None, iterations=ITERATIONS):
    """Return (salt_hex, hash_hex) for storing a secret without storing the secret."""
    salt = salt or _new_salt()
    return salt.hex(), _pbkdf2(secret, salt, iterations).hex()


def verify_secret(secret, salt_hex, hash_hex, iterations=ITERATIONS):
    actual = _pbkdf2(secret, bytes.fromhex(salt_hex), iterations)
    return hmac.compare_digest(actual, bytes.fromhex(hash_hex))


def derive_key(secret, salt, iterations=ITERATIONS):
    """A Fernet key made from a secret. Uses a different salt than the stored hash."""
    return base64.urlsafe_b64encode(_pbkdf2(secret, salt, iterations))


def _secret_record(secret, iterations):
    salt_hex, hash_hex = hash_secret(secret, iterations=iterations)
    return {"salt": salt_hex, "hash": hash_hex, "key_salt": _new_salt().hex()}


def create_credentials(pin, password, iterations=ITERATIONS):
    """Build the config dict saved at first-run setup."""
    return {
        "version": 1,
        "iterations": iterations,
        "pin": _secret_record(pin, iterations),
        "password": _secret_record(password, iterations),
    }


def verify_pin(pin, config):
    record = config["pin"]
    return verify_secret(pin, record["salt"], record["hash"], config["iterations"])


def verify_password(password, config):
    record = config["password"]
    return verify_secret(password, record["salt"], record["hash"], config["iterations"])


def _key_for(secret, record, iterations):
    return derive_key(secret, bytes.fromhex(record["key_salt"]), iterations)


def unlock_keys(config, pin, password):
    iterations = config["iterations"]
    return Keys(
        pin_key=_key_for(pin, config["pin"], iterations),
        password_key=_key_for(password, config["password"], iterations),
    )


def change_pin(config, keys, new_pin):
    """Return (new_config, new_keys) with a fresh PIN; the password layer is untouched."""
    iterations = config["iterations"]
    record = _secret_record(new_pin, iterations)
    new_config = {**config, "pin": record}
    return new_config, keys._replace(pin_key=_key_for(new_pin, record, iterations))


def change_password(config, keys, new_password):
    """Return (new_config, new_keys) with a fresh password; the PIN layer is untouched."""
    iterations = config["iterations"]
    record = _secret_record(new_password, iterations)
    new_config = {**config, "password": record}
    return new_config, keys._replace(password_key=_key_for(new_password, record, iterations))


# ----- double encryption ----------------------------------------------------
def double_encrypt(data, keys):
    inner = Fernet(keys.password_key).encrypt(data)
    return Fernet(keys.pin_key).encrypt(inner)


def double_decrypt(token, keys):
    """Raises cryptography.fernet.InvalidToken if either key is wrong."""
    inner = Fernet(keys.pin_key).decrypt(token)
    return Fernet(keys.password_key).decrypt(inner)
