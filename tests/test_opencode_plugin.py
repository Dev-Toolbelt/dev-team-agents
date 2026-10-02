"""opencode plugin behavior, driven through ``tests/js/opencode-plugin.test.mjs``.

The plugin is TypeScript with only erasable type syntax, so a node that strips types (22.18+)
imports it as shipped; no build step, no dependency. Skipped when no such node is on PATH.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

JS_TEST = REPO_ROOT / "tests" / "js" / "opencode-plugin.test.mjs"


def _node_imports_ts():
    node = shutil.which("node")
    if not node:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "p.ts"
        probe.write_text("const x: number = 1\nconsole.log(x)\n")
        result = subprocess.run([node, str(probe)], capture_output=True, text=True)
    return node if result.returncode == 0 and result.stdout.strip() == "1" else None


NODE = _node_imports_ts()


@requires_bash()
@unittest.skipUnless(NODE, "needs node >= 22.18 (native TypeScript type stripping)")
class OpencodePluginTest(unittest.TestCase):
    def test_plugin_contract(self):
        result = subprocess.run([NODE, "--test", str(JS_TEST)], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
