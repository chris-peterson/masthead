---
name: update-docs
disable-model-invocation: true
description: This skill should be used when the user wants an existing documentation hub brought up to date, such as "/masthead:update-docs", "update the docs site", "this docsify site needs the latest fixes", "fix the sidebar on our docs", "add a table of contents to the docs", or "check the docs hub against best practices". Carries the engine template's fixes and features into a site made earlier (keeping the site's own edits), and reports where its sidebar and pages depart from the engine's practices, proposing a fix for each.
argument-hint: "[repo path]"
---

# Update docs

Bring a hub that already exists up to date. A site keeps the template as it was
on the day it was made. Since then the template may have gained fixes and
features, such as the page-contents rail, and the site's sidebar and pages may
have drifted from the practices the engine reference describes. This skill
finds both, shows the user each change, and applies only what they approve.

Use `/masthead:init-docs` instead when the repo has no hub yet.

## How this skill is split

As with init-docs, the engine's script does the mechanical work, and you
handle the judgment:

| Engine | Update script | Reference |
|--------|---------------|-----------|
| docsify | `skills/init-docs/scripts/docsify/update.py` | [the docsify reference](../init-docs/references/docsify.md) |

The script reports and never writes unless `--apply` is passed. It reports two
things:

- **Template drift.** It reads the template's values back out of
  `docs/index.html` (name, repo URL, host, Prism languages, Mermaid), renders
  the current template with them, and compares the two block by block. The
  template is split into named blocks by `masthead:block` marker comments, and
  every site masthead generates carries them, along with a stamp naming the
  template it came from.
- **Findings.** Each place the sidebar or pages depart from the reference, with
  a rule ID, file and line, and the reference section that explains it.

## 1. Run the report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/init-docs/scripts/docsify/update.py" [REPO_PATH] --diff
```

Pass `--docs DIR` when the site lives somewhere other than `docs/`. The script
stops when there's no docsify hub (point the user at `/masthead:init-docs`) and
when another tool builds the site (name the tool and stop: masthead doesn't
update a site it doesn't own).

If the user named something specific ("fix the sidebar", "turn on the TOC"),
start with the part of the report that covers it, but still show the rest.

## 2. Carry in the template's changes

What to do depends on whether the site carries a stamp the script recognizes.

### A stamped site: the blocks are classified

| Status | Meaning | What `--apply` does |
|--------|---------|---------------------|
| `upstream` | The template changed the block; the site's copy is untouched | Takes the template's |
| `added` | New in the template | Adds it where the template puts it |
| `removed` | Dropped from the template; the site's copy is untouched | Removes it |
| `local` | Someone edited the site; the template's copy is unchanged | Keeps the edit |
| `local-added` / `local-removed` | The site added or removed a block of its own | Leaves it that way |
| `conflict` | Both the site and the template changed it | Refuses until resolved |

Tell the user what each upstream change does for them in a sentence, so they
don't have to read CSS to understand it ("adds the page-contents rail beside
each page"). Local edits stay as they are without asking.

For each conflict, the report prints two diffs: what the template changed and
what the site changed. Show both, say what each side was trying to do, and ask
which to keep:

- **Keep the site's:** `--resolve <block>=site`. The template's change to that
  block is lost; say what it was.
- **Take the template's:** `--resolve <block>=template`. The site's edit is
  lost; say what it was.
- **Both:** take the template's, then re-apply the site's edit by hand, and
  show the result.

Once the user has approved the changes:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/init-docs/scripts/docsify/update.py" [REPO_PATH] --apply [--resolve <block>=site|template ...]
```

### An unstamped site: one unclassified diff

A site made before stamps existed, made by hand, or stamped by a newer masthead
than this one comes back as a single diff from the current template. Classify
each hunk yourself, reading it against
[the template notes](../init-docs/references/docsify-template.md):

- **A fix or feature the site lacks:** the template's side of the hunk matches
  a rule the notes explain, or it's a block the site doesn't have at all.
- **The site's own edit:** the site's side adds something the template never
  had, such as a project-specific color, an extra plugin, or a config option.

List the hunks for the user in those two groups. After they approve, replace
the file with the current template and re-apply each local edit by hand:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/init-docs/scripts/docsify/update.py" [REPO_PATH] --apply --adopt
```

The site is stamped now, so the next update classifies its blocks, and the
local edits you re-applied show up as `local`.

### A local edit that fixes the template

If a local edit fixes a defect the template still has, such as a contrast
failure, a layout bug, or a broken link behavior, the defect belongs to the
template. Keep the edit, and suggest opening an issue against masthead so the
fix reaches every site
([why](../init-docs/references/docsify.md#a-defect-in-a-generated-site-is-a-template-defect-until-shown-otherwise)).

## 3. Fix the findings

Propose a fix for each finding, with the reference section the report names.
Show the change before making it. Group findings that share a fix (several
sidebar entries with the same mistake) into one proposal.

| Rule | Finding | Usual fix |
|------|---------|-----------|
| `LINT-02` | A sidebar level mixes `**Section**` labels with linked sections | Pick one form for the level |
| `LINT-03` | Sibling entries share an href | Give each child its own href, often a `#anchor` into the parent page |
| `LINT-04` | A section links to `/?id=…` on the home route | Give the section its own index page |
| `LINT-05` | A link's target is missing, outside `docs/`, or differs in letter case | Fix the path or the file name, or publish the file under `docs/` |
| `LINT-06` | Relative links on a site without `relativePath: true` | Take the template's config (step 2), or make the links absolute |
| `LINT-07` | `subMaxLevel` puts page headings in the sidebar | Set it to `0`; the page-contents rail lists a page's headings |
| `LINT-08` | No sidebar entry reaches a page | Put it through the audience test first (below) |
| `LINT-09` | No `docs/favicon.svg` | Design one ([init-docs, step 7](../init-docs/SKILL.md)) |
| `LINT-10` | A sidebar entry written `[**X**](path)` | Move the bold outside the link: `**[X](path)**` |

A page no sidebar entry reaches isn't automatically a missing sidebar entry. Ask
of it what init-docs asks of every page: could someone who only uses what the
repo ships, with no checkout, act on it
([init-docs, step 4](../init-docs/SKILL.md))?
If yes, add it to the sidebar where a new reader needs it. If no, tell the user
where it belongs, and announce it so the plugin that places content for that
audience can pick it up:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/announce.sh" content.routed \
  tier=maintainer path=docs/<page>.md title="<Page title>" \
  reason="<Why it fails the audience test, in a sentence.>"
```

Don't move or delete the page yourself.

The script checks only what it can check without judgment. Look over the rest
the reference describes while you're in the files, and propose what applies:
lists a reader jumps between that should be headings
([structure pages as headings](../init-docs/references/docsify.md#structure-pages-as-headings)),
a home page without a quickstart or a warning callout
([init-docs, step 5](../init-docs/SKILL.md)), and a
sidebar out of the order a new reader needs.

## 4. Verify

Re-run the report. What's left should be local edits and any findings the user
chose to keep.

Then check the site in a browser, as init-docs does: serve it (`just docs`),
open every sidebar entry, since a docsify 404 renders inside a page that
loaded fine, and run the search and contrast checks
([verifying the site](../init-docs/references/docsify.md#verifying-the-site)).
After a template update, look at a long page on a wide window too: the rail
should list its headings and follow the scroll.

`--check` exits 1 while the template has moved on or any finding is open. A
repo that wants to know when its hub falls behind can run it in CI.

## 5. Summarize

End with what changed and what didn't:

- the template changes applied, in a phrase each,
- the local edits kept, and the conflicts with the side the user chose,
- the findings fixed,
- the findings left, each with the reason (the user declined, or it needs
  something only they can provide, such as a favicon design they want to make),
- pages turned away to another audience, and where they belong.
