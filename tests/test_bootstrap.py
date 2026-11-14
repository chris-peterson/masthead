"""Tests for the docsify scaffold (skills/bootstrap/scripts/docsify/bootstrap.py)
and the announce script, run against throwaway git repos.

    python3 -m unittest discover -s tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "skills" / "bootstrap" / "scripts" / "docsify" / "bootstrap.py"
ANNOUNCE = ROOT / "scripts" / "announce.sh"


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


class Repo:
    """A git repo in a temp dir with an origin remote and one commit."""

    def __init__(self, origin="git@github.com:example-org/widget.git"):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "widget"
        self.path.mkdir()
        sh(self.path, "git", "init", "-q", "-b", "main")
        sh(self.path, "git", "config", "user.email", "test@example.com")
        sh(self.path, "git", "config", "user.name", "test")
        if origin:
            sh(self.path, "git", "remote", "add", "origin", origin)

    def write(self, rel, text=""):
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        sh(self.path, "git", "add", rel)

    def run(self, *flags):
        return subprocess.run(
            [sys.executable, str(BOOTSTRAP), str(self.path), *flags],
            capture_output=True, text=True,
        )

    def read(self, rel):
        return (self.path / rel).read_text(encoding="utf-8")

    def close(self):
        self.tmp.cleanup()


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)

    def test_github_scaffold(self):
        self.repo.write("tool.py", "print('hi')\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        index = self.repo.read("docs/index.html")
        self.assertNotIn("{{", index)
        self.assertIn("name: 'widget'", index)
        self.assertIn("repo: 'https://github.com/example-org/widget'", index)
        self.assertIn("prism-python.min.js", index)
        self.assertNotIn("mermaid.min.js", index)
        self.assertNotIn("gitlab-logo", index)
        self.assertEqual(self.repo.read("docs/_sidebar.md"), "- [Home](/README.md)\n")
        self.assertIn("# widget", self.repo.read("docs/README.md"))
        self.assertIn("npx docsify-cli serve docs --open", self.repo.read("justfile"))
        wf = self.repo.read(".github/workflows/deploy-docs.yml")
        self.assertIn("branches: [main]", wf)
        self.assertIn("https://example-org.github.io/widget/", r.stdout)
        self.assertIn("github.com/example-org/widget/settings/pages", r.stdout)

    def test_name_override_keeps_repo_name_in_urls(self):
        r = self.repo.run("--name", "Widget Docs")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("name: 'Widget Docs'", self.repo.read("docs/index.html"))
        self.assertIn("github.com/example-org/widget/settings/pages", r.stdout)

    def test_enterprise_github_prints_no_guessed_url(self):
        repo = Repo("git@github.acme.example:team/widget.git")
        self.addCleanup(repo.close)
        r = repo.run("--host", "github", "--repo-url", "https://github.acme.example/team/widget")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("github.io", r.stdout)
        self.assertNotIn("https://github.com/", r.stdout)
        self.assertIn("https://github.acme.example/team/widget/settings/pages", r.stdout)

    def test_user_site_and_cname_urls(self):
        repo = Repo("git@github.com:example-org/example-org.github.io.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Expected URL:     https://example-org.github.io/ ", r.stdout)
        self.repo.write("docs/CNAME", "docs.example.com\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Expected URL:     https://docs.example.com/ ", r.stdout)

    def test_gitlab_prints_where_to_read_the_url(self):
        repo = Repo("https://gitlab.example.com/group/widget.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Expected URL", r.stdout)
        self.assertIn("$CI_PAGES_URL", r.stdout)

    def test_gitlab_namespace_site_url(self):
        repo = Repo("git@gitlab.example.com:docs-team/docs-team.pages.example.com.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Expected URL:     https://docs-team.pages.example.com/ ", r.stdout)
        self.assertIn("unique domains", r.stdout)

    def test_gitlab_subgroup_namespace_shape_is_not_trusted(self):
        repo = Repo("https://gitlab.example.com/docs-team/sub/sub.pages.example.com.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Expected URL", r.stdout)

    def test_gitlab_previews_print_where_they_land(self):
        repo = Repo("git@gitlab.example.com:docs-team/docs-team.pages.example.com.git")
        self.addCleanup(repo.close)
        r = repo.run("--previews")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("https://docs-team.pages.example.com/preview-<branch-slug>/", r.stdout)
        repo = Repo("https://gitlab.example.com/group/widget.git")
        self.addCleanup(repo.close)
        r = repo.run("--previews")
        self.assertIn("Branch previews:", r.stdout)
        self.assertIn("environment link", r.stdout)

    def test_profile_repos_are_flagged(self):
        cases = [
            ("git@github.com:example-org/example-org.git", "https://github.com/example-org"),
            ("https://gitlab.example.com/someone/someone.git", "https://gitlab.example.com/someone"),
            ("https://gitlab.example.com/group/sub/gitlab-profile.git", "https://gitlab.example.com/group/sub"),
        ]
        for origin, profile in cases:
            repo = Repo(origin)
            self.addCleanup(repo.close)
            r = repo.run()
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"profile at {profile},", r.stdout)
        gh = Repo("git@github.com:example-org/example-org.git")
        self.addCleanup(gh.close)
        r = gh.run()
        self.assertIn("Expected URL:     https://example-org.github.io/example-org/ ", r.stdout)
        self.assertNotIn("Profile repo", self.repo.run().stdout)

    def test_gitlab_scaffold(self):
        repo = Repo("https://gitlab.example.com/group/widget.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gitlab-logo", repo.read("docs/index.html"))
        self.assertIn("pages: true", repo.read(".gitlab-ci.yml"))

    def test_unknown_host_fails_loud(self):
        repo = Repo("https://git.example.com/group/widget.git")
        self.addCleanup(repo.close)
        r = repo.run()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--host", r.stderr)
        self.assertFalse((repo.path / "docs").exists())
        r = repo.run("--host", "gitlab", "--repo-url", "https://git.example.com/group/widget")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(BOOTSTRAP), d], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not a git repository", r.stderr)

    def test_mermaid_and_spec(self):
        self.repo.write("notes.md", "```mermaid\nflowchart LR\n  a --> b\n```\n")
        self.repo.write("SPEC.md", "# Spec\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mermaid.min.js", self.repo.read("docs/index.html"))
        self.assertIn("- [Requirements](/SPEC.md)", self.repo.read("docs/_sidebar.md"))
        self.assertIn("cp SPEC.md docs/SPEC.md", self.repo.read("justfile"))
        wf = self.repo.read(".github/workflows/deploy-docs.yml")
        self.assertIn("cp SPEC.md docs/SPEC.md", wf)
        self.assertIn("paths: ['docs/**', 'SPEC.md']", wf)
        self.assertIn("docs/SPEC.md\n", self.repo.read(".gitignore"))

    def test_spec_copy_already_ignored_is_left_alone(self):
        self.repo.write("SPEC.md", "# Spec\n")
        self.repo.write(".gitignore", "docs/*\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.read(".gitignore"), "docs/*\n")

    def test_no_spec_leaves_gitignore_alone(self):
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.repo.path / ".gitignore").exists())
        self.assertIn("paths: ['docs/**']", self.repo.read(".github/workflows/deploy-docs.yml"))

    def test_gitlab_previews(self):
        repo = Repo("https://gitlab.example.com/group/widget.git")
        self.addCleanup(repo.close)
        r = repo.run("--previews")
        self.assertEqual(r.returncode, 0, r.stderr)
        ci = repo.read(".gitlab-ci.yml")
        self.assertNotIn("pages: true", ci)
        self.assertIn('path_prefix: "$PAGES_PREFIX"', ci)
        self.assertIn("PAGES_PREFIX: preview-$CI_COMMIT_REF_SLUG", ci)
        self.assertIn("PAGES_ENV: preview/$CI_COMMIT_REF_SLUG", ci)
        self.assertNotIn("merge_request_event", ci)
        self.assertIn("url: $CI_PAGES_URL", ci)
        self.assertIn("PAGES_EXPIRE: never", ci)
        self.assertIn("PAGES_EXPIRE: 1 week", ci)
        self.assertIn("expire_in: $PAGES_EXPIRE", ci)

    def test_gitlab_previews_with_existing_ci_prints_the_job(self):
        repo = Repo("https://gitlab.example.com/group/widget.git")
        self.addCleanup(repo.close)
        repo.write(".gitlab-ci.yml", "build:\n  script: [make]\n")
        r = repo.run("--previews")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(repo.read(".gitlab-ci.yml"), "build:\n  script: [make]\n")
        self.assertIn("PAGES_PREFIX: preview-$CI_COMMIT_REF_SLUG", r.stdout)
        self.assertIn("merge request pipelines", r.stdout)

    def test_previews_refused_on_github(self):
        r = self.repo.run("--previews")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("GitLab only", r.stderr)
        self.assertFalse((self.repo.path / "docs").exists())

    def test_existing_index_needs_force(self):
        self.repo.write("docs/index.html", "<html>mine</html>\n")
        r = self.repo.run()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force", r.stderr)
        self.assertEqual(self.repo.read("docs/index.html"), "<html>mine</html>\n")
        r = self.repo.run("--force")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("window.$docsify", self.repo.read("docs/index.html"))

    def test_other_engine_refused(self):
        for rel, needle in (("mkdocs.yml", "MkDocs"), ("plugin.yml", "shipyard")):
            with self.subTest(rel=rel):
                repo = Repo()
                self.addCleanup(repo.close)
                repo.write(rel, "name: x\ndocs:\n  mermaid: false\n")
                r = repo.run()
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(needle, r.stderr)
                self.assertFalse((repo.path / "docs").exists())

    def test_plugin_yml_without_docs_block_is_fine(self):
        self.repo.write("plugin.yml", "name: x\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_existing_ci_and_justfile_are_left_alone(self):
        self.repo.write(".github/workflows/ci.yml", "name: CI\n")
        self.repo.write("Justfile", "build:\n    echo build\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.repo.path / ".github/workflows/deploy-docs.yml").exists())
        self.assertIn("ci-integration.md", r.stdout)
        just = self.repo.read("Justfile")
        self.assertIn("build:", just)
        self.assertIn("docs:", just)

    def test_seeds_are_not_overwritten(self):
        self.repo.write("docs/README.md", "# Mine\n")
        self.repo.write("docs/_sidebar.md", "- [Mine](/README.md)\n")
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.read("docs/README.md"), "# Mine\n")
        self.assertEqual(self.repo.read("docs/_sidebar.md"), "- [Mine](/README.md)\n")


@unittest.skipUnless(shutil.which("jq"), "announce.sh needs jq")
class AnnounceTest(unittest.TestCase):
    def announce(self, *args):
        return subprocess.run(["bash", str(ANNOUNCE), *args], capture_output=True, text=True)

    def test_one_line_with_json_body(self):
        r = self.announce("content.routed", "tier=maintainer", "path=docs/releasing.md",
                          "title=Releasing", 'reason=Needs a checkout, "really"\nso it moves.')
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        key, body = lines[0].split(" ", 1)
        self.assertEqual(key, "codes.bridgeai.masthead/content.routed")
        self.assertEqual(json.loads(body), {
            "tier": "maintainer", "path": "docs/releasing.md", "title": "Releasing",
            "reason": 'Needs a checkout, "really"\nso it moves.',
        })

    def test_malformed_calls_exit_zero_and_print_nothing(self):
        for args in (("Content.Routed",), ("content.routed", "Tier=x"), ()):
            with self.subTest(args=args):
                r = self.announce(*args)
                self.assertEqual(r.returncode, 0)
                self.assertEqual(r.stdout, "")


GITLAB_PAGES = ROOT / "skills" / "bootstrap" / "scripts" / "gitlab_pages.py"

FAKE_GLAB = """#!/bin/sh
printf '%s\\n' "$@" > "$GLAB_ARGS"
if [ -n "$GLAB_FAIL" ]; then echo "$GLAB_FAIL" >&2; exit 1; fi
case "$*" in
  *pages_unique_domain_enabled=false*) unique=false; url="https://group.pages.example.com/widget" ;;
  *) unique=true; url="https://widget-a1b2c3.pages.example.com" ;;
esac
printf '{"url":"%s","is_unique_domain_enabled":%s,"deployments":[{"url":"%s","path_prefix":null},{"url":"%s/preview-fix-nav","path_prefix":"preview-fix-nav"}]}' "$url" "$unique" "$url" "$url"
"""


class GitlabPagesTest(unittest.TestCase):
    """gitlab_pages.py against a stub glab that records its arguments."""

    def setUp(self):
        self.repo = Repo("git@gitlab.example.com:group/widget.git")
        self.addCleanup(self.repo.close)
        self.bin = Path(self.repo.tmp.name) / "bin"
        self.bin.mkdir()
        glab = self.bin / "glab"
        glab.write_text(FAKE_GLAB, encoding="utf-8")
        glab.chmod(0o755)
        self.args_file = Path(self.repo.tmp.name) / "glab-args"

    def run_script(self, *args, fail=""):
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "GLAB_ARGS": str(self.args_file), "GLAB_FAIL": fail}
        return subprocess.run(
            [sys.executable, str(GITLAB_PAGES), *args, "--repo", str(self.repo.path)],
            capture_output=True, text=True, env=env,
        )

    def glab_args(self):
        return self.args_file.read_text(encoding="utf-8").splitlines()

    def test_status_reads_the_project_from_origin(self):
        r = self.run_script("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        args = self.glab_args()
        self.assertEqual(args[:4], ["api", "--hostname", "gitlab.example.com", "projects/group%2Fwidget/pages"])
        self.assertNotIn("--method", args)
        self.assertIn("Site URL:       https://widget-a1b2c3.pages.example.com", r.stdout)
        self.assertIn("Unique domain:  on", r.stdout)
        self.assertIn("preview-fix-nav", r.stdout)

    def test_unique_domain_off_patches_the_setting(self):
        r = self.run_script("unique-domain", "off")
        self.assertEqual(r.returncode, 0, r.stderr)
        args = self.glab_args()
        self.assertIn("PATCH", args)
        self.assertIn("pages_unique_domain_enabled=false", args)
        self.assertIn("Unique domain:  off", r.stdout)
        self.assertIn("https://group.pages.example.com/widget", r.stdout)

    def test_project_flag_overrides_origin(self):
        r = self.run_script("status", "--project", "other/sub/site", "--hostname", "git.example.org")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.glab_args()[2:4], ["git.example.org", "projects/other%2Fsub%2Fsite/pages"])

    def test_forbidden_names_the_role(self):
        r = self.run_script("unique-domain", "off", fail="glab: 403 Forbidden (HTTP 403)")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Maintainer", r.stderr)


if __name__ == "__main__":
    unittest.main()
