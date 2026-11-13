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
  that engine into the engine-neutral bootstrap flow.
- **Audience**: who a piece of documentation is for: end users, maintainers,
  or agents. Decided by one test: could someone who only uses what the repo
  ships, with no checkout, act on it?
- **Routing**: turning content away from the hub and saying which audience it
  belongs to, without moving it.
- **Announcement**: a one-line interop event masthead publishes for sibling
  plugins to react to (`content.routed`).
- **Owner**: whatever already builds a repo's docs site, such as another engine,
  or shipyard for a plugin repo.

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
shall exit non-zero and write nothing.

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
An announcement shall be one stdout line, `codes.bridgeai.masthead/<entity>.<event>`
followed by a JSON body, so field values may hold spaces, quotes, and newlines.

#### `EVENTS-03`
If an announcement call is malformed or its body can't be encoded, then
`announce.sh` shall print nothing on stdout, explain on stderr, and exit 0.

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
`<owner>.github.io` user site, or a `docs/CNAME` domain), the scaffold shall
print it.

#### `PUBLISH-06`
Where the repo has a spec, the GitHub workflow the scaffold writes shall also
publish on a push that changes only the spec.

#### `PUBLISH-07`
Where `--previews` is passed for a GitLab repo, the `pages` job shall publish
each merge request's docs to a Pages parallel deployment under `mr-<iid>`,
linked from the merge request as an environment, that expires after a week while
the live site never expires.

#### `PUBLISH-08`
If `--previews` is passed for a GitHub repo, then the scaffold shall exit
non-zero, saying GitHub Pages has no built-in previews, and write nothing.

#### `PUBLISH-09`
When the hub is on GitLab, masthead shall offer merge request previews, and pass
`--previews` only after the user confirms the project is on a tier with parallel
deployments (Premium or Ultimate).

#### `PUBLISH-10`
If the hub's Pages URL can't be derived for certain (GitHub Enterprise, or any
GitLab), then the scaffold shall print no URL and say where to read the real one
after the first deploy, and masthead shall link the README only to a URL from
that source.

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
