#!/usr/bin/env python3
"""Build the Windows CLI installers (ADR-0028): devteam-setup-<version>-<arch>.exe.

    python3 packaging/windows-cli/build.py [--arch x64|arm64|all] [--version X.Y.Z]
                                          [--out DIR] [--makensis PATH]

Runs on macOS, Linux or Windows — anywhere `git` and `makensis` exist. Python, not bash,
so extraction and hashing do not depend on which `unzip`/`shasum` a host ships.

The framework comes from `git archive HEAD`, so a build is the committed tree and never
the working copy. Every download is pinned in pins.json and refused on a digest mismatch;
downloads are cached in packaging/windows-cli/.cache/ (gitignored).
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = HERE / ".cache"
ARCHES = ("x64", "arm64")

sys.path.insert(0, str(REPO / "scripts" / "lib"))
from devteam.versions import CORE_TREES, OPTIONAL_TREES, version_from_tree  # noqa: E402

#: Root files `store install` copies beside the trees (versions.install_from_tree).
PAYLOAD_FILES = ("CHANGELOG.md", "CLAUDE.md")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, digest):
    """The bytes at `url`, from the cache when present; refused unless they hash to `digest`."""
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / url.rsplit("/", 1)[-1]
    if cached.is_file() and sha256(cached.read_bytes()) == digest:
        return cached.read_bytes()
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    actual = sha256(data)
    if actual != digest:
        raise SystemExit("build: {} hashes to {}, pins.json says {}".format(url, actual, digest))
    cached.write_bytes(data)
    return data


def committed_tree(destination):
    """`git archive HEAD`, extracted: the committed tree, without untracked or ignored files."""
    archive = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        links = [member.name for member in tar.getmembers() if member.issym() or member.islnk()]
        if links:
            # copytree would follow them and ship whatever they point at on the build host.
            raise SystemExit("build: the committed tree holds links, refusing: {}".format(", ".join(links)))
        if hasattr(tarfile, "data_filter"):
            tar.extractall(str(destination), filter="data")
        else:
            tar.extractall(str(destination))


def stage(arch, tree, pins, root):
    """Lay out exactly what the installer copies: python\\ cli\\ launcher\\ payload\\ postinstall.py."""
    root.mkdir(parents=True)

    python_pin = pins["python"][arch]
    with zipfile.ZipFile(io.BytesIO(fetch(python_pin["url"], python_pin["sha256"]))) as embedded:
        embedded.extractall(str(root / "python"))

    launcher_pin = pins["launcher"]
    with zipfile.ZipFile(io.BytesIO(fetch(launcher_pin["wheel_url"], launcher_pin["wheel_sha256"]))) as wheel:
        stub = wheel.read(launcher_pin[arch]["member"])
    if sha256(stub) != launcher_pin[arch]["sha256"]:
        raise SystemExit("build: {} in the distlib wheel does not match pins.json".format(launcher_pin[arch]["member"]))
    (root / "launcher").mkdir()
    (root / "launcher" / "launcher.exe").write_bytes(stub)

    # The CLI exactly as the Homebrew formula installs it: the entry script, and the
    # `devteam` package beside it under scripts/lib.
    cli = root / "cli" / "scripts"
    (cli / "cli").mkdir(parents=True)
    shutil.copy2(str(tree / "scripts" / "cli" / "devteam"), str(cli / "cli" / "devteam"))
    shutil.copytree(
        str(tree / "scripts" / "lib" / "devteam"),
        str(cli / "lib" / "devteam"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    payload = root / "payload"
    payload.mkdir()
    for name in CORE_TREES + OPTIONAL_TREES:
        if (tree / name).is_dir():
            shutil.copytree(
                str(tree / name),
                str(payload / name),
                symlinks=False,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    for name in PAYLOAD_FILES:
        if (tree / name).is_file():
            shutil.copy2(str(tree / name), str(payload / name))

    shutil.copy2(str(HERE / "postinstall.py"), str(root / "postinstall.py"))


def find_makensis(explicit):
    if explicit:
        return explicit
    found = shutil.which("makensis")
    if found:
        return found
    # NSIS's own installer (and Chocolatey's package) put it here and add nothing to PATH.
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base and Path(base, "NSIS", "makensis.exe").is_file():
            return str(Path(base, "NSIS", "makensis.exe"))
    # electron-builder downloads NSIS for the app's own installer; reuse it rather than
    # asking a maintainer who already builds the app to install a second copy.
    cache = Path.home() / "Library" / "Caches" / "electron-builder"
    name = {"darwin": "mac/makensis", "linux": "linux/makensis"}.get(sys.platform, "Bin/makensis.exe")
    for candidate in sorted(cache.glob("nsis-*/nsis-*/" + name), reverse=True):
        return str(candidate)
    raise SystemExit("build: no makensis found — install NSIS, or pass --makensis")


def build(arch, version, tree, pins, out, makensis, work):
    staged = work / arch
    stage(arch, tree, pins, staged)
    installer = out / "devteam-setup-{}-{}.exe".format(version, arch)
    command = [
        makensis,
        "-V2",
        "-DVERSION=" + version,
        "-DARCH=" + arch,
        "-DSTAGE=" + str(staged),
        "-DOUTFILE=" + str(installer),
        str(HERE / "devteam-cli.nsi"),
    ]
    # makensis's mac/linux build reads its stubs and plugins from NSISDIR.
    env = dict(os.environ)
    if not sys.platform.startswith("win") and "NSISDIR" not in env:
        env["NSISDIR"] = str(Path(makensis).resolve().parent.parent)
    subprocess.run(command, check=True, env=env)
    return installer


def main(argv=None):
    parser = argparse.ArgumentParser(prog="build.py", description=__doc__.splitlines()[0])
    parser.add_argument("--arch", choices=ARCHES + ("all",), default="all")
    parser.add_argument("--version", help="X.Y.Z (default: newest entry in CHANGELOG.md)")
    parser.add_argument("--out", default=str(HERE / "dist"))
    parser.add_argument("--makensis", help="path to makensis (default: PATH, then electron-builder's cache)")
    args = parser.parse_args(argv)

    pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
    makensis = find_makensis(args.makensis)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    arches = ARCHES if args.arch == "all" else (args.arch,)

    with tempfile.TemporaryDirectory(prefix="devteam-win-") as scratch:
        work = Path(scratch)
        tree = work / "tree"
        committed_tree(tree)
        version = args.version or version_from_tree(tree)
        if not version:
            raise SystemExit("build: no version in CHANGELOG.md — pass --version")
        installers = [build(arch, version, tree, pins, out, makensis, work) for arch in arches]

    sums = "".join("{}  {}\n".format(sha256(path.read_bytes()), path.name) for path in installers)
    (out / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    for path in installers:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
