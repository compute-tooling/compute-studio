# cs-crypt

Package for encrypting and decrypting secrets. This is used internally by the
Compute Studio webapp and kubernetes cluster for encrypting and decrypting
JWT secrets.

This package is a modified version of JupyterHub's crypto.py module:
https://github.com/jupyterhub/jupyterhub/blob/1.1.0/jupyterhub/crypto.py

### Usage

Generate cryptography key:

```bash
$ export CS_CRYPT_KEY=$(openssl rand -hex 32)
```

Use key to encrypt and decrypt secrets:

```python
In [1]: import cs_crypt

In [2]: ck = cs_crypt.CryptKeeper()

In [3]: encrypted = ck.encrypt("hello world")

In [4]: encrypted
Out[4]: 'gAAAAABfTPkkftDS0Od1_jfKOH0At2EK2sLJfiWUaR1QyXAI74Aq9Qvab5NPI-KLPN1WeoSQly5WKwcWT_-03uq9hKsVG7-MMQ=='

In [5]: ck.decrypt(encrypted)
Out[5]: 'hello world'
```
