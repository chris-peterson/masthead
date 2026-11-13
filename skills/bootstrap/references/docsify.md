# The docsify engine

What `/masthead:bootstrap` does on docsify, and what to know when writing pages
for a docsify hub. Read this after picking docsify as the engine.

A docsify hub is a single `docs/index.html` that renders the markdown files
beside it in the browser. There is no build step: the deploy publishes `docs/`
as it is.

## What the scaffold gives every site

- The Dracula dark theme with its Alucard light variant, and a day/night toggle
  that remembers the reader's choice and follows `prefers-color-scheme` until
  they make one.
- Prism syntax highlighting for the languages the repo uses.
- A copy button on every code block: a clipboard glyph that turns into a green
  check, then back.
- GitHub-style annotations (`> [!NOTE]`, `> [!WARNING]`, and so on).
- Full-text search, indexed from the rendered text rather than the raw markdown.
- A link back to the source repository on GitHub or GitLab.
- A CI workflow that publishes `docs/` to Pages, when the repo has no CI yet.

## The script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/scripts/docsify/bootstrap.py" [REPO_PATH] [flags]
```

`REPO_PATH` defaults to the current directory. The script checks that it's a
git repo, then scaffolds in place:

| Writes | When |
|--------|------|
| `docs/index.html` | Always, from `assets/docsify/index.html` with a handful of substitutions |
| `docs/_sidebar.md` | Only if missing: a `Home` entry, plus `Requirements` for a spec-driven repo |
| `docs/README.md` | Only if missing: a placeholder home page |
| a `docs` recipe in the justfile | Appended, or a new justfile; left alone if a `docs` recipe exists |
| a `docs/<spec>` line in `.gitignore` | Only for a spec-driven repo, and only when the copy isn't already ignored |
| `.github/workflows/deploy-docs.yml` or `.gitlab-ci.yml` | Only when the repo has no CI of its own |

It then prints a summary and a numbered list of follow-ups, which are the
judgment steps in SKILL.md.

| Flag | When |
|------|------|
| `--host github\|gitlab` and `--repo-url URL` | The remote isn't on GitHub or GitLab. Ask the user for the source URL and host first |
| `--name NAME` | The project name differs from the repo name |
| `--langs l1,l2,...` | Override the detected Prism language list |
| `--force` | Replace an existing `docs/index.html` with the current template |
| `--previews` | GitLab only: publish each merge request to its own Pages preview. Needs Premium or Ultimate; see [CI integration](ci-integration.md#merge-request-previews) |

The script fails rather than guessing. It stops when:

- **Another tool already builds the site:** a `plugin.yml` with a `docs:` block
  (shipyard renders those), `mkdocs.yml`, a Docusaurus config, `docs/conf.py`
  (Sphinx), or `book.toml` (mdBook). Tell the user which one and stop.
- **`docs/index.html` already exists.** It may be a site generated earlier from
  an older template, a hand-made one, or one that loads a
  [shared loader](docsify-shared-loader.md). Diff it against
  `assets/docsify/index.html` before deciding. `--force` replaces it, which
  drops any changes made to it since.
- **The host can't be detected** and wasn't passed.

## The template

`assets/docsify/index.html` is the whole site, and the script copies it
verbatim. It substitutes only the project name, the repo URL, the host's accent
color and corner logo, the Prism language tags, and the Mermaid script tags.
Everything else ships as it is: the palettes, the `light-dark()` theming, the
toggle, the sidebar layout and resize handle, the copy button, and the
soft-wrap rules.

Copying a real file is the point. A version of this skill that regenerated the
template from prose each time dropped or mangled CSS rules without anyone
noticing. Edit the template file itself; never retype it.

[The template notes](docsify-template.md) record why each rule exists. Read them
before changing a generated site's styles: every rule there fixes a bug that
has happened before. The constraints in short: WCAG 2.1 AA contrast on every
pairing, `light-dark()` for every themed value, and semantic color names only.

### A defect in a generated site is a template defect until shown otherwise

Every generated site inherits every decision in the template, so a theme bug in
one is rarely that site's own. Two signals point upstream, and both are cheap to
check before editing the target repo:

- **The user says it keeps happening.** "As usual, the new site has sidebar
  issues" is a diagnosis: the defect shows up in sites nobody wrote by hand.
- **A second generated site has it too.** Two copies that have drifted apart
  since they were made and still share the symptom settle the question.

When the defect is in the template, fix the site and open an issue against
masthead, so the fix isn't worked out again by hand in each repo.

**The fix may already be in the template.** A site keeps the template as it was
on the day it was made. Before working out new colors for an older site, diff
its palette block and element rules against the current template. On one older
site, six contrast failures were all already fixed upstream.

**Comments that contradict each other point at the template.** One version of
it set `--sidebar-padding: 0` with a reason in one place and, a few hundred
lines later, warned that zeroing it broke the search input and the nav
indentation. When the template argues with itself, fix the template.

## Writing links

The template sets `relativePath: true`, so a relative link resolves against the
current page, the way a repo checkout and the forge's own markdown view resolve
it. One relative link then works in all three places.

- **docsify's own default is `relativePath: false`**, which resolves relative
  links from the site root. On a site that leaves it unset, a sibling link
  `[setup](setup)` on `/guides/` goes to `#/setup` and 404s, while the
  sidebar's absolute links to the same page work. When adopting an existing
  site, either set the flag or make every link absolute. A mix is what breaks.
- **Images don't follow the flag.** docsify always resolves an image against the
  page's own directory, so `![…](diagram.png)` beside the page is correct under
  either setting.

### Pages rendered from somewhere else

If a build renders sources into `docs/` (say `guides/setup.md` to
`docs/setup.md`), the page moves, and a link the source wrote correctly as
`../images/x.png` now points one level too far. No `relativePath` value fixes
that. Have the build record each source's published path and rewrite links to
match, and check that every linked file is published at all.

### Match file names case-exactly

macOS and Windows resolve `SPEC.md` when asked for `spec.md`; GitHub Pages and
GitLab Pages don't. A link checker that asks the local filesystem can't see the
one bug class that only shows up on the host. Compare names case-exactly in the
checker itself.

## Structure pages as headings

Headings are the only page content docsify turns into navigation. Each `##` and
`###` gets a `?id=` share link, a row in the page-contents rail, its own search
entry, and a sidebar sub-entry where `subMaxLevel` reaches it. A table row, a
list item, or a bold lead-in gets none of those.

When a page lists things a reader will jump between or link to (commands,
options, FAQ entries), give each one a heading with its detail beneath:

````markdown
<!-- Invisible to the rail, search, and share links -->
| Command | What it does |
|---------|--------------|
| `foo sync` | Pulls the latest config |
| `foo prune` | Removes stale entries |

<!-- Each item navigable -->
## `foo sync`

Pulls the latest config.

## `foo prune`

Removes stale entries.
````

A table still earns its place for comparisons read across a row, and as a
summary above the headings with each first cell linking to its heading.

A heading whose text is itself a link (the usual catalog entry) and pages that
repeat the same sub-heading under each item both need care; see
[the recipes](docsify-recipes.md).

## Sidebar structure

The script seeds a minimal sidebar. Building it out is judgment, and it lists
only hub pages (SKILL.md, step 4).

### Pick one form per level: `**Section**` or `[Section](path)`

The two render as different kinds of thing, so mixing them at one level reads
as a distinction even when none was meant.

| Markdown | Renders as | Expands |
|----------|------------|---------|
| `- **Section**` | Uppercase label with a rule under it | No |
| `- [Section](/path.md)` with children | A folder link with a chevron | Yes |
| `- [Page](/path.md)` with no children | A leaf link | n/a |

The one mix that works: `**Section**` for groups shown inline, plus a top-level
`[Section](/section/)` with no children for a section whose contents live on
its own index page.

### Give every entry its own href

When a parent link has children, every entry needs a distinct href, or docsify
merges them into one item and draws a stray chevron on a leaf:

```markdown
- [Access](/users.md)
  - [Users](/users.md#users)
  - [Request access](https://example.com/request)
```

The template sets `subMaxLevel: 0`, so docsify doesn't add the page's own H1 as
a phantom child of its sidebar entry.

### Long lists get an index page

For a section with too many children to show inline, give it
`docs/section/README.md` and one top-level `[Section](/section/)` link with no
children. Pointing a section at `/?id=foo` instead makes it expand on every
visit to the home page, since it shares the home route's path.

### A clickable section header fights the collapse plugin

A header that is a label, a link, and a collapsible parent at once runs into
each layer in turn: `[**X**](path)` loses the section styling (use
`**[X](path)**`), the nav anchor's padding indents it, and one click both
navigates and collapses. On a small sidebar, consider dropping
`docsify-sidebar-collapse` instead: then `**[X](path)**` is a static header that
navigates. Sites that work pick one: no collapse plugin and flat links, or the
plugin with top-level page links whose children are anchors into that page.

## Spec-driven repos

Some repos keep a `SPEC.md` at the root, a numbered requirements list that spec
tools (such as sextant's) read from there. The script detects `SPEC.md`,
`spec.md`, or `SPECIFICATION.md`, adds `- [Requirements](/<file>)` as the last
sidebar entry, and adds a copy step to the justfile recipe and the CI it writes.
The spec stays at the root and the deploy copies it into `docs/` at build time;
the script ignores that copy in `.gitignore`, and the GitHub workflow it writes
triggers on a change to the spec as well as to `docs/`. If you wire the deploy
into existing CI by hand, add the copy step and the spec's path there too.

## Annotations

The template loads `docsify-plugin-flexible-alerts`, colored for both themes:

```markdown
> [!NOTE]
> Informational callout

> [!TIP]
> Helpful advice

> [!IMPORTANT]
> Key information

> [!WARNING]
> Something to watch out for

> [!CAUTION]
> A dangerous action or consequence
```

`WARNING` and `CAUTION` are where a hub records what to watch out for.

## Embedding source files

docsify can embed and highlight a file from the repo:

```markdown
[example.py](../examples/example.py ':include :type=code python')
```

The path is relative to the current page, and the file has to be published
under `docs/` for the deployed site to reach it.

## Mermaid

The script keeps the Mermaid CDN only when a tracked `.md` file has a
` ```mermaid ` block. To call out a node, write `class <node> highlight` and let
the template color it in both themes. A `style <node> fill:<hex>` line has one
color for both themes and leaves dark-mode labels unreadable on it.

## Verifying the site

A docsify 404 is not an HTTP 404: the router renders its own not-found page
inside a page that returned 200, so a status-code sweep calls every dead link
healthy. `curl` proves a file exists; only driving the router in a browser
proves a link resolves.

Two checks ship with the engine. Each is one async function: pass the file's
contents to Playwright's `browser_evaluate` (or `page.evaluate()`) on any page
of the served site. Each is clean when its `problems` list is empty.

- **`scripts/docsify/check-search.js`** searches for every heading on every
  sidebar page and reports results showing raw markup, results linking to ids
  that don't exist, and headings search can't find. Run it after changing
  search config or a page that uses raw HTML; a few hand-typed queries miss
  what it finds.
- **`scripts/docsify/check-contrast.js`** visits every sidebar page in both
  themes and reports text below WCAG AA, Mermaid labels against their fills,
  and controls under 3:1. Run it after changing the template's colors or any
  rule with a broad selector. Reading the CSS misses plugin-injected colors.

Serve the site with a cache-busting query (`/?v=<n>#/`): a browser holding the
old `index.html` checks the old CSS.

Don't bind `/` or any other bare key to focus search. Browsers and extensions
use those keys, and the search box is always visible.

## More

- [Template notes](docsify-template.md): why each CSS rule and constraint exists.
- [Recipes](docsify-recipes.md): small JS patterns to add when a site needs them.
- [Shared loader](docsify-shared-loader.md): several sites sharing one loader.
- [CI integration](ci-integration.md): adding the deploy to an existing pipeline.
- [Data-driven sites](data-driven-sites.md): pages generated from data.
