"""Test-only Ed25519 signer (RFC 8032 section 5.1.6). Never shipped: `tests/` is stripped.

The package carries a verifier and nothing else (ADR-0029 SR-28). Fixtures need real
signatures, so the signing half lives here, built on the verifier's own curve arithmetic.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from devteam import ed25519 as _e  # noqa: E402


def _encode(point):
    zinv = pow(point[2], _e._P - 2, _e._P)
    x, y = point[0] * zinv % _e._P, point[1] * zinv % _e._P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _secret(seed):
    digest = hashlib.sha512(seed).digest()
    a = int.from_bytes(digest[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, digest[32:]


def public_key(seed):
    a, _prefix = _secret(seed)
    return _encode(_e._mul(a, _e._BASE))


def sign(seed, message):
    a, prefix = _secret(seed)
    pub = _encode(_e._mul(a, _e._BASE))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % _e._L
    r_bytes = _encode(_e._mul(r, _e._BASE))
    k = int.from_bytes(hashlib.sha512(r_bytes + pub + message).digest(), "little") % _e._L
    s = (r + k * a) % _e._L
    return r_bytes + s.to_bytes(32, "little")
