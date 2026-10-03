"""`scripts/hooks/pre-tool-use/03-credential-guard.sh` — which Bash commands it refuses.

The guard matches command text, so what it must get right is the split between
text that NAMES a credential file and text that READS one. A heredoc body is data:
a session-summary entry mentioning the file in a markdown table, or after a `;`,
was refused as a dump. A command on the line after a heredoc terminator is not
data, and used to pass unseen.
"""

import json
import subprocess
import unittest

from devteam_support import REPO_ROOT, requires_bash

GUARD = REPO_ROOT / "scripts" / "hooks" / "pre-tool-use" / "03-credential-guard.sh"
CRED = "credentials.local.json"


def run_guard(command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command, "description": "x"}})
    return subprocess.run(["bash", str(GUARD)], input=payload, capture_output=True, text=True)


@requires_bash()
class CredentialGuardTest(unittest.TestCase):
    def assertAllowed(self, command):
        result = run_guard(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("BLOCKED", result.stderr)

    def assertRefused(self, command):
        result = run_guard(command)
        self.assertEqual(result.returncode, 2, "expected a refusal for: " + command)

    def test_direct_dump_is_refused(self):
        self.assertRefused("cat " + CRED)

    def test_redirect_read_is_refused(self):
        self.assertRefused("python3 - < " + CRED)

    def test_heredoc_body_mentioning_the_file_is_allowed(self):
        self.assertAllowed("cat >> s.md <<'EOF'\n**Done**: " + CRED + " exists\nEOF")

    def test_heredoc_body_with_semicolon_and_verb_word_is_allowed(self):
        self.assertAllowed("cat >> s.md <<'EOF'\nHealth check done; did not read " + CRED + "\nEOF")

    def test_heredoc_body_with_markdown_table_is_allowed(self):
        self.assertAllowed("cat >> s.md <<EOF\n| Credentials | OK (did not open " + CRED + ") |\nEOF")

    def test_prepend_idiom_is_allowed(self):
        self.assertAllowed(
            "{ cat <<'EOF'\n## entry\nCredentials: OK & " + CRED + " not read\nEOF\ncat s.md; } > t && mv t s.md"
        )

    def test_dash_heredoc_with_indented_terminator_is_allowed(self):
        self.assertAllowed("cat <<-EOF > s.md\n\tsee; open " + CRED + "\n\tEOF")

    def test_dump_after_heredoc_terminator_is_refused(self):
        self.assertRefused("cat > s.md <<'EOF'\nhi\nEOF\ncat " + CRED)

    def test_dump_on_a_later_line_is_refused(self):
        self.assertRefused("echo start\ncat " + CRED)

    def test_unterminated_heredoc_keeps_the_text_visible(self):
        self.assertRefused("echo $((1<<2))\ncat " + CRED)

    def test_line_continuation_joins_the_command(self):
        self.assertRefused("cat \\\n  " + CRED)

    def test_escaped_newline_inside_a_string_is_not_a_separator(self):
        self.assertAllowed("printf '%s\\n' 'Credentials OK: " + CRED + " exists' >> s.md")

    def test_search_needle_is_allowed(self):
        self.assertAllowed('grep -n "' + CRED + '" docs/notes.md')

    def test_devteam_cred_is_allowed(self):
        self.assertAllowed("devteam cred import " + CRED + " | sed 's/^/  /'")

    def test_git_history_is_allowed(self):
        self.assertAllowed("git log -- " + CRED)

    def test_git_add_force_is_refused(self):
        self.assertRefused("git add -f " + CRED)

    def test_confirmed_prefix_is_allowed(self):
        self.assertAllowed("DEVTEAM_CRED_READ_CONFIRMED=1 cat " + CRED)


if __name__ == "__main__":
    unittest.main()


@requires_bash()
class IntegrationTokenGuardTest(unittest.TestCase):
    """ADR-0031: an integration token is the CLI's to use, never an agent's to print."""

    def test_reading_an_integration_token_is_refused(self):
        result = run_guard("devteam cred get integration.cloudflare.token")
        self.assertEqual(result.returncode, 2)
        self.assertIn("devteam integration call", result.stderr)
        self.assertNotIn("integration.cloudflare.token", result.stderr)

    def test_reading_another_credential_is_still_allowed(self):
        result = run_guard("devteam cred get deploy.staging.password")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_call_proxy_itself_is_allowed(self):
        result = run_guard("devteam integration call cloudflare GET /zones --json")
        self.assertEqual(result.returncode, 0, result.stderr)
