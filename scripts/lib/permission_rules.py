#!/usr/bin/env python3
"""Write the provider-native "ask" rules for `integration call` writes (ADR-0032).

Run by the installers that cannot import the CLI package directly:

    permission_rules.py claude   <settings.json> [--check]   # install.sh (v2 Claude layout)
    permission_rules.py opencode <opencode.json> [--check]   # install-opencode.sh
    permission_rules.py codex    <devteam.rules>             # install-codex.sh

The rule text and the merge logic live in ``devteam.permissions``; this is only the entry
point. ``--check`` validates without writing. Exit codes: 0 ok, 4 the file is not a shape
this script can merge into (it is left untouched and named on stderr — the code the
ownership guard uses for a conflict), 1 anything else.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devteam import permissions  # noqa: E402
from devteam.errors import EnvError  # noqa: E402

CONFLICT_EXIT = 4


def _callable_names():
    from devteam import integrations

    return integrations.callable_names()


def _load(path):
    """The parsed object, ``{}`` for a missing file; ``EnvError`` for anything unmergeable."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        raise EnvError("{} is not strict JSON (comments or trailing commas?)".format(path)) from None
    if not isinstance(data, dict):
        raise EnvError("{} is not a JSON object".format(path))
    return data


def _write_atomic(path, text):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".devteam-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if os.path.exists(path):
            os.chmod(tmp, os.stat(path).st_mode & 0o777)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _merge_json(path, merge, check):
    data = _load(path)
    changed = merge(data)
    if check or not changed:
        return
    _write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("claude", "opencode", "codex"):
        print(__doc__.strip(), file=sys.stderr)
        return 1
    provider, path = argv[0], argv[1]
    check = "--check" in argv[2:]
    try:
        if provider == "claude":
            _merge_json(path, permissions.merge_claude, check)
        elif provider == "opencode":
            _merge_json(path, permissions.merge_opencode, check)
        elif not check:
            _write_atomic(path, permissions.codex_rules(_callable_names()))
    except EnvError as exc:
        print("permission_rules: {}: {}; it was left untouched.".format(path, exc.message), file=sys.stderr)
        return CONFLICT_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
