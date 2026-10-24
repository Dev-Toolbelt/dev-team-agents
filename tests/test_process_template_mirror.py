"""templates/process-template.md's Owner Table mirrors the gated column of scripts/lib/doc-layouts.json."""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAYOUTS = REPO_ROOT / "scripts" / "lib" / "doc-layouts.json"
TEMPLATE = REPO_ROOT / "templates" / "process-template.md"
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(yes|no)\s*\|\s*$")


def gated_map():
    docs = json.loads(LAYOUTS.read_text(encoding="utf-8"))["docs"]
    return {key: (entry["gated"], entry["owner"], entry["readonly"])
            for key, entry in docs.items() if entry["gated"] is not None}


def owner_table():
    text = TEMPLATE.read_text(encoding="utf-8")
    section = text.split("## Owner Table", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        match = ROW.match(line)
        if match:
            key, path, owner, readonly = match.groups()
            if key in rows:
                raise AssertionError(f"duplicate Owner Table row for `{key}`")
            rows[key] = (path, owner, readonly == "yes")
    return rows


class ProcessTemplateMirrorTest(unittest.TestCase):
    def test_owner_table_lists_every_gated_key(self):
        self.assertEqual(sorted(owner_table()), sorted(gated_map()))

    def test_each_row_matches_the_map(self):
        table = owner_table()
        for key, expected in gated_map().items():
            with self.subTest(key=key):
                self.assertEqual(table.get(key), expected)

    def test_a_null_gated_key_has_no_row(self):
        docs = json.loads(LAYOUTS.read_text(encoding="utf-8"))["docs"]
        absent = {key for key, entry in docs.items() if entry["gated"] is None}
        self.assertFalse(absent & set(owner_table()))


if __name__ == "__main__":
    unittest.main()
