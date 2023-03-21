This file explains how to build the cryptography 38 wheels for Python 3.10 (chaquopy 14.0.2).

Just follow the instructions of `README_cryptography_39.md` but with the following changes:

- in `server/pypi/packages/cryptography/meta.yaml` change version to `version: 38.0.4`
- `rm server/pypi/packages/cryptography/patches/no_legacy_ciphers_39.patch`
- `cp server/pypi/packages/cryptography/no_legacy_ciphers_38.patch server/pypi/packages/cryptography/patches`
