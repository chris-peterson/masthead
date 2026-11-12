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

> [!WARNING]
> Bootstrap stops rather than overwrite a docs site that already exists: one
> built by another tool, or a `docs/index.html` that's already there. Read what
> it reports before passing `--force`, which replaces `docs/index.html` and any
> changes made to it.
