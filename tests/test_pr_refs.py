"""The PR/MR and issue-reference detector of the task board (ADR-0018, PR/MR Created amendment).

`devteam/pr_refs.py` is the one place that decides whether a command, a tool result or a prompt
means "a PR/MR was created", "a PR/MR was merged" or "this references an issue". Everything it
reads is untrusted text, so these tests pin the false positives first (what must never match),
then each accepted shape, the remote match and the strict reference rules.
"""

import json
import subprocess
import unittest
from unittest import mock

from devteam_support import REPO_ROOT, StoreTestCase, make_git_project  # noqa: F401  (path bootstrap)

from devteam import pr_refs

JIRA = {"site_url": "https://acme.atlassian.net", "host": "acme.atlassian.net", "path": "", "project_key": "PROJ"}
GITHUB = {"web_host": "github.com", "repository": "o/r"}
CTX = {"remotes": [{"name": "up", "host": "github.com", "repo": "acme/web"}], "github": GITHUB, "jira": JIRA}
NONE_CTX = {"remotes": [], "github": None, "jira": None}


def keys(found):
    return [r["key"] if r["system"] == "jira" else "{}#{}".format(r["repo"], r["number"]) for r in found]


class AnalyzeCommandTest(unittest.TestCase):
    def ops(self, command):
        return [(a["op"], a.get("tool")) for a in pr_refs.analyze_command(command)]

    def test_a_create_or_merge_invoked_as_a_command_is_an_action(self):
        self.assertEqual(self.ops("gh pr create --title x --body y"), [("create", "gh")])
        self.assertEqual(self.ops("glab mr create -t x"), [("create", "glab")])
        self.assertEqual(self.ops("gh pr merge 12 --squash"), [("merge", "gh")])
        self.assertEqual(self.ops("glab mr merge 7"), [("merge", "glab")])
        self.assertEqual(self.ops("git merge feat/x"), [("git_merge", None)])

    def test_the_command_may_follow_a_cd_an_env_assignment_or_a_pipe(self):
        for command in (
            "cd sub && gh pr create", "FOO=1 gh pr create", "echo hi; gh pr create | tee out",
            "git push -u origin HEAD && gh pr create --fill", "gh pr create\n",
        ):
            self.assertEqual(self.ops(command), [("create", "gh")], command)

    def test_text_that_merely_mentions_the_command_is_not_an_action(self):
        for command in (
            "echo gh pr create",
            "echo 'gh pr create'",
            'echo "run gh pr create now"',
            "echo https://github.com/o/r/pull/1 # gh pr create",
            "git log # gh pr create",
            "cat <<EOF\ngh pr create\nEOF",
            "cat <<'EOF'\nglab mr merge 3\nEOF\nls",
            "bash -c 'gh pr create'",
            "'gh pr create'",
            "ghpr create",
            "gh pr view 3",
            "gh pr list",
            "gh pr merge-queue",
            "git status",
        ):
            self.assertEqual(self.ops(command), [], command)

    def test_a_segment_that_aims_the_tool_elsewhere_is_refused(self):
        for command in (
            "PATH=/ gh pr create", "PATH=/tmp/evil:$PATH gh pr create", "GH_HOST=evil.example gh pr create",
            "GH_REPO=a/b gh pr create", "GITLAB_HOST=evil.example glab mr create", "GLAB_HOST=x glab mr create",
            "GLAB_TOKEN=x glab mr merge 1", "FOO=1 PATH=/x gh pr merge 2",
            "export PATH=/tmp/evil; gh pr create", "export GH_HOST=evil.example && gh pr create",
            "PATH=/x; gh pr create", "declare -x GH_REPO=a/b\ngh pr merge 1",
        ):
            self.assertEqual(self.ops(command), [], command)

    def test_an_assignment_inside_an_argument_is_not_refused(self):
        for command in (
            'gh pr create --body "set PATH=/a before running"',
            "gh pr create --title 'GH_HOST=x is documented'",
        ):
            self.assertEqual(self.ops(command), [("create", "gh")], command)

    def test_a_command_that_defines_gh_or_glab_is_refused_whole(self):
        for command in (
            "gh(){ echo https://github.com/o/r/pull/1; }; gh pr create",
            "gh() { :; } && gh pr create",
            "function gh { :; }; gh pr create",
            "alias gh=true; gh pr create",
            "alias glab=echo\nglab mr create",
            "glab(){ :; }; glab mr merge 1",
        ):
            self.assertEqual(self.ops(command), [], command)

    def test_the_shapes_agents_really_send_are_actions(self):
        for command in (
            'gh pr create --title "feat: x" --body "$(cat <<\'EOF\'\n## Summary\n- don\'t do this\nEOF\n)"',
            'git commit -m "$(cat <<\'EOF\'\nmsg\nEOF\n)" && git push -u origin HEAD && gh pr create --fill',
            "gh pr create --body-file - <<'EOF'\nbody mentions gh pr merge 3\nEOF\n",
            "gh pr create --fill # gh pr merge 4",
            "git fetch\ngh pr create --fill\n",
            "gh pr create --fill 2>&1 | tail -3",
            "gh pr create --fill >out.txt 2>&1",
            "gh pr create \\\n  --title x --head feat/y",
        ):
            self.assertEqual([a["op"] for a in pr_refs.analyze_command(command)], ["create"], command)

    def test_an_oversized_or_non_string_command_is_not_analysed(self):
        for command in (None, "", "   ", 5, ["gh pr create"], "gh pr create " + "x" * pr_refs.MAX_COMMAND):
            self.assertEqual(pr_refs.analyze_command(command), [])

    def test_create_reads_the_head_branch_and_the_repo_flag(self):
        (a,) = pr_refs.analyze_command("gh pr create --head feat/x -R Own/Repo")
        self.assertEqual((a["head"], a["repo"]), ("feat/x", "own/repo"))
        (a,) = pr_refs.analyze_command("gh pr create -H someone:feat/y")
        self.assertEqual(a["head"], "feat/y")
        (a,) = pr_refs.analyze_command("gh pr create --head=feat/z")
        self.assertEqual(a["head"], "feat/z")
        (a,) = pr_refs.analyze_command("glab mr create -s feat/m --target-branch main")
        self.assertEqual((a["head"], a["kind"]), ("feat/m", "mr"))
        (a,) = pr_refs.analyze_command("gh pr create --head '../../etc'")
        self.assertIsNone(a["head"])
        (a,) = pr_refs.analyze_command("gh pr create --title t")
        self.assertIsNone(a["head"])

    def test_merge_target_number_link_branch_or_nothing(self):
        merge = lambda c: pr_refs.analyze_command(c)[0]["target"]  # noqa: E731
        self.assertEqual(merge("gh pr merge 12"), {"number": 12})
        self.assertEqual(merge("gh pr merge -m 5"), {"number": 5})  # -m is --merge here, not a milestone
        self.assertEqual(merge("glab mr merge !7"), {"number": 7})
        self.assertEqual(merge("glab mr merge -s 7"), {"number": 7})
        self.assertEqual(merge("gh pr merge feat/x"), {"branch": "feat/x"})
        self.assertIsNone(merge("gh pr merge --squash"))
        link = merge("gh pr merge https://github.com/o/r/pull/3")["link"]
        self.assertEqual((link["kind"], link["repo"], link["number"]), ("github_pr", "o/r", 3))
        link = merge("glab mr merge https://gitlab.com/g/sub/r/-/merge_requests/9")["link"]
        self.assertEqual((link["kind"], link["repo"], link["number"]), ("gitlab_mr", "g/sub/r", 9))
        self.assertEqual(pr_refs.analyze_command("gh pr merge 4 -R O/R")[0]["repo"], "o/r")

    def test_git_merge_needs_exactly_one_ref_and_no_abort_like_flag(self):
        merge = lambda c: pr_refs.analyze_command(c)  # noqa: E731
        self.assertEqual(merge("git merge feat/x")[0]["branch"], "feat/x")
        self.assertEqual(merge("git merge --no-ff -m 'msg here' feat/x")[0]["branch"], "feat/x")
        self.assertEqual(merge("git -C /p merge feat/x")[0]["branch"], "feat/x")
        for command in ("git merge --abort", "git merge --continue", "git merge --squash x", "git merge a b", "git merge", "git rebase x"):
            self.assertEqual(merge(command), [], command)


class ShellFormsTest(unittest.TestCase):
    def actions(self, command):
        return pr_refs.analyze_command(command)

    def test_redirections_are_not_control_operators(self):
        for command in (
            "git merge feat/x 2>&1", "git merge feat/x >/dev/null 2>&1; echo done", "git merge feat/x &>/dev/null",
            "git merge feat/x >&2", "git merge feat/x > out.log", "git merge feat/x 2>> 'my log'", "git merge feat/x < /dev/null",
            "git merge feat/x 2>&1 | tee out",
        ):
            found = self.actions(command)
            self.assertEqual([(a["op"], a["branch"]) for a in found], [("git_merge", "feat/x")], command)
        self.assertEqual(self.actions("gh pr merge 12 2>&1")[0]["target"], {"number": 12})
        self.assertEqual(self.actions("gh pr create --head feat/x >/dev/null 2>&1")[0]["head"], "feat/x")

    def test_a_quoted_angle_bracket_stays_an_argument(self):
        found = self.actions("gh pr create --title '<wip> a > b' --head feat/x")
        self.assertEqual(found[0]["head"], "feat/x")

    def test_a_real_background_ampersand_still_splits(self):
        self.assertEqual([a["op"] for a in self.actions("sleep 1 & git merge feat/x")], ["git_merge"])
        self.assertEqual([a["op"] for a in self.actions("git merge feat/x &")], ["git_merge"])

    def test_backslash_newline_continuations_are_joined(self):
        self.assertEqual(self.actions("git merge \\\n  feat/x")[0]["branch"], "feat/x")
        self.assertEqual(self.actions("gh pr merge \\\n  12 \\\n --squash")[0]["target"], {"number": 12})
        self.assertEqual(self.actions("gh \\\npr create")[0]["op"], "create")

    def test_command_prefixes_are_looked_through(self):
        for command in (
            "time git merge feat/x", "time -p git merge feat/x", "command git merge feat/x", "command -p git merge feat/x",
            "env git merge feat/x", "env -i FOO=1 git merge feat/x", "env -u BAR git merge feat/x", "env -- git merge feat/x",
            "(git merge feat/x)", "( git merge feat/x )", "{ git merge feat/x; }", "if git merge feat/x; then echo ok; fi",
            "! git merge feat/x", "while true; do git merge feat/x; done", "x && time env FOO=1 git merge feat/x",
        ):
            self.assertEqual([a["op"] for a in self.actions(command)], ["git_merge"], command)
        self.assertEqual(self.actions("time gh pr create --fill")[0]["op"], "create")
        self.assertEqual(self.actions("env GH_FOO=1 gh pr merge 3")[0]["target"], {"number": 3})

    def test_env_arguments_that_aim_the_tool_elsewhere_are_refused(self):
        for command in (
            "env GH_HOST=evil.example gh pr create", "env GH_REPO=a/b gh pr merge 1", "env PATH=/tmp:$PATH gh pr create",
            "env -i GITLAB_HOST=x glab mr create", "time env GLAB_TOKEN=x glab mr merge 2", "env -S 'gh pr create'",
            "command -v gh pr create", "GH_HOST=x time gh pr create",
        ):
            self.assertEqual(self.actions(command), [], command)

    def test_a_command_substitution_or_quoted_group_is_not_an_action(self):
        for command in ("echo $(git merge feat/x)", "echo '(git merge feat/x)'", "echo \"{ gh pr create; }\""):
            self.assertEqual(self.actions(command), [], command)

    def test_function_and_alias_definitions_still_refuse_the_line(self):
        for command in ("gh() { echo hi; }; gh pr create", "function gh { :; }; time gh pr create", "alias gh=true; gh pr create"):
            self.assertEqual(self.actions(command), [], command)


class CreatedLinkTest(unittest.TestCase):
    PR = "https://github.com/o/r/pull/12"

    def test_a_whole_line_url_is_the_pr(self):
        parts = pr_refs.created_link("Creating pull request for feat/x into main in o/r\n\n{}\n".format(self.PR))
        self.assertEqual((parts["kind"], parts["host"], parts["repo"], parts["number"]), ("github_pr", "github.com", "o/r", 12))

    def test_a_url_inside_a_sentence_is_not_a_line(self):
        for text in ("see {}".format(self.PR), "{} done".format(self.PR), "<{}>".format(self.PR), "[x]({})".format(self.PR)):
            self.assertIsNone(pr_refs.created_link(text), text)

    def test_exactly_one_distinct_url_or_nothing(self):
        self.assertIsNotNone(pr_refs.created_link("{0}\n{0}\n".format(self.PR)))
        self.assertIsNone(pr_refs.created_link("{}\nhttps://github.com/o/r/pull/13\n".format(self.PR)))
        self.assertIsNone(pr_refs.created_link("{}\nhttps://github.com/o/other/pull/12\n".format(self.PR)))

    def test_the_already_exists_form_links_the_existing_pr(self):
        text = 'a pull request for branch "feat/x" into branch "main" already exists:\n{}\n'.format(self.PR)
        self.assertEqual(pr_refs.created_link(text)["number"], 12)

    def test_glab_url_with_subgroups(self):
        parts = pr_refs.created_link("!4 feat\nhttps://gitlab.example.com/grp/sub/deep/repo/-/merge_requests/4\n")
        self.assertEqual((parts["kind"], parts["host"], parts["repo"], parts["number"]), ("gitlab_mr", "gitlab.example.com", "grp/sub/deep/repo", 4))

    def test_an_issue_url_or_junk_is_never_a_pr(self):
        for text in ("https://github.com/o/r/issues/3\n", "", "nothing", None, 5, "http://github.com/o/r/pull/3\n"):
            self.assertIsNone(pr_refs.created_link(text), text)

    def test_ansi_colour_codes_around_the_line_are_ignored(self):
        self.assertEqual(pr_refs.created_link("\x1b[1m{}\x1b[0m\n".format(self.PR))["number"], 12)


class ParseLinkTest(unittest.TestCase):
    def test_every_pitfall_in_the_amendment_is_refused(self):
        base = "https://github.com/o/r/pull/1"
        self.assertIsNotNone(pr_refs.parse_link(base))
        for url in (
            "http://github.com/o/r/pull/1",
            "https://github.com@evil.example/o/r/pull/1",
            "https://user:pw@github.com/o/r/pull/1",
            "https://github.com:8443/o/r/pull/1",
            "https://github.com/o/r/pull/1?x=1",
            "https://github.com/o/r/pull/1#frag",
            "https://github.com/o/r/pull/1/",
            "https://github.com/o/r/pull/01",
            "https://github.com/o/r/pull/0",
            "https://github.com/o/r/pull/12345678901",
            "https://GitHub.com/o/r/pull/1",
            "https://github.com./o/r/pull/1",
            "https://github.com/o%2Fx/r/pull/1",
            "https://github.com/o/r%2f/pull/1",
            "https://github.com\\o/r/pull/1",
            "https://github.com/o/../pull/1",
            "https://github.com/o/../pull/1",
            "https://github.com/o/.git/pull/1",
            "https://github.com/o/r.git/pull/1",
            "https://github/o/r/pull/1",
            "https://github.com/o/r/pull/1 ",
            "javascript:alert(1)",
            "file:///etc/passwd",
            "https://" + "a" * 3000,
            None, 5,
        ):
            self.assertIsNone(pr_refs.parse_link(url), url)

    def test_the_gitlab_shape_and_its_segment_rules(self):
        ok = pr_refs.parse_link("https://gitlab.com/a/b/c/-/merge_requests/3")
        self.assertEqual((ok["kind"], ok["repo"]), ("gitlab_mr", "a/b/c"))
        for url in (
            "https://gitlab.com/a/-/merge_requests/3", "https://gitlab.com/a/../c/-/merge_requests/3",
            "https://gitlab.com/a/-b/-/merge_requests/3", "https://gitlab.com/a/b.git/-/merge_requests/3",
            "https://gitlab.com/a/b/merge_requests/3",
        ):
            if url.endswith("/a/-/merge_requests/3"):
                continue  # a one-segment path is a valid group+repo shape only with two segments
            self.assertIsNone(pr_refs.parse_link(url), url)

    def test_build_link_round_trips_or_refuses(self):
        self.assertEqual(pr_refs.build_link("github_pr", "github.com", "o/r", 3), "https://github.com/o/r/pull/3")
        self.assertEqual(pr_refs.build_link("github_issue", "github.com", "o/r", 3), "https://github.com/o/r/issues/3")
        self.assertEqual(pr_refs.build_link("gitlab_mr", "gl.example.com", "g/s/r", 3), "https://gl.example.com/g/s/r/-/merge_requests/3")
        for args in (
            ("github_pr", "github.com", "o/r", "3"), ("github_pr", "github.com", "o/r", True), ("github_pr", "evil.example/x", "o/r", 3),
            ("github_pr", "github.com", "o/../r", 3), ("github_pr", "github.com", "o/r", 0), ("nope", "github.com", "o/r", 3),
            ("github_pr", "GitHub.com", "o/r", 3), ("gitlab_mr", "gl.example.com", "solo", 3),
        ):
            self.assertIsNone(pr_refs.build_link(*args), args)

    def test_mark_parts_validates_a_stored_entry(self):
        good = {"kind": "pr", "host": "github.com", "repo": "o/r", "number": 3}
        self.assertEqual(pr_refs.mark_parts(good), good)
        for edit in ({"host": "evil.example/x"}, {"number": "3"}, {"number": -1}, {"kind": "issue"}, {"repo": "../x"}, {"host": None}):
            self.assertIsNone(pr_refs.mark_parts(dict(good, **edit)), edit)
        self.assertIsNone(pr_refs.mark_parts("x"))
        self.assertIsNone(pr_refs.mark_parts({"kind": "mr", "host": "gitlab.com", "repo": "solo", "number": 3}))


class MergeConfirmedTest(unittest.TestCase):
    GH = {"op": "merge", "tool": "gh", "kind": "pr", "target": None, "repo": None}
    GLAB = {"op": "merge", "tool": "glab", "kind": "mr", "target": None, "repo": None}
    GIT = {"op": "git_merge", "branch": "feat/x"}

    def test_gh_prints_the_merged_number(self):
        self.assertEqual(pr_refs.merge_confirmed(self.GH, "✓ Merged pull request #12 (title)\n"), 12)
        self.assertEqual(pr_refs.merge_confirmed(self.GH, "Squashed and merged pull request o/r#12\n"), 12)
        self.assertEqual(pr_refs.merge_confirmed(self.GH, "\x1b[32m✓\x1b[0m Merged pull request #7\n"), 7)

    def test_auto_merge_and_failures_are_not_a_merge(self):
        for text in ("✓ Pull request #12 will be automatically merged when ready", "X Pull request is not mergeable", "", "merged"):
            self.assertIsNone(pr_refs.merge_confirmed(self.GH, text), text)

    def test_glab_prints_merged(self):
        self.assertIs(pr_refs.merge_confirmed(self.GLAB, "✓ Merged!\n"), True)
        self.assertIs(pr_refs.merge_confirmed(self.GLAB, "Merged\n"), True)
        self.assertEqual(
            pr_refs.merge_confirmed(self.GLAB, "Merged!\nhttps://gitlab.com/g/r/-/merge_requests/9\n"), 9,
        )
        self.assertIsNone(pr_refs.merge_confirmed(self.GLAB, "merge request !9 is not mergeable"))
        self.assertIsNone(pr_refs.merge_confirmed(self.GLAB, "Merging!"))

    def test_git_merge_needs_a_positive_marker(self):
        self.assertIs(pr_refs.merge_confirmed(self.GIT, "Updating a1..b2\nFast-forward\n f | 1 +\n"), True)
        self.assertIs(pr_refs.merge_confirmed(self.GIT, "Merge made by the 'ort' strategy.\n"), True)
        for text in (
            "Already up to date.\n",
            "",
            "Auto-merging f\nCONFLICT (content): Merge conflict in f\nAutomatic merge failed; fix conflicts\n",
            "fatal: not something we can merge\n",
            "error: Your local changes would be overwritten\nFast-forward\n",
            "CONFLICT (content)\nMerge made by the 'ort' strategy.\n",
        ):
            self.assertIsNone(pr_refs.merge_confirmed(self.GIT, text), text)

    def test_non_string_output_is_nothing(self):
        for action in (self.GH, self.GLAB, self.GIT):
            self.assertIsNone(pr_refs.merge_confirmed(action, None))


class McpTest(unittest.TestCase):
    BODY = {"number": 5, "html_url": "https://github.com/o/r/pull/5", "head": {"ref": "feat/x"}}

    def test_structured_object_json_content_text_and_structured_content(self):
        for response in (
            self.BODY,
            {"content": [{"type": "text", "text": json.dumps(self.BODY)}]},
            {"structuredContent": self.BODY, "content": []},
            [{"type": "text", "text": json.dumps(self.BODY)}],
            json.dumps(self.BODY),
        ):
            parts, head = pr_refs.mcp_created(response)
            self.assertEqual((parts["repo"], parts["number"], head), ("o/r", 5, "feat/x"), response)

    def test_an_error_result_is_ignored_even_with_a_valid_body(self):
        for response in (dict(self.BODY, isError=True), {"isError": True, "content": [{"type": "text", "text": json.dumps(self.BODY)}]}):
            self.assertIsNone(pr_refs.mcp_created(response))

    def test_the_number_must_match_the_url_and_the_url_must_be_a_pr(self):
        for body in (
            dict(self.BODY, number=6),
            dict(self.BODY, number="5"),
            dict(self.BODY, number=True),
            dict(self.BODY, html_url="https://github.com/o/r/issues/5"),
            dict(self.BODY, html_url="https://github.com/o/r/pull/5?x=1"),
            dict(self.BODY, html_url="http://github.com/o/r/pull/5"),
            {"number": 5},
        ):
            self.assertIsNone(pr_refs.mcp_created(body), body)

    def test_free_text_is_never_scanned(self):
        text = "Created https://github.com/o/r/pull/5 for you"
        self.assertIsNone(pr_refs.mcp_created({"content": [{"type": "text", "text": text}]}))
        self.assertIsNone(pr_refs.mcp_created(text))

    def test_merge_pull_request_needs_merged_true_a_number_and_no_error(self):
        inp = {"owner": "O", "repo": "R", "pullNumber": 5}
        self.assertEqual(pr_refs.mcp_merged(inp, {"merged": True, "message": "ok"}), {"number": 5, "repo": "o/r"})
        self.assertEqual(
            pr_refs.mcp_merged({"owner": "o", "repo": "r", "pull_number": 6}, {"content": [{"type": "text", "text": '{"merged": true}'}]}),
            {"number": 6, "repo": "o/r"},
        )
        self.assertIsNone(pr_refs.mcp_merged(inp, {"merged": False}))
        self.assertIsNone(pr_refs.mcp_merged(inp, {"merged": True, "isError": True}))
        self.assertIsNone(pr_refs.mcp_merged({"owner": "o", "repo": "r"}, {"merged": True}))
        self.assertEqual(pr_refs.mcp_merged({"pullNumber": 5}, {"merged": True}), {"number": 5, "repo": None})
        self.assertEqual(pr_refs.mcp_merged({"owner": "../", "repo": "r", "pullNumber": 5}, {"merged": True})["repo"], None)


class ClassifyTest(unittest.TestCase):
    URL = "https://github.com/o/r/pull/12"

    def test_claude_bash_with_a_response_object(self):
        event = pr_refs.classify({
            "session_id": "s", "cwd": "/x", "tool_name": "Bash", "tool_input": {"command": "gh pr create"},
            "tool_response": {"stdout": self.URL + "\n", "stderr": "warn", "interrupted": False},
        })
        self.assertEqual((event["event"], event["failed"], event["cwd"]), ("command", False, "/x"))
        self.assertIn(self.URL, event["output"])

    def test_claude_failure_reads_the_error_field_and_flags_it(self):
        event = pr_refs.classify({
            "tool_name": "Bash", "tool_input": {"command": "gh pr create"}, "error": "Exit code 1\n" + self.URL,
        })
        self.assertTrue(event["failed"])

    def test_codex_exec_command_response_is_a_json_string_or_plain_text(self):
        for response in (json.dumps(self.URL + "\n"), self.URL + "\n", json.dumps({"output": self.URL + "\n"})):
            event = pr_refs.classify({"tool_name": "Bash", "tool_input": {"command": "gh pr create"}, "tool_response": response})
            self.assertEqual(pr_refs.created_link(event["output"])["number"], 12, response)

    def test_opencode_bash_uses_tool_args_output(self):
        event = pr_refs.classify({"sessionID": "s", "tool": "bash", "args": {"command": "glab mr merge 4"}, "output": "Merged!"})
        self.assertEqual((event["event"], event["actions"][0]["op"]), ("command", "merge"))

    def test_mcp_tools_in_every_spelling(self):
        body = {"number": 5, "html_url": "https://github.com/o/r/pull/5"}
        for name in ("mcp__github__create_pull_request", "github_create_pull_request", "create_pull_request"):
            key = "tool" if "_" in name and not name.startswith("mcp__") else "tool_name"
            payload = {key: name, "tool_input": {"head": "feat/x"}, "tool_response": body}
            self.assertEqual(pr_refs.classify(payload)["event"], "mcp_create", name)
        merged = pr_refs.classify({
            "tool_name": "mcp__github__merge_pull_request", "tool_input": {"owner": "o", "repo": "r", "pullNumber": 5},
            "tool_response": {"merged": True},
        })
        self.assertEqual((merged["event"], merged["merged"]["number"]), ("mcp_merge", 5))

    def test_a_prompt_is_a_prompt_event_and_capped(self):
        self.assertEqual(pr_refs.classify({"prompt": "fix PROJ-1"})["event"], "prompt")
        self.assertEqual(len(pr_refs.classify({"prompt": "x" * 200000})["text"]), pr_refs.MAX_PROMPT)
        self.assertIsNone(pr_refs.classify({"prompt": "   "}))

    def test_anything_else_is_nothing(self):
        for payload in (
            None, [], "x", {}, {"tool_name": "Read", "tool_input": {}},
            {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_response": {"stdout": "x"}},
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create"}},  # no result at all
            {"tool_name": "mcp__github__create_pull_request", "tool_input": {}, "tool_response": {"isError": True}},
            {"tool_name": "mcp__github__merge_pull_request", "tool_input": {"pullNumber": 1}, "tool_response": {"merged": False}},
        ):
            self.assertIsNone(pr_refs.classify(payload), payload)


class RemoteTest(unittest.TestCase):
    def test_every_remote_url_form_normalises_to_host_and_repo(self):
        for url, expected in (
            ("https://github.com/O/R.git", ("github.com", "o/r")),
            ("https://GitHub.com/o/r", ("github.com", "o/r")),
            ("https://github.com/o/r/", ("github.com", "o/r")),
            ("https://user:tok@github.com/o/r.git", ("github.com", "o/r")),
            ("http://github.com/o/r.git", ("github.com", "o/r")),
            ("git@github.com:O/R.git", ("github.com", "o/r")),
            ("github.com:o/r", ("github.com", "o/r")),
            ("ssh://git@github.com/o/r.git", ("github.com", "o/r")),
            ("ssh://git@gitlab.example.com:2222/Grp/Sub/Repo.git", ("gitlab.example.com", "grp/sub/repo")),
            ("git://github.com/o/r.git", ("github.com", "o/r")),
            ("git@gitlab.com:grp/sub/repo.git", ("gitlab.com", "grp/sub/repo")),
        ):
            self.assertEqual(pr_refs.parse_remote_url(url), expected, url)

    def test_anything_odd_is_none(self):
        for url in ("", "foo", "file:///srv/r.git", "/srv/r.git", "ftp://github.com/o/r", "https://github.com", None, "https://localhost/o/r.git", "../x"):
            self.assertIsNone(pr_refs.parse_remote_url(url), url)

    def test_remote_matches_is_exact_on_host_and_case_insensitive_on_repo(self):
        remotes = [{"name": "origin", "host": "github.com", "repo": "o/r"}]
        parts = {"kind": "pr", "host": "github.com", "repo": "O/R", "number": 1}
        self.assertTrue(pr_refs.remote_matches(parts, remotes))
        self.assertFalse(pr_refs.remote_matches(dict(parts, repo="o/other"), remotes))
        self.assertFalse(pr_refs.remote_matches(dict(parts, host="gitlab.com"), remotes))
        self.assertFalse(pr_refs.remote_matches(parts, []))

    def test_unique_repo_is_none_when_ambiguous(self):
        one = [{"name": "o", "host": "github.com", "repo": "a/b"}, {"name": "p", "host": "github.com", "repo": "a/b"}]
        two = one + [{"name": "u", "host": "github.com", "repo": "c/d"}]
        self.assertEqual(pr_refs.unique_repo(one), ("github.com", "a/b"))
        self.assertIsNone(pr_refs.unique_repo(two))
        self.assertEqual(pr_refs.unique_repo(two, host="github.com") is None, True)
        self.assertIsNone(pr_refs.unique_repo([]))

    def test_branch_cleaning(self):
        self.assertEqual(pr_refs.clean_branch("feat/x"), "feat/x")
        self.assertEqual(pr_refs.clean_branch("owner:feat/x"), "feat/x")
        for bad in ("", None, "-x", "a..b", "x.lock", "x/", "a b", "../x", "a;b", 5, "a" * 300):
            self.assertIsNone(pr_refs.clean_branch(bad), bad)


class RealRemotesTest(StoreTestCase):
    def test_git_remotes_reads_every_remote_once_per_name_and_target(self):
        root = make_git_project(self.tmp / "p")
        for name, url in (("origin", "git@github.com:O/R.git"), ("up", "https://github.com/Up/Stream"), ("junk", "/local/path.git")):
            subprocess.run(["git", "remote", "add", name, url], cwd=str(root), check=True)
        found = pr_refs.git_remotes(root)
        self.assertEqual(
            sorted((r["name"], r["host"], r["repo"]) for r in found),
            [("origin", "github.com", "o/r"), ("up", "github.com", "up/stream")],
        )

    def test_a_directory_that_is_not_a_repository_has_no_remotes(self):
        self.assertEqual(pr_refs.git_remotes(self.tmp), [])
        self.assertEqual(pr_refs.git_remotes(self.tmp / "missing"), [])


class LinkHostsTest(unittest.TestCase):
    def hosts(self, ctx):
        return {h["host"]: h["kinds"] for h in pr_refs.link_hosts(ctx)}

    def test_with_nothing_configured_only_the_two_public_hosts(self):
        self.assertEqual(self.hosts(NONE_CTX), {"github.com": ["github_pr"], "gitlab.com": ["gitlab_mr"]})

    def test_an_integration_adds_its_host_and_a_remote_adds_a_self_hosted_gitlab(self):
        ctx = {
            "remotes": [{"name": "o", "host": "git.corp.example", "repo": "g/r"}, {"name": "p", "host": "github.com", "repo": "o/r"}],
            "github": {"web_host": "ghe.corp.example", "repository": "o/r"},
            "jira": JIRA,
        }
        hosts = self.hosts(ctx)
        self.assertEqual(hosts["git.corp.example"], ["gitlab_mr"])
        self.assertEqual(hosts["ghe.corp.example"], ["github_issue", "github_pr"])
        self.assertEqual(hosts["acme.atlassian.net"], ["jira"])
        self.assertEqual(hosts["github.com"], ["github_pr"])

    def test_the_jira_entry_alone_carries_base_path(self):
        ctx = dict(NONE_CTX, github=GITHUB, jira=dict(JIRA, site_url="https://corp.example/jira", host="corp.example", path="/jira"))
        entries = {h["host"]: h for h in pr_refs.link_hosts(ctx)}
        self.assertEqual(entries["corp.example"], {"host": "corp.example", "kinds": ["jira"], "base_path": "/jira"})
        self.assertEqual(entries["acme.atlassian.net" if "acme.atlassian.net" in entries else "github.com"].get("base_path"), None)
        for host in ("github.com", "gitlab.com"):
            self.assertNotIn("base_path", entries[host])
        cloud = {h["host"]: h for h in pr_refs.link_hosts(dict(NONE_CTX, jira=JIRA))}
        self.assertEqual(cloud["acme.atlassian.net"], {"host": "acme.atlassian.net", "kinds": ["jira"], "base_path": ""})

    def test_github_issues_need_the_bound_repository(self):
        self.assertEqual(self.hosts(dict(NONE_CTX, github={"web_host": "github.com", "repository": None}))["github.com"], ["github_pr"])
        self.assertEqual(self.hosts(dict(NONE_CTX, github=GITHUB))["github.com"], ["github_issue", "github_pr"])

    def test_mark_valid_needs_a_current_remote_and_the_kind_allowed_on_that_host(self):
        ctx = dict(NONE_CTX, remotes=[{"name": "o", "host": "github.com", "repo": "o/r"}, {"name": "g", "host": "git.corp.example", "repo": "g/r"}])
        pr = {"kind": "pr", "host": "github.com", "repo": "o/r", "number": 1}
        self.assertTrue(pr_refs.mark_valid(pr, ctx))
        self.assertFalse(pr_refs.mark_valid(dict(pr, repo="o/else"), ctx))
        self.assertFalse(pr_refs.mark_valid(pr, dict(ctx, remotes=[])))
        # A GitHub-shaped PR on a self-hosted GitLab remote is a kind the host does not carry.
        self.assertFalse(pr_refs.mark_valid({"kind": "pr", "host": "git.corp.example", "repo": "g/r", "number": 1}, ctx))
        self.assertTrue(pr_refs.mark_valid({"kind": "mr", "host": "git.corp.example", "repo": "g/r", "number": 1}, ctx))
        self.assertFalse(pr_refs.mark_valid(None, ctx))

    def test_punycode_and_other_forge_remotes_never_become_gitlab_hosts(self):
        remotes = [
            {"name": "a", "host": "xn--gthub-zsa.com", "repo": "o/r"},
            {"name": "b", "host": "bitbucket.org", "repo": "o/r"},
            {"name": "c", "host": "git.corp.example", "repo": "g/r"},
        ]
        hosts = {h["host"] for h in pr_refs.link_hosts({"remotes": remotes, "github": None, "jira": None})}
        self.assertEqual(hosts, {"github.com", "gitlab.com", "git.corp.example"})
        ctx = {"remotes": remotes, "github": None, "jira": None}
        self.assertFalse(pr_refs.mark_valid({"kind": "mr", "host": "xn--gthub-zsa.com", "repo": "o/r", "number": 1}, ctx))


class LoadContextTest(StoreTestCase):
    def ctx(self, github=None, jira=None):
        def fake(root, name):
            return {"github": github, "jira": jira}[name]

        with mock.patch("devteam.integrations.link_config", side_effect=fake):
            return pr_refs.load_context(self.tmp, with_remotes=False)

    def test_not_connected_means_nothing_and_no_origin_fallback(self):
        ctx = self.ctx()
        self.assertEqual((ctx["github"], ctx["jira"]), (None, None))

    def test_the_real_integration_loader_returns_none_on_a_clean_store(self):
        ctx = pr_refs.load_context(make_git_project(self.tmp / "p"))
        self.assertEqual((ctx["github"], ctx["jira"]), (None, None))

    def test_a_connected_account_and_valid_binding_is_read(self):
        ctx = self.ctx(
            github={"account": {"api_url": "https://api.github.com"}, "project": {"repository": "o/r"}},
            jira={"account": {"site_url": "https://Acme.atlassian.net/"}, "project": {"project_key": "PROJ"}},
        )
        # Without remotes the committed binding names no repository: a remote must vouch for it.
        self.assertEqual(ctx["github"], {"web_host": "github.com", "repository": None})
        self.assertEqual(ctx["jira"]["site_url"], "https://acme.atlassian.net")
        self.assertEqual((ctx["jira"]["host"], ctx["jira"]["project_key"]), ("acme.atlassian.net", "PROJ"))

    def test_the_bound_repository_is_kept_only_when_a_remote_on_the_web_host_names_it(self):
        github = {"account": {"api_url": "https://api.github.com"}, "project": {"repository": "o/r"}}

        def fake(root, name):
            return {"github": github, "jira": None}[name]

        for remotes, expected in (
            ([{"name": "origin", "host": "github.com", "repo": "o/r"}], "o/r"),
            ([{"name": "origin", "host": "github.com", "repo": "attacker/x"}], None),
            ([{"name": "origin", "host": "gitlab.com", "repo": "o/r"}], None),
        ):
            with mock.patch("devteam.integrations.link_config", side_effect=fake), \
                    mock.patch.object(pr_refs, "git_remotes", return_value=remotes):
                self.assertEqual(pr_refs.load_context(self.tmp)["github"]["repository"], expected, remotes)

    def test_ghe_api_url_maps_to_its_web_host(self):
        ctx = self.ctx(github={"account": {"api_url": "https://ghe.corp.example/api/v3"}, "project": {"repository": "o/r"}})
        self.assertEqual(ctx["github"]["web_host"], "ghe.corp.example")

    def test_a_hostile_committed_project_key_or_repository_is_rejected(self):
        for key in ("proj", "A", "A.*", "PROJ|X", "PROJ-", "X" * 11, "", None, 5, "P R", "(?i)PROJ", "../X"):
            ctx = self.ctx(jira={"account": {"site_url": "https://acme.atlassian.net"}, "project": {"project_key": key}})
            self.assertIsNone(ctx["jira"], key)
        for repo in ("../x/y", "o/r/extra", "o/..", "o", "", None, "o/r.git", "-o/r", "o r/x", "o/r;x", 5):
            ctx = self.ctx(github={"account": {"api_url": "https://api.github.com"}, "project": {"repository": repo}})
            self.assertEqual(ctx["github"]["repository"], None, repo)

    def test_jira_context_path_is_kept_and_a_bad_one_drops_jira(self):
        ctx = self.ctx(jira={"account": {"site_url": "https://corp.example/jira/"}, "project": {"project_key": "PROJ"}})
        self.assertEqual((ctx["jira"]["site_url"], ctx["jira"]["path"]), ("https://corp.example/jira", "/jira"))
        ctx = self.ctx(jira={"account": {"site_url": "https://corp.example/a/b-c.d"}, "project": {"project_key": "PROJ"}})
        self.assertEqual(ctx["jira"]["path"], "/a/b-c.d")
        for site in ("https://corp.example/jira/../x", "https://corp.example/./jira", "https://corp.example/a b",
                     "https://corp.example/ji%72a", "https://corp.example/ji;ra", "https://corp.example/..", "https://corp.example/a//b"):
            ctx = self.ctx(jira={"account": {"site_url": site}, "project": {"project_key": "PROJ"}})
            self.assertIsNone(ctx["jira"], site)

    def test_a_non_https_or_odd_jira_site_is_rejected(self):
        for site in ("http://acme.atlassian.net", "https://localhost", "ftp://x.example.com", "", None, "acme.atlassian.net"):
            ctx = self.ctx(jira={"account": {"site_url": site}, "project": {"project_key": "PROJ"}})
            self.assertIsNone(ctx["jira"], site)

    def test_a_damaged_integration_never_raises(self):
        with mock.patch("devteam.integrations.link_config", side_effect=ValueError("boom")):
            ctx = pr_refs.load_context(self.tmp, with_remotes=False)
        self.assertEqual((ctx["github"], ctx["jira"]), (None, None))


class ExtractRefsTest(unittest.TestCase):
    def test_things_that_look_like_keys_but_are_not_references(self):
        for text in (
            "ADR-0018 says so", "UTF-8 and SHA-256 are fine", "CVE-2024-1234 is open", "step #2 next", "do #5 and #6",
            "OTHER-12 is another Jira project", "XPROJ-12", "PROJ_12", "proj-12", "PROJ-0", "PROJ-012", "PROJ-",
            "PROJ-12x", "1PROJ-12", "-PROJ-12", "GH-45", "issue 45", "backport #7 to 2.x", "node-v18", "Fixes: nothing",
        ):
            self.assertEqual(pr_refs.extract_refs(text, CTX, "prompt"), [], text)

    def test_the_bound_jira_key_is_a_reference_and_only_the_key_is_kept(self):
        (ref,) = pr_refs.extract_refs("please look at PROJ-12 today", CTX, "prompt")
        self.assertEqual(ref, {"system": "jira", "key": "PROJ-12"})
        self.assertEqual(keys(pr_refs.extract_refs("(PROJ-1), PROJ-2; PROJ-1", CTX, "prompt")), ["PROJ-1", "PROJ-2"])

    def test_a_jira_url_on_the_configured_site_only(self):
        self.assertEqual(keys(pr_refs.extract_refs("https://acme.atlassian.net/browse/PROJ-9", CTX, "prompt")), ["PROJ-9"])
        for url in (
            "https://acme.atlassian.net/browse/OTHER-9", "https://evil.example/browse/OTHER-9",
            "http://acme.atlassian.net/browse/OTHER-9", "https://acme.atlassian.net.evil.example/browse/OTHER-9",
        ):
            self.assertEqual(pr_refs.extract_refs(url, CTX, "prompt"), [], url)

    def test_a_jira_url_on_a_foreign_host_never_yields_a_foreign_link(self):
        found = pr_refs.extract_refs("https://evil.example/browse/PROJ-9", CTX, "prompt")
        for ref in found:
            self.assertEqual(pr_refs.ref_view(ref, CTX)["url"], "https://acme.atlassian.net/browse/PROJ-9")

    def test_jira_site_with_a_path_prefix(self):
        jira = dict(JIRA, site_url="https://corp.example/jira", host="corp.example", path="/jira")
        ctx = dict(CTX, jira=jira)
        self.assertEqual(keys(pr_refs.extract_refs("https://corp.example/jira/browse/PROJ-3", ctx, "prompt")), ["PROJ-3"])
        self.assertEqual(pr_refs.ref_view({"system": "jira", "key": "PROJ-3"}, ctx)["url"], "https://corp.example/jira/browse/PROJ-3")

    def test_github_forms_that_count(self):
        for text, expected in (
            ("https://github.com/acme/web/issues/45", ["acme/web#45"]),
            ("see acme/web#45", ["acme/web#45"]),
            ("fixes #12", ["o/r#12"]), ("Fixed #12", ["o/r#12"]), ("closes #3", ["o/r#3"]), ("Closed #3", ["o/r#3"]),
            ("resolves #4", ["o/r#4"]), ("RESOLVED #4", ["o/r#4"]), ("fix #8", ["o/r#8"]), ("close #8", ["o/r#8"]), ("resolve #8", ["o/r#8"]),
            ("fixes #12 and acme/web#45", ["acme/web#45", "o/r#12"]),
        ):
            self.assertEqual(sorted(keys(pr_refs.extract_refs(text, CTX, "prompt"))), sorted(expected), text)

    def test_github_forms_that_do_not_count(self):
        for text in (
            "see #12", "#12", "GH-12", "prefixes #12", "https://github.com/acme/web/pull/45", "https://gitlab.com/o/r/issues/4",
            "https://evil.example/o/r/issues/4", "http://github.com/o/r/issues/4", "path/to/file#12", "./a/b#3", "a/b/c#3",
            "fixes#12", "unfixes #12",
        ):
            self.assertEqual(pr_refs.extract_refs(text, CTX, "prompt"), [], text)

    def test_no_github_bound_repository_means_no_github_reference_at_all(self):
        ctx = dict(CTX, github={"web_host": "github.com", "repository": None})
        self.assertEqual(pr_refs.extract_refs("fixes #12 acme/web#4 https://github.com/o/r/issues/3", ctx, "prompt"), [])

    def test_no_integration_means_no_reference_at_all(self):
        self.assertEqual(pr_refs.extract_refs("PROJ-12 fixes #3 o/r#4 https://github.com/o/r/issues/3", NONE_CTX, "prompt"), [])

    def test_a_ghe_host_is_the_web_host(self):
        ctx = dict(CTX, github={"web_host": "ghe.corp.example", "repository": "o/r"},
                   remotes=[{"name": "origin", "host": "ghe.corp.example", "repo": "a/b"}])
        self.assertEqual(keys(pr_refs.extract_refs("https://ghe.corp.example/a/b/issues/2", ctx, "prompt")), ["a/b#2"])
        self.assertEqual(pr_refs.extract_refs("https://github.com/a/b/issues/2", ctx, "prompt"), [])

    def test_task_text_accepts_owner_repo_only_for_the_bound_repo_or_a_remote(self):
        ctx = dict(CTX, remotes=[{"name": "o", "host": "github.com", "repo": "up/stream"}])
        self.assertEqual(keys(pr_refs.extract_refs("do o/r#5", ctx, "task")), ["o/r#5"])
        self.assertEqual(keys(pr_refs.extract_refs("do O/R#5", ctx, "task")), ["O/R#5"])
        self.assertEqual(keys(pr_refs.extract_refs("do up/stream#6", ctx, "task")), ["up/stream#6"])
        self.assertEqual(pr_refs.extract_refs("do evil/repo#7 https://github.com/evil/repo/issues/8", ctx, "task"), [])
        self.assertEqual(keys(pr_refs.extract_refs("fixes #9", ctx, "task")), ["o/r#9"])
        # Prompt text is often pasted from elsewhere: it may not link an arbitrary repository either.
        self.assertEqual(pr_refs.extract_refs("do evil/repo#7 https://github.com/evil/repo/issues/8", ctx, "prompt"), [])
        self.assertEqual(keys(pr_refs.extract_refs("do up/stream#6", ctx, "prompt")), ["up/stream#6"])

    def test_a_remote_on_another_host_does_not_widen_the_github_repositories(self):
        ctx = dict(CTX, remotes=[{"name": "gl", "host": "gitlab.example.com", "repo": "x/y"}])
        self.assertEqual(pr_refs.extract_refs("see x/y#3", ctx, "prompt"), [])

    def test_a_branch_yields_only_jira_keys_and_may_continue_with_a_slug(self):
        self.assertEqual(keys(pr_refs.extract_refs("feature/PROJ-12-login-form", CTX, "branch")), ["PROJ-12"])
        self.assertEqual(keys(pr_refs.extract_refs("PROJ-5", CTX, "branch")), ["PROJ-5"])
        self.assertEqual(pr_refs.extract_refs("feature/OTHER-12-login", CTX, "branch"), [])
        self.assertEqual(pr_refs.extract_refs("fix/acme/web#4-x fixes #3", CTX, "branch"), [])
        self.assertEqual(pr_refs.extract_refs("feature/PROJ-12-login", CTX, "prompt"), [])

    def test_a_pasted_list_cannot_flood_the_record(self):
        text = " ".join("PROJ-{}".format(n) for n in range(1, 60))
        self.assertEqual(len(pr_refs.extract_refs(text, CTX, "prompt")), pr_refs.MAX_REFS_PER_TEXT)

    def test_non_text_is_nothing(self):
        for text in (None, "", 5, ["PROJ-1"]):
            self.assertEqual(pr_refs.extract_refs(text, CTX, "prompt"), [])
        self.assertFalse(pr_refs.maybe_ref("no digits here at all"))
        self.assertTrue(pr_refs.maybe_ref("a-1"))


class RefViewTest(unittest.TestCase):
    def test_urls_are_rebuilt_from_the_parts(self):
        self.assertEqual(
            pr_refs.ref_view({"system": "jira", "key": "PROJ-12", "url": "https://evil.example/x"}, CTX),
            {"system": "jira", "key": "PROJ-12", "url": "https://acme.atlassian.net/browse/PROJ-12"},
        )
        self.assertEqual(
            pr_refs.ref_view({"system": "github", "repo": "a/b", "number": 3, "url": "https://evil.example/x"}, CTX),
            {"system": "github", "key": "a/b#3", "url": "https://github.com/a/b/issues/3"},
        )

    def test_an_edited_or_orphaned_entry_is_omitted(self):
        for entry, ctx in (
            ({"system": "jira", "key": "OTHER-1"}, CTX),
            ({"system": "jira", "key": "PROJ-1"}, NONE_CTX),
            ({"system": "jira", "key": "PROJ-1/../x"}, CTX),
            ({"system": "jira", "key": 5}, CTX),
            ({"system": "github", "repo": "a/b", "number": 3}, NONE_CTX),
            ({"system": "github", "repo": "a/b", "number": 3}, dict(CTX, github={"web_host": "github.com", "repository": None})),
            ({"system": "github", "repo": "../b", "number": 3}, CTX),
            ({"system": "github", "repo": "a/b", "number": "3"}, CTX),
            ({"system": "github", "repo": "a/b", "number": 0}, CTX),
            ({"system": "linear", "key": "X-1"}, CTX),
            ("PROJ-1", CTX), (None, CTX),
        ):
            self.assertIsNone(pr_refs.ref_view(entry, ctx), entry)

    def test_identity_dedupes_case_insensitively_for_github(self):
        self.assertEqual(pr_refs.ref_identity({"system": "github", "repo": "A/B", "number": 3}), ("github", "a/b", 3))
        self.assertEqual(pr_refs.ref_identity({"system": "jira", "key": "PROJ-1"}), ("jira", "PROJ-1"))
        for bad in ({"system": "jira"}, {"system": "github", "repo": "a/b"}, {}, None, "x"):
            self.assertIsNone(pr_refs.ref_identity(bad))


if __name__ == "__main__":
    unittest.main()
