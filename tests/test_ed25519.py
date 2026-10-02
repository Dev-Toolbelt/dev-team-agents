"""Verify-only Ed25519: RFC 8032 vectors and strict-decoding rejects (ADR-0029 SR-28, SR-29)."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import ed25519_signer  # noqa: E402
from devteam import ed25519  # noqa: E402

P = ed25519._P
L = ed25519._L

# RFC 8032 section 7.1: (secret seed, public key, message, signature). The three short
# vectors are transcribed from the RFC; the SHA(abc) vector is its fifth, with the message
# the SHA-512 of "abc".
RFC_VECTORS = [
    (
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        b"",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        bytes.fromhex("72"),
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
    (
        "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
        "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        bytes.fromhex("af82"),
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    ),
    (
        "833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42",
        "ec172b93ad5e563bf4932c70e1245034c35467ef2efd4d64ebf819683467e2bf",
        hashlib.sha512(b"abc").digest(),
        "dc2a4459e7369633a52b1bf277839a00201009a3efbf3ecb69bea2186c26b58909351fc9ac90b3ecfdfbc7c66431e0303dca179c138ac17ad9bef1177331a704",
    ),
]


class Rfc8032VectorsTest(unittest.TestCase):
    def test_published_vectors_verify(self):
        for seed, pub, message, sig in RFC_VECTORS:
            with self.subTest(pub=pub[:8]):
                self.assertTrue(ed25519.verify(bytes.fromhex(pub), message, bytes.fromhex(sig)))

    def test_test_signer_reproduces_the_published_signatures(self):
        for seed, pub, message, sig in RFC_VECTORS:
            with self.subTest(pub=pub[:8]):
                self.assertEqual(ed25519_signer.public_key(bytes.fromhex(seed)).hex(), pub)
                self.assertEqual(ed25519_signer.sign(bytes.fromhex(seed), message).hex(), sig)

    def test_wrong_message_fails(self):
        _seed, pub, _message, sig = RFC_VECTORS[1]
        self.assertFalse(ed25519.verify(bytes.fromhex(pub), b"\x73", bytes.fromhex(sig)))

    def test_wrong_key_fails(self):
        _s, _p, message, sig = RFC_VECTORS[1]
        other = bytes.fromhex(RFC_VECTORS[0][1])
        self.assertFalse(ed25519.verify(other, message, bytes.fromhex(sig)))


class RejectTest(unittest.TestCase):
    def setUp(self):
        _seed, pub, self.message, sig = RFC_VECTORS[1]
        self.pub = bytes.fromhex(pub)
        self.sig = bytes.fromhex(sig)

    def test_every_flipped_signature_byte_fails(self):
        for index in range(64):
            with self.subTest(byte=index):
                broken = bytearray(self.sig)
                broken[index] ^= 0x01
                self.assertFalse(ed25519.verify(self.pub, self.message, bytes(broken)))

    def test_malleated_s_plus_l_fails(self):
        s = int.from_bytes(self.sig[32:], "little")
        malleated = self.sig[:32] + (s + L).to_bytes(32, "little")
        self.assertTrue(ed25519.verify(self.pub, self.message, self.sig))
        self.assertFalse(ed25519.verify(self.pub, self.message, malleated))

    def test_s_equal_to_l_fails(self):
        self.assertFalse(ed25519.verify(self.pub, self.message, self.sig[:32] + L.to_bytes(32, "little")))

    def test_non_canonical_r_fails(self):
        s = self.sig[32:]
        # y = p + 1 reduces to y = 1 (the identity), but is not its canonical encoding.
        self.assertFalse(ed25519.verify(self.pub, self.message, (P + 1).to_bytes(32, "little") + s))
        # y = 1 with the sign bit set: x == 0 cannot carry a sign.
        negative_zero = (1 | (1 << 255)).to_bytes(32, "little")
        self.assertFalse(ed25519.verify(self.pub, self.message, negative_zero + s))

    def test_non_canonical_public_key_fails(self):
        for encoded in (
            (P + 1).to_bytes(32, "little"),
            (P + 3).to_bytes(32, "little"),
            (1 | (1 << 255)).to_bytes(32, "little"),
        ):
            with self.subTest(key=encoded.hex()[:8]):
                self.assertFalse(ed25519.verify(encoded, self.message, self.sig))

    def test_point_off_the_curve_fails(self):
        y = 2
        while ed25519._recover_x(y, 0) is not None:
            y += 1
        self.assertFalse(ed25519.verify(y.to_bytes(32, "little"), self.message, self.sig))
        self.assertFalse(ed25519.verify(self.pub, self.message, y.to_bytes(32, "little") + self.sig[32:]))

    def test_small_order_public_keys_fail(self):
        identity = (1).to_bytes(32, "little")
        order_two = (P - 1).to_bytes(32, "little")
        for key in (identity, order_two):
            with self.subTest(key=key.hex()[:8]):
                # A signature the all-zero scalar makes valid against a small-order key.
                self.assertFalse(ed25519.verify(key, self.message, identity + bytes(32)))
                self.assertFalse(ed25519.verify(key, self.message, self.sig))

    def test_lengths_and_types(self):
        self.assertFalse(ed25519.verify(self.pub[:31], self.message, self.sig))
        self.assertFalse(ed25519.verify(self.pub + b"\x00", self.message, self.sig))
        self.assertFalse(ed25519.verify(self.pub, self.message, self.sig[:63]))
        self.assertFalse(ed25519.verify(self.pub, self.message, self.sig + b"\x00"))
        self.assertFalse(ed25519.verify(self.pub.hex(), self.message, self.sig))
        self.assertFalse(ed25519.verify(self.pub, "text", self.sig))
        self.assertFalse(ed25519.verify(None, self.message, self.sig))


class SurfaceTest(unittest.TestCase):
    def test_module_exposes_verify_only(self):
        self.assertEqual(ed25519.__all__, ["verify"])
        public = [name for name in vars(ed25519) if not name.startswith("_")]
        self.assertFalse([name for name in public if "sign" in name.lower()])

    def test_licence_notice_is_kept(self):
        self.assertIn("Simplified BSD License", ed25519.__doc__)
        self.assertIn("IETF Trust", ed25519.__doc__)


if __name__ == "__main__":
    unittest.main()
