import base64
import binascii
import os
from typing import List, Union


try:
    from cryptography.fernet import Fernet, MultiFernet
except ImportError:
    Fernet = None
    MultiFernet = None


__version__ = "0.0.2"

KEY_ENV = "CS_CRYPT_KEY"
KEY_FROM_ENV = os.environ.get(KEY_ENV, "")


def _validate_key(key):
    """
    Validate and return a 32B key.

    Key can be generated via:
    - openssl rand -hex 32
    - Fernet.generate_key()
    
    Returns:
    - key (bytes): raw 32B key
    """
    if isinstance(key, str):
        key = key.encode("ascii")

    if len(key) == 44:
        try:
            key = base64.urlsafe_b64decode(key)
        except ValueError:
            pass

    elif len(key) == 64:
        try:
            # 64B could be 32B, hex-encoded
            return binascii.a2b_hex(key)
        except ValueError:
            # not 32B hex
            pass

    if len(key) != 32:
        raise ValueError("Encryption keys must be 32 bytes, hex or base64-encoded.")

    return key


class CryptKeeper:
    def __init__(self, keys: List[Union[str, bytes]] = None):
        self._keys = self.read_keys(keys)

        self.check_available()

        self._fernet = MultiFernet(
            [Fernet(base64.urlsafe_b64encode(key)) for key in self._keys]
        )

    def read_keys(self, keys: List[Union[str, bytes]] = None):
        if keys is not None:
            return [_validate_key(key) for key in keys]
        else:
            return [
                _validate_key(key) for key in KEY_FROM_ENV.split(";") if key.strip()
            ]

    def encrypt(self, data: str):
        self.check_available()
        return self._fernet.encrypt(data.encode("utf8")).decode("utf-8")

    def decrypt(self, data: str):
        self.check_available()
        return self._fernet.decrypt(data.encode("utf-8")).decode("utf-8")

    def check_available(self):
        if Fernet is None or MultiFernet is None:
            raise CryptographyUnavailable()

        if not self._keys:
            raise NoEncryptionKeys()


class EncryptionUnavailable(Exception):
    pass


class CryptographyUnavailable(EncryptionUnavailable):
    def __str__(self):
        return "cryptography library is required for encryption"


class NoEncryptionKeys(EncryptionUnavailable):
    def __str__(self):
        return "Encryption keys must be specified in %s env" % KEY_ENV
