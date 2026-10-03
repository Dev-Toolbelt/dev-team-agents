"""The service-role secret scanner finds what it must (ADR-0029 SR-36).

The positive cases are built at runtime, so no credential-shaped string is committed and the
scanner, run over this repository, stays clean.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("secret_scan", ROOT / ".github" / "scripts" / "ci" / "secret_scan.py")
scan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scan)


def _segment(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def jwt(role):
    return ".".join(
        (_segment({"alg": "HS256", "typ": "JWT"}), _segment({"iss": "supabase", "role": role}), "s" * 43)
    )


class SecretScanTest(unittest.TestCase):
    def test_a_service_role_jwt_is_found(self):
        self.assertEqual(scan.scan_text("key = '{}'\n".format(jwt("service_role"))), [(1, "service_role JWT")])

    def test_an_anon_jwt_is_not_a_finding(self):
        self.assertEqual(scan.scan_text("anon = '{}'".format(jwt("anon"))), [])

    def test_a_new_style_secret_key_is_found(self):
        key = "sb_" + "secret_" + "A1b2C3d4E5f6G7h8I9j0"
        self.assertEqual(scan.scan_text("x\nSUPABASE_KEY={}\n".format(key)), [(2, "sb_secret_ key")])

    def test_a_tree_with_a_seeded_key_fails_and_names_only_the_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "leak.env").write_text("SERVICE={}\n".format(jwt("service_role")))
            findings = scan.scan_tree(tmp)
        self.assertEqual(findings, ["leak.env:1: service_role JWT"])

    def test_in_a_git_tree_ignored_files_are_skipped_and_untracked_ones_scanned(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            (Path(tmp) / ".gitignore").write_text("ignored/\n")
            (Path(tmp) / "ignored").mkdir()
            (Path(tmp) / "ignored" / "docker.env").write_text("K={}\n".format(jwt("service_role")))
            (Path(tmp) / "new.env").write_text("K={}\n".format(jwt("service_role")))
            findings = scan.scan_tree(os.path.realpath(tmp))
        self.assertEqual(findings, ["new.env:1: service_role JWT"])

    def test_this_repository_is_clean(self):
        self.assertEqual(scan.scan_tree(str(ROOT)), [])


if __name__ == "__main__":
    unittest.main()
