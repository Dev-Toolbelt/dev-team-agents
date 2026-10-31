"""`devteam tools` provisions the pinned helper tools (ADR-0060).

Nothing here touches the network: `_download` is replaced by a fake that serves archives
built in memory, and `shutil.which` is blinded so the developer's own tools on PATH do not
turn every case into "already present".
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import unittest
import zipfile
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase  # sys.path bootstrap

from devteam import tools

PLATFORM_KEYS = {"darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64", "windows-arm64", "windows-x64"}


def _tar(name, payload):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def _zip(name, payload):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(name, payload)
    return buf.getvalue()


def _binary_tool(name, data, fmt, sha=None, **extra):
    tool = {
        "name": name, "binary": name, "version": "1.0.0", "purpose": "test tool", "kind": "binary",
        "assets": {"linux-x64": {"url": "https://example.test/" + name, "format": fmt,
                                 "sha256": sha or hashlib.sha256(data).hexdigest()}},
    }
    tool.update(extra)
    return tool


class ToolsInstallTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        os.environ.pop(tools.SKIP_ENV, None)
        self.served = {}
        self.downloads = []
        patches = [
            mock.patch.object(tools, "_download", side_effect=self._serve),
            mock.patch.object(tools.shutil, "which", return_value=None),
            mock.patch.object(tools, "host_platform", return_value="linux-x64"),
            mock.patch.object(tools, "host_os", return_value="linux"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.bin = tools.bin_dir()

    def _serve(self, url):
        self.downloads.append(url)
        if url not in self.served:
            raise OSError("offline")
        return self.served[url]

    def _pins(self, *pins):
        patcher = mock.patch.object(tools, "load_pins", return_value=list(pins))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _offer(self, tool, data):
        self.served[tool["assets"]["linux-x64"]["url"]] = data
        return tool

    def test_each_archive_format_installs_the_named_executable(self):
        rg = self._offer(_binary_tool("rg", _tar("ripgrep-1.0/rg", b"rg-bin"), "tar.gz"), _tar("ripgrep-1.0/rg", b"rg-bin"))
        fd = self._offer(_binary_tool("fd", _zip("fd-1.0/fd", b"fd-bin"), "zip"), _zip("fd-1.0/fd", b"fd-bin"))
        jq = self._offer(_binary_tool("jq", b"jq-bin", "raw"), b"jq-bin")
        self._pins(rg, fd, jq)
        payload = tools.install()
        self.assertEqual([e["status"] for e in payload["tools"]], ["installed"] * 3)
        for name, body in (("rg", b"rg-bin"), ("fd", b"fd-bin"), ("jq", b"jq-bin")):
            self.assertEqual((self.bin / name).read_bytes(), body)
            if os.name == "posix":
                self.assertTrue(os.access(str(self.bin / name), os.X_OK))

    def test_a_digest_mismatch_installs_nothing(self):
        data = _tar("gitleaks", b"tampered")
        tool = self._offer(_binary_tool("gitleaks", data, "tar.gz", sha="0" * 64), data)
        self._pins(tool)
        entry = tools.install()["tools"][0]
        self.assertEqual(entry["status"], "failed")
        self.assertIn("sha256 mismatch", entry["reason"])
        self.assertFalse((self.bin / "gitleaks").exists())

    def test_an_archive_path_cannot_write_outside_the_bin_directory(self):
        data = _tar("../../escape/rg", b"rg-bin")
        tool = self._offer(_binary_tool("rg", data, "tar.gz"), data)
        self._pins(tool)
        self.assertEqual(tools.install()["tools"][0]["status"], "installed")
        self.assertEqual((self.bin / "rg").read_bytes(), b"rg-bin")
        self.assertFalse((self.tmp / "escape").exists())

    def test_a_present_tool_is_never_downloaded(self):
        data = b"jq-bin"
        tool = self._offer(_binary_tool("jq", data, "raw"), data)
        self._pins(tool)
        with mock.patch.object(tools.shutil, "which", return_value="/usr/bin/jq"):
            entry = tools.install()["tools"][0]
        self.assertEqual((entry["status"], entry["path"]), ("present", "/usr/bin/jq"))
        self.assertEqual(self.downloads, [])

    def test_one_failure_does_not_stop_the_others(self):
        broken = _binary_tool("rg", b"x", "raw")  # nothing served: the fake raises
        data = b"jq-bin"
        good = self._offer(_binary_tool("jq", data, "raw"), data)
        self._pins(broken, good)
        statuses = [e["status"] for e in tools.install()["tools"]]
        self.assertEqual(statuses, ["failed", "installed"])

    def test_the_opt_out_installs_nothing(self):
        data = b"jq-bin"
        self._pins(self._offer(_binary_tool("jq", data, "raw"), data))
        os.environ[tools.SKIP_ENV] = "1"
        payload = tools.install()
        self.assertEqual(payload["skipped_all"], "DEVTEAM_SKIP_TOOLS=1")
        self.assertEqual([e["status"] for e in payload["tools"]], ["skipped"])
        self.assertEqual(self.downloads, [])

    def test_an_unmet_requirement_and_an_unsupported_platform_are_skipped(self):
        needs = {"name": "graphify", "binary": "graphify", "version": "1", "purpose": "p", "kind": "python",
                 "package": "graphifyy", "python_min": [3, 10], "requires": ["jq"]}
        nowin = {"name": "semgrep", "binary": "semgrep", "version": "1", "purpose": "p", "kind": "python",
                 "package": "semgrep", "python_min": [3, 10], "platforms": ["darwin"]}
        self._pins(_binary_tool("jq", b"", "raw"), needs, nowin)
        entries = {e["name"]: e for e in tools.install()["tools"]}
        self.assertEqual(entries["jq"]["status"], "failed")
        self.assertEqual((entries["graphify"]["status"], entries["graphify"]["reason"]), ("skipped", "needs jq"))
        self.assertEqual(entries["semgrep"]["status"], "skipped")
        self.assertIn("WSL or Docker", entries["semgrep"]["reason"])

    def test_a_requirement_already_on_the_machine_counts_when_not_selected(self):
        jq = _binary_tool("jq", b"", "raw")
        graphify = {"name": "graphify", "binary": "graphify", "version": "1", "purpose": "p", "kind": "python",
                    "package": "graphifyy", "python_min": [3, 99], "requires": ["jq"]}
        self._pins(jq, graphify)
        with mock.patch.object(tools.shutil, "which", side_effect=lambda name: "/usr/bin/jq" if name == "jq" else None):
            entry = tools.install(["graphify"])["tools"][0]
        # Past the requirement, it stops at the interpreter floor instead.
        self.assertEqual(entry["reason"], "needs Python 3.99+")

    def test_no_build_and_no_homebrew_is_a_skip(self):
        tool = _binary_tool("tokei", b"", "raw")
        tool["assets"] = {}
        tool["brew"] = "tokei"
        self._pins(tool)
        entry = tools.install()["tools"][0]
        self.assertEqual((entry["status"], entry["reason"]), ("skipped", "no pinned build for linux-x64"))

    def test_python_tool_without_a_new_enough_interpreter_is_a_skip(self):
        tool = {"name": "semgrep", "binary": "semgrep", "version": "1", "purpose": "p", "kind": "python",
                "package": "semgrep", "python_min": [3, 99]}
        self._pins(tool)
        entry = tools.install()["tools"][0]
        self.assertEqual((entry["status"], entry["reason"]), ("skipped", "needs Python 3.99+"))

    def test_an_unknown_name_is_a_usage_error(self):
        code, out, _ = self.run_cli("tools", "install", "nope", "--json")
        self.assertEqual(code, 2)
        self.assertIn("unknown tool", json.loads(out)["error"])


class ToolsCliTest(StoreTestCase):
    def test_install_json_is_one_document_and_progress_stays_off_stdout(self):
        # The fixture keeps the opt-out on, so this never downloads.
        code, out, err = self.run_cli("tools", "install", "--json")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["skipped_all"], "DEVTEAM_SKIP_TOOLS=1")
        self.assertEqual({e["name"] for e in payload["tools"]}, {t["name"] for t in tools.load_pins()})

    def test_list_reports_every_pinned_tool(self):
        payload = json.loads(self.run_cli("tools", "list", "--json")[1])
        self.assertEqual(len(payload["tools"]), len(tools.load_pins()))
        self.assertTrue(all(e["status"] in ("present", "missing") for e in payload["tools"]))


class PinsFileTest(StoreTestCase):
    def test_every_asset_is_https_digest_pinned_and_on_a_known_platform(self):
        for tool in tools.load_pins():
            with self.subTest(tool=tool["name"]):
                self.assertIn(tool["kind"], ("binary", "python"))
                if tool["kind"] == "python":
                    self.assertTrue(tool["package"] and tool["python_min"])
                    continue
                self.assertTrue(tool["assets"])
                self.assertLessEqual(set(tool["assets"]), PLATFORM_KEYS)
                for asset in tool["assets"].values():
                    self.assertTrue(asset["url"].startswith("https://"))
                    self.assertRegex(asset["sha256"], r"^[0-9a-f]{64}$")
                    self.assertIn(asset["format"], ("raw", "tar.gz", "zip"))

    def test_every_binary_tool_reaches_linux_and_windows_x64(self):
        # The two platforms with no Homebrew fallback in practice: a gap there is a silent skip.
        for tool in tools.load_pins():
            if tool["kind"] == "binary":
                with self.subTest(tool=tool["name"]):
                    self.assertIn("linux-x64", tool["assets"])
                    self.assertIn("windows-x64", tool["assets"])

    def test_the_graphify_package_is_the_double_y_distribution(self):
        graphify = next(t for t in tools.load_pins() if t["name"] == "graphify")
        self.assertEqual(graphify["package"], "graphifyy")
        self.assertIsNotNone(re.match(r"^\d+\.\d+\.\d+$", graphify["version"]))


class BindProvisionsToolsTest(StoreTestCase):
    """Provider parity: every provider's bind runs `tools.install` (ADR-0060)."""

    #: One case per provider; a provider added to ALL_PROVIDERS without one fails below.
    BIND_CASES = {"claude": "auto", "opencode": "auto", "codex": "auto"}

    def setUp(self):
        super().setUp()
        from devteam import versions

        versions.install_from_tree(REPO_ROOT, version="9.9.9", force=True, make_current=True)
        # The Codex installer looks at ~/.codex/prompts; keep it off the real home.
        (self.tmp / "fake-home").mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.tmp / "fake-home")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_provider_has_a_case(self):
        from devteam import providers

        self.assertEqual(set(self.BIND_CASES), set(providers.ALL_PROVIDERS))

    def test_bind_reports_the_tools_install_for_every_provider(self):
        for provider, mode in self.BIND_CASES.items():
            with self.subTest(provider=provider):
                root = self.new_project("tools-" + provider)
                code, out, err = self.run_cli("--json", "bind", str(root), "--provider", provider, "--mode", mode)
                self.assertEqual(code, 0, err)
                report = json.loads(out)["tools"]
                # The fixture's opt-out is what proves the call happened without a download.
                self.assertEqual(report["skipped_all"], "DEVTEAM_SKIP_TOOLS=1")
                self.assertEqual(len(report["tools"]), len(tools.load_pins()))

    def test_no_tools_skips_the_install_and_keeps_the_key(self):
        os.environ.pop(tools.SKIP_ENV, None)  # proves the flag alone stops it, with nothing to download
        root = self.new_project("tools-flag")
        with mock.patch.dict(os.environ, {"PATH": ""}):
            code, out, err = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--no-tools")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["tools"]["skipped_all"], "--no-tools")

    def test_sync_never_provisions_tools(self):
        root = self.new_project("tools-sync")
        self.assertEqual(self.run_cli("bind", str(root), "--provider", "claude")[0], 0)
        code, out, err = self.run_cli("--json", "sync", str(root))
        self.assertEqual(code, 0, err)
        self.assertNotIn("tools", json.loads(out))


class PinsAgreeWithCiTest(StoreTestCase):
    def test_ci_scanners_use_the_versions_the_local_tools_install(self):
        # The commit guard and CI must agree on what counts as a secret (ADR-0059).
        pin = (REPO_ROOT / ".github" / "security-tools.pin").read_text(encoding="utf-8")
        ci = dict(line.split("=", 1) for line in pin.splitlines() if "=" in line and not line.startswith("#"))
        local = {t["name"]: t["version"] for t in tools.load_pins()}
        self.assertEqual(ci["gitleaks_version"], local["gitleaks"])
        self.assertEqual(ci["semgrep_version"], local["semgrep"])


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "drives a bash library")
class ProvisionToolsShellTest(StoreTestCase):
    """`provision-tools.sh`, which the standalone installers of every provider source (ADR-0060)."""

    #: The installer each provider's standalone path ends in; a provider added without one fails.
    INSTALLERS = {"claude": "install.sh", "opencode": "install-opencode.sh", "codex": "install-codex.sh"}

    def _provision(self, path_dirs, scripts_dir):
        lib = REPO_ROOT / "scripts" / "lib" / "provision-tools.sh"
        return subprocess.run(
            ["bash", "-c", '. "$1" && pt_provision demo "$2"', "_", str(lib), str(scripts_dir)],
            env=dict(os.environ, PATH=os.pathsep.join(path_dirs)), capture_output=True, text=True, timeout=60,
        )

    def test_every_provider_installer_calls_it_outside_bind(self):
        from devteam import providers

        self.assertEqual(set(self.INSTALLERS), set(providers.ALL_PROVIDERS))
        for provider, script in self.INSTALLERS.items():
            with self.subTest(provider=provider):
                text = (REPO_ROOT / "scripts" / script).read_text(encoding="utf-8")
                self.assertIn("provision-tools.sh", text)
                self.assertIn("pt_provision", text)

    def test_it_runs_tools_install_through_the_cli_on_path(self):
        stub_dir = self.tmp / "stub"
        stub_dir.mkdir()
        log = self.tmp / "calls"
        stub = stub_dir / "devteam"
        stub.write_text('#!/bin/sh\necho "$*" >> "{}"\n'.format(log))
        stub.chmod(0o755)
        result = self._provision([str(stub_dir), "/usr/bin", "/bin"], self.tmp / "no-scripts")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log.read_text().split(), ["tools", "install"])

    def test_no_cli_is_a_note_not_a_failure(self):
        result = self._provision(["/usr/bin", "/bin"], self.tmp / "no-scripts")
        self.assertEqual(result.returncode, 0)
        self.assertIn("devteam tools install", result.stdout)
