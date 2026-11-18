# Changelog

## Unreleased

### Added

- **`/masthead:docs` loads what masthead knows about your hub's docs engine.** Reach for it (typing `/docs` finds it) when working on a hub: writing pages and navigation that render, fixing the theme, adding a recipe, or tracing a defect back to the template. It finds the engine from the site's files, and hands standing up or updating a hub to the skills that do it.

### Changed

- **`/masthead:bootstrap` is now `/masthead:init-docs`**, pairing it with `/masthead:update-docs`. Its docsify script is now `init.py`.

## 0.3.0

### Added

- **`/masthead:update-docs` brings an existing hub up to date.** It carries the template's fixes and features into a site made earlier while keeping the edits made to the site since, and asks when both changed the same part. It also checks the sidebar and pages for the problems that break docsify sites: mixed sidebar forms, entries that share an href, sections on the home route, links that 404 on the host (including letter-case mismatches), relative links without `relativePath`, headings pushed into the sidebar, pages nothing links to, and a missing favicon. Each finding comes with the fix and the reasoning behind it, and nothing changes until you approve it.
- **A page-contents rail.** On a wide screen, each page lists its headings in a column on the right and highlights the one you're reading. Turn it off with `pageToc: false`.
- **Sites are stamped with the template they came from**, so the next update can tell the template's changes from the site's own.

### Changed

- **Bootstrap points at `/masthead:update-docs`** when `docs/index.html` already exists, instead of asking you to diff the template by hand.

## 0.2.0

### Added

- **GitLab branch previews.** With `--previews`, each branch's docs publish beside the live site under `preview-<branch-slug>/`, linked from the branch's merge request, and expire after a week. Needs GitLab Premium or Ultimate.
- **Site URLs for more repo shapes.** Bootstrap now prints the URL of a GitLab namespace site (`<group>/<group>.<pages-domain>`), says where a branch preview lands, and warns when the repo is a profile repo (`<owner>/<owner>`, `gitlab-profile`) whose README is a public profile.
- **`gitlab_pages.py` reads and sets a GitLab project's Pages domain.** `status` prints the site URL, whether the unique domain is on, and every deployment; `unique-domain off` serves the site at the predictable namespace URL instead of `<project>-<hash>.<pages-domain>`.

### Fixed

- **A change to only the spec now republishes the GitHub site.** The spec is copied into the site at build time, and the workflow didn't trigger on it.
- **No more guessed Pages URLs.** On GitHub Enterprise and GitLab project sites, bootstrap no longer prints a github.io URL or github.com settings link; it says where to read the real URL after the first deploy.

## 0.1.0

### Added

- **`/masthead:bootstrap` stands up a documentation hub for a repo.** On docsify, the one engine so far, it writes a site with a light and dark theme, search, syntax highlighting, and a copy button on every code block, plus a home page, a sidebar, and a `just docs` recipe to preview it. When the repo has no CI yet, it adds a workflow that publishes the site to GitHub Pages or GitLab Pages on every push; when it has CI, it shows you the job to add.
- **The hub holds pages for people who use the project.** Bootstrap goes through the docs the repo already has and asks of each one whether someone with no checkout could act on it. Build steps, release checklists, and agent instructions stay out, and you're told where each one belongs.
- **Turned-away pages are announced** as `content.routed`, so another plugin, such as cleat, can offer to put them where maintainers or agents will find them.
- **Bootstrap won't overwrite a site that already exists.** It stops when the repo's docs are built by another tool (MkDocs, Docusaurus, Sphinx, mdBook, or shipyard) or when `docs/index.html` is already there, and tells you what it found.
