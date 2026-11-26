"""Tests for the docsify update script (skills/init-docs/scripts/docsify/update.py)
and the template history it reads, run against throwaway git repos.

    python3 -m unittest discover -s tests -k test_update
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_init import Repo

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "init-docs"
SCRIPTS = SKILL / "scripts" / "docsify"
UPDATE = SCRIPTS / "update.py"
TEMPLATE_BLOCKS = SCRIPTS / "template_blocks.py"

sys.path.insert(0, str(SCRIPTS))
import template_blocks as tb  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True)


class Plugin:
    """A copy of the docsify adapter in a temp dir, so a test can give it a
    template history of its own."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill = self.root / "skills" / "init-docs"
        shutil.copytree(SCRIPTS, self.skill / "scripts" / "docsify")
        (self.skill / "assets" / "docsify").mkdir(parents=True)
        self.template = self.skill / "assets" / "docsify" / "index.html"
        self.history = self.skill / "assets" / "docsify" / "template-history.json"
        self.history.write_text(json.dumps({"templates": {}, "blocks": {}}), encoding="utf-8")

    def script(self, name):
        return self.skill / "scripts" / "docsify" / name

    def use(self, template_text):
        """Make template_text the current template and record it."""
        self.template.write_text(template_text, encoding="utf-8")
        r = run(self.script("template_blocks.py"), "record")
        assert r.returncode == 0, r.stderr

    def close(self):
        self.tmp.cleanup()


def edit_block(text, block, old, new):
    """Replace the first old after a block's marker with new, leaving the rest
    of the text (the stamp line included) as it was."""
    m = re.search(rf"masthead:block {re.escape(block)}(?![a-z0-9-])", text)
    assert m, block
    at = text.index(old, m.end())
    return text[:at] + new + text[at + len(old):]


def drop_block(text, block):
    """Remove a block's lines, from its marker to the next one."""
    lines = text.split("\n")
    marker = re.compile(r"masthead:block ([a-z0-9-]+)")
    start = next(i for i, l in enumerate(lines) if (m := marker.search(l)) and m.group(1) == block)
    end = next(i for i in range(start + 1, len(lines)) if marker.search(lines[i]))
    return "\n".join(lines[:start] + lines[end:])


class TemplateHistoryTest(unittest.TestCase):
    def test_current_template_is_recorded(self):
        r = run(TEMPLATE_BLOCKS, "check")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_blocks_rejoin_to_the_template(self):
        text = (SKILL / "assets" / "docsify" / "index.html").read_text(encoding="utf-8")
        blocks = tb.split_blocks(text)
        self.assertEqual("".join(b for _, b in blocks), tb.normalize(text))
        names = [n for n, _ in blocks]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("page-toc", names)


class UpdateTemplateTest(unittest.TestCase):
    """A site made from an older template, then edited, brought current."""

    def setUp(self):
        self.plugin = Plugin()
        self.addCleanup(self.plugin.close)
        self.repo = Repo()
        self.addCleanup(self.repo.close)
        current = (SKILL / "assets" / "docsify" / "index.html").read_text(encoding="utf-8")
        old = drop_block(current, "page-toc")
        old = edit_block(old, "copy-button", "/* ── Copy button", "/* ── Copy button (old)")
        old = edit_block(old, "search", ".sidebar {", ".sidebar { /* old search */")
        self.current = current
        self.plugin.use(old)
        r = run(self.plugin.script("init.py"), self.repo.path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.repo.write("docs/favicon.svg", "<svg/>")
        self.plugin.use(current)
        self.index = self.repo.path / "docs" / "index.html"
        site = self.index.read_text(encoding="utf-8")
        site = edit_block(site, "sidebar-layout", ".sidebar {", ".sidebar { /* ours */")
        site = edit_block(site, "search", ".sidebar {", ".sidebar { /* our search */")
        self.index.write_text(site, encoding="utf-8")

    def update(self, *flags):
        return run(self.plugin.script("update.py"), self.repo.path, *flags)

    def statuses(self):
        r = self.update("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return {b["block"]: b["status"] for b in json.loads(r.stdout)["template"]["blocks"]}

    def test_classifies_each_block(self):
        self.assertEqual(self.statuses(), {
            "copy-button": "upstream",
            "page-toc": "added",
            "sidebar-layout": "local",
            "search": "conflict",
        })

    def test_report_writes_nothing_and_check_fails(self):
        before = self.index.read_text(encoding="utf-8")
        r = self.update("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--resolve search=site|template", r.stdout)
        self.assertEqual(self.index.read_text(encoding="utf-8"), before)

    def test_apply_refuses_an_unresolved_conflict(self):
        before = self.index.read_text(encoding="utf-8")
        r = self.update("--apply")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--resolve search=", r.stderr)
        self.assertEqual(self.index.read_text(encoding="utf-8"), before)

    def test_apply_merges_and_restamps(self):
        r = self.update("--apply", "--resolve", "search=site")
        self.assertEqual(r.returncode, 0, r.stderr)
        site = self.index.read_text(encoding="utf-8")
        self.assertIn("masthead:block page-toc", site)
        self.assertNotIn("Copy button (old)", site)
        self.assertIn("/* ours */", site)
        self.assertIn("/* our search */", site)
        self.assertEqual(tb.read_stamp(site)[1], tb.fingerprint(self.current))
        # The new block lands where the template puts it.
        names = [n for n, _ in tb.split_blocks(site)]
        self.assertEqual(names.index("page-toc"), names.index("deep-link-settle") + 2)
        # What's left are the site's own edits, which don't fail --check.
        self.assertEqual(self.statuses(), {"sidebar-layout": "local", "search": "local"})
        self.assertEqual(self.update("--check").returncode, 0)

    def test_resolving_to_the_template_drops_the_local_edit(self):
        r = self.update("--apply", "--resolve", "search=template")
        self.assertEqual(r.returncode, 0, r.stderr)
        site = self.index.read_text(encoding="utf-8")
        self.assertNotIn("/* our search */", site)
        self.assertNotIn("/* old search */", site)


class UpdateUnstampedTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)
        self.assertEqual(self.repo.run().returncode, 0)
        self.index = self.repo.path / "docs" / "index.html"
        site = self.index.read_text(encoding="utf-8")
        site = "\n".join(l for l in site.split("\n") if 'name="generator"' not in l)
        self.index.write_text(site.replace("subMaxLevel: 0", "subMaxLevel: 2"), encoding="utf-8")

    def test_reports_one_unclassified_diff(self):
        r = run(UPDATE, self.repo.path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Stamp:     none", r.stdout)
        self.assertIn("-      subMaxLevel: 2,", r.stdout)
        self.assertIn("+      subMaxLevel: 0,", r.stdout)

    def test_apply_needs_adopt(self):
        r = run(UPDATE, self.repo.path, "--apply")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--adopt", r.stderr)
        r = run(UPDATE, self.repo.path, "--apply", "--adopt")
        self.assertEqual(r.returncode, 0, r.stderr)
        site = self.index.read_text(encoding="utf-8")
        self.assertIn("subMaxLevel: 0", site)
        self.assertIsNotNone(tb.read_stamp(site))


class UpdateRefusesTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)

    def test_no_hub_points_at_init_docs(self):
        r = run(UPDATE, self.repo.path)
        self.assertEqual(r.returncode, 2)
        self.assertIn("/masthead:init-docs", r.stderr)

    def test_another_owner(self):
        self.repo.write("mkdocs.yml", "site_name: x\n")
        self.repo.write("docs/index.html", "docsify")
        r = run(UPDATE, self.repo.path)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MkDocs", r.stderr)


class FindingsTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)
        self.assertEqual(self.repo.run().returncode, 0)
        self.repo.write("docs/favicon.svg", "<svg/>")

    def findings(self):
        r = run(UPDATE, self.repo.path, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return [(f["rule"], f["file"], f["line"]) for f in json.loads(r.stdout)["findings"]]

    def test_fresh_site_is_clean(self):
        self.assertEqual(self.findings(), [])
        self.assertEqual(run(UPDATE, self.repo.path, "--check").returncode, 0)

    def test_sidebar_rules(self):
        self.repo.write("docs/guide.md", "# Guide\n")
        self.repo.write("docs/users.md", "# Users\n")
        self.repo.write("docs/_sidebar.md", "\n".join([
            "- [Home](/README.md)",
            "- **Basics**",                       # a label beside ...
            "- [Guide](/guide.md)",               # ... a linked section with children: 08a
            "  - [Users](/users.md)",
            "  - [Again](/users.md)",             # shares an href: 08b
            "- [Setup](/?id=setup)",              # a section on the home route: 08c
            "  - [Step](/guide.md#step)",
            "- [Gone](/missing.md)",              # 08d
            "- [Case](/Guide.md)",                # 08d, case only
        ]) + "\n")
        got = self.findings()
        self.assertIn(("LINT-02", "docs/_sidebar.md", 3), got)
        self.assertIn(("LINT-03", "docs/_sidebar.md", 5), got)
        self.assertIn(("LINT-04", "docs/_sidebar.md", 6), got)
        self.assertIn(("LINT-05", "docs/_sidebar.md", 8), got)
        self.assertIn(("LINT-05", "docs/_sidebar.md", 9), got)
        self.assertEqual(len(got), 5, got)

    def test_linked_section_headings(self):
        self.repo.write("docs/changelog.md", "# Changelog\n")
        self.repo.write("docs/guides/README.md", "# Guides\n")
        self.repo.write("docs/guides/install.md", "# Install\n")
        self.repo.write("docs/_sidebar.md", "\n".join([
            "- [Home](/README.md)",
            "- **[Changelog](/changelog.md)**",   # a linked heading: fine
            "- **[Guides](/guides/)**",           # a linked heading with items ...
            "  - [Install](/guides/install.md)",
            "  - [Overview](/guides/)",           # ... that share its href
            "- [**Bold**](/changelog.md)",        # the bold inside the link
        ]) + "\n")
        got = self.findings()
        self.assertIn(("LINT-03", "docs/_sidebar.md", 5), got)
        self.assertIn(("LINT-10", "docs/_sidebar.md", 6), got)
        self.assertEqual(len(got), 2, got)

    def test_page_links_and_reach(self):
        self.repo.write("docs/_sidebar.md", "- [Home](/README.md)\n- [Guides](/guides/)\n")
        self.repo.write("docs/guides/README.md", "# Guides\n\n[Setup](setup)\n")
        self.repo.write("docs/guides/setup.md", "# Setup\n\n![shot](shot.png)\n[src](../../src/x.py)\n"
                                                "```\n[not a link](nowhere.md)\n```\n")
        self.repo.write("docs/orphan.md", "# Orphan\n")
        got = self.findings()
        self.assertIn(("LINT-05", "docs/guides/setup.md", 3), got)   # missing image
        self.assertIn(("LINT-05", "docs/guides/setup.md", 4), got)   # outside docs/
        self.assertIn(("LINT-08", "docs/orphan.md", 1), got)
        # guides/setup.md is reached through the section's index page.
        self.assertNotIn(("LINT-08", "docs/guides/setup.md", 1), got)
        self.assertEqual(len(got), 3, got)

    def test_relative_links_without_relative_path(self):
        index = self.repo.path / "docs" / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace("relativePath: true", "relativePath: false"),
                         encoding="utf-8")
        self.repo.write("docs/_sidebar.md", "- [Home](/README.md)\n- [Guides](/guides/)\n")
        self.repo.write("docs/guides/README.md", "# Guides\n\n[Setup](setup)\n[Abs](/guides/setup)\n")
        self.repo.write("docs/guides/setup.md", "# Setup\n")
        got = [f for f in self.findings() if f[0] != "LINT-08"]
        self.assertIn(("LINT-06", "docs/guides/README.md", 3), got)
        # The template changed, so the site is behind but has no 08e on the absolute link.
        self.assertEqual([f for f in got if f[0] == "LINT-06"], [("LINT-06", "docs/guides/README.md", 3)])

    def test_sub_max_level_and_favicon(self):
        index = self.repo.path / "docs" / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace("subMaxLevel: 0", "subMaxLevel: 3"),
                         encoding="utf-8")
        (self.repo.path / "docs" / "favicon.svg").unlink()
        rules = [f[0] for f in self.findings()]
        self.assertEqual(sorted(rules), ["LINT-07", "LINT-09"])

    def test_spec_copy_counts_as_present(self):
        self.repo.write("SPEC.md", "# Spec\n")
        self.repo.write("docs/_sidebar.md", "- [Home](/README.md)\n- [Requirements](/SPEC.md)\n")
        self.assertEqual(self.findings(), [])


if __name__ == "__main__":
    unittest.main()
