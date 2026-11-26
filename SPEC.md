# masthead specification

masthead stands up a documentation hub for a repo on a docs engine chosen
through an adapter, publishes it on every push, and keeps only end-user content
in it. Anything meant for maintainers or agents is announced and pointed
elsewhere.

Requirements use [EARS syntax](https://alistairmavin.com/ears). Each is one of:
Ubiquitous (`The <system> shall …`), State-Driven (`While …`), Event-Driven
(`When …`), Optional (`Where …`), or Unwanted Behaviour (`If … then …`).

Each requirement is its own heading carrying a stable ID (`XX-NN`), one level
below its category's heading, so every requirement has a linkable anchor
(`SPEC.md#xx-nn`). Lettered decompositions (`XX-NNa`) each count as one.

## Concepts

- **Hub**: the documentation site for the people who use what the repo ships.
- **Engine**: the tool that renders the hub (docsify today).
- **Adapter**: one engine's script, template, and reference page, which plug
  that engine into the engine-neutral init-docs flow.
- **Audience**: who a piece of documentation is for: end users, maintainers,
  or agents. Decided by one test: could someone who only uses what the repo
  ships, with no checkout, act on it?
- **Routing**: turning content away from the hub and saying which audience it
  belongs to, without moving it.
- **Announcement**: a one-line interop event masthead publishes for sibling
  plugins to react to (`content.routed`).
- **Owner**: whatever already builds a repo's docs site, such as another engine,
  or shipyard for a plugin repo.
- **Stamp**: the masthead version a site's template came from, recorded in the
  site itself.
- **Upstream change**: a difference between a site and the current template
  that comes from the template having changed since the site was made.
- **Local edit**: a difference that comes from someone changing the site.
- **Finding**: one place where a hub departs from a practice its engine's
  reference describes, with a rule ID and a pointer to that reference.

## Requirements

### `ENGINE`
Engine adapters

#### `ENGINE-01`
Where the user names an engine, masthead shall scaffold the hub with that
engine's adapter.

#### `ENGINE-02`
When no engine is named, masthead shall use docsify and say in its summary that
it chose it.

#### `ENGINE-03`
If the user names an engine masthead has no adapter for, then masthead shall say
so and stop without scaffolding a site by hand.

#### `ENGINE-04`
Each engine adapter shall provide a scaffold script that takes the repo path,
`--name`, `--host`, and `--repo-url`, a site template, and a reference page, and
its script shall end with a summary and a list of follow-ups.

### `SCAFFOLD`
Hub scaffold

#### `SCAFFOLD-01`
If the target path is not a git repository, then the scaffold shall exit
non-zero.

#### `SCAFFOLD-02`
If another tool already builds the repo's docs site (an MkDocs, Docusaurus,
Sphinx, or mdBook config, or a `plugin.yml` with a `docs:` block), then the
scaffold shall exit non-zero naming that tool and write nothing.

#### `SCAFFOLD-03`
If `docs/index.html` exists and `--force` was not passed, then the scaffold
shall exit non-zero, name `/masthead:update-docs` as the way to bring the site
current, and write nothing.

#### `SCAFFOLD-04`
If the source host can't be told from the origin remote and wasn't passed, then
the scaffold shall exit non-zero asking for `--host` and `--repo-url`.

#### `SCAFFOLD-05`
The scaffold shall write `docs/index.html` from the engine's template, and if
any template placeholder is left unfilled, then it shall exit non-zero.

#### `SCAFFOLD-06`
The generated site shall use the Dracula dark theme with its Alucard light
variant, with a day/night toggle that follows `prefers-color-scheme` until the
reader picks one and remembers the pick.

#### `SCAFFOLD-07`
The generated site shall provide full-text search, a copy button on every code
block, GitHub-style annotations, and a link to the source repo (a GitLab logo on
GitLab).

#### `SCAFFOLD-08`
The scaffold shall highlight bash, yaml, and the languages of the repo's tracked
files, unless `--langs` names the set.

#### `SCAFFOLD-09`
Where the repo's markdown contains a mermaid block, the generated site shall
load Mermaid; otherwise it shall omit it.

#### `SCAFFOLD-10`
Where `--name` is passed, the scaffold shall use it as the site's display name
and keep the repo's own name in URLs.

#### `SCAFFOLD-11`
The scaffold shall seed `docs/_sidebar.md` and `docs/README.md` only when they
don't exist.

#### `SCAFFOLD-12`
The scaffold shall add a `docs` preview recipe to the justfile, creating the
justfile if there is none, and leave an existing `docs` recipe unchanged.

#### `SCAFFOLD-13`
Where the repo root holds `SPEC.md`, `spec.md`, or `SPECIFICATION.md`
(case-exact), the scaffold shall add a Requirements entry last in the sidebar
and copy the spec into `docs/` in the preview recipe and the deploy it writes.

#### `SCAFFOLD-14`
When the scaffold finishes, it shall print the files it wrote, the detected
host, branch, languages, Mermaid use, and spec, whether a favicon exists, and
the follow-ups left to judgment.

#### `SCAFFOLD-15`
Where the scaffold copies a spec into `docs/`, it shall add that copy to the
repo's `.gitignore` unless git already ignores it.

#### `SCAFFOLD-16`
The scaffold shall stamp the site it writes with the masthead version and a
fingerprint of the template it came from (on docsify, `<meta name="generator"
content="masthead <semver>; template <fingerprint>">` in `docs/index.html`).

#### `SCAFFOLD-17`
The generated site shall show a page-contents rail listing the current page's
headings, built from each heading's id and text, indented by nesting, and
highlighting the section being read.

### `AUDIENCE`
Audience routing

#### `AUDIENCE-01`
When bootstrapping, masthead shall ask of each existing markdown page whether
someone who only uses what the repo ships, with no checkout, could act on it.

#### `AUDIENCE-02`
When a page passes that test, masthead shall treat it as a hub page.

#### `AUDIENCE-03`
If a page fails that test and already lives where its audience looks, then
masthead shall leave it where it is.

#### `AUDIENCE-04`
If a page fails that test and sits where the hub would publish it, then masthead
shall keep it out of the sidebar and tell the user which audience it belongs to.

#### `AUDIENCE-05`
masthead shall not move or delete a page it turns away.

#### `AUDIENCE-06`
When a page is mostly for end users but holds a maintainer section, masthead
shall keep it in the hub and suggest moving that section out.

### `EVENTS`
Interop announcements

#### `EVENTS-01`
When masthead turns a page away, it shall publish one `content.routed`
announcement for it, carrying `tier` (`agent` or `maintainer`), `path`, `title`
where there is one, and `reason`.

#### `EVENTS-02`
An announcement shall be the line bridge.ai WIRE-01..05 define
([SPEC.md](https://github.com/chris-peterson/claude-marketplace/blob/main/SPEC.md)),
under the `masthead` namespace, so field values may hold spaces, quotes, and
newlines.

#### `EVENTS-03`
`announce.sh` shall be the publisher script of bridge.ai EMIT-06 and EMIT-07: a
malformed call prints nothing on stdout, explains on stderr, and exits 0.

### `CONTENT`
Hub content

#### `CONTENT-01`
masthead shall write the home page for end users: what the project is and why
someone would use it, a quickstart, links to deeper pages, and a warning callout
on what to watch out for, with no build or contribution content.

#### `CONTENT-02`
masthead shall order the sidebar in the order a new reader needs it, with
Requirements last.

#### `CONTENT-03`
masthead shall design a project-specific `docs/favicon.svg` in the template's
palette, used as the browser icon, sidebar logo, and home page heading icon.

#### `CONTENT-04`
When the hub's URL resolves, masthead shall link it directly under the root
README's title; while it doesn't, masthead shall leave the link for after the
first deploy.

### `PUBLISH`
Publishing

#### `PUBLISH-01`
While a GitHub repo has no workflow, the scaffold shall write one that publishes
`docs/` to Pages through Actions on a push to the default branch and on manual
dispatch.

#### `PUBLISH-02`
While a GitLab repo has no `.gitlab-ci.yml`, the scaffold shall write a `pages`
job that publishes `docs/` from the default branch.

#### `PUBLISH-03`
If CI already exists, then the scaffold shall leave it unchanged and print the
job to add, and masthead shall wire the publish job into the existing pipeline.

#### `PUBLISH-04`
masthead shall tell the user the one-time Pages setting each host needs, with
the settings URL on GitHub.

#### `PUBLISH-05`
Where the hub's Pages URL follows from the remote (a github.com repo, its
`<owner>.github.io` user site, a `docs/CNAME` domain, or a top-level GitLab
project named `<namespace>.<pages-domain>`), the scaffold shall print it, at
the domain's root for a user or namespace site.

#### `PUBLISH-06`
Where the repo has a spec, the GitHub workflow the scaffold writes shall also
publish on a push that changes only the spec.

#### `PUBLISH-07`
Where `--previews` is passed for a GitLab repo, the `pages` job shall publish
each non-default branch's docs to a Pages parallel deployment under
`preview-<branch-slug>`, as a `preview/<branch-slug>` environment, that expires
after a week while
the live site never expires.

#### `PUBLISH-08`
If `--previews` is passed for a GitHub repo, then the scaffold shall exit
non-zero, saying GitHub Pages has no built-in previews, and write nothing.

#### `PUBLISH-09`
When the hub is on GitLab, masthead shall offer branch previews, and pass
`--previews` only after the user confirms the project is on a tier with parallel
deployments (Premium or Ultimate).

#### `PUBLISH-10`
If the hub's Pages URL can't be derived for certain (GitHub Enterprise, or a
GitLab project that isn't a namespace site), then the scaffold shall print no URL and say where to read the real one
after the first deploy, and masthead shall link the README only to a URL from
that source.

#### `PUBLISH-11`
Where `--previews` is passed, the scaffold shall say where a branch's preview
lands (the site URL plus `preview-<branch-slug>/` when the site URL is known)
and name the preview's environment link as the URL to trust.

#### `PUBLISH-12`
If the repo is a profile repo (`<owner>/<owner>`, or `<group>/gitlab-profile`
on GitLab), then the scaffold shall say which profile page its README renders
on, and masthead shall confirm with the user before linking the hub under that
README's title.

#### `PUBLISH-13`
When the hub is on GitLab, masthead shall ask whether the site keeps GitLab's
unique domain or is served at the namespace URL, and turn the unique domain off
(`gitlab_pages.py unique-domain off`) only after the user says to.

#### `PUBLISH-14`
`gitlab_pages.py status` shall print the site URL, whether the unique domain is
on, and each deployment's URL and path prefix, reading the project and host from
the origin remote unless `--project` and `--hostname` are passed; if GitLab
refuses a change, then it shall exit non-zero naming the role the change needs.

### `CHECK`
Site checks

#### `CHECK-01`
Before reporting done, masthead shall serve the site and open every sidebar
entry, since a docsify 404 renders inside a page that returned 200.

#### `CHECK-02`
The docsify adapter shall provide a search check that reports results showing
raw markup, results linking to ids that don't exist, and headings search can't
find.

#### `CHECK-03`
The docsify adapter shall provide a contrast check that reports, in both themes,
text below WCAG AA, Mermaid labels against their fills, and controls under 3:1.

#### `CHECK-04`
When bootstrapping ends, masthead shall summarize the engine, the files written,
the pages put in the hub, the pages turned away and where they belong, and what
is left for the user.

### `MAINTAIN`
Keeping the hub current

#### `MAINTAIN-01`
Where `--force` is passed, the scaffold shall replace `docs/index.html` with the
current template and leave the sidebar, home page, preview recipe, and CI
unchanged.

#### `MAINTAIN-02`
If a generated site shows a theme or layout defect, then masthead shall treat it
as a defect in the engine's template until shown otherwise.

### `UPDATE`
Updating an existing hub (`/masthead:update-docs`)

#### `UPDATE-01`
If the repo has no hub one of masthead's adapters recognizes, then
`/masthead:update-docs` shall say so, point at `/masthead:init-docs`, and write
nothing.

#### `UPDATE-02`
If another tool already builds the repo's docs site (the owners `SCAFFOLD-02`
names), then `/masthead:update-docs` shall name that tool and write nothing.

#### `UPDATE-03`
Each engine adapter shall provide an update script that reads the template's
substitution values back out of the existing site, renders the current template
with them, and reports how the site differs from it, writing nothing unless
`--apply` is passed.

#### `UPDATE-04`
Where the site carries a stamp, the update script shall classify each difference
from the current template as an upstream change or a local edit.

#### `UPDATE-05`
If the site carries no stamp, then the update script shall report every
difference unclassified, and masthead shall classify them by reading the
template notes before proposing any change.

#### `UPDATE-06`
When applying a template update, masthead shall carry every upstream change into
the site and keep every local edit, and if one part of the site holds both, then
it shall show the user both versions and ask which to keep.

#### `UPDATE-07`
When the update script writes the current template into a site, it shall stamp
the site with the current masthead version.

#### `UPDATE-08`
Where `--check` is passed, the update script shall exit non-zero when it reports
any upstream change or finding, so CI can catch a hub falling behind.

#### `UPDATE-09`
When the update script reports a page no sidebar entry reaches (`LINT-08`),
masthead shall put it through the audience test (`AUDIENCE-01` to
`AUDIENCE-06`) before adding it to the sidebar.

#### `UPDATE-10`
masthead shall show each change it proposes and apply none until the user
approves it.

#### `UPDATE-11`
Before reporting done, `/masthead:update-docs` shall run the site checks
(`CHECK-01` to `CHECK-03`).

#### `UPDATE-12`
When `/masthead:update-docs` ends, masthead shall summarize the upstream changes
applied, the local edits kept, the findings fixed, and the findings left, each
with the reason it was left.

### `LINT`
Hub checks (the findings `/masthead:update-docs` reports)

#### `LINT-01`
The update script shall check the hub's sidebar and pages and report each
finding with its rule ID, file, line, and the reference section that explains
the practice.

#### `LINT-02`
The docsify update script shall report a sidebar level that mixes `**Section**`
labels with linked sections.

#### `LINT-03`
The docsify update script shall report sibling sidebar entries under a linked
parent that share an href.

#### `LINT-04`
The docsify update script shall report a sidebar section that links to the home
route with an `?id=` anchor.

#### `LINT-05`
The docsify update script shall report a sidebar entry or page link whose target
doesn't exist, or exists only under a different letter case.

#### `LINT-06`
The docsify update script shall report a page with a relative sibling link on a
site that doesn't set `relativePath: true`.

#### `LINT-07`
The docsify update script shall report a site whose `subMaxLevel` adds pages'
headings as sidebar children.

#### `LINT-08`
The docsify update script shall report a markdown page under `docs/` that no
sidebar entry reaches.

#### `LINT-09`
The docsify update script shall report a site with no `docs/favicon.svg`.
