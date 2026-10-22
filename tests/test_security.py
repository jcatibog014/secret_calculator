import pytest

from secret_calculator import security
from secret_calculator.security import InvalidToken

FAST = 1_000  # few PBKDF2 rounds so tests stay quick


@pytest.mark.parametrize("pin, ok", [
    ("48201937", True), ("00918273", True),
    ("", False), ("1234567", False), ("123456789", False), ("1234567a", False),
    ("11111111", False), ("12345678", False), ("87654321", False), ("23456789", False),
])
def test_validate_pin(pin, ok):
    assert (security.validate_pin(pin) is None) is ok


@pytest.mark.parametrize("password, ok", [
    ("secret1", True), ("Mango2026!", True),
    ("", False), ("abc12", False), ("abcdefgh", False), ("12345678", False),
    (" secret1", False), ("secret1 ", False), ("a1" * 17, False),
])
def test_validate_password(password, ok):
    assert (security.validate_password(password) is None) is ok


def test_password_cannot_equal_pin():
    assert security.validate_password("48201937a", pin="48201937a") is not None


def test_hash_and_verify():
    salt, digest = security.hash_secret("48201937", iterations=FAST)
    assert security.verify_secret("48201937", salt, digest, FAST)
    assert not security.verify_secret("48201938", salt, digest, FAST)


def test_credentials_do_not_contain_secrets():
    config = security.create_credentials("48201937", "secret1", iterations=FAST)
    text = str(config)
    assert "48201937" not in text and "secret1" not in text
    assert security.verify_pin("48201937", config)
    assert security.verify_password("secret1", config)
    assert not security.verify_password("secret2", config)


def test_double_encryption_needs_both_keys():
    config = security.create_credentials("48201937", "secret1", iterations=FAST)
    keys = security.unlock_keys(config, "48201937", "secret1")
    token = security.double_encrypt(b"hello", keys)
    assert b"hello" not in token
    assert security.double_decrypt(token, keys) == b"hello"

    wrong_pin = security.unlock_keys(config, "48201938", "secret1")
    wrong_password = security.unlock_keys(config, "48201937", "secret2")
    for bad in (wrong_pin, wrong_password):
        with pytest.raises(InvalidToken):
            security.double_decrypt(token, bad)


def test_change_pin_and_password():
    config = security.create_credentials("48201937", "secret1", iterations=FAST)
    keys = security.unlock_keys(config, "48201937", "secret1")

    config, keys = security.change_pin(config, keys, "55500011")
    assert security.verify_pin("55500011", config)
    assert not security.verify_pin("48201937", config)
    assert keys == security.unlock_keys(config, "55500011", "secret1")

    config, keys = security.change_password(config, keys, "newpass9")
    assert security.verify_password("newpass9", config)
    assert keys == security.unlock_keys(config, "55500011", "newpass9")
