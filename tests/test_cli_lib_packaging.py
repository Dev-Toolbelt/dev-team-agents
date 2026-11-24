"""Every installer ships each scripts/lib file the CLI package reads beside itself.

The three installers (packaging/windows-cli/build.py, the Homebrew formula and
scripts/install-cli.sh) copy an explicit list of scripts/lib files next to the
``devteam`` package. A file the package reads but the list omits works from a
checkout and fails only in an installed CLI (``stack-signals.json`` did, as a
FileNotFoundError from ``devteam detect``). This test derives the list from the
code, so a new sibling read fails here instead.
"""

import importlib.util
import re
import unittest

from devteam_support import REPO_ROOT

LIB = REPO_ROOT / "scripts" / "lib"
SOURCES = sorted((LIB / "devteam").rglob("*.py")) + [LIB / "docs_root.py", LIB / "index_lint.py"]

#: The ways the package names a file beside itself in scripts/lib.
SIBLING_READS = (
    re.compile(r'Path\(__file__\)\.resolve\(\)\.parent\.parent / "([^"]+)"'),
    re.compile(r'\bLIB_DIR / "([^"]+)"'),
    re.compile(r'_load_json\("([^"]+)"'),
    re.compile(r'os\.path\.join\(_LIB, "([^"]+)"\)'),
)


def _sibling_reads():
    names = set()
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        for pattern in SIBLING_READS:
            names.update(pattern.findall(text))
    return names


def _windows_list():
    spec = importlib.util.spec_from_file_location(
        "windows_cli_build_for_lib_test", str(REPO_ROOT / "packaging" / "windows-cli" / "build.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.CLI_LIB_FILES)


def _homebrew_list():
    formula = (REPO_ROOT / "packaging" / "homebrew" / "devteam.rb").read_text(encoding="utf-8")
    return set(re.findall(r'\(libexec/"scripts/lib"\)\.install "scripts/lib/([^"]+)"', formula))


def _install_cli_list():
    script = (REPO_ROOT / "scripts" / "install-cli.sh").read_text(encoding="utf-8")
    names = set(re.findall(r'"\$source/scripts/lib/([^"/$]+\.[a-z]+)"', script))
    for loop in re.findall(r"for name in ([^;\n]+); do\n\s+cp \"\$source/scripts/lib/\$name\"", script):
        names.update(loop.split())
    return names


class CliLibPackagingTest(unittest.TestCase):
    def test_the_scan_finds_the_known_sibling_reads(self):
        # Guards against a pattern drift that would make every assertion below vacuous.
        reads = _sibling_reads()
        for name in ("auth-config.json", "doc-layouts.json", "stack-signals.json", "commands.json"):
            self.assertIn(name, reads)

    def test_every_sibling_read_exists_in_the_checkout(self):
        for name in sorted(_sibling_reads()):
            self.assertTrue((LIB / name).is_file(), name)

    def test_every_installer_ships_every_sibling_read(self):
        reads = _sibling_reads()
        for installer, shipped in (
            ("packaging/windows-cli/build.py", _windows_list()),
            ("packaging/homebrew/devteam.rb", _homebrew_list()),
            ("scripts/install-cli.sh", _install_cli_list()),
        ):
            with self.subTest(installer=installer):
                self.assertEqual(sorted(reads - shipped), [], "add these to " + installer)

    def test_the_three_installers_ship_the_same_list(self):
        self.assertEqual(sorted(_windows_list()), sorted(_homebrew_list()))
        self.assertEqual(sorted(_windows_list()), sorted(_install_cli_list()))


if __name__ == "__main__":
    unittest.main()
