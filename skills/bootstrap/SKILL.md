---
name: bootstrap
disable-model-invocation: true
description: This skill should be used when the user wants a documentation hub for a repo, such as "/masthead:bootstrap", "set up a docs site for this repo", "give this project a pages site", "bootstrap docsify here", "publish these docs to GitHub Pages", or "add a docs hub". Scaffolds the hub on the docs engine the user picks (docsify today) with a home page, navigation, search, and a deploy that publishes it on every push, then sorts the repo's existing docs by audience so only end-user pages go in it.
argument-hint: "[repo path] [engine]"
---

# Bootstrap

Stand up a documentation hub for a repo: a site for the people who use what the
repo ships, with a deploy that publishes it on every push.

The hub runs on a docs engine, and the engine is an adapter. The steps below are
the same on any engine; what each engine needs is in its own reference. docsify
is the one engine today.

## How this skill is split

The mechanical scaffold is done by a script; the judgment stays with you.

- **The engine's script** detects what it can (host, default branch, languages,
  diagrams, a spec), writes the site from the engine's template, seeds a home
  page and sidebar, adds a preview recipe, and writes a deploy workflow when the
  repo has none. It ends by printing the follow-ups that need judgment.
- **This page** covers what a script can't decide: what belongs in the hub, the
  home page, the navigation, the icon, and wiring the deploy into CI that
  already exists.
- **`references/`** holds the material for one engine or one situation. Read a
  page when it applies, not before.

| Engine | Script | Template | Reference |
|--------|--------|----------|-----------|
| docsify | `scripts/docsify/bootstrap.py` | `assets/docsify/index.html` | [references/docsify.md](references/docsify.md) |

A new engine adds a row: a script under `scripts/<engine>/` that takes the same
inputs (repo path, `--name`, `--host`, `--repo-url`) and ends with the same
summary and follow-ups, a template under `assets/<engine>/`, and a reference
page. Nothing on this page changes.

## 1. Pick the engine

Use the engine named in the arguments. With none named, use docsify and say so
in your summary, so the user knows a choice was made.

If the user names an engine masthead has no adapter for (MkDocs, Docusaurus,
mdBook, a wiki), say so and stop. Don't scaffold it by hand: a hand-made site
gets none of the fixes the template carries, and the next run of this skill
can't maintain it.

## 2. Check that nobody else owns the site

A repo should have one docs site. Before running anything, look for one that
already exists:

- **Another engine's config** (`mkdocs.yml`, `docusaurus.config.*`,
  `docs/conf.py`, `book.toml`): the repo already has a site. Ask whether the
  user wants to replace it; masthead doesn't run two side by side.
- **A `plugin.yml` with a `docs:` block:** a Claude Code plugin whose site
  shipyard renders (`shipyard build-docs`). Its `docs/index.html` is generated,
  so stop and point the user at shipyard.
- **An existing `docs/index.html`:** a site already made, perhaps from an older
  template, perhaps loading a [shared loader](references/docsify-shared-loader.md).
  Diff it against the template before deciding anything.

The docsify script checks all of these and refuses rather than overwriting.

## 3. Run the scaffold

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/scripts/docsify/bootstrap.py" [REPO_PATH] [flags]
```

The flags and what each file holds are in
[the docsify reference](references/docsify.md#the-script). If the script stops
because it can't tell the host, ask the user where the source lives and re-run
with `--host` and `--repo-url`; don't guess.

On GitLab, offer merge request previews: each MR's docs published beside the
live site. Pass `--previews` only once the user confirms the project is on
Premium or Ultimate, since previews need GitLab's parallel deployments
([why that matters](references/ci-integration.md#merge-request-previews)).

Read the summary and the follow-ups it prints. The steps below are those
follow-ups.

## 4. Sort the existing docs by audience

A repo's documentation has three audiences, and the hub is for one of them
([who the hub is for](../../docs/audiences.md)):

| Audience | Where their docs live |
|----------|-----------------------|
| End users: people using what the repo ships | the hub |
| Maintainers: people changing the repo | `README.md`, `CONTRIBUTING.md` |
| Agents: AI tools working in the repo | `AGENTS.md`, `CLAUDE.md`, rules, skills |

Go through the markdown the repo already has (`docs/*.md` first, then guides
and other top-level pages) and ask of each page: **could someone who only uses
what this repo ships, with no checkout, act on this?**

- **Yes:** it's a hub page. It goes in the sidebar (step 6).
- **No, and it already lives where its audience looks** (build steps in the
  root README, conventions in `AGENTS.md`): leave it there. It isn't hub
  material and nothing needs to move.
- **No, and it sits where the hub would publish it** (a release checklist in
  `docs/`, a page that only makes sense with links into the source): keep it
  out of the sidebar, tell the user where it belongs, and announce it so a
  plugin that places content for that audience can pick it up:

  ```bash
  bash "${CLAUDE_PLUGIN_ROOT}/scripts/announce.sh" content.routed \
    tier=maintainer path=docs/releasing.md title="Releasing" \
    reason="Release steps need a checkout, so they belong with the maintainers."
  ```

  One announcement per page turned away. `tier` is `maintainer` or `agent`.
  Don't move or delete the page yourself: say where it belongs and let the user
  decide.

A page that is mostly for end users with a maintainer section in it stays in the
hub; suggest moving that section out rather than turning the page away.

## 5. Write the home page

`docs/README.md` is the hub's front door, for end users. Replace the seed with:

- one paragraph on what the project is and why someone would use it,
- a quickstart: the shortest path from "never heard of this" to "it's working,"
- links into the deeper pages,
- what to watch out for: what surprises people, what fails quietly, what to
  check before relying on it. A `> [!WARNING]` callout is the place for it.

Build steps, repo layout, and contribution flow stay out; that's the root
README's job. A one-line pitch or a screenshot can appear in both.

The home page heading carries the icon (step 7):

```markdown
# <img src="favicon.svg" alt="project-name" width="64" height="64" style="vertical-align: middle"> Project name
```

## 6. Build the navigation

Add a sidebar entry for each hub page from step 4, in the order a new reader
needs them. The seed holds only `Home` (and `Requirements` for a spec-driven
repo, which stays last). How to group and nest entries without tripping
docsify's quirks is in
[the docsify reference](references/docsify.md#sidebar-structure).

## 7. Design the icon

`docs/favicon.svg` is a small SVG made for this project. On docsify it is the
browser icon, the sidebar logo beside the site name, and the home page heading
icon, so it's the one image to design. Make it say something about what the
project does, and draw it in the template's palette: `#282a36` background,
`#50fa7b` green, `#bd93f9` purple, `#ff79c6` pink, `#8be9fd` cyan.

## 8. Link the hub from the root README

Put a docs link directly under the root README's title, before any build or dev
content:

```markdown
# Project name

**[Read the docs](https://owner.github.io/project/)**
```

Take the URL from a reliable source, never by building one from the remote: the
script's `Expected URL` when it printed one, otherwise the host's Pages settings
or the deploy's own output (`$CI_PAGES_URL` on GitLab) after the first deploy.
The script prints no URL when it can't be sure, as on GitHub Enterprise or any
GitLab, which may give a project a unique domain.

Check that the URL resolves before writing it. A hash-routed site can live at
`/<repo>/`, `/<repo>/#/`, or a subpath, and a wrong link is worse than none:

```bash
curl -sI -o /dev/null -w "%{http_code}\n" https://owner.github.io/project/
```

Before the first deploy it won't resolve yet. Say so, and leave the link for
after the deploy rather than guessing.

## 9. Wire the deploy

When the repo had no CI, the script wrote a standalone workflow; nothing more to
do there. When it already had a workflow, the script left it alone and printed
a note. Add the publish job to the existing pipeline by hand, following
[CI integration](references/ci-integration.md).

Either way, Pages needs turning on once per repo. On GitHub the script prints
the settings URL; tell the user to set the source to GitHub Actions.

## 10. Preview and verify

`just docs` serves the site locally. Open it and click through every sidebar
entry. A docsify 404 renders inside a page that loaded fine, so a dead link
doesn't show up as an error anywhere else. Then run the search and contrast
checks described in
[the docsify reference](references/docsify.md#verifying-the-site).

End with a short summary for the user: the engine used, what was written, which
pages went in the hub and which were turned away (and where they belong), and
anything left for them, such as turning on Pages.

## When the hub needs changes later

- **Pages generated from data** (a reference built from a spec, a status page
  from scan results): [data-driven sites](references/data-driven-sites.md).
- **A small JS behavior** (deep-link fixes, copy buttons on values, row anchors):
  [docsify recipes](references/docsify-recipes.md).
- **A theme or layout bug:** treat it as a template defect until shown
  otherwise; see [the docsify reference](references/docsify.md#a-defect-in-a-generated-site-is-a-template-defect-until-shown-otherwise)
  and [the template notes](references/docsify-template.md).
- **Several repos sharing one look:**
  [shared loader](references/docsify-shared-loader.md).
