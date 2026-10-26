import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from devteam import doctor, permissions  # noqa: E402

ON = "[tools.update_plan]\nenabled = true\n"


def _home_with(tmp, text):
    home = Path(tmp) / "home"
    (home / ".codex").mkdir(parents=True)
    if text is not None:
        (home / ".codex" / "config.toml").write_text(text, encoding="utf-8")
    return home


def _project_with(tmp, text):
    root = Path(tmp) / "proj"
    (root / ".codex").mkdir(parents=True)
    (root / ".codex" / "config.toml").write_text(text, encoding="utf-8")
    return root


class CodexUpdatePlanFlagTest(unittest.TestCase):
    def user(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            return permissions.codex_update_plan_enabled(home=_home_with(tmp, text))

    def test_enabled_in_tools_table(self):
        self.assertTrue(self.user('model = "x"\n' + ON + "[other]\n"))

    def test_dotted_form(self):
        self.assertTrue(self.user("tools.update_plan.enabled = true\n"))

    def test_false_value(self):
        self.assertFalse(self.user("[tools.update_plan]\nenabled = false\n"))

    def test_absent(self):
        self.assertFalse(self.user('model = "x"\n'))

    def test_key_in_another_table_does_not_count(self):
        self.assertFalse(self.user("[tools.update_plan]\nx = 1\n[other]\nenabled = true\n"))

    def test_project_config_enables_in_a_trusted_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project_with(tmp, ON)
            home = _home_with(tmp, '[projects."{}"]\ntrust_level = "trusted"\n'.format(root.resolve()))
            self.assertTrue(permissions.codex_update_plan_enabled(root, home=home))

    def test_project_config_ignored_in_an_untrusted_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _home_with(tmp, "[features]\n")
            root = _project_with(tmp, ON)
            self.assertFalse(permissions.codex_update_plan_enabled(root, home=home))

    def test_dotted_under_tools_table(self):
        self.assertTrue(self.user("[tools]\nupdate_plan.enabled = true\n"))

    def test_inline_table(self):
        self.assertTrue(self.user("[tools]\nupdate_plan = { enabled = true }\n"))

    def test_spaced_header(self):
        self.assertTrue(self.user("[ tools.update_plan ]\nenabled = true\n"))

    def test_dotted_key_inside_another_table_does_not_count(self):
        self.assertFalse(self.user("[profiles.x]\ntools.update_plan.enabled = true\n"))

    def test_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(permissions.codex_update_plan_enabled(home=Path(tmp) / "none"))
            self.assertIsNone(permissions.codex_update_plan_enabled(Path(tmp) / "p", home=_home_with(tmp, None)))

    def test_codex_home_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config.toml").write_text(ON, encoding="utf-8")
            old = os.environ.get("CODEX_HOME")
            os.environ["CODEX_HOME"] = tmp
            try:
                self.assertTrue(permissions.codex_update_plan_enabled())
            finally:
                if old is None:
                    os.environ.pop("CODEX_HOME", None)
                else:
                    os.environ["CODEX_HOME"] = old

    def test_a_project_off_overrides_a_user_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project_with(tmp, "[tools.update_plan]\nenabled = false\n")
            home = _home_with(tmp, ON + '[projects."{}"]\ntrust_level = "trusted"\n'.format(root.resolve()))
            self.assertFalse(permissions.codex_update_plan_enabled(root, home=home))

    def test_a_project_that_sets_nothing_defers_to_the_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project_with(tmp, 'model = "x"\n')
            home = _home_with(tmp, ON + '[projects."{}"]\ntrust_level = "trusted"\n'.format(root.resolve()))
            self.assertTrue(permissions.codex_update_plan_enabled(root, home=home))

    def test_a_bracketed_line_inside_a_multi_line_array_hides_no_later_key(self):
        self.assertTrue(self.user('matrix = [\n  [1, 2],\n  [3, 4]\n]\n[tools.update_plan]\nenabled = true\n'))
        self.assertTrue(self.user('[tools.update_plan]\nlist = [\n  [1, 2],\n]\nenabled = true\n'))
        self.assertTrue(self.user('matrix = [\n  ["a", "b"], # [x]\n  [3]\n]\ntools.update_plan.enabled = true\n'))

    def test_a_bracket_inside_a_multi_line_string_hides_no_later_header(self):
        self.assertFalse(self.user("[tools.update_plan]\nnote='''\nsee [docs\n'''\n[tools.other]\nenabled = true\n"))
        self.assertTrue(self.user('[tools.update_plan]\nnote = """\n[not a header\n"""\nenabled = true\n'))
        self.assertTrue(self.user('[tools.update_plan]\nnote = """one line"""\nenabled = true\n'))

    def test_every_config_read_honors_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            text = '[features]\ndefault_mode_request_user_input = true\n[projects."{}"]\ntrust_level = "trusted"\n'.format(root.resolve())
            (Path(tmp) / "config.toml").write_text(text, encoding="utf-8")
            old = os.environ.get("CODEX_HOME")
            os.environ["CODEX_HOME"] = tmp
            try:
                self.assertTrue(permissions.codex_default_mode_questions_enabled())
                self.assertTrue(permissions.codex_project_trusted(root))
            finally:
                if old is None:
                    os.environ.pop("CODEX_HOME", None)
                else:
                    os.environ["CODEX_HOME"] = old

    def test_helper_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = _home_with(tmp, "[features]\n")
            before = (home / ".codex" / "config.toml").read_text()
            permissions.codex_update_plan_enabled(home=home)
            self.assertEqual((home / ".codex" / "config.toml").read_text(), before)


class DoctorUpdatePlanTest(unittest.TestCase):
    def run_doctor(self, bound, user_text, project_text=None):
        old = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "CODEX_HOME")}
        with tempfile.TemporaryDirectory() as tmp:
            root = _project_with(tmp, project_text) if project_text else Path(tmp) / "proj"
            if user_text is not None and "{}" in user_text:
                user_text = user_text.format(root.resolve())
            home = _home_with(tmp, user_text)
            # Path.home() reads USERPROFILE on Windows, HOME elsewhere.
            os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
            os.environ.pop("CODEX_HOME", None)
            root.mkdir(exist_ok=True)
            snapshot = sorted(p.name for p in (home / ".codex").iterdir())
            try:
                found = doctor._task_board_findings(root, bound)
                self.assertEqual(sorted(p.name for p in (home / ".codex").iterdir()), snapshot)
                if user_text is not None:
                    self.assertEqual((home / ".codex" / "config.toml").read_text(), user_text)
                return [f for f in found if f["category"] == "task-board"]
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def test_warns_when_off(self):
        found = self.run_doctor(["codex"], "[features]\n")
        self.assertEqual([f["level"] for f in found], ["warn"])
        self.assertIn("update_plan", found[0]["hint"])

    def test_ok_when_user_config_on(self):
        self.assertEqual([f["level"] for f in self.run_doctor(["codex"], ON)], ["ok"])

    def test_ok_when_trusted_project_config_on(self):
        trusted = '[projects."{}"]\ntrust_level = "trusted"\n'
        self.assertEqual([f["level"] for f in self.run_doctor(["codex"], trusted, ON)], ["ok"])

    def test_warns_when_untrusted_project_config_on(self):
        self.assertEqual([f["level"] for f in self.run_doctor(["codex"], "[features]\n", ON)], ["warn"])

    def test_an_unreadable_config_is_not_reported_as_off(self):
        found = self.run_doctor(["codex"], None)
        self.assertEqual([f["level"] for f in found], ["warn"])
        self.assertIn("could not be read", found[0]["message"])
        self.assertNotIn("is off", found[0]["message"])

    def test_silent_for_non_codex(self):
        self.assertEqual(self.run_doctor(["claude"], "[features]\n"), [])


if __name__ == "__main__":
    unittest.main()
