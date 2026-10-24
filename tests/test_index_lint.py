"""The retrieval indexes are checked mechanically, and new-adr.sh keeps the ADR index.

`scripts/index-lint.sh`, its Stop hook and `scripts/new-adr.sh` run against throwaway git
repositories and a scratch state directory — never the developer's own. See
skills/shared/docs-sync/references/wiki-format.md and skills/shared/adr/SKILL.md § ADR Index.
"""

import json
import os
import shutil
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project, requires_bash

from devteam import providers

LINT = REPO_ROOT / "scripts" / "index-lint.sh"
HOOK = REPO_ROOT / "scripts" / "hooks" / "stop" / "03g-index-lint.sh"
NEW_ADR = REPO_ROOT / "scripts" / "new-adr.sh"

#: Whether each provider shows a Stop hook's stderr to the agent — same decision as
#: tests/test_spec_gate.py. Fails when a provider is added without a case.
SURFACES_WARNING = {"claude": True, "codex": True, "opencode": False}

TAGS = "order, pedido, cancel, cancelamento"
ENTRY = "# Order cancel\n\n**Origin:** t | 2026-10-17\n**Tags:** {tags}\n\n> Read this first.\n"
WIKI_INDEX = "# Wiki\n\n## Index\n\n| Entry | Keywords | Read it when |\n|---|---|---|\n{rows}"
ADR_INDEX = "# Architecture Decision Records\n\n## Index\n\n| ADR | Status | Keywords | Read it when |\n|---|---|---|---|\n{rows}"


PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"


class _DocsRepo(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.repo = make_git_project(self.tmp / "app")

    def use_write_root(self, *context_paths):
        """Record context_paths in project.json and leave only the first one on disk."""
        self.write(".dev-team-agents/project.json", json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": list(context_paths)}))
        (self.repo / "docs").rmdir()
        (self.repo / context_paths[0]).mkdir(parents=True, exist_ok=True)

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def wiki(self, tags=TAGS, row_keywords=None, row=True):
        self.write("docs/wiki/orders/cancel.md", ENTRY.format(tags=tags))
        rows = "| `orders/cancel.md` | {} | Cancelling an order |\n".format(row_keywords or tags) if row else ""
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows=rows))


@requires_bash()
class IndexLintTest(_DocsRepo):
    def lint(self):
        result = subprocess.run(["bash", str(LINT)], cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stdout.decode()

    def assert_warn(self, needle):
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"WARN .*" + needle)

    def test_a_repository_without_indexes_is_silent(self):
        self.assertEqual(self.lint(), (0, ""))

    def test_the_indexes_under_the_context_paths_write_root_are_checked(self):
        self.use_write_root(".claude/docs", "docs")
        self.write(".claude/docs/wiki/README.md", WIKI_INDEX.format(rows="| `gone.md` | a, b, c, d | Never |\n"))
        self.write(".claude/docs/development/adrs/0001-use-x.md", "# Use X\n")
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn(".claude/docs/wiki/README.md", out)
        self.assertIn(".claude/docs/development/adrs", out)

    def test_an_escaping_write_root_falls_back_to_docs(self):
        self.write(".dev-team-agents/project.json", json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["../outside"]}))
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows="| `gone.md` | a, b, c, d | Never |\n"))
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("docs/wiki/README.md", out)

    def test_a_consistent_wiki_passes_silently(self):
        self.wiki()
        self.assertEqual(self.lint(), (0, ""))

    def test_an_entry_without_tags_warns(self):
        self.write("docs/wiki/orders/cancel.md", "# Order cancel\n\n> Read this first.\n")
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows="| `orders/cancel.md` | a, b, c, d | x |\n"))
        self.assert_warn("no \\*\\*Tags:\\*\\* line")

    def test_an_unindexed_entry_warns(self):
        self.wiki(row=False)
        self.assert_warn("no row in docs/wiki/README.md")

    def test_drifted_keywords_warn(self):
        self.wiki(row_keywords="order, cancel, refund, estorno")
        self.assert_warn("Keywords differ")

    def test_thin_tags_warn(self):
        self.wiki(tags="order, cancel")
        self.assert_warn("fewer than 4 terms")

    def test_a_row_pointing_at_a_missing_entry_blocks(self):
        self.wiki()
        (self.repo / "docs" / "wiki" / "orders" / "cancel.md").unlink()
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("does not exist", out)

    def test_legacy_domain_rows_are_not_entries(self):
        self.wiki()
        index = self.repo / "docs" / "wiki" / "README.md"
        index.write_text(index.read_text() + "\n## Domains\n\n| Domain | Covers | Entries |\n|---|---|---|\n| `orders/` | cancel flow | 1 |\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_a_domain_readme_is_not_an_entry(self):
        self.wiki()
        self.write("docs/wiki/orders/README.md", "# Orders\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_a_row_with_the_wrong_case_blocks_on_every_filesystem(self):
        self.write("docs/wiki/orders/cancel.md", ENTRY.format(tags=TAGS))
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows="| `Orders/Cancel.md` | {} | x |\n".format(TAGS)))
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("does not exist", out)

    def test_an_adr_index_written_with_links_is_read(self):
        self.write("docs/adr/ADR-0001-use-postgres.md", "# Use Postgres\n")
        self.write("docs/adr/README.md", ADR_INDEX.format(rows="| [ADR-0001](ADR-0001-use-postgres.md) | Accepted | a, b, c, d | x |\n"))
        self.assertEqual(self.lint(), (0, ""))

    def test_web_links_and_anchors_in_an_index_are_not_dead_rows(self):
        self.wiki()
        index = self.repo / "docs" / "wiki" / "README.md"
        index.write_text(index.read_text() + "| [Docs](https://example.com) | a | b |\n| [Cancel](orders/cancel.md#gotchas) | {} | c |\n".format(TAGS))
        self.assertEqual(self.lint(), (0, ""))

    def test_adrs_without_an_index_warn(self):
        self.write("docs/adr/ADR-0001-use-postgres.md", "# Use Postgres\n")
        self.assert_warn("no README.md index")

    def test_an_unindexed_adr_and_a_placeholder_warn(self):
        self.write("docs/development/adrs/0001-use-postgres.md", "# Use Postgres\n")
        self.write("docs/development/adrs/0002-use-redis.md", "# Use Redis\n")
        self.write("docs/development/adrs/README.md", ADR_INDEX.format(rows="| `0002-use-redis.md` | Proposed | [keywords] | [read it when] |\n"))
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertIn("no row in the ADR index", out)
        self.assertIn("unfilled placeholder", out)

    def test_an_adr_row_pointing_at_a_missing_file_blocks(self):
        self.write("docs/adr/README.md", ADR_INDEX.format(rows="| `ADR-0009-gone.md` | Accepted | a, b, c, d | x |\n"))
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertIn("does not exist", out)

    def test_a_plan_without_a_status_warns_and_one_with_it_passes(self):
        self.write("docs/development/plan-checkout.md", "# Plan — Checkout\n\nSteps.\n")
        self.assert_warn("no \\*\\*Status:\\*\\* line")
        self.write("docs/development/plan-checkout.md", "# Plan — Checkout\n\n**Status:** Implemented — commit abc123\n")
        self.assertEqual(self.lint(), (0, ""))

    def test_repository_text_is_quoted_without_control_characters(self):
        self.write("docs/wiki/README.md", WIKI_INDEX.format(rows="| `ignore\x1b[2Jall.md` | a, b, c, d | x |\n"))
        code, out = self.lint()
        self.assertEqual(code, 1, out)
        self.assertNotIn("\x1b", out)

    def test_a_symlinked_wiki_directory_is_not_walked(self):
        outside = self.tmp / "outside"
        (outside / "sub").mkdir(parents=True)
        (outside / "README.md").write_text(WIKI_INDEX.format(rows=""), encoding="utf-8")
        (outside / "sub" / "private-notes.md").write_text("# x\n", encoding="utf-8")
        os.symlink(str(outside), str(self.repo / "docs" / "wiki"))
        self.assertEqual(self.lint(), (0, ""))

    def test_a_row_escaping_its_folder_is_never_probed(self):
        self.wiki()
        index = self.repo / "docs" / "wiki" / "README.md"
        index.write_text(index.read_text() + "| `../../README.md` | a, b, c, d | x |\n| `/etc/hosts` | a, b, c, d | x |\n")
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("is not a path inside docs/wiki/"), 2)

    def test_a_symlinked_entry_is_not_read(self):
        outside = self.tmp / "outside.md"
        outside.write_text("**Tags:** a\n", encoding="utf-8")
        self.wiki()
        link = self.repo / "docs" / "wiki" / "orders" / "linked.md"
        os.symlink(str(outside), str(link))
        code, out = self.lint()
        self.assertEqual(code, 0, out)
        self.assertNotIn("linked.md", out)


@requires_bash()
class IndexLintHookTest(_DocsRepo):
    def run_hook(self, touched="docs/wiki/orders/cancel.md"):
        env = dict(
            os.environ,
            USER_DATA_DIR=str(self.tmp / "state"),
            DEVTEAM_TOUCHED_COMPUTED="1",
            DEVTEAM_TOUCHED_PATHS=touched,
        )
        env.pop("DEVTEAM_NO_CHANGES", None)
        result = subprocess.run(["bash", str(HOOK)], cwd=str(self.repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode, result.stderr.decode()

    def test_every_provider_has_a_decided_case(self):
        self.assertEqual(set(SURFACES_WARNING), set(providers.ALL_PROVIDERS))

    def test_a_touched_path_under_a_custom_write_root_runs_the_lint(self):
        self.use_write_root("handbook", "docs")
        self.write("handbook/wiki/README.md", WIKI_INDEX.format(rows="| `gone.md` | a, b, c, d | Never |\n"))
        code, err = self.run_hook(touched="handbook/wiki/README.md")
        self.assertEqual(code, 2, err)
        self.assertIn("handbook/wiki/README.md", err)
        self.assertEqual(self.run_hook(touched="src/app.py")[0], 0)

    def test_who_sees_the_warning_matches_each_provider_s_stop_wiring(self):
        plugin = (REPO_ROOT / "opencode" / "plugin" / "dev-team-agents.ts").read_text(encoding="utf-8")
        for provider, surfaces in SURFACES_WARNING.items():
            with self.subTest(provider=provider):
                if provider == "opencode":
                    self.assertFalse(surfaces)
                    self.assertIn("client.app.log", plugin)
                else:
                    self.assertTrue(surfaces)

    def test_errors_block_on_every_stop(self):
        self.wiki()
        (self.repo / "docs" / "wiki" / "orders" / "cancel.md").unlink()
        for _ in range(2):
            code, err = self.run_hook()
            self.assertEqual(code, 2)
            self.assertIn("RETRIEVAL INDEX ERRORS", err)

    def test_warnings_surface_once_per_set_of_findings(self):
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider):
                self.setUp()
                self.wiki(row=False)
                code, err = self.run_hook()
                self.assertEqual(code, 2)
                self.assertIn("RETRIEVAL INDEX WARNINGS", err)
                self.assertEqual(self.run_hook(), (0, ""))

    def test_a_session_that_did_not_touch_the_docs_is_skipped(self):
        self.wiki(row=False)
        self.assertEqual(self.run_hook(touched="src/app.js"), (0, ""))


@requires_bash()
class NewAdrTest(_DocsRepo):
    def setUp(self):
        super().setUp()
        bound = self.repo / ".dev-team-agents"
        (bound / "scripts").mkdir(parents=True)
        (bound / "templates").mkdir()
        shutil.copy(str(NEW_ADR), str(bound / "scripts" / "new-adr.sh"))
        shutil.copy(str(REPO_ROOT / "templates" / "adr-template.md"), str(bound / "templates" / "adr-template.md"))

    def ship_lib(self):
        """The resolver new-adr.sh sources beside it — absent, it falls back to docs/."""
        lib = self.repo / ".dev-team-agents" / "scripts" / "lib"
        lib.mkdir()
        for name in ("docs-root.sh", "docs_root.py", "doc-layouts.json"):
            shutil.copy(str(REPO_ROOT / "scripts" / "lib" / name), str(lib / name))
        shutil.copytree(str(REPO_ROOT / "scripts" / "lib" / "devteam"), str(lib / "devteam"),
                        ignore=shutil.ignore_patterns("__pycache__"))

    def use_docs_layout(self, value):
        self.write(".dev-team-agents/project.json", json.dumps(
            {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"], "docs_layout": value}))

    def test_a_gated_project_starts_its_series_in_docs_adr_with_the_adr_prefix(self):
        self.ship_lib()
        self.use_docs_layout("gated")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/adr")
        self.new_adr("Use Postgres")
        self.new_adr("Use Redis")
        self.assertTrue((self.repo / "docs/adr/ADR-0001-use-postgres.md").is_file())
        self.assertTrue((self.repo / "docs/adr/ADR-0002-use-redis.md").is_file())
        self.assertFalse((self.repo / "docs/development").exists())

    def test_a_gated_project_with_a_development_series_keeps_it(self):
        self.ship_lib()
        self.use_docs_layout("gated")
        self.write("docs/development/adrs/0003-old.md", "# Old\n")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/development/adrs")
        self.new_adr("Use Redis")
        self.assertTrue((self.repo / "docs/development/adrs/0004-use-redis.md").is_file())

    def test_the_development_layout_is_unchanged_with_the_resolver_shipped(self):
        self.ship_lib()
        self.use_docs_layout("development")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/development/adrs")
        self.new_adr("Use Postgres")
        self.assertTrue((self.repo / "docs/development/adrs/0001-use-postgres.md").is_file())

    def test_the_writer_and_the_checker_agree_on_the_directory(self):
        import index_lint

        states = {
            "empty": (),
            "empty-development": ("docs/development/adrs/.keep",),
            "empty-adr": ("docs/adr/.keep",),
            "both-empty": ("docs/development/adrs/.keep", "docs/adr/.keep"),
            "development-series": ("docs/development/adrs/0001-a.md",),
            "adr-series": ("docs/adr/ADR-0001-a.md",),
        }
        self.ship_lib()
        for layout in ("development", "gated"):
            for label, files in states.items():
                with self.subTest(layout=layout, state=label):
                    for sub in ("docs/development", "docs/adr"):
                        shutil.rmtree(str(self.repo / sub), ignore_errors=True)
                    for rel in files:
                        self.write(rel, "# A\n")
                    self.use_docs_layout(layout)
                    written = self.new_adr("--dir").strip()
                    checked = index_lint.adr_dir(str(self.repo), "docs")
                    if checked is None:
                        # The checker has nothing to read until the writer creates the directory.
                        self.assertFalse((self.repo / written).exists())
                    else:
                        self.assertEqual(os.path.relpath(checked, str(self.repo)), written)

    def test_the_adr_directory_follows_the_context_paths_write_root(self):
        self.ship_lib()
        self.use_write_root(".claude/docs", "docs")
        self.assertEqual(self.new_adr("--dir").strip(), ".claude/docs/development/adrs")
        self.new_adr("Use Redis")
        self.assertTrue((self.repo / ".claude/docs/development/adrs/0001-use-redis.md").is_file())
        self.assertFalse((self.repo / "docs").exists())

    def test_without_the_resolver_the_adr_directory_stays_under_docs(self):
        self.use_write_root(".claude/docs", "docs")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/development/adrs")

    def test_a_symlink_on_the_way_to_the_write_root_is_refused(self):
        self.ship_lib()
        self.use_write_root(".claude/docs", "docs")
        outside = self.tmp / "outside"
        (self.repo / ".claude/docs").rename(outside)
        os.symlink(str(outside), str(self.repo / ".claude/docs"))
        result = subprocess.run(["bash", ".dev-team-agents/scripts/new-adr.sh", "Use X"],
                                cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def new_adr(self, *args):
        result = subprocess.run(
            ["bash", ".dev-team-agents/scripts/new-adr.sh"] + list(args),
            cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout.decode()

    def test_the_default_directory_and_scheme(self):
        self.assertEqual(self.new_adr("--dir").strip(), "docs/development/adrs")
        self.new_adr("Use Postgres")
        self.assertTrue((self.repo / "docs/development/adrs/0001-use-postgres.md").is_file())

    def test_an_existing_docs_adr_series_is_continued(self):
        self.write("docs/adr/ADR-0007-old.md", "# Old\n")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/adr")
        self.new_adr("Use Redis")
        self.assertTrue((self.repo / "docs/adr/ADR-0008-use-redis.md").is_file())
        self.assertFalse((self.repo / "docs/development/adrs").exists())

    def test_the_list_does_not_repeat_a_file_per_scheme(self):
        self.write("docs/adr/ADR-0001-one.md", "# One\n")
        self.assertEqual(self.new_adr("--list").count("# One"), 1)

    def test_the_index_row_is_appended_and_an_existing_index_kept(self):
        self.write("docs/development/adrs/README.md", ADR_INDEX.format(rows="| `0000-kept.md` | Accepted | a, b, c, d | x |\n"))
        self.new_adr("Use Postgres")
        index = (self.repo / "docs/development/adrs/README.md").read_text()
        self.assertIn("`0000-kept.md`", index)
        self.assertIn("| `0001-use-postgres.md` | Proposed | [keywords] | [read it when] |", index)

    def test_the_row_lands_inside_a_table_that_is_not_last(self):
        self.write("docs/development/adrs/README.md",
                   ADR_INDEX.format(rows="| `0000-kept.md` | Accepted | a, b, c, d | x |\n") + "\n## Notes\n\ntext")
        self.new_adr("Use Postgres")
        lines = (self.repo / "docs/development/adrs/README.md").read_text().splitlines()
        row = lines.index("| `0001-use-postgres.md` | Proposed | [keywords] | [read it when] |")
        self.assertEqual(lines[row - 1], "| `0000-kept.md` | Accepted | a, b, c, d | x |")
        self.assertEqual(lines[-1], "text")

    def test_a_prose_readme_is_left_untouched(self):
        self.write("docs/development/adrs/README.md", "# ADRs\n\nSome prose\n")
        self.new_adr("Use Postgres")
        self.assertEqual((self.repo / "docs/development/adrs/README.md").read_text(), "# ADRs\n\nSome prose\n")

    def test_an_index_heading_without_a_table_gets_one(self):
        self.write("docs/development/adrs/README.md", "# ADRs\n\n## Index\n\n## Notes\n")
        self.new_adr("Use Postgres")
        lines = (self.repo / "docs/development/adrs/README.md").read_text().splitlines()
        self.assertLess(lines.index("| `0001-use-postgres.md` | Proposed | [keywords] | [read it when] |"), lines.index("## Notes"))

    def test_a_table_in_a_later_section_is_not_the_index(self):
        self.write("docs/development/adrs/README.md", "# ADRs\n\n## Index\n\nSee below.\n\n## Links\n\n| a | b |\n|---|---|\n")
        self.new_adr("Use Postgres")
        lines = (self.repo / "docs/development/adrs/README.md").read_text().splitlines()
        self.assertLess(lines.index("| `0001-use-postgres.md` | Proposed | [keywords] | [read it when] |"), lines.index("## Links"))

    def test_a_new_index_lists_every_existing_adr(self):
        for n in (1, 2):
            self.write("docs/adr/ADR-000{}-old.md".format(n), "# Old\n")
        self.new_adr("Use Redis")
        index = (self.repo / "docs/adr/README.md").read_text()
        self.assertIn("| `ADR-0001-old.md` | [status] |", index)
        self.assertIn("| `ADR-0002-old.md` | [status] |", index)
        self.assertIn("| `ADR-0003-use-redis.md` | Proposed |", index)

    def test_a_long_series_keeps_its_prefix(self):
        for n in range(1, 151):
            self.write("docs/adr/ADR-{:04d}-t.md".format(n), "# T\n")
        self.new_adr("Use Redis")
        self.assertTrue((self.repo / "docs/adr/ADR-0151-use-redis.md").is_file())

    def test_a_populated_docs_adr_beats_an_empty_default(self):
        (self.repo / "docs/development/adrs").mkdir(parents=True)
        self.write("docs/adr/ADR-0001-one.md", "# One\n")
        self.assertEqual(self.new_adr("--dir").strip(), "docs/adr")

    def test_a_symlinked_adr_directory_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        os.symlink(str(outside), str(self.repo / "docs" / "adr"))
        result = subprocess.run(["bash", ".dev-team-agents/scripts/new-adr.sh", "Use X"],
                                cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_a_title_without_ascii_is_rejected(self):
        result = subprocess.run(["bash", ".dev-team-agents/scripts/new-adr.sh", "日本"],
                                cwd=str(self.repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)

    def test_a_symlinked_index_is_never_written_through(self):
        victim = self.tmp / "victim.md"
        victim.write_text("mine\n", encoding="utf-8")
        (self.repo / "docs/development/adrs").mkdir(parents=True)
        os.symlink(str(victim), str(self.repo / "docs/development/adrs/README.md"))
        self.new_adr("Use Postgres")
        self.assertEqual(victim.read_text(encoding="utf-8"), "mine\n")
        self.assertTrue((self.repo / "docs/development/adrs/0001-use-postgres.md").is_file())

    def test_a_missing_index_is_created_with_its_header(self):
        self.new_adr("Use Postgres")
        index = (self.repo / "docs/development/adrs/README.md").read_text()
        self.assertIn("| ADR | Status | Keywords | Read it when |", index)


if __name__ == "__main__":
    unittest.main()
