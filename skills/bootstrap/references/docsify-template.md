# The docsify template, and why it's built this way

The canonical site is **`assets/docsify/index.html`**, a real file rather than a fenced copy. `scripts/docsify/bootstrap.py` copies it verbatim and substitutes a handful of placeholders. Edit `assets/docsify/index.html` directly; never regenerate it by paraphrase.

This document is the consolidated record of **why** each non-obvious rule exists, so an edit doesn't regress a fix that has bitten before. The same warnings live as inline comments in the file; this page is the index you read before touching the styles.

## What the script substitutes

Everything else in the template ships as-is. `bootstrap.py` fills only these:

| Placeholder | Filled with | Source |
|-------------|-------------|--------|
| `{{PROJECT_NAME}}` | Project name (also `<title>`, meta description, sidebar `name`) | `--name`, else repo directory basename |
| `{{REPO_URL}}` | Source repo URL, normalized to `https://…` (no `.git`) | git remote `origin`, or `--repo-url` |
| `{{TITLEBAR_ACCENT_START}}` | Accent gradient start: purple (GitHub) or orange (GitLab); mid/end stay cyan/pink | detected host |
| `{{GITLAB_CORNER_CSS}}` | GitLab logo corner override, or empty for GitHub | detected host |
| `{{PRISM_PLUGINS}}` | One `<script>` per detected language | tracked file extensions + `--langs` |
| `{{MERMAID_SCRIPTS}}` | Mermaid CDN + init line, or empty if no Mermaid is used | ` ```mermaid ` blocks in `.md` files |

`nameLink` is **not** a placeholder; it's hardcoded to `'#/'`. A hash-only link preserves the pathname under Pages subpath hosting; path-anchored values (`'/'`, `'/<repo>/'`) break on at least one of local preview, Pages, or a site served under a shared loader.

### Prism plugin format

Each language becomes one tag, after the search/alerts/copy-code plugins:

```html
<script src="https://cdn.jsdelivr.net/npm/prismjs@1/components/prism-bash.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1/components/prism-yaml.min.js"></script>
```

`bash` and `yaml` are always included; `json` is highlighted by Prism core and needs no plugin. The full extension→language map lives in `bootstrap.py` (`EXT_TO_PRISM`).

## UI control placement

Each control has a dedicated, non-overlapping home.

### Top-right corner: source link only

The top-right corner belongs exclusively to docsify's built-in `repo:` corner widget. Do not place other controls here.

- **GitHub**: no extra CSS; the built-in octocat renders from `repo:`.
- **GitLab**: `{{GITLAB_CORNER_CSS}}` swaps the octocat for the GitLab logo:

```css
.github-corner svg { display: none; }
.github-corner {
  position: fixed; top: 0; right: 0;
  width: 80px; height: 80px; z-index: 10;
  background: url('https://about.gitlab.com/images/press/gitlab-logo-500-rgb.svg') no-repeat center center;
  background-size: 56px 56px;
}
```

### Sidebar: sticky header with toggle and search

The sidebar header is restructured on `hook.ready` into a sticky container: the app name/logo (pulled from `.app-name-link`), the theme toggle pill (both sun and moon icons with a sliding indicator), and the search bar. The nav below scrolls independently. Search is focused by clicking it. The page binds no keyboard shortcuts: bare keys and browser chords alike (`/`, `Cmd+F`/`Ctrl+F`, `Cmd+K`) belong to the browser and to the reader's extensions, and a page that captures one takes away find-in-page or a plugin the reader relies on.

### Gradient accent

A 2px gradient line along the sidebar's right edge is the site's visual signature, built from `--titlebar-accent-start/mid/end`.

## Sidebar layout constraints to preserve

Every rule below fixes a specific bug. If a project's site doesn't match, copy the whole sidebar block; partial patches have compounding failure modes.

1. **`overflow: hidden` on `.sidebar` with a `box-shadow` inset right-border**: not `border-right` (consumes layout width), not `::after` + `overflow: visible` (breaks resize-handle hit-testing).
2. **`--sidebar-padding: 0`, with every gutter set where it applies.** Zero padding lands the nav's scrollbar flush at the edge. The theme sizes the search row for its own `0 25px` padding (`--search-input-margin: 0 -25px`), so with the padding zeroed the search row overhangs both sidebar edges by 25px unless `--search-input-margin` is also `0`.
3. **Resize handle at `right: 0; width: 4px`** (not a straddle that needs `overflow: visible`). 4px is narrower than any OS scrollbar, so the scrollbar track stays clickable.
4. **Use mouse events, not pointer events, for drag**: simpler, no pointer-capture weirdness. Disable `sidebar.style.transition` during drag, restore on mouseup.
5. **Double-click handle → auto-fit** (measure `scrollWidth` with `white-space: nowrap`, clamp to `[200, viewport/2]`, write `--sidebar-width`).
6. **Theme toggle right-anchored via `margin-left: auto`** on the pill, not via flex `justify-content` (survives plugin-wrapped app-name nodes).
7. **`overflow-wrap: anywhere` + `word-break: break-word` on `.sidebar-nav a`**: long monospace labels wrap instead of forcing horizontal scroll.
8. **Suppress the chevron on leaves with `background: none` only**: never zero `padding-left` here. `docsify-sidebar-collapse` indents `.file` and external links differently, so zeroing padding on the chevron rule produces a ragged left margin. Set a uniform gutter separately (`padding-left: 16px` on every `.sidebar-nav li a`); the header icon and the search magnifier sit on the same 16px line.
9. **Color the app name explicitly** with `--sidebar-name-color` on `.sidebar-header-row .app-name-link`. The header is rebuilt on `hook.ready`, which moves the link out of the `.sidebar .app-name` the theme colors, so without the rule it renders in the browser's default link blue. The light value is darkened like the syntax tokens, since plain `--alucard-pink` is 4.23:1 on the sidebar fill.
10. **Clear the mobile menu button.** Below 768px, docsify's `.sidebar-toggle` floats over the top-left of the content and covers the H1. The template pads `.content .markdown-section` down by `3.5rem` at `max-width: 767px`; the `.content` prefix is needed because a stylesheet injected at runtime sets `.markdown-section { padding: 16px }` at the same breakpoint and loads after the template.
11. **The favicon is the sidebar logo.** `hook.ready` puts an `<img class="app-name-icon">` before the app name, its `src` read from the page's `<link rel="icon">`, so `docs/favicon.svg` is the only file to design. The name sits in `.app-name-text` beside a 32px icon and wraps at its spaces rather than truncating or pushing the toggle off the row, so a two-word name reads as a lockup at the default sidebar width. A word wider than the column ellipsizes (`overflow: hidden; text-overflow: ellipsis`, no `nowrap`): at the 200px minimum the name column is about 55px, and `overflow-wrap: break-word` there splits "Machine Images" into four lines mid-word.
12. **One gutter on each side of the header.** The icon and the nav text start at 16px. The toggle's right edge sits 12px from the sidebar edge, and so do both edges of the search field, which is a rounded input inset in the header (its own border and focus ring, the theme's `.input-wrap` border and fill cleared) rather than a full-width band. One hairline under the header separates it from the nav.
13. **The search icons are the template's, not the theme's.** The theme draws the magnifier as a background image with a fixed `rgba(…, 0.3)` stroke that disappears on the light input, so `--search-input-background-image: none` and an `.input-wrap::before` mask (`--icon-search`) draws it in `--search-icon-color`. The plugin's clear button is a block whose 24px svg sits at the top of the 39px input, and its svg draws the circle off-center in a 26×24 box; the template centers the button absolutely, sets the svg's `viewBox` to `0 0 24 24` on `hook.ready`, and colors it through the theme's `--search-clear-icon-color1`/`2`. In dark mode `--dracula-comment` is 1.9:1 on the `--dracula-current` input, so the placeholder and icons use a 50% mix toward white (4.65:1).

## Visual polish baked into the template

These ship in `assets/docsify/index.html` and are what set the site apart from a default docsify install. Listed so an edit knows what's intentional:

1. **Theme toggle pill**: both sun and moon icons always visible side-by-side; a sliding indicator (`cubic-bezier(0.4, 0, 0.2, 1)`) marks the active theme, so the user sees what they're switching *to*.
2. **Gradient accent line**: 2px line from `--titlebar-accent-start/mid/end`, opacity up on hover.
3. **Hover micro-interactions**: links/icons transition color/opacity, not just cursor. Nav items hold their position: a hover that changes padding reflows the label and can rewrap a long one, shifting every row below it.
4. **Sticky sidebar header**: logo, toggle, and search stay fixed while the nav scrolls, so search never scrolls out of view on long sidebars.

For data-driven sites that add their own grids, prefer **container-width-aware grids** (`grid-template-columns: repeat(auto-fit, minmax(<min>, 1fr))`) over fixed media-query breakpoints: with a ~280px sidebar the article column lands near ~870px on a 1200px viewport, so a `@media (min-width: 900px)` breakpoint never fires and the grid stays single-column even on a wide monitor.

## Dates and in-page chart links

- **A date in a `<time>` stays on one line.** Browsers break an ISO date after its hyphens (`2026-` / `07-` / `10`) once a wide neighbor, usually unbreakable inline code, squeezes its column. Wrap a table's dates in `<time>` and `.markdown-section time { white-space: nowrap; }` holds each one together.
- **`svgLinks` makes a link inside an SVG scroll to its `?id=` target.** docsify scrolls on a same-page `?id=` link only when its click handler saw an HTML link (`tagName === 'A'`); a link inside an SVG reports `a`, so a chart row linking to its table entry would change the URL and leave the page where it was. The plugin handles that one case and leaves `target="_blank"` links to the browser. Charts drawn by the industry-trends skill rely on it.

## Multi-line content soft-wraps (copy-safe)

`theme-simple-dark` ships `white-space: nowrap` on inline `code` at specificity `0,0,3,1`, which also matches the inner `<code>` of `<pre><code>` and collapses it to one line. The template counters with `white-space: pre-wrap !important` on **both** `.markdown-section pre` and `.markdown-section pre > code`. `pre-wrap` soft-wraps long lines at whitespace, so a command (a marketplace `add` URL is the usual victim) stays fully visible rather than scrolling off-screen, and it breaks at the space *before* the URL, leaving the URL intact on the next line.

Leave `overflow-wrap` at its default `normal`: `anywhere`/`break-word` splits the URL mid-character, which reads as broken. The wrap is **copy-safe**: CSS line breaks insert no characters into the DOM, so `docsify-copy-code` (which reads `textContent`) still yields the verbatim one-line command. Prefer this over `white-space: pre` + horizontal scroll, which hides the tail of long commands.

(For *generated* `<pre><code>` blocks, also escape blank lines as `&#10;` entities; see [data-driven sites](data-driven-sites.md).)

### Inline code wraps like text

The same `nowrap` keeps *inline* code on one line, so a long token (a module source, a full URL) runs past the right edge of a table cell or an annotation box. The template sets `white-space: normal` on `.markdown-section code:not([class*=lang-]):not([class*=language-])`, the theme's own selector, which wins because the template's `<style>` loads after the theme. Inline code then breaks at its spaces, and mid-token through the theme's `overflow-wrap: break-word` when a single token is wider than the line. Mid-token is right here, unlike in a code block: the reader copies inline code by selecting it, and the break inserts no characters.

### Forcing a break at a chosen point

Word-boundary wrapping breaks *wherever the line fills up*, which for a long command often lands mid-URL (the browser treats the `-` in `ai-tools` or a `/` as a wrap point). To pin the break to a specific spot (after `add`, after `--global`), wrap the argument that should stay together in `<span class="nowrap">`: the line then breaks at the space before it and the run stays whole. The template ships the `.nowrap` helper plus a `:has(.nowrap)` hanging indent so the wrapped continuation reads as a continuation (`display: block; padding-left: 2ch; text-indent: -2ch`). The hanging indent is scoped to `:has(.nowrap)` on purpose: a global one would shift every line after the first in a normal multi-line code block. This needs a raw-HTML `<pre data-lang="sh">` block (not a fenced ` ``` ` block, since Prism would rebuild the DOM and drop the span), so it costs syntax highlighting for that block; reach for it only where the forced break matters. `data-lang` is required for `docsify-copy-code` to attach a button.

## Copy button: clipboard glyph → green check → revert

`docsify-copy-code` ships a hard-cornered label block pinned to the code panel's corner that slides a "Copied" word out on success, which is noisy. The template restyles it to a compact 30×30 clipboard-icon button that reveals on `pre:hover` (and keyboard `:focus`), flips to a green check on copy, then reverts. The plugin toggles `.success`/`.error` on the button; every visual keys off those states.

Mechanics worth preserving when editing:

- **Icon via `mask-image`, not `content`.** `--icon-clipboard` and `--icon-check` are inline-SVG data URIs applied as a mask on the button's `::after`. A mask keys off the SVG's alpha, so `background-color` recolors the glyph; that's how the same element goes grey at rest (`--copy-btn-fg`) and green on `.success` (`--copy-btn-success-fg`). The SVG's own `stroke` color is irrelevant under a mask.
- **Hide the plugin's text.** `.docsify-copy-code-button span { display: none }` drops both the resting label and the slide-out "Copied"/"Error" words, leaving just the glyph.
- **Scope under `.markdown-section`.** The plugin's own rules are single-class (`0,0,1,0`); the template's `.markdown-section .docsify-copy-code-button` (`0,0,2,0`) outranks them regardless of stylesheet insertion order, so the restyle wins without `!important`.
- **Five palette vars** (`--copy-btn-bg`, `-bg-hover`, `-fg`, `-success-bg`, `-success-fg`) carry both themes through `light-dark()`, like every other themed value.

### Language label is hidden on purpose

`theme-simple-dark` renders the fenced block's language as a label via `pre[data-lang]::after`, which sits in the same top-right corner as the copy button. The template hides it (`.markdown-section pre[data-lang]::after { display: none }`) so the corner belongs to the button alone; the language adds little next to syntax highlighting that already conveys it. `data-lang` itself stays on the element (Prism and `docsify-copy-code` both rely on it); only its `::after` label is suppressed.

## Readable headings and visible code blocks

Three theme defaults need correcting:

- **Heading scale.** `docsify-themeable` shrinks `h5`/`h6` *below* body size (`h6` ≈ 9px), so any deeply-nested heading is unreadable: a catalog nesting tier > team > plugin lands real headings at `h5`/`h6`. The template pins `h3`–`h6` to a scale that steps down but never drops below body (`h6` = `1rem`), and sizes backticked names in headings to `0.9em` of their heading rather than the small global code size.
- **Code-block fill.** `--code-theme-background` must differ from the page background or the block has no visible box. In dark mode that means **not** `--dracula-bg` (which equals `--base-background-color`); the template uses the darker `#21222c`. With the fills equal, a code block reads as plain text and the copy button appears to float above it.
- **Syntax token colors.** `theme-simple-dark` hardcodes Prism token colors (Material-style `#c2e78c`, `#89ddff`, `#ffcb6b`) chosen for a dark fill, and nothing in the theme switches them. In light mode a YAML key lands near 1.2:1 on the `#eeeee8` code fill. The template maps each token class to a `--code-token-*` semantic variable with both palettes. The Alucard hues sit near 4.2:1 on that fill, short of AA, so the light values are `color-mix(in srgb, <alucard> 80%, black)`, which clears 5.9:1; Dracula's `comment` is mixed toward white for the same reason. Swapping in a Prism theme stylesheet such as `dracula-prism` does not help: it is dark-only too. Diff lines (`.token.inserted`, `.token.deleted`) map to green and red so a `diff` block reads as one; they show only on a site whose `--langs` includes `diff`.
- **Mermaid labels and highlighted nodes.** Mermaid's dark theme colors every label `#ccc`, which is 4.4:1 on its own `#585858` edge-label fill. Its rules are scoped by the SVG's id, so the template's `.mermaid :is(.nodeLabel, .edgeLabel, .cluster-label)` rule needs `!important` to set labels to `--base-color`. A page that calls out a node with `style <node> fill:<hex>` sets a fill and no label color, so the label keeps the theme's: readable on a mid-tone fill such as `#f96` in light mode, 1.3:1 on it in dark. The diagram can't fix this itself, because mermaid's parser rejects any parenthesis in `style` and `classDef`, `var()` included. Pages mark the node with `class <node> highlight` instead, and the template colors it from `--diagram-highlight-fill` and `--diagram-highlight-stroke`. In the hand-drawn look a fill is hatching: rough.js draws it as a stroked path ahead of the outline path, so the rule sets `stroke` on `path:first-child` and `path:last-child`, and the fill is a tint because the label has to read against both the hatch lines and the background between them.

## Design constraints

Three rules govern all the template's CSS:

1. **WCAG 2.1 AA contrast**: 4.5:1 for body text, 3:1 for large text and UI/graphical components. The Alucard light palette is tuned for this; if you adjust palette colors, run a contrast check on every foreground/background pairing. Notable trap: Dracula `comment` (`#6272a4`) is borderline against both backgrounds, so verify any text that uses it. Validate swapped-in Pro Alucard values with a tool like the [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/); the Pro palette is optimized for editor UIs, not prose on `#f8f8f2`. Then run `scripts/docsify/check-contrast.js` on a served site: a color passes on the page background and fails on the backgrounds stacked on it. Alucard's accents are 4.6:1 on `#f8f8f2` and 3.9:1 on `--alucard-current` (table rows, blockquotes), which is why `--link-color` mixes `--alucard-cyan` 80% toward black. Plugins bring their own colors too: flexible-alerts titles are 1.8–4.3:1 until the `--alert-*-color` rules replace them. The script's text walk skips `<svg>`, so it measures mermaid labels separately, against their node's fill or hatch and the background between the hatch lines.

2. **`light-dark()` for all themed values**: every semantic variable provides both theme values in a single declaration. Architecture: (a) both palettes defined unconditionally in `:root`, (b) `[data-theme]` selectors set only `color-scheme`, (c) all semantic mappings use `light-dark(light-value, dark-value)`. This makes it structurally impossible to forget a mode. The only remaining `[data-theme="light"]`/`[data-theme="dark"]` selectors are for the toggle icon show/hide (opacity/transform), which are structural, not color.

3. **Semantic color names only**: colors live in three layers: raw palette tokens (`--dracula-cyan`, `--alucard-purple`) defined once in the `:root` palette block; semantic variables (`--link-color`, `--hover-color`, `--corner-accent`) that map palette tokens to purpose via `light-dark()`; and CSS rules that reference **only** semantic variables. No palette token or hardcoded hex/RGB/HSL in an element rule.

   - `--link-color: light-dark(var(--alucard-cyan), var(--dracula-cyan));`: correct (semantic variable aliasing palette tokens)
   - `color: var(--link-color)`: correct (rule uses semantic variable)
   - `color: var(--dracula-cyan)`: wrong (palette token in a rule; won't communicate intent or adapt to themes)
   - `color: #8be9fd`: wrong (hardcoded value outside the palette block)
