"""Self-test for helpers/canonical-facts.py and the agent-lint Untrusted Content check."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import requires_bash

REPO = Path(__file__).resolve().parent.parent
LINT = REPO / "helpers" / "canonical-facts.py"
CONFIG = REPO / "helpers" / "canonical-facts.json"


def run_lint(root, config=CONFIG):
    return subprocess.run(
        [sys.executable, "-I", str(LINT), "--root", str(root), "--config", str(config)],
        capture_output=True, text=True, check=False,
    )


class CanonicalFactsTest(unittest.TestCase):
    def tree(self, text, rel="skills/demo/SKILL.md"):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        target = tmp / rel
        target.parent.mkdir(parents=True)
        target.write_text(text, encoding="utf-8")
        return tmp

    def test_repository_is_clean(self):
        result = run_lint(REPO)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_each_fact_catches_its_wrong_claim(self):
        wrong = {
            "fid-as-current-metric": "Keep FID under 100ms.",
            "faq-howto-rich-result-promise": "Add FAQPage markup to earn a rich result.",
            "rel-next-prev-pagination": 'Mark pagination with rel="next" links.',
            "google-extended-affects-search": "Block Google-Extended to leave AI Overviews.",
            "sitemap-priority-changefreq-used": "Set the sitemap priority to 1.0 so Google crawls it first.",
            "sitelinks-search-box-benefit": "Add SearchAction to get a sitelinks search box.",
            "llms-txt-helps-google": "Publish llms.txt to rank in AI Overviews.",
            "chunking-for-google-ai": "Chunk every page into short blocks for AI Overviews.",
            "ai-specific-structured-data": "Add structured data for AI Overviews.",
            "leaked-chatbot-tokens": "See the guide (https://example.org/guide?utm_source=chatgpt.com).",
            "crawl-delay-honoured-by-google": "Set Crawl-delay: 10 to slow Googlebot down.",
            "url-parameters-tool": "Configure the URL Parameters tool in Search Console.",
            "410-faster-than-404": "Return 410 so Google drops the page faster.",
        }
        ids = {f["id"] for f in json.loads(CONFIG.read_text(encoding="utf-8"))["facts"]}
        self.assertEqual(ids, set(wrong), "every fact needs a wrong-claim case here")
        for fact_id, line in wrong.items():
            with self.subTest(fact=fact_id):
                result = run_lint(self.tree(line + "\n"))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(f"[{fact_id}]", result.stdout)

    def test_rich_result_promise_caught_in_either_order(self):
        result = run_lint(self.tree("Use rich results for FAQ pages.\n"))
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_allowed_wording_passes(self):
        allowed = [
            "FID was replaced by INP in March 2024.",
            "FAQPage: no rich result outside government and health sites.",
            'Google has ignored rel="next" since 2019.',
            "Google-Extended has no effect on Search.",
            "Google ignores priority and changefreq.",
            "The sitelinks search box was removed.",
            "llms.txt is not used by Google Search.",
            "Chunking is not needed for AI Overviews.",
            "There is no special structured data for AI Overviews.",
            # near misses: topic word without the wrong claim
            "Chunk size for the embedding index is 512 tokens.",
            "Serve llms.txt as text/plain at the site root.",
            "Strip tracking parameters such as `utm_source=chatgpt.com` from URLs.",
            "Googlebot ignores crawl-delay in robots.txt.",
            "The URL Parameters tool was retired in 2022.",
            "410: Google treats it like 404.",
            "Delete subscriptions that return 410 or 404.",
            '| "llms.txt", "GEO", "AEO", "AI Overviews" | `seo-specialist` |',
            # near misses: correct, adjacent wording
            "P1 priority: improve Google ranking of the landing page.",
            "Google-Extended is separate from Googlebot, which serves Search.",
            "Sitemaps: Google ignores <priority> values.",
            "HowTo markup: no rich result since 2023.",
        ]
        result = run_lint(self.tree("\n".join(allowed) + "\n"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_paths_outside_scope_are_not_scanned(self):
        root = self.tree("Keep FID under 100ms.\n", rel="docs/notes.md")
        (root / "skills").mkdir()
        result = run_lint(root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_scan_root_exits_2(self):
        result = run_lint(Path(tempfile.gettempdir()) / "canonical-facts-no-such-root")
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_broken_config_exits_2(self):
        root = self.tree("x\n")
        cases = {
            "not json": "{",
            "bad regex": json.dumps({"paths": ["skills"], "facts": [
                {"id": "a", "pattern": "(", "why": "w", "source": "s"}]}),
            "missing key": json.dumps({"paths": ["skills"], "facts": [{"id": "a", "pattern": "x"}]}),
            "top-level list": "[]",
            "entry not an object": json.dumps({"paths": ["skills"], "facts": ["x"]}),
            "allow not a list": json.dumps({"paths": ["skills"], "facts": [
                {"id": "a", "pattern": "x", "why": "w", "source": "s", "allow": "y"}]}),
            "duplicate id": json.dumps({"paths": ["skills"], "facts": [
                {"id": "a", "pattern": "x", "why": "w", "source": "s"},
                {"id": "a", "pattern": "y", "why": "w", "source": "s"}]}),
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                cfg = root / "facts.json"
                cfg.write_text(body, encoding="utf-8")
                self.assertEqual(run_lint(root, cfg).returncode, 2)


@requires_bash()
class UntrustedContentLintTest(unittest.TestCase):
    def test_agent_lint_fails_without_the_section(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in ("agents", "skills", "commands", "helpers", "scripts/lib"):
            shutil.copytree(REPO / rel, tmp / rel, ignore=shutil.ignore_patterns("__pycache__"))
        skill = tmp / "skills/shared/project-context/SKILL.md"
        text = skill.read_text(encoding="utf-8")
        skill.write_text(re.sub(r"^## Untrusted Content$", "## Untrusted Data", text, flags=re.M),
                         encoding="utf-8")
        result = subprocess.run(["bash", "helpers/agent-lint.sh"], cwd=tmp,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("missing '## Untrusted Content'", result.stdout)

    def test_agent_lint_fails_when_the_section_is_emptied(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in ("agents", "skills", "commands", "helpers", "scripts/lib"):
            shutil.copytree(REPO / rel, tmp / rel, ignore=shutil.ignore_patterns("__pycache__"))
        skill = tmp / "skills/shared/project-context/SKILL.md"
        text = skill.read_text(encoding="utf-8")
        skill.write_text(text.replace("cloud metadata service", "remote service"), encoding="utf-8")
        result = subprocess.run(["bash", "helpers/agent-lint.sh"], cwd=tmp,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("cloud metadata service", result.stdout)


if __name__ == "__main__":
    unittest.main()
