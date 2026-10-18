"""Verify-only Ed25519 (RFC 8032), standard library only (ADR-0009, ADR-0029 SR-28/SR-29).

Ported from the reference code in RFC 8032 section 6, reduced to signature
verification. There is no signing function in this module and none may be added:
the CLI only ever checks signatures the server made. Constant-time behaviour is
not required, because every input here (public key, message, signature) is public.

Decoding is strict, which the RFC reference code is not:

* the public key is exactly 32 bytes and the signature exactly 64;
* ``S >= L`` is rejected, so a signature cannot be malleated into a second valid one;
* a point encoding with ``y >= p``, or with ``x == 0`` and the sign bit set, is rejected;
* a point that is not on the curve is rejected;
* a public key of small order is rejected.

The equation checked is the cofactorless ``[S]B == R + [k]A`` with
``k = SHA-512(R || A || M) mod L``, compared in projective coordinates.

The RFC 8032 code components are used under the Simplified BSD License:

    Copyright (c) 2017 IETF Trust and the persons identified as the document
    authors. All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
    LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import annotations

import hashlib

__all__ = ["verify"]

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _recover_x(y, sign):
    """The x coordinate for ``y`` and the sign bit, or ``None`` when none exists."""
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


def _add(a, b):
    """Extended-coordinate addition (RFC 8032 section 5.1.4)."""
    t1 = (a[1] - a[0]) * (b[1] - b[0]) % _P
    t2 = (a[1] + a[0]) * (b[1] + b[0]) % _P
    c = 2 * a[3] * b[3] * _D % _P
    dd = 2 * a[2] * b[2] % _P
    e, f, g, h = t2 - t1, dd - c, dd + c, t2 + t1
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


_IDENTITY = (0, 1, 1, 0)


def _mul(scalar, point):
    result = _IDENTITY
    addend = point
    while scalar > 0:
        if scalar & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        scalar >>= 1
    return result


def _equal(a, b):
    """Projective equality: no inversion needed."""
    if (a[0] * b[2] - b[0] * a[2]) % _P != 0:
        return False
    return (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _decode(data):
    """A point from its 32-byte encoding, or ``None`` when it is not canonical."""
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _P)


_G_Y = 4 * pow(5, _P - 2, _P) % _P
_G_X = _recover_x(_G_Y, 0)
_BASE = (_G_X, _G_Y, 1, _G_X * _G_Y % _P)


def _small_order(point):
    """True when ``[8]point`` is the identity, which only a small-order point satisfies."""
    return _equal(_mul(8, point), _IDENTITY)


def _sha512_int(*parts):
    digest = hashlib.sha512()
    for part in parts:
        digest.update(part)
    return int.from_bytes(digest.digest(), "little")


def verify(public_key, message, signature):
    """True only for a canonical, valid signature of ``message`` by ``public_key``.

    Never raises on malformed input: a wrong type, length or encoding is ``False``.
    """
    if not isinstance(public_key, (bytes, bytearray)) or not isinstance(
        signature, (bytes, bytearray)
    ) or not isinstance(message, (bytes, bytearray)):
        return False
    public_key, message, signature = bytes(public_key), bytes(message), bytes(signature)
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a_point = _decode(public_key)
    if a_point is None or _small_order(a_point):
        return False
    r_bytes = signature[:32]
    r_point = _decode(r_bytes)
    if r_point is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    k = _sha512_int(r_bytes, public_key, message) % _L
    left = _mul(s, _BASE)
    right = _add(r_point, _mul(k, a_point))
    return _equal(left, right)
