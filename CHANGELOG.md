# Changelog

## 0.1.0

### Added

- **`/masthead:bootstrap` stands up a documentation hub for a repo.** On docsify, the one engine so far, it writes a site with a light and dark theme, search, syntax highlighting, and a copy button on every code block, plus a home page, a sidebar, and a `just docs` recipe to preview it. When the repo has no CI yet, it adds a workflow that publishes the site to GitHub Pages or GitLab Pages on every push; when it has CI, it shows you the job to add.
- **The hub holds pages for people who use the project.** Bootstrap goes through the docs the repo already has and asks of each one whether someone with no checkout could act on it. Build steps, release checklists, and agent instructions stay out, and you're told where each one belongs.
- **Turned-away pages are announced** as `content.routed`, so another plugin, such as cleat, can offer to put them where maintainers or agents will find them.
- **Bootstrap won't overwrite a site that already exists.** It stops when the repo's docs are built by another tool (MkDocs, Docusaurus, Sphinx, mdBook, or shipyard) or when `docs/index.html` is already there, and tells you what it found.
