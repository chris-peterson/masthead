#!/usr/bin/env python3
"""Scaffold a docsify hub into a target repo: the deterministic half of
/masthead:bootstrap on the docsify engine.

This script owns everything mechanical: detect the source host, default branch,
languages, Mermaid usage, and SPEC.md; copy assets/docsify/index.html verbatim
with a handful of substitutions; seed _sidebar.md, README.md, and a `docs`
recipe in the justfile; write a standalone CI file when the repo has none; and
print a summary plus the follow-ups that need judgment.

It deliberately makes no content or design decisions. Those stay with the model
running the skill (see SKILL.md):
  - the favicon (a per-project SVG),
  - what goes in the hub, and what gets turned away to another audience,
  - the home page and sidebar beyond the seed,
  - wiring the deploy into an existing CI workflow,
  - whether the detected language list is right.

Fail loud, never guess. If the host can't be determined and wasn't passed, if
another tool already owns the repo's docs site, or if docs/index.html exists and
--force wasn't passed, exit non-zero with a message saying what to do instead of
leaving a half-configured site.

Usage:
  bootstrap.py [REPO_PATH] [--name NAME] [--host github|gitlab]
               [--repo-url URL] [--langs l1,l2,...] [--force]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Extension / basename -> Prism language. json is highlighted by Prism core, so
# it needs no component plugin and is intentionally absent here.
EXT_TO_PRISM = {
    ".cs": "csharp",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "jsx",
    ".java": "java",
    ".rb": "ruby",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".sh": "bash",
    ".bash": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".sql": "sql",
    ".tf": "hcl",
}
BASENAME_TO_PRISM = {"Dockerfile": "docker"}

# bash and yaml ship in nearly every project's CI and scripts, so include them by default.
ALWAYS_PRISM = ["bash", "yaml"]

PRISM_CDN = "https://cdn.jsdelivr.net/npm/prismjs@1/components/prism-{}.min.js"

ACCENT_START = {
    "github": "light-dark(var(--alucard-purple),  var(--dracula-purple))",
    "gitlab": "light-dark(var(--alucard-orange),  var(--dracula-orange))",
}

GITLAB_CORNER_CSS = """
    /* ── GitLab corner ─────────────────────────────────────
         docsify's built-in `repo:` corner draws a GitHub octocat; swap it for
         the GitLab logo. (GitHub repos leave this block empty.) */
    .github-corner svg { display: none; }
    .github-corner {
      position: fixed; top: 0; right: 0;
      width: 80px; height: 80px; z-index: 10;
      background: url('https://about.gitlab.com/images/press/gitlab-logo-500-rgb.svg') no-repeat center center;
      background-size: 56px 56px;
    }
"""

MERMAID_SCRIPTS = """  <!-- Mermaid (handDrawn look; re-rendered on theme toggle + route change) -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>if (typeof mermaid !== 'undefined') mermaid.initialize({ startOnLoad: false, theme: getMermaidTheme(), look: 'handDrawn' });</script>
"""

SPEC_CANDIDATES = ["SPEC.md", "spec.md", "SPECIFICATION.md"]
JUSTFILE_NAMES = ["justfile", "Justfile", ".justfile"]

# Files that say another tool already builds this repo's docs site. Scaffolding
# a docsify site beside one gives the repo two sites that disagree.
OTHER_ENGINES = [
    ("mkdocs.yml", "MkDocs"),
    ("mkdocs.yaml", "MkDocs"),
    ("docusaurus.config.js", "Docusaurus"),
    ("docusaurus.config.ts", "Docusaurus"),
    ("docusaurus.config.mjs", "Docusaurus"),
    ("docs/conf.py", "Sphinx"),
    ("book.toml", "mdBook"),
]


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def git(repo, *args):
    """Run a git command in repo; return stdout stripped, or '' on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _host_of(url):
    if "github.com" in url:
        return "github"
    if "gitlab" in url:
        return "gitlab"
    return None


def detect_host_and_url(repo, host_arg, url_arg):
    """Return (host, https_repo_url, org, repo_name). Fail loud if undetectable."""
    origin = git(repo, "remote", "get-url", "origin")
    url = url_arg or _to_https(origin)
    host = host_arg or _host_of(url or "")

    if not host or not url:
        die(
            "could not tell GitHub or GitLab from the git remote "
            f"({origin or 'no origin'}). Ask the user where the source lives, "
            "then re-run with --host and --repo-url."
        )

    org, name = _org_and_name(url)
    return host, url, org, name


def _to_https(origin):
    """Normalize a git remote (ssh or https) to a clean https URL, no .git."""
    if not origin:
        return ""
    m = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", origin)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    m = re.match(r"ssh://git@([^/:]+)(?::\d+)?/(.+?)(?:\.git)?$", origin)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    return re.sub(r"\.git$", "", origin)


def _org_and_name(url):
    m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2)
    return "", ""


def default_branch(repo):
    ref = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ref:
        return ref.rsplit("/", 1)[-1]
    return git(repo, "branch", "--show-current") or "main"


def other_owner(repo):
    """Name the tool that already builds this repo's docs site, or None."""
    plugin_yml = repo / "plugin.yml"
    if plugin_yml.is_file():
        text = plugin_yml.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^docs:", text, re.MULTILINE):
            return "shipyard (plugin.yml has a docs: block; `shipyard build-docs` renders docs/)"
    for rel, tool in OTHER_ENGINES:
        if (repo / rel).is_file():
            return f"{tool} ({rel})"
    return None


def detect_langs(repo, langs_arg):
    if langs_arg:
        return list(dict.fromkeys(l.strip() for l in langs_arg if l.strip()))
    files = git(repo, "ls-files").splitlines()
    found = list(ALWAYS_PRISM)
    for f in files:
        p = Path(f)
        lang = BASENAME_TO_PRISM.get(p.name) or EXT_TO_PRISM.get(p.suffix.lower())
        if lang and lang not in found:
            found.append(lang)
    return found


def uses_mermaid(repo):
    files = [f for f in git(repo, "ls-files").splitlines() if f.endswith(".md")]
    for f in files:
        try:
            text = (repo / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "```mermaid" in text:
            return True
    return False


def detect_spec(repo):
    names = {p.name for p in repo.iterdir() if p.is_file()}
    for cand in SPEC_CANDIDATES:
        if cand in names:  # case-exact, whatever the filesystem does
            return cand
    return None


def render_index(template, name, url, host, langs, mermaid):
    prism = "\n".join(
        f'  <script src="{PRISM_CDN.format(l)}"></script>' for l in langs
    )
    out = template
    out = out.replace("{{PROJECT_NAME}}", name)
    out = out.replace("{{REPO_URL}}", url)
    out = out.replace("{{TITLEBAR_ACCENT_START}}", ACCENT_START[host])
    out = out.replace("{{GITLAB_CORNER_CSS}}", GITLAB_CORNER_CSS if host == "gitlab" else "")
    out = out.replace("{{PRISM_PLUGINS}}", prism)
    out = out.replace("{{MERMAID_SCRIPTS}}", MERMAID_SCRIPTS if mermaid else "")
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        die(f"template still has unfilled placeholders: {sorted(set(leftover))}")
    return out


def seed_sidebar(docs, spec):
    path = docs / "_sidebar.md"
    if path.exists():
        return False
    lines = ["- [Home](/README.md)"]
    if spec:
        lines.append(f"- [Requirements](/{spec})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def seed_readme(docs, name):
    path = docs / "README.md"
    if path.exists():
        return False
    path.write_text(
        f"# {name}\n\n"
        f"_One paragraph for someone who uses {name}: what it is and why they'd want it._\n\n"
        "## Quickstart\n\n"
        "_The shortest path from \"never heard of this\" to \"it's working.\"_\n",
        encoding="utf-8",
    )
    return True


def ensure_justfile(repo, spec):
    path = next((repo / n for n in JUSTFILE_NAMES if (repo / n).is_file()), repo / "justfile")
    spec_cp = f"    cp {spec} docs/{spec}\n" if spec else ""
    recipe = (
        "# Preview the docs site locally\n"
        f"docs:\n{spec_cp}    npx docsify-cli serve docs --open\n"
    )
    if not path.exists():
        path.write_text(recipe, encoding="utf-8")
        return path.name, "created"
    text = path.read_text(encoding="utf-8")
    if re.search(r"^docs\s*:", text, re.MULTILINE):
        return path.name, "left as-is, it already has a docs recipe"
    path.write_text(text.rstrip("\n") + "\n\n" + recipe, encoding="utf-8")
    return path.name, "appended"


def write_ci(repo, host, branch, spec):
    """Write the standalone CI file when no workflow exists yet. Returns a
    (path_or_None, note) tuple; note is set when the model must wire the deploy
    into an existing workflow by hand."""
    if host == "github":
        wf_dir = repo / ".github" / "workflows"
        existing = sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")) if wf_dir.is_dir() else []
        if existing:
            names = ", ".join(p.name for p in existing)
            return None, (
                f"GitHub workflows already exist ({names}). Add a publish-docs "
                "job to the existing CI rather than a standalone file; see "
                "references/ci-integration.md."
            )
        spec_step = (
            "      - name: Copy SPEC into docs\n"
            f"        run: cp {spec} docs/{spec}\n"
            if spec else ""
        )
        wf_dir.mkdir(parents=True, exist_ok=True)
        path = wf_dir / "deploy-docs.yml"
        path.write_text(
            "name: Deploy docs\n"
            "on:\n"
            "  push:\n"
            f"    branches: [{branch}]\n"
            "    paths: ['docs/**']\n"
            "  workflow_dispatch:\n"
            "permissions:\n"
            "  pages: write\n"
            "  id-token: write\n"
            "concurrency:\n"
            "  group: pages\n"
            "  cancel-in-progress: false\n"
            "jobs:\n"
            "  deploy:\n"
            "    environment:\n"
            "      name: github-pages\n"
            "      url: ${{ steps.deployment.outputs.page_url }}\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v6\n"
            f"{spec_step}"
            "      - uses: actions/configure-pages@v5\n"
            "      - uses: actions/upload-pages-artifact@v4\n"
            "        with:\n"
            "          path: docs\n"
            "      - id: deployment\n"
            "        uses: actions/deploy-pages@v4\n",
            encoding="utf-8",
        )
        return path, None

    # GitLab
    spec_step = f"    - cp {spec} docs/{spec}\n" if spec else ""
    job = (
        "pages:\n"
        "  stage: deploy\n"
        "  script:\n"
        "    - mkdir -p public\n"
        f"{spec_step}"
        "    - cp -r docs/* public/\n"
        "  pages: true\n"
        "  rules:\n"
        "    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH\n"
    )
    path = repo / ".gitlab-ci.yml"
    if path.exists():
        return None, (
            ".gitlab-ci.yml already exists. Append this pages job by hand "
            "(check that a `deploy` stage is declared):\n\n" + job
        )
    path.write_text(job, encoding="utf-8")
    return path, None


def main():
    ap = argparse.ArgumentParser(description="Scaffold a docsify hub into a git repo.")
    ap.add_argument("repo", nargs="?", default=".", help="target repo path (default: .)")
    ap.add_argument("--name", help="project name (default: the repo name)")
    ap.add_argument("--host", choices=["github", "gitlab"], help="override host detection")
    ap.add_argument("--repo-url", help="override the source repo URL")
    ap.add_argument("--langs", help="comma-separated Prism languages (overrides detection)")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing docs/index.html with the current template")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not git(repo, "rev-parse", "--git-dir"):
        die(f"{repo} is not a git repository")

    owner = other_owner(repo)
    if owner:
        die(
            f"this repo's docs site is already built by {owner}. masthead "
            "doesn't scaffold a second site beside it."
        )

    docs = repo / "docs"
    index = docs / "index.html"
    if index.exists() and not args.force:
        die(
            "docs/index.html already exists. Diff it against the template "
            "(assets/docsify/index.html) and carry fixes across by hand, or "
            "re-run with --force to replace it with the current template."
        )

    host, url, org, repo_name = detect_host_and_url(repo, args.host, args.repo_url)
    name = args.name or repo_name or repo.name
    branch = default_branch(repo)
    langs = detect_langs(repo, args.langs.split(",") if args.langs else None)
    mermaid = uses_mermaid(repo)
    spec = detect_spec(repo)

    template_path = Path(__file__).resolve().parents[2] / "assets" / "docsify" / "index.html"
    if not template_path.is_file():
        die(f"template not found at {template_path}")
    template = template_path.read_text(encoding="utf-8")

    replaced = index.exists()
    docs.mkdir(exist_ok=True)
    index.write_text(render_index(template, name, url, host, langs, mermaid), encoding="utf-8")

    sidebar_new = seed_sidebar(docs, spec)
    readme_new = seed_readme(docs, name)
    just_name, just_state = ensure_justfile(repo, spec)
    has_favicon = (docs / "favicon.svg").is_file()
    ci_path, ci_note = write_ci(repo, host, branch, spec)

    # ── Summary ─────────────────────────────────────────────
    print("Created / updated:")
    print(f"  docs/index.html   {'replaced with the current template' if replaced else 'docsify site (theme, day/night toggle, search, copy buttons)'}")
    print(f"  docs/_sidebar.md  {'seeded' if sidebar_new else 'left as-is (already existed)'}")
    print(f"  docs/README.md    {'seeded home page' if readme_new else 'left as-is (already existed)'}")
    print(f"  {just_name:<17} `just docs` preview recipe ({just_state})")
    if ci_path:
        print(f"  {ci_path.relative_to(repo).as_posix()}  publishes docs/ to Pages")
    print()
    print(f"Source host:      {host} ({url})")
    print(f"Default branch:   {branch}")
    print(f"Prism languages:  {', '.join(langs)}")
    print(f"Mermaid:          {'used, CDN included' if mermaid else 'not used, CDN omitted'}")
    print(f"SPEC:             {spec if spec else 'none'}")
    print(f"Favicon:          {'present' if has_favicon else 'missing, design docs/favicon.svg'}")
    if host == "github" and org and repo_name:
        print(f"Expected URL:     https://{org.lower()}.github.io/{repo_name}/ (check it resolves before linking it)")

    print()
    print("Follow-ups (judgment, not done by this script):")
    steps = []
    steps.append("Sort the repo's existing docs by audience: hub pages go in the "
                 "sidebar, the rest is turned away (SKILL.md, step 4).")
    if readme_new:
        steps.append("Write docs/README.md, the hub's home page, for end users.")
    steps.append("Add sidebar entries for the hub pages.")
    if not has_favicon:
        steps.append("Design docs/favicon.svg. It is the browser icon, the sidebar "
                     "logo, and the home page heading icon.")
    steps.append("Link the hub from the top of the root README once its URL resolves.")
    if ci_note:
        steps.append(f"CI: {ci_note}")
    if host == "github" and org and repo_name:
        steps.append("Turn on GitHub Pages with GitHub Actions as the source: "
                     f"https://github.com/{org}/{repo_name}/settings/pages")
    else:
        steps.append("Check Settings > Pages on GitLab once the pages job has run.")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")

    print()
    print("Preview locally:  just docs")


if __name__ == "__main__":
    main()
