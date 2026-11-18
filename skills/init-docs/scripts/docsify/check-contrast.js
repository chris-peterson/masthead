// Measures WCAG 2.1 AA contrast across a served docsify site in both themes,
// and reports every pairing below the bar. Runs inside the page: pass this
// whole file as the function to Playwright MCP's `browser_evaluate`, or to
// `page.evaluate()`, on any page of the site. Clean when `problems` is empty.
//
// Each sidebar page is visited in light and then dark. On every one:
//   text  each visible text node against the background it sits on, 4.5:1,
//         or 3:1 when the text is large (24px, or 18.66px bold)
//   ui    the controls a reader has to find (search icon and input border,
//         theme-toggle icons, code copy button), 3:1
//   text  each mermaid node, edge, and subgraph label against the fill it
//         sits on, which the text walk can't see from inside the <svg>, 4.5:1
// Search results are checked after a query for the first page heading, and
// one alert of each flexible-alerts type is added to the first page, since a
// site rarely uses all five. Serve the page with a cache-busting query
// (`/?v=<n>#/`): a browser holding the old index.html measures the old CSS.
async () => {
  const SETTLE_MS = 900;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const html = document.documentElement;
  const startTheme = html.getAttribute('data-theme');
  const startHash = location.hash;

  const parse = (s) => {
    let m = s.match(/rgba?\(([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
    }
    // color-mix() and light-dark() resolve to color(srgb r g b / a).
    m = s.match(/color\(srgb ([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[ /]+/).filter(Boolean).map(Number);
      return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1];
    }
    return null;
  };
  const over = (top, under) => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat(1);
  // Composite every translucent background up to the first opaque one.
  const backgroundOf = (el) => {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) {
        layers.push(c);
        if (c[3] >= 1) break;
      }
    }
    let base = parse(getComputedStyle(document.body).backgroundColor) || [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) base = over(layers[i], base);
    return base;
  };
  const luminance = (c) => {
    const f = (v) => ((v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const ratio = (a, b) => {
    const [x, y] = [luminance(a), luminance(b)];
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const describe = (el) => {
    const cls = (n) => (typeof n.className === 'string' && n.className.trim() ? '.' + n.className.trim().split(/\s+/).join('.') : '');
    const p = el.parentElement;
    return `${p ? p.tagName.toLowerCase() + cls(p) + ' > ' : ''}${el.tagName.toLowerCase()}${cls(el)}`;
  };

  const problems = new Map();
  const report = (theme, route, kind, element, sample, fg, bg, need) => {
    const r = ratio(fg, bg);
    if (r >= need) return;
    const key = [theme, kind, element, hex(fg), hex(bg)].join('|');
    if (!problems.has(key)) {
      problems.set(key, { theme, kind, element, sample, fg: hex(fg), bg: hex(bg), ratio: +r.toFixed(2), need, routes: [] });
    }
    problems.get(key).routes.push(route);
  };

  const checkText = (theme, route) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      const el = t.parentElement;
      if (!t.textContent.trim() || !el || el.closest('svg, script, style, noscript')) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || !el.getClientRects().length || +cs.opacity === 0) continue;
      const color = parse(cs.color);
      if (!color) continue;
      const bg = backgroundOf(el);
      const size = parseFloat(cs.fontSize);
      const large = size >= 24 || (size >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
      report(theme, route, 'text', describe(el), t.textContent.trim().slice(0, 40), over(color, bg), bg, large ? 3 : 4.5);
    }
    const input = document.querySelector('.search input');
    if (input) {
      const ph = parse(getComputedStyle(input, '::placeholder').color);
      const bg = backgroundOf(input);
      if (ph) report(theme, route, 'text', 'search input::placeholder', input.placeholder, over(ph, bg), bg, 4.5);
    }
  };

  const checkControls = (theme, route) => {
    const wrap = document.querySelector('.sidebar .search .input-wrap');
    if (wrap) {
      const icon = parse(getComputedStyle(wrap, '::before').backgroundColor);
      if (icon && icon[3] > 0) report(theme, route, 'ui', 'search icon', '', over(icon, backgroundOf(wrap)), backgroundOf(wrap), 3);
    }
    const input = document.querySelector('.search input');
    if (input) {
      const outside = backgroundOf(input.parentElement);
      report(theme, route, 'ui', 'search input border', '', over(parse(getComputedStyle(input).borderBottomColor), outside), outside, 3);
    }
    document.querySelectorAll('.theme-toggle [class*="theme-toggle-"]').forEach((el) => {
      const c = parse(getComputedStyle(el).color);
      if (c && el.getClientRects().length) report(theme, route, 'ui', describe(el), '', over(c, backgroundOf(el)), backgroundOf(el), 3);
    });
    // A pseudo-element with `content: none` keeps its computed background
    // color but never paints, so it says nothing about the button.
    const painted = (el, pseudo) => {
      const cs = getComputedStyle(el, pseudo);
      return cs.content === 'none' || cs.content === 'normal' ? null : parse(cs.backgroundColor);
    };
    document.querySelectorAll('pre button').forEach((el) => {
      let c = painted(el, '::before');
      if (!c || !c[3]) c = painted(el, '::after');
      if (!c || !c[3]) c = parse(getComputedStyle(el).color);
      if (c) report(theme, route, 'ui', 'code copy button', '', over(c, backgroundOf(el)), backgroundOf(el), 3);
    });
  };

  // A label reads against its own plate when it has one (edge labels do),
  // otherwise against every fill of its node or subgraph. A hand-drawn fill
  // is hatching: rough.js draws it as a stroked path ahead of the outline,
  // so the label has to clear both the hatch color and the gaps between.
  const checkDiagrams = (theme, route) => {
    document.querySelectorAll('.mermaid svg').forEach((svg) => {
      const behind = backgroundOf(svg);
      svg.querySelectorAll('.nodeLabel, .edgeLabel span, .cluster-label span').forEach((label) => {
        const text = label.textContent.trim();
        const fg = parse(getComputedStyle(label).color);
        if (!text || !fg || !label.getClientRects().length) return;
        let plate = null;
        for (let n = label; n && n.tagName.toLowerCase() !== 'foreignobject'; n = n.parentElement) {
          const c = parse(getComputedStyle(n).backgroundColor);
          if (c && c[3] > 0) { plate = over(c, behind); break; }
        }
        const grounds = [];
        const group = label.closest('g.node, g.rough-node, g.cluster');
        if (plate) grounds.push(plate);
        else if (group) {
          const shapes = [...group.querySelectorAll('path, rect, polygon, circle, ellipse')]
            .filter((s) => !s.closest('.label, .cluster-label, foreignObject'));
          shapes.forEach((s) => {
            const cs = getComputedStyle(s);
            const fill = parse(cs.fill);
            if (fill) grounds.push(over([fill[0], fill[1], fill[2], fill[3] * +cs.fillOpacity], behind));
          });
          const strokeOnly = shapes.filter((s) => getComputedStyle(s).fill === 'none');
          if (strokeOnly.length >= 2) {
            const hatch = parse(getComputedStyle(strokeOnly[0]).stroke);
            if (hatch) grounds.push(over(hatch, behind), behind);
          }
        }
        if (!grounds.length) grounds.push(behind);
        grounds.forEach((bg) => report(theme, route, 'text', 'mermaid label', text.slice(0, 40), over(fg, bg), bg, 4.5));
      });
    });
  };

  const section = () => document.querySelector('.markdown-section');
  const visit = async (route) => {
    location.hash = route;
    await wait(SETTLE_MS);
  };
  const addAlerts = () => {
    const box = document.createElement('div');
    box.dataset.checkContrast = '';
    box.innerHTML = ['note', 'tip', 'important', 'warning', 'attention']
      .map((t) => `<div class="alert callout ${t}"><p class="title">${t}</p><p>Sample ${t} body</p></div>`)
      .join('');
    section().prepend(box);
  };

  const routes = [...new Set(
    [...document.querySelectorAll('.sidebar-nav a[href^="#/"]')].map((a) => a.getAttribute('href').split('?')[0]),
  )];
  if (!routes.length) routes.push('#/');

  for (const theme of ['light', 'dark']) {
    html.setAttribute('data-theme', theme);
    let query = '';
    for (const [i, route] of routes.entries()) {
      await visit(route);
      if (i === 0) {
        addAlerts();
        const h = section().querySelector('h2, h1');
        query = h ? h.textContent.trim().split(/\s+/)[0] : '';
      }
      checkText(theme, route);
      checkControls(theme, route);
      checkDiagrams(theme, route);
    }
    const input = document.querySelector('.search input');
    if (input && query) {
      input.value = query;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      await wait(SETTLE_MS);
      checkText(theme, `search "${query}"`);
      input.value = '';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  if (startTheme) html.setAttribute('data-theme', startTheme);
  else html.removeAttribute('data-theme');
  await visit(startHash.split('?')[0] || '#/');
  const list = [...problems.values()].sort((a, b) => a.ratio - b.ratio);
  return { pages: routes.length, themes: 2, problems: list };
}
