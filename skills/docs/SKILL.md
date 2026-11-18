---
name: docs
description: This skill should be used when work touches a repo's documentation hub, such as "/masthead:docs", "/docs", "why is the docs sidebar doing this", "add a plugin to the docs site", "fix search on the docs site", "the docs theme fails contrast", "deep links land in the wrong place", or editing the site files or pages of a hub (a docsify `docs/index.html`, `docs/_sidebar.md`, and the pages it renders). Loads masthead's knowledge of the hub's docs engine (how its template is built and why, how to write links, pages, and navigation that render, recipes, and CI) and routes standing up or updating a hub to the skills that do it.
argument-hint: "[what you're working on]"
---

# Docs

masthead's knowledge of a documentation hub, for any work on one that exists:
writing pages, fixing the theme, adding a recipe, or working out why something
renders wrong. What applies depends on the hub's docs engine, so the engine's
reference carries the substance and this page finds it.

## Route the operations first

Two jobs belong to their own skills, which run the engine's scripts. Hand them
off rather than doing them by hand:

| The user wants | Use |
|----------------|-----|
| A hub for a repo that has none | `/masthead:init-docs` |
| An existing hub brought up to date with the template, or its navigation and pages checked | `/masthead:update-docs` |

Everything else is work on a hub that exists. Read on.

## Find the engine and read its reference

Tell the engine from the site's files, then start with its reference:

| Engine | Signs | Reference |
|--------|-------|-----------|
| docsify | `docs/index.html` loads docsify, or a shared loader that does; `docs/_sidebar.md` | [the docsify reference](../init-docs/references/docsify.md) |

A site on an engine masthead has no adapter for (MkDocs, Docusaurus, Sphinx,
mdBook) isn't masthead's to maintain; say so rather than applying one engine's
practices to another.

The engine's reference covers what every site gets, how links, pages, and
navigation must be written to render, and how to verify a site in a browser. It
ends with a list of the narrower pages (template notes, recipes, shared
loaders, CI, data-driven sites); read one when its situation applies, not
before.

## Fix upstream when the template is at fault

A defect in a generated site is a template defect until shown otherwise
([why](../init-docs/references/docsify.md#a-defect-in-a-generated-site-is-a-template-defect-until-shown-otherwise)).
Before working a fix out by hand, check whether the current template already
has it; if it does, `/masthead:update-docs` carries it in. If it doesn't, fix
the site and say the template needs the same fix, so the next site doesn't
start with the bug.
