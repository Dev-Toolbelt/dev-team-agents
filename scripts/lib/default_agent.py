#!/usr/bin/env python3
"""Apply ``orchestrator_default`` (ADR-0062) from the installers that cannot import the CLI.

    default_agent.py claude <project-root>     # install.sh (v2 Claude layout)

Writes ``.claude/settings.local.json`` only; opencode and Codex have no such key.

The preference is read from the project's resolved preferences, else the v2 file; absent
means off. The rule lives in ``devteam.default_agent``. Exit codes: 0 ok, 4 the config is
not a shape this script can merge into or resolves outside the project (left untouched, named on
stderr), 1 usage.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devteam import default_agent  # noqa: E402
from devteam.errors import ConflictError, EnvError  # noqa: E402

CONFLICT_EXIT = 4


def main(argv):
    if len(argv) != 2 or argv[0] not in default_agent.KEYS:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    provider, root = argv
    try:
        default_agent.apply_project(root, provider, default_agent.read_enabled(root))
    except (ConflictError, EnvError) as exc:
        print("default_agent: {}; it was left untouched.".format(exc.message), file=sys.stderr)
        return CONFLICT_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
