import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from devteam import doctor, permissions  # noqa: E402


def _home_with(tmp, text):
    home = Path(tmp) / "home"
    (home / ".codex").mkdir(parents=True)
    if text is not None:
        (home / ".codex" / "config.toml").write_text(text, encoding="utf-8")
    return home


class CodexQuestionFlagTest(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            return permissions.codex_default_mode_questions_enabled(home=_home_with(tmp, text))

    def test_enabled_in_features_table(self):
        self.assertTrue(self.check('model = "x"\n[features]\ndefault_mode_request_user_input = true\n[other]\n'))

    def test_false_value(self):
        self.assertFalse(self.check("[features]\ndefault_mode_request_user_input = false\n"))

    def test_absent_key(self):
        self.assertFalse(self.check("[features]\nother = true\n"))
        self.assertFalse(self.check('model = "x"\n'))

    def test_key_in_another_table_does_not_count(self):
        self.assertFalse(self.check("[features]\nx = 1\n[other]\ndefault_mode_request_user_input = true\n"))

    def test_dotted_form(self):
        self.assertTrue(self.check("features.default_mode_request_user_input = true\n"))

    def test_unreadable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(permissions.codex_default_mode_questions_enabled(home=Path(tmp) / "none"))
            home = _home_with(tmp, None)
            self.assertIsNone(permissions.codex_default_mode_questions_enabled(home=home))

    def test_helper_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _home_with(tmp, "[features]\n")
            before = (home / ".codex" / "config.toml").read_text()
            permissions.codex_default_mode_questions_enabled(home=home)
            self.assertEqual((home / ".codex" / "config.toml").read_text(), before)


class DoctorCodexFlagTest(unittest.TestCase):
    def findings(self, bound, config_text):
        old = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp:
            home = _home_with(tmp, config_text)
            os.environ["HOME"] = str(home)
            try:
                root = Path(tmp) / "proj"
                root.mkdir()
                return doctor._ask_rule_findings(root, bound, {})
            finally:
                if old is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old

    def flagged(self, findings):
        return [f for f in findings if "default_mode_request_user_input" in f.get("hint", "")]

    def test_warns_for_codex_without_flag(self):
        found = self.flagged(self.findings(["codex"], "[features]\n"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["level"], "warn")

    def test_silent_when_enabled(self):
        self.assertFalse(self.flagged(self.findings(["codex"], "[features]\ndefault_mode_request_user_input = true\n")))

    def test_silent_for_non_codex_project(self):
        self.assertFalse(self.flagged(self.findings(["claude"], "[features]\n")))


if __name__ == "__main__":
    unittest.main()
