# Data-driven sites

Read this when the hub's pages are generated from data rather than written by
hand: the two-stage pipeline, config as the seam between data and presentation,
why generated pages are never committed back, and the checklist for turning a
hand-edited page into a generated one.

Some hubs aren't authored, they're rendered from data: an access directory
generated from directory-service queries, an API reference generated from an
OpenAPI spec, a status page generated from scan results. If the answer to
"where does the content come from?" is anything other than "someone typed it,"
the conventions below apply. Otherwise skip this page.

## Two-stage pipeline

Split CI into a generate stage and a render-and-publish stage, with a checked
artifact between them:

```text
data source -> 1. generate report -> (YAML / JSON artifact) -> 2. render markdown + publish -> Pages
```

Stage 1 is the only stage that touches the data source or its credentials;
stage 2 reads the artifact alone. The split pays off twice: someone working on
presentation can re-render the site in seconds without re-querying, and the same
artifact can be linked from the site as a raw download, so users scripting
against the data don't have to scrape the rendered pages.

## Config as the seam between data and presentation

Raw data usually has gaps the rendered site needs filled: display labels,
groupings, overrides, entries marked as intentionally empty. Put them in a
version-controlled `config.yml` at the repo root, not in the renderer and not
patched into the data source.

| Lives in | What it holds |
|----------|---------------|
| Data source (directory, API, scan) | Ground truth that changes on its own schedule |
| `config.yml` | The bridge: labels, mappings, overrides, allow-listed entries |
| Renderer | Layout decisions only, never data and never naming |

The seam lets the site refuse to publish entries nobody has vetted (anything not
declared in `config.yml` is hidden), and turns "rename a label" or "fix a
miscategorized entry" into a one-line edit instead of a code change.

## No commit-back

Generated markdown lives only as a CI artifact and a gitignored local output.
The publish stage reads the generator's artifact directly, through `needs:` on
GitLab or `actions/upload-artifact` and `download-artifact` on GitHub. Don't
commit rendered files back to the repo: it fills git history with update noise
and turns every data refresh into a merge.

A `.gitignore` that allow-lists the static files instead of listing each
generated one:

```text
docs/*
!docs/favicon.svg
!docs/index.html
!docs/<static-page>.md
```

## Make the hand-edited vs. generated boundary explicit

The contract that keeps the repo maintainable is "this file is regenerated end
to end; don't edit it by hand." Without it, edits to generated files survive
until the next CI run and then disappear. If the repo has an `AGENTS.md` or
`CLAUDE.md`, put one table there listing every file under `docs/` and whether
it's generated or hand-maintained, with the entry-point function for changing
each generated page's shape. (That table is for agents and maintainers; it
doesn't belong in the hub.)

For the in-between case, pages that are mostly hand-written but need a few
generated values (a date, a count, a freshness line), keep the page as a
markdown file under `scripts/templates/` with `{{KEY}}` placeholders and have
the renderer do a substitution pass. The template stays editable as plain
markdown without touching the renderer.

## Escaping multi-line content in generated `<pre><code>`

docsify's markdown pass re-parses blank lines in literal `<pre><code>` bodies as
`<p>` and `<ul>`. In any generator that emits paste-ready blocks, escape
newlines as `&#10;` entities: `<pre>` preserves them, and `textContent` (what
the copy button reads) decodes them back to real newlines. The soft-wrap
behavior that goes with this is built into the template; see
[the template notes](docsify-template.md).

## Hand-edited to generated: migration checklist

Turning a static page into a generated one takes updates in four places at
once. Skip one and the repo is left half-finished, where the next reader can't
tell which file is the source of truth:

1. **The generator script's top-of-file comment:** what it produces and where
   the output lands.
2. **The `AGENTS.md` / `CLAUDE.md` boundary table:** flip the file's row from
   hand-maintained to generated, and note the entry-point function.
3. **The `.gitignore` allow-list:** remove the formerly hand-edited file so the
   generated copy stops being committed.
4. **Links into the page:** anchored `[Section](/path.md?id=...)` links that
   pointed at the static file may need to point at ids on the generated page.

The fourth is the one most often missed. Work through the whole list before
calling the migration done.
