# A family of sites behind a shared loader

Read this when several repos' docs sites should share one look: one titlebar,
one theme, one set of fixes, loaded from a central site instead of each repo
carrying its own copy of the template.

That is a different shape from what `/masthead:bootstrap` scaffolds. The
standalone template copies the whole site into each repo, so each site keeps the
template as it was the day it was made. A shared loader keeps one script on a
central site, and each repo's `docs/index.html` is a few lines that load it:

- `docs/index.html` loads the loader script from the central site and calls an
  init function with the per-project values (name, code languages, Mermaid).
- The central site keeps a list of projects for its cross-site navigation, and
  each project's favicon stays in its own `docs/favicon.svg`.
- A fix to the theme or a plugin lands once, in the loader, and every site picks
  it up on the next page load.

For a worked public example, the author's own sites (chris-peterson.github.io)
run this way: each project's `index.html` loads `js/docsify-shared.js` from the
central site and calls `initProject({ name, code_languages })`.

Don't run the scaffold script in a repo that already loads a shared loader: it
refuses to replace an existing `docs/index.html` without `--force`, and with it
would swap the loader for a standalone copy. Add the project to the central
site's list and write its pages; everything below is about building and
maintaining the loader itself.

## Local preview

`just docs` serves `docs/` locally. The shared script handles theme, titlebar,
and CSS loading, so no local CSS files are needed.

The loader's `cssOrigin` logic determines where CSS is fetched from. The correct behavior is:

```javascript
var cssOrigin = window.location.origin === CENTRAL_ORIGIN ? '' : CENTRAL_ORIGIN;
```

Only the central site itself uses relative paths (empty `cssOrigin`). Every other origin, localhost included, fetches CSS from the central site. If localhost is incorrectly treated as a local origin, local preview will lack theming and visual treatment because `/css/theme.css` and `/css/titlebar.css` won't exist locally.

## Fixed titlebar needs `topMargin`

Say the loader renders a `position: fixed; top: 0` titlebar (`titlebar.css`, `height: 52px`, `z-index: 1000`) and clears it with `.content { padding-top: 64px }` (52px bar + 12px gap). But docsify's `auto2top` anchor scroll lands the target heading at *viewport top*, behind the titlebar, because it doesn't know the fixed bar exists. So any deep link (a page's own H1 via `?id=`, and every `?id=` sub-anchor) scrolls the heading under the bar.

The loader sets `topMargin: 64` in its `$docsify` defaults to fix this once for every project. 64 mirrors `.content`'s resting `padding-top`, so an anchored heading lands with the same 12px gap below the titlebar that it has at rest. This is the general *sticky-header-overlaps-target* case (see *Deep-linked anchors landing off-target* in [the recipes](docsify-recipes.md)); a shared titlebar is the concrete instance, and because the titlebar is shared, the fix belongs in the shared loader, not per-project `index.html`. If the titlebar height changes, re-derive `topMargin` from it.

`topMargin` alone is necessary but **not sufficient** under a shared loader: two more anchor-scroll bugs surface, below. All three were found only by measuring `getBoundingClientRect().top` against the titlebar's `.bottom` in a live browser (Playwright); none is visible in a screenshot, and the two below hide behind HTTP caching (the loader's `<script src>` has no cache-buster, so a browser that already loaded the old loader keeps it for the Pages `max-age`, so verify a fix by fetching the loader cache-busted *and* by loading in a fresh browser context, not by re-navigating the same one). Re-navigating is weaker than it looks on a hash-routed site: a `page.goto` to the same path with a different `#fragment` is a fragment navigation, so the document never reloads and the loader never re-runs, and every route on these sites has that shape. Put a unique query on the page URL (`?r=<now>#/route`) to force a real load, and give the loader's own CSS hrefs a query too if you are checking a stylesheet change.

## Deep-link below a mermaid diagram lands short: re-scroll after render

`topMargin` fixes the titlebar overlap, but a `?id=` anchor **below a mermaid diagram** still lands ~2000px short on first load. This is the *post-snapshot reflow* case (see **Deep-linked anchors landing off-target**) with an async twist: docsify snapshots the target's position once, *then* `docsify-mermaid` renders the diagram asynchronously, the diagram expands above the target, and the target drops far below where docsify scrolled. `topMargin` can't help, because the target moved after the measurement.

With async third-party rendering the layout can't be settled before the snapshot, so the shared loader does a **one-shot re-scroll after mermaid settles** (the same correction the standalone template's `deepLinkSettle` makes; see *Async rendering above the target* in [the recipes](docsify-recipes.md)), registered as a second `doneEach` inside the existing mermaid plugin block. Two gotchas learned the hard way:

- **Wait for the render, not a fixed timeout.** Poll (via `requestAnimationFrame`) until every `.mermaid` has produced an `<svg>` child. A fixed 1s cap expired before slow diagrams finished and the correction never ran.
- **Wait for docsify's own tween to settle, too.** docsify's `auto2top` smooth-scroll animates over ~500ms toward the *wrong* (pre-render) target; if you re-scroll while it's still animating, the tween finishes afterward and overrides you. Gate the correction on the tween's 500ms having elapsed, `scrollY` being unchanged for ~3 frames, *and* mermaid rendered, then scroll once. Still frames alone don't prove the tween is done; see *Wait out the whole tween* in [the recipes](docsify-recipes.md). This is a bounded one-shot, **not** a `ResizeObserver` that re-scrolls on every reflow (still the wrong tool).

## Same-page `?id=` clicks don't scroll: handle `hashchange`

When only the `?id=` changes on the same page, docsify scrolls only if it classes the hash change as a link click: its `window` click listener has to see an `<a>` as the click's target or that target's parent. A click on markup nested deeper inside the link, an SVG `<a>`, or a click a `document` handler stopped from propagating all read as back/forward, and docsify leaves `scrollY` where it is. So a deep-link *load* works, but clicking a **sidebar sub-heading or heading permalink while already on that page** can do nothing. This is independent of mermaid and independent of `topMargin` (both the fresh-load fixes leave it unsolved), and docsify doesn't re-render for a same-path change, so `doneEach` doesn't fire and a `doneEach` hook can't catch it either.

Fix in the shared loader with a plain `window.addEventListener('hashchange', …)` (a native listener, so it's immune to the registration-order trap below): when the old and new URLs share a route path, parse `?id=` from `location.hash` and `scrollTo` the target with the `topMargin` offset. Compare the paths rather than checking whether the target is in the current DOM: at `hashchange` time the outgoing page is still rendered, so a cross-page link whose `?id=` also exists on the page you're leaving (two report pages that both have a `search` group) finds that stale element and scrolls the old page. Compare like with like, too: `e.oldURL` and `e.newURL` both need the part after `#`, while `location.hash` keeps the `#`, so a path taken from one and compared with the other never matches.

## Registration order in the shared loader

Anything that registers through `window.$docsify.plugins` **must load before docsify core** in the loader: third-party plugins (copy-code, flexible-alerts, sidebar-collapse, mermaid, etc.) and a bare `doneEach`/lifecycle hook pushed in for custom behavior alike. The loader injects scripts sequentially *after* the page has parsed, so docsify runs `new Docsify()`, which reads `$docsify.plugins` once, the instant its script loads. Anything appended *after* `docsify@4` registers too late and silently never runs (no error; the behavior is just absent).

This differs from a static `index.html`, where every `<script>` tag executes in document order around `DOMContentLoaded`, so registration-after-docsify works fine. The dynamic sequential injection in the shared loader is what makes ordering load-bearing. Symptom to recognize: a configured plugin's output (e.g. `.docsify-copy-code-button`) is missing from the rendered DOM, or a custom hook's effect (e.g. a `.copied` class on click) never appears, even though the script is loaded. Fix for a third-party plugin: move it into the pre-core step list alongside flexible-alerts. When you add one, check the CDN URL actually serves JavaScript: jsDelivr's bare `npm/<pkg>@<major>` resolves through the package's `main`, and a package whose `main` names a directory (`docsify-plugin-toc`) answers with a 200 whose body is `Couldn't find the requested file /src in <pkg>`. The script tag loads, nothing registers, and it reads exactly like the ordering trap. Point at the dist file.

For custom element behavior (copy-button feedback, etc.), prefer a delegated `click` listener on `document` over a docsify hook. Delegation runs independently of `new Docsify()` init order and re-binds nothing on each route change, so it sidesteps both this late-registration trap and per-route re-render timing. This trap has bitten one shared loader three times: the copy-code plugin registering after core, an `initCopyButtons()` `doneEach` hook that added the `.copied` green-check class (both fixed by not depending on `$docsify.plugins` registration timing, the latter by moving to a delegated `document` listener), and `search.min.js`, which came in written the conventional way (core first, plugin after) back when the loader `document.write`-ed parser-inserted `<script>` tags and that order was safe. The refactor to sequential injection is what broke it, without touching either line.

So a change to *how* scripts are injected has to re-check the order of everything already in the list, not just what it adds. Nothing in the diff that introduced the bug mentioned search.

That one hid the longest because the feature **half-worked**: the titlebar box matches sidebar link titles from its own index, so a cmdlet name or a page title returned rows and only body text came up empty. A feature with a working half is the shape to watch for: the ordering trap doesn't announce itself when something else answers. Two checks settle it in a live browser: `document.querySelectorAll('.search').length` is 0 when the plugin never installed (its own sidebar box, which `titlebar.css` hides with `display: none`, is proof it did), and `localStorage.getItem('docsify.search.index')` is null when no index was ever built.

## What the search plugin indexes

`paths: 'auto'` is not "every page". On each `doneEach` the plugin walks `.sidebar-nav a`, converts each href to a route, and **skips absolute hrefs**, so the index covers what the sidebar of the page the visitor is on links to, relatively, plus `/`. Paths already indexed are skipped, so the set grows as they navigate and persists in `localStorage` for `maxAge` (a day by default).

Two consequences on a central site. Its landing sidebar lists one entry, so a visitor who searches before going anywhere is searching one page. And in sidebar mode the rail holds absolute URLs to the sibling sites, which the crawler drops. A central site is searchable through whatever non-docsify source it already has (its project list, matched on name *and* description) rather than through the crawl. Enumerating `search.paths` instead would fix the first, but the list has to exist before docsify core loads, and the loader's step chain is synchronous.

`depth` bounds which headings open an index entry, and it **defaults to 2**. An `h3`'s text lands in the body of the `h2` above it, so a hit on it scrolls to the wrong heading. Set it to match the depth the page's own navigation offers (`toc.target` lists `h2, h3`, so `depth: 3`).

## Reading docsify's search index

A titlebar search in the loader can read the index the search plugin persists to `localStorage` under `docsify.search.index`. Its shape is **page path -> section slug -> `{slug, title, body}`**: one entry per heading, nested a level below the page. A prebuilt `window.SEARCH_INDEX` (the offline build of the same plugin) is flat: slug -> `{title, body}`. Code that accepts either flattens the nested one first, or `item.title` and `item.body` are `undefined` on every entry and nothing matches.

Section slugs already carry their `#` and their `?id=` (`#/MergeRequests/Get-GitlabMergeRequest?id=aliases`), so they are the href, and a row titled with the heading alone ("ALIASES") says nothing about which page it came from, so lead with the page name.

`docsify.search.index` and `docsify.search.expires` are a pair. The plugin resets its in-memory index to `{}` only when the expiry has passed; with a live expiry and a missing index it throws on the null and rebuilds nothing, so the site looks like it never indexes. Clearing one key by hand while debugging produces exactly that state. Clear both, or the whole of `localStorage`.

## The page contents rail

`docsify-plugin-toc` builds the right-hand rail, loaded pre-core like every other plugin and configured by `$docsify.toc`. Three things about it the CSS has to know:

- **`Docsify.dom.before(content, nav)` prepends the `<aside>` *into* `.content`**, rather than inserting it before as a sibling. A rule written as `aside.toc-nav + .content` matches nothing; the aside is `.content`'s first child.
- **Rows are built from each heading's `innerHTML`**, so a heading injected after render (the comments heading the loader appends) has no anchor inside it and its row goes nowhere. Hide such a row rather than removing it: the plugin's scroll-spy pairs rows to headings by position.
- **The rail is fixed**, so the column beside it gives up the width itself: `.content` takes the padding, and a page whose rail is empty takes it back.

Style it from the tokens. The plugin's own stylesheet paints a white panel and hardcodes its link colors, which reads as a hole in the dark theme.

## Step loader: run code as a function, not `new Function(string)`

The shared loader's `loadNext` processes a `steps` array where each step is either an external script (`{ src }`, loaded via a `<script>` tag) or inline setup. Inline setup should be `{ fn: function () { … } }`, executed with `step.fn()`. Do **not** use `{ code: 'js source string' }` run via `new Function(step.code)()`. That's an `eval`-family pattern with no upside, since every inline step is a hardcoded constant:

- Security guards and most linters flag `new Function`/`eval` on sight, and a `PreToolUse` guard that hard-blocks the pattern makes the **whole file** uneditable via the normal Edit tool for as long as the eval exists, forcing every change through a one-off script. Removing the eval restores normal editing.
- It requires `script-src 'unsafe-eval'` under any CSP, and is a genuine injection sink if the string ever stops being a literal.

A real function is strictly better: same behavior, statically analyzable, closes over globals resolved at call time (e.g. `mermaid` is defined by the time the fn runs, after `mermaid.min.js` loads). Store the function, call it; never stringify-then-eval code you wrote at authoring time.

**When you convert, convert every `{ code }` step in one pass: the branch and the steps are coupled.** `loadNext` dispatches on the step shape (`if (step.src) … else if (step.fn) …`), so changing the branch from `step.code` to `step.fn` orphans any `{ code }` step you left behind: it matches neither arm, `loadNext(i+1)` never fires, and the **entire chain halts at that step**: docsify core never loads and the page sits on "Loading…" forever. The trap is that this fails **silently**: no console error (nothing threw; the recursion just stopped), so it looks like a deploy/CDN problem, not a code bug. There are (at least) two `{ code }` steps and they don't grep alike: the mermaid `mermaid.initialize(...)` and a `window.Docsify = { version: … }` stub at the top of `steps`. Grep `code:` (the step literal), **not** `step.code` (the branch). The verification grep that only checked `step.code` is exactly how the second one got shipped and took every site down. Verify a loader change by serving the central site's `docs/` locally (`python3 -m http.server` from `docs/`, since its `index.html` loads the loader same-origin) and confirming in a browser that content renders **and** `window.Docsify.version` is the real docsify version, before deploying to the central site.

## Setting up several repos in one session

When bootstrapping multiple repos in one session, use `git -C /path/to/repo` instead of `cd` to avoid working directory drift. Verify the current branch with `git branch --show-current` before committing: feature branches in multi-repo sessions cause cherry-pick cleanup.
