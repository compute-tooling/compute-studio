import os

import pytest
from cryptography.fernet import Fernet

from cs_crypt import CryptKeeper, NoEncryptionKeys, CryptographyUnavailable
import cs_crypt


@pytest.fixture
def cs_crypt_key(monkeypatch):
    monkeypatch.setattr(cs_crypt, "KEY_FROM_ENV", Fernet.generate_key().decode("utf-8"))


@pytest.fixture
def no_cs_crypt_key(monkeypatch):
    monkeypatch.setattr(cs_crypt, "KEY_FROM_ENV", "")


def test_basic(cs_crypt_key):
    ck = CryptKeeper()

    encrypted = ck.encrypt("hello world")
    assert isinstance(encrypted, str)

    assert ck.decrypt(encrypted) == "hello world"

    ck2 = CryptKeeper(keys=[Fernet.generate_key() for _ in range(3)])
    encrypted = ck2.encrypt("hello world")
    assert isinstance(encrypted, str)

    assert ck2.decrypt(encrypted) == "hello world"


def test_available(monkeypatch, no_cs_crypt_key):
    with pytest.raises(NoEncryptionKeys):
        CryptKeeper(keys=None)

    monkeypatch.setattr(cs_crypt, "Fernet", None)
    monkeypatch.setattr(cs_crypt, "MultiFernet", None)
    with pytest.raises(CryptographyUnavailable):
        CryptKeeper(keys=[Fernet.generate_key()])
