"""Hand-built strict-verification cases standing in for the Wycheproof EdDSA set (ADR-0029 SR-29).

The Wycheproof data is not vendored (no verifiable offline copy), so the categories it exercises
are built here from the curve itself: the eight torsion points, non-canonical encodings, scalars
at and past the group order, and mixed-order keys. Expected results follow from the cofactorless
equation the verifier documents, never from a copied value.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import ed25519_signer as signer  # noqa: E402
from devteam import ed25519  # noqa: E402

P, L = ed25519._P, ed25519._L
SEED = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")


def torsion_points():
    """All eight points of order dividing 8, derived by clearing the prime-order part."""
    y = 2
    while True:
        x = ed25519._recover_x(y, 0)
        if x is not None:
            t = ed25519._mul(L, (x, y, 1, x * y % P))
            if not ed25519._equal(ed25519._mul(4, t), ed25519._IDENTITY):
                break
        y += 1
    points, current = [], ed25519._IDENTITY
    for _ in range(8):
        points.append(current)
        current = ed25519._add(current, t)
    return points


TORSION = torsion_points()
ENCODED_TORSION = [signer._encode(point) for point in TORSION]


class StrictVerificationTest(unittest.TestCase):
    def setUp(self):
        self.pub = signer.public_key(SEED)
        self.msg = b"strict"
        self.sig = signer.sign(SEED, self.msg)

    def test_the_valid_signature_is_accepted(self):
        self.assertTrue(ed25519.verify(self.pub, self.msg, self.sig))

    def test_there_are_eight_distinct_torsion_points(self):
        self.assertEqual(len(set(ENCODED_TORSION)), 8)

    def test_every_small_order_public_key_is_refused(self):
        for index, key in enumerate(ENCODED_TORSION):
            with self.subTest(torsion=index):
                self.assertFalse(ed25519.verify(key, self.msg, self.sig))
                self.assertFalse(ed25519.verify(key, self.msg, key + bytes(32)))

    def test_small_order_r_with_an_unrelated_scalar_is_refused(self):
        for index, r in enumerate(ENCODED_TORSION):
            with self.subTest(torsion=index):
                for s in (0, 1, 8, L - 1):
                    self.assertFalse(ed25519.verify(self.pub, self.msg, r + s.to_bytes(32, "little")))

    def test_a_scalar_at_or_past_the_group_order_is_refused_in_every_form(self):
        s = int.from_bytes(self.sig[32:], "little")
        for label, value in (
            ("S+L", s + L),
            ("L", L),
            ("L+1", L + 1),
            ("2^253", 1 << 253),
            ("2^256-1", (1 << 256) - 1),
        ):
            with self.subTest(case=label):
                self.assertFalse(ed25519.verify(self.pub, self.msg, self.sig[:32] + value.to_bytes(32, "little")))

    def test_the_scalar_just_under_the_order_is_a_real_comparison(self):
        # L - 1 is canonical, so the rejection is the equation failing, not a length or range quirk.
        self.assertFalse(ed25519.verify(self.pub, self.msg, self.sig[:32] + (L - 1).to_bytes(32, "little")))

    def test_every_non_canonical_y_encoding_is_refused_for_a_and_for_r(self):
        # y in [p, 2^255) reduces to a small y but is a second spelling of the same point.
        for y in range(P, P + 19):
            raw = y.to_bytes(32, "little")
            for sign in (0, 1):
                encoded = raw if not sign else (y | (1 << 255)).to_bytes(32, "little")
                with self.subTest(y=y - P, sign=sign):
                    self.assertFalse(ed25519.verify(encoded, self.msg, self.sig))
                    self.assertFalse(ed25519.verify(self.pub, self.msg, encoded + self.sig[32:]))

    def test_a_sign_bit_on_x_equal_zero_is_refused(self):
        for y in (1, P - 1):
            encoded = (y | (1 << 255)).to_bytes(32, "little")
            with self.subTest(y=y):
                self.assertFalse(ed25519.verify(encoded, self.msg, self.sig))
                self.assertFalse(ed25519.verify(self.pub, self.msg, encoded + self.sig[32:]))

    def test_a_flipped_sign_bit_on_the_public_key_is_refused(self):
        flipped = bytearray(self.pub)
        flipped[31] ^= 0x80
        self.assertFalse(ed25519.verify(bytes(flipped), self.msg, self.sig))

    def test_a_mixed_order_key_does_not_validate_the_prime_order_signature(self):
        a = signer._secret(SEED)[0]
        for index in range(1, 8):
            mixed = signer._encode(ed25519._add(ed25519._mul(a, ed25519._BASE), TORSION[index]))
            for message in (b"m0", b"m1", b"m2", b"m3"):
                sig = signer.sign(SEED, message)
                k = int.from_bytes(hashlib.sha512(sig[:32] + mixed + message).digest(), "little") % L
                with self.subTest(torsion=index, message=message):
                    # [S]B == R + [k]A' only when [k]T vanishes, i.e. k is a multiple of the torsion order.
                    holds = ed25519._equal(
                        ed25519._mul(int.from_bytes(sig[32:], "little"), ed25519._BASE),
                        ed25519._add(ed25519._decode(sig[:32]), ed25519._mul(k, ed25519._decode(mixed))),
                    )
                    self.assertEqual(ed25519.verify(mixed, message, sig), holds)

    def test_a_mixed_order_r_is_refused_when_the_equation_does_not_hold(self):
        r = ed25519._decode(self.sig[:32])
        for index in range(1, 8):
            mixed = signer._encode(ed25519._add(r, TORSION[index]))
            with self.subTest(torsion=index):
                self.assertFalse(ed25519.verify(self.pub, self.msg, mixed + self.sig[32:]))

    def test_an_identity_r_and_zero_scalar_does_not_verify_for_a_real_key(self):
        self.assertFalse(ed25519.verify(self.pub, self.msg, (1).to_bytes(32, "little") + bytes(32)))

    def test_empty_and_oversized_inputs_fail_closed(self):
        self.assertFalse(ed25519.verify(b"", self.msg, self.sig))
        self.assertFalse(ed25519.verify(self.pub, self.msg, b""))
        self.assertFalse(ed25519.verify(bytes(32), self.msg, bytes(64)))
        self.assertFalse(ed25519.verify(b"\xff" * 32, self.msg, b"\xff" * 64))

    def test_a_long_message_round_trips_and_one_flipped_bit_fails(self):
        message = bytes(range(256)) * 4
        sig = signer.sign(SEED, message)
        self.assertTrue(ed25519.verify(self.pub, message, sig))
        self.assertFalse(ed25519.verify(self.pub, message[:-1] + bytes([message[-1] ^ 1]), sig))


class Rfc8032Test1024(unittest.TestCase):
    @unittest.skip(
        "RFC 8032 section 7.1 TEST 1024 needs its 1023-byte message, which is not available "
        "offline and must not be reconstructed from memory; long messages are covered by "
        "test_a_long_message_round_trips_and_one_flipped_bit_fails"
    )
    def test_the_1023_byte_vector_verifies(self):
        raise AssertionError("unreachable")


if __name__ == "__main__":
    unittest.main()
