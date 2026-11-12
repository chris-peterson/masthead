# Interactive recipes for docsify

A handful of small JS patterns recur across docsify sites that do more than serve pages. None are in the base template: add one only when the site needs it, wired into the same `hook.doneEach` callback the template already uses for Mermaid re-runs.

### Pin the document title to the page H1

Docsify's default behavior swaps `document.title` to the deep-linked heading's text whenever a `?id=…` anchor activates, so clicking a sub-anchor like `#/families?id=al2023-standard` leaves the browser tab labeled "Standard," with no page or site context. After every route render, restore the title to `<page H1> · <site name>`:

```javascript
hook.doneEach(function() {
  var siteName = 'Your Site Name';
  var pageH1 = document.querySelector('.markdown-section > h1');
  document.title = pageH1
    ? pageH1.textContent.trim() + ' · ' + siteName
    : siteName;
});
```

### Auto-open `<details>` on deep-link

Native `<details>` elements don't open from a URL hash on their own: an anchor like `#/status?id=asset` will scroll to the collapsed `<details id="asset">` and leave its body hidden. A target *inside* a collapsed `<details>` (one row of a closed group) is worse: it isn't rendered at all, so docsify scrolls to a box with no position. Force-open the target and every `<details>` around it after each route render:

```javascript
hook.doneEach(function() {
  var idMatch = window.location.hash.match(/[?&]id=([^&]+)/);
  if (!idMatch) return;
  var target = document.getElementById(decodeURIComponent(idMatch[1]));
  for (var el = target; el; el = el.parentElement) {
    if (el.tagName === 'DETAILS') el.open = true;
  }
});
```

This pairs well with `<details>` for any collapsible group view (compliance report cards, FAQ pages, audit logs). Any other fold a site applies with `display: none`, such as a default "in use only" filter, needs the same treatment: reveal the target in `doneEach` when it's inside one. Opening an enclosing fold moves the target after docsify measured it, so the landing depends on the correction in *Async rendering above the target* below.

#### Auxiliary `<details>` above the target need build-time `open`

Docsify's `?id=` resolver snapshots `getBoundingClientRect().top` once at tween construction, before `doneEach`. Opening auxiliary `<details>` in JS after the snapshot leaves the scroll landing partway down the wrong row. Bake `open` into the HTML at build time for any rows expected to be expanded on first paint:

```html
<details class="report-row" id="asset" open>
```

Reserve JS auto-open for the target row only; expanding it after the tween is safe because its top doesn't move.

### Deep-linked anchors landing off-target: sticky headers and post-snapshot reflow

Docsify snapshots the target's `getBoundingClientRect().top` **once**, at tween construction (before `doneEach`), and animates to that fixed value over ~500ms; it never re-measures. So a `?id=` deep-link lands wrong whenever the target's real position differs from that single snapshot. Three causes, three fixes: a sticky header, layout you can settle before the snapshot, and async rendering you can't. (A `ResizeObserver` that re-scrolls on every reflow is fighting docsify, not cooperating with it; don't reach for it.)

**A sticky/fixed header overlaps the target → set `topMargin`.** If the site has a sticky element at the top of the content column (a CTA bar, a persistent notice), a *correctly*-scrolled heading lands at viewport top, i.e. *behind* the header. `topMargin` is docsify's own config field for exactly this: the offset it subtracts when scrolling to an anchor, so the heading lands below the header instead.

```javascript
window.$docsify = {
  auto2top: true,
  topMargin: 74,   // sticky header height (~58px) + breathing room
  // ...
};
```

It's global (one value for every page), so pages without the header get that much blank space above an anchored heading. That's usually fine as breathing room; there's no per-page `topMargin` short of a custom scroll shim. The standalone base template ships no sticky content header, so it leaves `topMargin` at its default `0`; add it per site when you introduce one. A family of sites behind a shared loader with a fixed titlebar is such a site: the loader must set `topMargin` or every deep-linked anchor (including a page's own H1 via `?id=`) lands behind the titlebar. See [the shared loader](docsify-shared-loader.md).

**Layout above the target changes after the snapshot → make it final before render.** Anything that shifts content *above* the target after the snapshot pushes the heading off by that delta, landing it off-screen. When the change is yours to schedule, settle the layout before the snapshot rather than re-scrolling after:

- **Auxiliary `<details>` opened in JS:** bake `open` into the HTML at build time (see *Auxiliary `<details>` above the target* above; same root cause).
- **Route-conditional CSS that changes page height,** such as a density/spacing class applied on only one route. Toggle it in `beforeEach` (which runs *before* render and the snapshot), on a stable ancestor like `<body>`, **not** in `doneEach` (which runs after). Drive the CSS off the `body` route class so the tightened layout is already in place when docsify measures:

  ```javascript
  hook.beforeEach(function (content) {
    document.body.classList.toggle('route-plugins', /^#\/plugins(\?|$)/.test(location.hash));
    return content;
  });
  ```
  ```css
  body.route-plugins .markdown-section h4 { margin-top: 24px; }   /* tighter list rhythm */
  ```

  Applying the same class in `doneEach` (on `.markdown-section`) is the trap: the spacing tightens *after* docsify has already scrolled, every heading shifts up, and the deep-linked anchor ends up above the viewport. The tell is a *constant* overshoot equal to the layout delta on every load of that page.

**Async rendering above the target → re-scroll once it settles.** Mermaid diagrams and images without fixed dimensions reach their real height after the snapshot, and nothing in the site can make them final first. Each one above the target pushes it down, so a deep link lands short by their combined height, and the further down the page, the more there is to push. On a long page with a few diagrams it lands more than a screen short. The base template's `deepLinkSettle` plugin handles it: after `doneEach`, it polls on `requestAnimationFrame` until every `.mermaid` above the target has an `<svg>`, every `<img>` above it is `complete`, docsify's 500ms tween has had time to finish, and `scrollY` has held for three frames, then scrolls once, honoring `topMargin`. Three conditions are required:

- **Wait out the whole tween; a still `scrollY` doesn't mean it's done.** docsify's tween eases out, so its tail holds `scrollY` still for several frames before its last write, and that write lands after the correction and undoes it. A tween aimed past the top or bottom of the page (a target measured while hidden) writes a value the browser clamps, so `scrollY` doesn't move for its whole run. Both pass a three-still-frames check alone. The tell is a landing that's off by a constant amount on one page and right on the next reload.

- **Only wait on content above the target, and make it load.** Content below can't move it, and a lazy-loaded image below the fold never completes until the reader scrolls to it. Footnote back-reference emoji are the usual case, and waiting on them stalls the correction until the frame cap expires. A lazy image *above* the target stalls it the same way once the page has scrolled past it (docsify renders `:+1:` and friends as `<img class="emoji" loading="lazy">`), so switch each incomplete one above the target to `loading = 'eager'` before waiting on it.
- **Scroll once, and only when off by more than a couple of pixels.** It is a bounded correction after docsify's own scroll, not a loop that re-scrolls on every reflow.

A shared loader runs the same correction for mermaid; see *Deep-link below a mermaid diagram lands short* in [the shared loader](docsify-shared-loader.md).

Verify with Playwright, not a screenshot: compare the heading's `getBoundingClientRect().top` to the sticky header's `.bottom` (a clean landing sits just below it), and toggle the route class to confirm the position delta equals the overshoot.

### Mermaid `click` links change the URL but don't scroll

A mermaid node with `click A "#/page?id=heading"` renders as an SVG `<a>`, and clicking it updates the hash without moving the page. docsify tells a link click from back/forward by checking whether the click's target, or its parent, has `tagName === 'A'`. An SVG `<a>` reports lowercase `'a'`, and the click lands on a `<p>` inside the node's label anyway, so docsify classes the hash change as history navigation and skips its `?id=` scroll. The base template's `mermaidLinks` plugin cancels the SVG link's click and replays it on a temporary HTML `<a>` with the same href, which docsify handles like any other link (scroll, sidebar highlight). A click with a modifier key, or on a link with a `target`, passes through, so opening a node in a new tab still works.

Verify by clicking a node with Playwright and reading `getElementById(id).getBoundingClientRect().top`; a target near the end of the page stops at the maximum scroll instead of reaching 0.

### A click handler that stops propagation turns its links into back/forward

docsify listens for link clicks on `window`. A delegated `document` click handler that calls `stopPropagation()` on a link (a row anchor that sets the hash itself, a copy-link icon) keeps the click from reaching that listener, so docsify classes the hash change as history navigation and doesn't scroll. On a same-page `?id=` link the page doesn't move at all. Call `preventDefault()` to keep the link from toggling a parent `<summary>`, and let the click propagate.

### Style the search match highlight and clear button

Docsify's full-text search ships two rough edges that the base themes don't fix, so any site that restyles the search box has to handle them explicitly:

1. **Match highlight (`.search-keyword`) is low-contrast.** The plugin wraps matches in `<em class="search-keyword">`; the fill and text color come from whatever the theme/highlighter defaults to. On docsify-themeable + dracula-prism that lands as amber text on a `#FFCB6B` yellow fill, which is close to illegible. Set both explicitly: dark text on the accent (or accent text with no fill), and verify the pair against WCAG AA.
2. **Clear (`×`) button sits as a static block *past* the input**, not inside it, so it collides with a custom-bordered input and floats out of vertical center. Seat it with `position: absolute` inside a `position: relative` `.input-wrap`, and reserve right-padding on the input so the query text doesn't run under it. Its SVG is a `<circle fill="#ccc">` + white `×` strokes, and docsify-themeable paints search-box SVGs with `fill/stroke: … !important`, so recoloring the icon needs `!important` too.

```css
/* Readable highlight: dark text on the accent, not the theme default */
.search .matching-post .search-keyword,
.search .search-keyword {
  color: var(--base-background-color) !important;
  background: var(--link-color) !important;
  padding: 0 3px; border-radius: 3px; font-style: normal;
}
/* Seat the clear button inside the input's right edge; restyle its icon */
.search .input-wrap { position: relative; }
.search .clear-button {
  position: absolute; top: 50%; right: 8px; transform: translateY(-50%);
  width: auto; height: auto; padding: 0; margin: 0; cursor: pointer;
}
.search input { padding-right: 34px; }
.search .clear-button svg circle { fill: transparent !important; }
.search .clear-button svg path { stroke: var(--search-icon-color) !important; }
.search .clear-button:hover svg path { stroke: var(--link-color) !important; }
```

Verify both in a browser (Playwright): read the computed `background`/`color` on `.search-keyword` and the clear button's `getBoundingClientRect()` vs the input's. A screenshot misses the `!important` override and the off-by-a-few-px vertical centering. And remember docsify caches `index.html`: test a restyle on a fresh port or with a cache-busting query, or the old CSS silently masks the fix.

### Search indexes the raw markdown: hand it the rendered text instead

The search plugin builds its index from `marked.lexer` tokens and stores each block's `token.text`, which is the block's markdown source. Every result it draws inherits that:

1. **Snippets show markdown links, backticks, bold, and raw HTML.** The plugin cuts each snippet from that source and joins several fragments with `...`, so a link or a tag can also be cut partway through.
2. **A heading that is a link gets a raw title and a slug no heading has.** `##### [`beacon`](https://…)` indexes with the title ``[`beacon`](https://…)`` and slugifies that whole string, so the result links to `?id=beaconhttpschris-petersongithubiobeacon` while the rendered heading's id is `beacon`. The hit looks right and lands nowhere. Catalog pages whose entries are linked headings are exactly this shape.
3. **An HTML heading slugs from its markup**, so the home H1 carrying an inline logo gets an id built from the `<img>` attributes.

Fix it where the index is built, not in the results panel. The plugin reads `window.marked.lexer` when it indexes a page, so give it a lexer whose tokens carry the text the page renders: render each block, take its `textContent`, and let the plugin cut, escape, and highlight that. A heading's plain text slugs to the id docsify gives it, because docsify's `slugify` strips the tags from the rendered heading before slugging it (4.13). The one place the two part is a heading that renders with a tag: `slugify` trims before it strips, so `<img …> Name` keeps its space and gets the id `-name`. When the page's id differs from what the plugin slugs from the plain text, the lexer appends docsify's own `:id=` heading option carrying the page's id, which the plugin honors.

Pages are unaffected: docsify renders them through the `marked` it captured at startup, so swapping the `window.marked` object changes only what search sees.

The template (`assets/index.html`) ships this plugin, so only a site generated before it needs the block below added (replacing an older `searchResultLinks` results-panel rewrite, where a site has one):

```js
function searchPlainText(hook) {
  hook.init(function () {
    var marked = window.marked;
    var lex = marked.lexer;
    function text(html) {
      return new DOMParser().parseFromString(html, 'text/html').body.textContent.trim();
    }
    // docsify slugs a heading's rendered HTML, trimming it before it
    // strips the tags, so <img> Name gets the id "-name" where the plain
    // text would slug to "name". These are its slugify rules without the
    // per-page counter, which the index's own slugify still applies.
    var SLUG_PUNCT = /[\u2000-\u206F\u2E00-\u2E7F\\'!"#$%&()*+,./:;<=>?@[\]^`{|}~]/g;
    function pageId(html) {
      return html.trim().replace(/[A-Z]+/g, function (s) { return s.toLowerCase(); })
        .replace(/<[^>]+>/g, '').replace(SLUG_PUNCT, '')
        .replace(/\s/g, '-').replace(/-+/g, '-').replace(/^(\d)/, '_$1');
    }
    // The plugin slugs a heading as slugify(escapeHtml(text)) with this escape.
    function escapeHtml(s) {
      return s.replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    }
    function heading(md) {
      // Inline only: the heading renderer advances docsify's slug
      // counter, which would shift every indexed id to "<id>-1".
      var html = marked.parseInline(md);
      var plain = text(html);
      var id = pageId(html);
      // An author's own :id= stays in the text, where docsify and the plugin both read it.
      if (/(^|\s):id=/.test(plain) || id === pageId(escapeHtml(plain))) return plain;
      // The plugin reads an option's value only up to the first character outside [\w%-].
      if (/^[\w%-]+$/.test(id)) return plain + ' :id=' + id;
      console.error('searchPlainText: search cannot link to the heading id "' + id + '"');
      return plain;
    }
    // docsify's renderer, except that a heading nested in a blockquote or list
    // renders as bare text: docsify's heading renderer would advance its slug
    // counter and add the heading to the page's table of contents.
    function block(md) {
      var renderer = Object.create(marked.defaults.renderer);
      renderer.heading = function (text) { return '<p>' + text + '</p>\n'; };
      return marked(md, { renderer: renderer });
    }
    function lexer(src, options) {
      var tokens = lex(src, options);
      tokens.forEach(function (token) {
        if (token.type === 'heading') token.text = heading(token.text);
        else if (token.type === 'code') token.text = token.lang === 'mermaid' ? '' : token.text;
        else if (token.type !== 'space') token.text = text(block(token.raw));
      });
      return tokens;
    }
    window.marked = Object.assign(function () { return marked.apply(this, arguments); }, marked, { lexer: lexer });
  });
}
```

Four traps, each found by running `scripts/docsify/check-search.js`:

- **Don't call `Docsify.slugify` to get a heading's page id.** It keeps a per-page count for duplicate headings, and the index's own `slugify` call on the same id then comes out `<id>-1`. `pageId` copies its rules without the count.

- **Render a heading inline, not as a block.** docsify's heading renderer runs `slugify`, which counts every heading it sees per page. Rendering the heading for the index advances that count, and the index's own slug then comes out `<id>-1` for every heading on the site.
- **Rendering `1. Install` as a block makes it a list item** and drops the number, which is the other reason headings go through `parseInline`.
- **Keep code blocks as their source**, which is what the reader sees, but drop mermaid blocks: their source is diagram syntax, not text anyone searches for.

Three more that `check-search.js` can't see, because it skips H1s, pages outside the sidebar, and the cache:

- **Append `:id=` only when the ids differ.** The plugin reads an option's value up to the first character outside `[\w%-]`, so an id carrying `↗` or an accented letter comes back cut short. Such a heading's plain text already slugs to the page's id, so it needs no option; the lexer logs the rare one that needs an option it can't carry.
- **Render nested headings without docsify's heading renderer.** A `> ## Note` inside a blockquote or list goes through it when its block renders, which advances the slug count and adds the heading to the page's table of contents.
- **Set `search.namespace`, and change it when what gets indexed changes.** The plugin caches its index in localStorage for `maxAge` (a day by default), so a returning reader keeps the old index until it expires.
- **Start `search.namespace` with `location.pathname`.** The plugin stores the index under `docsify.search.index/<namespace>`, and localStorage is per origin. GitLab Pages serves a group's sites and each site's preview deployments from one origin (`<group>.pages.<host>/<project>/`), so a fixed name lets one site, or a preview, serve another's cached index.

What's left is docsify's own: it cuts the snippet from the HTML-escaped string, so a cut can land inside `&lt;` and leave `lt;` at a fragment's edge. That needs a change to the plugin, not to its input.

`search.depth` has to reach the linked headings for any of this to show up; a catalog of `#####` entries needs `depth: 5`. Verify with the check below rather than a hand-picked query or two: every search the agent tried by hand in the session that produced this recipe's first version was a query that happened to work.

### Check search the way a reader uses it

`scripts/docsify/check-search.js` is one async function that runs inside a served page. It visits every page the sidebar links, records the ids each renders, searches for every heading, and reports three kinds of problem:

| Kind | Means |
|---|---|
| `raw-markup` | a result title or snippet showing markdown link syntax, an HTML element, or a comment (backticks count in titles only); a `<word>` placeholder is page text, not markup |
| `dead-link` | a result whose `?id=` matches no id on the page it opens |
| `not-found` | a heading that returns no result titled with its own text (`search.depth` too shallow, or a raw-markdown title) |

Pass the file's contents as the function to Playwright MCP's `browser_evaluate` (or to `page.evaluate()`) on any page of the site. It is clean when `problems` is empty. Run it after any change to search config, to the plain-text indexing above, or to a page that authors raw HTML, and before the before/after screenshots for a review: it covers every heading, where a screenshot covers the one query someone thought to type.

### Build the page-contents rail from ids, not from heading HTML

`docsify-plugin-toc` copies each heading's `innerHTML` into its row. On a heading whose text is a link, the in-page anchor docsify renders is empty and the text is the outbound link, so the copied row links off-site. Anything a plugin appended to the heading (copy-link or source buttons) rides along too. When a site has such headings, build the rail itself from each heading's `id` and text:

- **Rows link to `#/<route>?id=<id>`**, labelled from a clone of the heading with the appended tools removed.
- **Indent by nesting, not by tag level.** A page that puts `h5` entries directly under an `h2` is one step in, not three: keep a stack of open levels, pop while the top is `>=` the current level, and the stack's length is the depth.
- **Sections that aren't headings can join the rail.** A data-driven tree (a catalog built from JSON) has group rows that are the page's real sections; give them ids, add them to the rail's selector, and rebuild the rail when the tree re-renders (a custom event from the render works). A click on one of those rows has to open collapsed ancestors and do its own scroll, since docsify only scrolls to headings.
- **One landing offset for every scroll.** With a fixed top bar and a sticky in-page bar, a deep link, a rail click, and the scroll-spy all need the same "below the chrome" figure; compute it in one function from the elements' live heights rather than restating numbers.
- **Highlight what's being read.** "Last section whose top passed the bar" lags when a section starts just below the bar; "next section within the top quarter" jumps ahead on a page of short entries. Use the first rule, and advance to the next section only when the current one has already scrolled out of sight.

### Click-to-copy: GitHub-style popout button, not the value itself

For rendered identifiers a reader is likely to paste elsewhere (full image names, build identifiers, pipeline URLs), surface a small copy affordance, but **not by making the value text itself clickable**. The value should remain a normal anchor (so click navigates to its in-page hash if it has one) and the copy goes to a sibling button:

```html
<span class="copy-group">
  <a class="heading-link" href="#/families/...?id=..."><code>acme-web-2024-06-x86_64</code></a>
  <button type="button" class="copy-button" data-copy="acme-web-2024-06-x86_64"
          aria-label="Copy acme-web-2024-06-x86_64" title="Copy">
    <i class="fa-regular fa-copy" aria-hidden="true"></i>
  </button>
</span>
```

The button is `opacity: 0` at rest, revealed on `:hover` / `:focus-within` of the group. Click swaps the icon to `fa-check` for ~1.2s, then reverts. **Call `button.blur()` after the success state ends**; otherwise `:focus-within` keeps the button visible and it looks stuck on.

Avoid: whole-value click-to-copy (fights the wrapping anchor's navigation), floating "copied" pills (clipped by `.markdown-section`'s `overflow-x: hidden`), in-place text swap (jarring, unfamiliar).

Wrapping anchors that contain a copy-target should drop their hover-underline so it doesn't compete with the popout button:

```css
.markdown-section .heading-link:has(.copy-group):hover { border-bottom-color: transparent; }
```

`:has()` is well-supported in modern browsers (Chrome 105+, Safari 15.4+, Firefox 121+).

### Shareable row anchors (hover-reveal chain-link icon)

Docsify auto-anchors headings, so a reader can deep-link to any section. It does *not* anchor table rows or list items, so there's no way to point someone at a specific pattern row, anti-pattern, or glossary entry. Add a GitLab/GitHub-style affordance: a faint chain-link icon that appears on row hover and, when clicked, navigates to that row's anchor and copies the share URL to the clipboard.

The author drops a manual empty `<a id="…"></a>` marker into the row or list item; a plugin decorates each marker with the icon. Empty-and-`id` is the signal: text-bearing anchors are normal links or docsify's own heading anchors and are left alone.

```html
| Pattern | When to use |
| --- | --- |
| <a id="feedback-backpressure"></a>Feedback Backpressure | … |
```

```javascript
// Registered in $docsify.plugins; under a shared loader, see its ordering caveat.
function rowAnchors(hook, vm) {
  hook.doneEach(function () {
    var section = document.querySelector('.markdown-section');
    if (!section) return;
    var path = (vm.route && vm.route.path) || '';
    section.querySelectorAll('a[id]').forEach(function (a) {
      // Decorate only manual, empty <a id></a> markers; headings get docsify's own handling.
      if (a.getAttribute('data-row-anchor') || a.textContent.trim()) return;
      a.setAttribute('data-row-anchor', '1');
      var hash = '#' + path + '?id=' + a.id;
      var link = document.createElement('a');
      link.className = 'row-anchor';
      link.href = hash;
      link.innerHTML = '<svg viewBox="0 0 24 24" width="0.85em" height="0.85em" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
      link.title = 'Link to this item (copies URL)';
      link.setAttribute('aria-label', 'Link to this item');
      link.addEventListener('click', function () {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(location.href.split('#')[0] + hash).catch(function () {});
        }
      });
      a.parentNode.appendChild(link);
    });
  });
}
```

The icon stays invisible at rest and fades in on row hover (or keyboard focus), so it never clutters the table:

```css
.markdown-section .row-anchor {
  opacity: 0;
  margin-left: 0.4em;
  color: var(--link-color);
  text-decoration: none;
  vertical-align: middle;
  transition: opacity 0.15s ease;
}
.markdown-section .row-anchor svg { vertical-align: middle; display: inline-block; }
.markdown-section tr:hover .row-anchor,
.markdown-section li:hover > .row-anchor,
.markdown-section .row-anchor:focus { opacity: 0.55; }
.markdown-section .row-anchor:hover { opacity: 1; text-decoration: none; }
```

Same `?id=` deep-link the title-pinning and auto-open patterns above already handle. Pairing this with **Pin the document title to the page H1** keeps the tab labeled by page, not by the clicked row. Under a shared loader, this registers through `$docsify.plugins` and so is subject to the late-registration trap in *Registration order in the shared loader* ([the shared loader](docsify-shared-loader.md)): load it before docsify core.

### Version persisted UI state

When a docsify site uses `localStorage` for client-side filter state, persisted values can outlive a schema/semantic change and leave returning visitors with a "broken default." If you flip the meaning of a stored value (e.g. inverting a toggle's pressed/unpressed semantics, or changing a single-select to multi-select), bump the storage key:

```javascript
// Bumped from `catalog-arch-excluded`; the older key was written
// under inverted semantics and would otherwise leave returning
// users with a stale filtered state.
var FILTER_KEY = 'catalog-arch-filter';
```

The old key is orphaned and ignored. localStorage is invisible to grep, so when in doubt, version it.
