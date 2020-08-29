import os

from cryptography.fernet import Fernet

from cs_crypt import CryptKeeper

os.environ["CS_CRYPT_KEEPER"] = Fernet.generate_key().decode("utf-8")


def test_basic():
    ck = CryptKeeper()

    encrypted = ck.encrypt("hello world")
    assert isinstance(encrypted, str)

    assert ck.decrypt(encrypted) == "hello world"
