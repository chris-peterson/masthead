# <img src="favicon.svg" alt="masthead" width="64" height="64" style="vertical-align: middle"> masthead

**Put your docs where readers can see them.**

A repo's docs usually live in its README and a few Markdown files nobody finds.
masthead stands up a documentation hub for the repo, with a deploy that
publishes it on every push, and keeps it current as the code moves. The person
who comes next gets one place to read how the thing works and what to watch out
for.

The hub runs on the docs engine you choose. docsify is the one engine today.

## Getting started

In a session inside the repo, run:

```text
/masthead:bootstrap
```

It writes the site under `docs/`, adds a deploy when the repo has no CI yet,
and goes through the docs you already have to decide which ones belong in the
hub. Pages written for maintainers or agents stay out, and you're told where
they belong. What it does step by step is on the
[bootstrap page](/skills/bootstrap).

## Keeping it current

A site keeps the template as it was on the day it was made. To bring it up to
date, run:

```text
/masthead:update-docs
```

It carries in the template's fixes and features, such as the page-contents
rail, while keeping the edits made to the site since. It also checks the sidebar
and pages against the practices docsify needs (one form per sidebar level,
links that resolve on the host, every page reachable) and proposes a fix for
each problem it finds. Nothing changes until you approve it. Details are on the
[update-docs page](/skills/update-docs).

> [!WARNING]
> Bootstrap stops rather than overwrite a docs site that already exists: one
> built by another tool, or a `docs/index.html` that's already there. Use
> `/masthead:update-docs` on an existing site. Bootstrap's `--force` replaces
> `docs/index.html` and drops any changes made to it.
>
> A site made before update-docs existed carries no stamp, so update-docs can't tell
> the template's changes from the site's own and shows them as one diff to
> sort through. Once updated, the site is stamped, and later updates sort the
> changes themselves.
