// Drives a served docsify site's search the way a reader would, and reports
// every result that reads wrong or lands nowhere. Runs inside the page: pass
// this whole file as the function to Playwright MCP's `browser_evaluate`, or
// to `page.evaluate()`, on any page of the site. Clean when `problems` is empty.
//
// For each page the sidebar links, it records the ids that page renders, then
// searches for every heading on it and checks each result:
//   raw-markup  a title or snippet showing markdown link syntax, an HTML
//               element, or a comment (backticks count in a title only)
//   dead-link   a result whose ?id= matches no id on the page it opens
//   not-found   a heading whose own text returns no result titled with it
//               (search.depth too shallow, or the title is the raw markdown)
async () => {
  const SETTLE_MS = 700;
  const QUERY_MS = 250;
  // Element names, not any <word>: a rendered snippet carries the page's own
  // text, and docs are full of <branch>-style placeholders that are content.
  const TAG = /<\/?(?:a|b|br|code|details|div|em|h[1-6]|i|img|kbd|li|ol|p|pre|span|strong|sub|summary|sup|table|td|th|tr|ul)\b[^<>]*>/i;
  const RAW_MARKUP = new RegExp(TAG.source + /|<!--|"\s*>|\]\(/.source, 'i');
  // A code block's source can hold backticks, so only a title is checked for them.
  const RAW_TITLE = new RegExp(RAW_MARKUP.source + /|`/.source, 'i');
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const input = document.querySelector('.search input');
  if (!input) throw new Error('no docsify search input on this page');

  const section = () => document.querySelector('.markdown-section');
  async function visit(route) {
    if ((location.hash.split('?')[0] || '#/') === route) return;
    const marker = document.createElement('i');
    marker.dataset.checkSearchStale = '';
    section().appendChild(marker);
    location.hash = route;
    for (let i = 0; i < 100 && section().querySelector('[data-check-search-stale]'); i++) await wait(50);
    await wait(SETTLE_MS);
  }
  function headingText(h) {
    const clone = h.cloneNode(true);
    clone.querySelectorAll('button, .heading-tools').forEach((n) => n.remove());
    return clone.textContent.trim();
  }

  const startHash = location.hash;
  const routes = [...new Set([...document.querySelectorAll('.sidebar-nav a[href^="#/"]')]
    .map((a) => a.getAttribute('href').split('?')[0]))];
  const ids = {};
  const headings = [];
  for (const route of routes) {
    await visit(route);
    ids[route] = new Set([...section().querySelectorAll('[id]')].map((e) => e.id));
    section().querySelectorAll('h2[id], h3[id], h4[id], h5[id], h6[id]').forEach((h) => {
      headings.push({ route, id: h.id, text: headingText(h) });
    });
  }

  const problems = [];
  const seen = new Set();
  const report = (kind, detail) => {
    const key = kind + '|' + JSON.stringify(detail);
    if (!seen.has(key)) { seen.add(key); problems.push({ kind, ...detail }); }
  };
  for (const h of headings) {
    input.value = h.text;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await wait(QUERY_MS);
    const results = [...document.querySelectorAll('.search .matching-post > a')].map((a) => ({
      title: (a.querySelector('h2') || a).textContent.trim(),
      snippet: (a.querySelector('p') || { textContent: '' }).textContent.trim(),
      href: a.getAttribute('href') || '',
    }));
    for (const r of results) {
      if (RAW_TITLE.test(r.title) || RAW_MARKUP.test(r.snippet)) {
        report('raw-markup', { query: h.text, title: r.title, snippet: r.snippet.slice(0, 120) });
      }
      const [route, query] = r.href.split('?');
      const id = decodeURIComponent((/(?:^|&)id=([^&]+)/.exec(query || '') || [])[1] || '');
      if (id && ids[route] && !ids[route].has(id)) report('dead-link', { title: r.title, href: r.href });
    }
    if (!results.some((r) => r.title === h.text)) report('not-found', { heading: h.text, page: h.route });
  }

  input.value = '';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await visit(startHash.split('?')[0] || '#/');
  return { pages: routes.length, headings: headings.length, problems };
}
