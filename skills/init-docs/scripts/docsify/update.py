#!/usr/bin/env python3
"""Bring an existing docsify hub current: the deterministic half of
/masthead:update-docs on the docsify engine.

Two jobs, both reported before anything is written:

1. Template drift. Read the template's values back out of docs/index.html (the
   name, repo URL, host, Prism languages, Mermaid), render the current template
   with them, and compare the two block by block. When the site carries a stamp
   whose template is in template-history.json, each block is classified:

     upstream          the template changed it; the site's copy is untouched
     added / removed   the template gained or dropped it; the site's copy is untouched
     local             the site changed it; the template's is unchanged
     conflict          both changed it, so someone has to choose

   Without a stamp (a site made before stamps, or by hand) the differences are
   printed as one diff, unclassified, for the model to sort out.

2. Findings. Check the sidebar and pages against the practices the docsify
   reference describes, each with a rule ID (LINT-02..h in SPEC.md), the
   file and line, and the reference section that explains it.

--apply writes the merged template (upstream changes in, local edits kept) and
stamps the site with the current template. It refuses while a conflict has no
--resolve, and on an unstamped site unless --adopt says to replace the file
with the current template outright. Findings are never fixed here: they need
judgment, and the model proposes each fix (see the update-docs SKILL.md).

Exit status: 0, or with --check 1 when the template has moved on or any finding
is reported; 2 when the script can't proceed.

Usage:
  update.py [REPO_PATH] [--docs DIR] [--diff] [--json] [--check]
            [--apply [--resolve BLOCK=site|template ...] [--adopt]]
"""

import argparse
import difflib
import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import init
import template_blocks as tb

REFERENCE = "skills/init-docs/references/docsify.md"
INIT_SKILL = "skills/init-docs/SKILL.md"
RULES = {
    "LINT-02": (REFERENCE, "Pick one form per level"),
    "LINT-03": (REFERENCE, "Give every entry its own href"),
    "LINT-04": (REFERENCE, "Long lists get an index page"),
    "LINT-05": (REFERENCE, "Match file names case-exactly"),
    "LINT-06": (REFERENCE, "Writing links"),
    "LINT-07": (REFERENCE, "Give every entry its own href"),
    "LINT-08": (INIT_SKILL, "4. Sort the existing docs by audience"),
    "LINT-09": (INIT_SKILL, "7. Design the icon"),
    "LINT-10": (REFERENCE, "A linked section heading"),
}

STATUS_TEXT = {
    "upstream": "the template changed it; the site's copy is untouched, so it takes the template's",
    "added": "new in the template",
    "removed": "dropped from the template; the site's copy is untouched, so it goes",
    "local": "edited in the site; the template's is unchanged, so the edit stays",
    "local-added": "only in the site, so it stays",
    "local-removed": "removed from the site; the template's is unchanged, so it stays out",
    "conflict": "edited in the site and changed in the template",
}
CHANGES = {"upstream", "added", "removed"}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


# ── The site's own values ───────────────────────────────────

def recover_values(repo, site):
    """The substitutions the template was rendered with, read back from the
    site. Falls back to what init.py would detect for anything the site
    doesn't say."""
    def find(pattern):
        m = re.search(pattern, site, re.MULTILINE)
        return m.group(1) if m else None

    url = find(r"^\s*repo:\s*'([^']*)'")
    if url is None:
        url = init._to_https(init.git(repo, "remote", "get-url", "origin"))
    name = find(r"^\s*name:\s*'((?:[^'\\]|\\.)*)'")
    if name is None:
        name = init._org_and_name(url or "")[1] or repo.name
    if ".github-corner svg { display: none; }" in site:
        host = "gitlab"
    else:
        host = init._host_of(url or "") or "github"
    langs = re.findall(r"prismjs@1/components/prism-([\w-]+)\.min\.js", site)
    mermaid = bool(re.search(r"<script[^>]+src=\"[^\"]*mermaid[^\"]*\.js\"", site))
    return {"name": name, "url": url or "", "host": host, "langs": langs, "mermaid": mermaid}


def render(template_text, v):
    return init.render_index(
        template_text, v["name"], v["url"], v["host"], v["langs"], v["mermaid"], "masthead"
    )


# ── Template comparison ─────────────────────────────────────

def classify(site_blocks, base_blocks, current_blocks):
    """One entry per block name: (name, status, site, base, current)."""
    S, B, C = dict(site_blocks), dict(base_blocks), dict(current_blocks)
    names = [n for n, _ in current_blocks]
    names += [n for n, _ in site_blocks if n not in C]
    names += [n for n, _ in base_blocks if n not in C and n not in S]
    out = []
    for n in names:
        s, b, c = S.get(n), B.get(n), C.get(n)
        if s is not None and c is not None:
            if s == c:
                status = None
            elif b is None:
                status = "conflict"  # the site has its own block by a name the template now uses
            elif s == b:
                status = "upstream"
            elif b == c:
                status = "local"
            else:
                status = "conflict"
        elif c is not None:  # not in the site
            if b is None:
                status = "added"
            elif b == c:
                status = "local-removed"
            else:
                status = "conflict"
        elif s is not None:  # not in the template
            if b is None:
                status = "local-added"
            elif s == b:
                status = "removed"
            else:
                status = "conflict"
        else:
            status = None  # removed on both sides
        if status:
            out.append({"block": n, "status": status, "site": s, "base": b, "current": c})
    return out


def merge(site_blocks, current_blocks, entries, resolutions):
    """The site with upstream changes in and local edits kept. Returns the text,
    or raises KeyError naming an unresolved conflict."""
    by_name = {e["block"]: e for e in entries}
    C = dict(current_blocks)
    result = []  # [(name, text)]
    for name, text in site_blocks:
        e = by_name.get(name)
        if e is None or e["status"] in ("local", "local-added"):
            result.append((name, text))
        elif e["status"] == "upstream":
            result.append((name, e["current"]))
        elif e["status"] == "removed":
            continue
        elif e["status"] == "conflict":
            choice = resolutions.get(name) or resolutions.get("all")
            if choice is None:
                raise KeyError(name)
            if choice == "site":
                result.append((name, text))
            elif e["current"] is not None:
                result.append((name, e["current"]))
    # Blocks the site doesn't have: new upstream ones, and conflicts resolved
    # to the template. Each goes after the block that precedes it in the template.
    order = [n for n, _ in current_blocks]
    for name in order:
        e = by_name.get(name)
        if e is None or e["site"] is not None:
            continue
        if e["status"] == "conflict":
            choice = resolutions.get(name) or resolutions.get("all")
            if choice is None:
                raise KeyError(name)
            if choice == "site":
                continue
        elif e["status"] != "added":
            continue
        have = [n for n, _ in result]
        prev = next((p for p in reversed(order[: order.index(name)]) if p in have), None)
        at = have.index(prev) + 1 if prev else 0
        result.insert(at, (name, C[name]))
    return "".join(text for _, text in result)


def stamp(text, generator):
    """Put the stamp line in a site's head, replacing any there."""
    line = f'  <meta name="generator" content="{generator}">'
    lines = [l for l in text.split("\n") if not tb.GENERATOR_LINE_RE.match(l)]
    at = next((i + 1 for i, l in enumerate(lines) if re.search(r"<meta\s+charset", l, re.I)), None)
    if at is None:
        at = next((i + 1 for i, l in enumerate(lines) if re.search(r"<head\b", l, re.I)), 0)
    lines.insert(at, line)
    return "\n".join(lines)


def udiff(a, b, a_name, b_name):
    return "".join(difflib.unified_diff(
        (a or "").splitlines(keepends=True), (b or "").splitlines(keepends=True),
        fromfile=a_name, tofile=b_name, n=2,
    ))


def compare_template(repo, index):
    site = index.read_text(encoding="utf-8")
    report = {"site": index.relative_to(repo).as_posix()}
    if "window.$docsify" not in site:
        report["mode"] = "no-template"
        report["note"] = ("docs/index.html has no window.$docsify config of its own (a shared "
                          "loader?), so there's no template to compare it with")
        return report, site, None
    values = recover_values(repo, site)
    template = tb.TEMPLATE.read_text(encoding="utf-8")
    current_fp = tb.fingerprint(template)
    current = render(template, values)
    report["values"] = values
    report["template"] = tb.generator(template)
    st = tb.read_stamp(site)
    report["stamp"] = f"masthead {st[0]}; template {st[1]}" if st else None
    history = tb.load_history()
    base_raw = tb.template_blocks(history, st[1]) if st else None

    if base_raw is None:
        report["mode"] = "unclassified"
        if st:
            report["note"] = (f"the stamp's template ({st[1]}) isn't in this masthead's history "
                              "(a newer masthead made it?), so its blocks can't be classified")
        diff = udiff(tb.normalize(site), tb.normalize(current), "site", "current template")
        report["diff"] = diff
        report["up_to_date"] = not diff and st is not None and st[1] == current_fp
        return report, site, {"current": current, "generator": tb.generator(template)}

    report["mode"] = "classified"
    base = render("".join(t for _, t in base_raw), values)
    site_blocks = tb.split_blocks(site)
    current_blocks = tb.split_blocks(current)
    entries = classify(site_blocks, tb.split_blocks(base), current_blocks)
    report["blocks"] = entries
    report["up_to_date"] = st[1] == current_fp and not any(e["status"] in CHANGES | {"conflict"} for e in entries)
    return report, site, {
        "site_blocks": site_blocks, "current_blocks": current_blocks,
        "entries": entries, "generator": tb.generator(template), "current": current,
    }


# ── Findings ────────────────────────────────────────────────

FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
LINK_RE = re.compile(r"(!?)\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
REFLINK_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)")
HTML_RE = re.compile(r"<(a|img)\b[^>]*?\s(href|src)=\"([^\"]+)\"", re.I)
SKIP_DIRS = {"node_modules", ".git"}


def strip_code(text):
    """The text with fenced blocks blanked and inline code spans removed, line for line."""
    out, fenced = [], False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            fenced = not fenced
            out.append("")
        elif fenced:
            out.append("")
        else:
            out.append(re.sub(r"`+[^`]*`+", "", line))
    return out


def links(text):
    """(line number, target, is_image) for every link in markdown text."""
    for i, line in enumerate(strip_code(text), 1):
        for m in LINK_RE.finditer(line):
            yield i, m.group(2), m.group(1) == "!"
        m = REFLINK_RE.match(line)
        if m:
            yield i, m.group(1), False
        for m in HTML_RE.finditer(line):
            yield i, m.group(3), m.group(1).lower() == "img"


def resolve(target, page_dir):
    """What a link points at under docs/: ("file", path), ("outside", path), or
    ("skip", None) for external links and in-page anchors. A route resolves the
    way docsify does: `x/` to x/README.md, `x` to x.md."""
    t = target.strip()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", t) or t.startswith("//"):
        return "skip", None
    if t.startswith("#/"):
        t = t[1:]
    elif t.startswith("#"):
        return "skip", None
    t = unquote(re.split(r"[?#]", t, maxsplit=1)[0])
    if not t:
        return "skip", None
    if t.startswith("/"):
        joined = posixpath.normpath(t.lstrip("/") or ".")
    else:
        joined = posixpath.normpath(posixpath.join(page_dir, t))
    if joined == ".":
        joined = ""
    if joined == ".." or joined.startswith("../"):
        return "outside", joined
    last = joined.rsplit("/", 1)[-1]
    if t.endswith("/") or not joined:
        path = posixpath.join(joined, "README.md") if joined else "README.md"
    elif "." not in last:
        path = joined + ".md"
    else:
        path = joined
    return "file", path


def exists_exact(docs, rel):
    """'ok', 'missing', or the path as it exists in a different letter case."""
    cur, actual = docs, []
    for part in rel.split("/"):
        try:
            entries = {p.name: p for p in cur.iterdir()}
        except (NotADirectoryError, FileNotFoundError):
            return "missing"
        if part in entries:
            cur = entries[part]
            actual.append(part)
            continue
        alt = next((n for n in entries if n.lower() == part.lower()), None)
        if alt is None:
            return "missing"
        cur = entries[alt]
        actual.append(alt)
    return "ok" if "/".join(actual) == rel else "/".join(actual)


def parse_sidebar(text):
    """Sidebar entries as dicts: line, depth, kind (label, link, text), href,
    parent (index or None), children (indexes), and bold_link when the bold is
    inside the link (`[**X**](path)`) rather than around it."""
    items, stack = [], []  # stack of (indent, index)
    for no, line in enumerate(text.split("\n"), 1):
        m = re.match(r"^(\s*)[-*+]\s+(.*\S)\s*$", line)
        if not m:
            continue
        indent = len(m.group(1).replace("\t", "    "))
        body = m.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else None
        link = LINK_RE.search(body)
        if re.match(r"^\*\*.*\*\*$", body):
            kind = "label"
        elif link and link.start() == 0:
            kind = "link"
        else:
            kind = "text"
        item = {"line": no, "depth": len(stack), "kind": kind,
                "href": link.group(2) if link else None, "parent": parent, "children": [],
                "bold_link": bool(re.match(r"^\[\*\*.*\*\*\]\(", body))}
        items.append(item)
        if parent is not None:
            items[parent]["children"].append(len(items) - 1)
        stack.append((indent, len(items) - 1))
    return items


def finding(rule, path, line, message):
    ref, section = RULES[rule]
    return {"rule": rule, "file": path, "line": line, "message": message,
            "reference": f"{ref}, \"{section}\""}


def find_issues(repo, docs, site_text):
    out = []
    rel = lambda p: p.relative_to(repo).as_posix()
    docs_rel = docs.relative_to(repo).as_posix()
    spec = init.detect_spec(repo)
    has_config = site_text is not None and "window.$docsify" in site_text

    def check_target(src, line, target, page_dir):
        kind, path = resolve(target, page_dir)
        if kind == "outside":
            out.append(finding("LINT-05", src, line,
                               f"`{target}` points outside {docs_rel}/, which the site doesn't publish"))
            return None
        if kind != "file":
            return None
        if spec and path == spec and (repo / spec).is_file():
            return path  # the build copies the spec in
        state = exists_exact(docs, path)
        if state == "missing":
            out.append(finding("LINT-05", src, line, f"`{target}` points at {docs_rel}/{path}, which doesn't exist"))
        elif state != "ok":
            out.append(finding("LINT-05", src, line,
                               f"`{target}` points at {docs_rel}/{path}, which exists only as {docs_rel}/{state}; "
                               "Pages hosts match case-exactly"))
        return path

    # Sidebar
    sidebar_path = docs / "_sidebar.md"
    sidebar_targets = []
    if sidebar_path.is_file():
        src = rel(sidebar_path)
        items = parse_sidebar(sidebar_path.read_text(encoding="utf-8"))
        groups = {}
        for i, it in enumerate(items):
            groups.setdefault(it["parent"], []).append(i)
        for parent, members in groups.items():
            labels = [i for i in members if items[i]["kind"] == "label"]
            folders = [i for i in members if items[i]["kind"] == "link" and items[i]["children"]]
            if labels and folders:
                out.append(finding("LINT-02", src, items[folders[0]]["line"],
                                   "this level mixes `**Section**` labels with linked sections that have children; "
                                   "they render as different kinds of thing"))
        for it in items:
            if it["bold_link"]:
                out.append(finding("LINT-10", src, it["line"],
                                   "the bold is inside the link, so docsify renders a bold link rather than a "
                                   "section heading; write `**[Section](path)**`"))
            if it["href"] and it["kind"] in ("link", "label") and it["children"]:
                seen = {it["href"]: it["line"]}
                for c in it["children"]:
                    href = items[c]["href"]
                    if href is None:
                        continue
                    if href in seen:
                        out.append(finding("LINT-03", src, items[c]["line"],
                                           f"`{href}` is also the href on line {seen[href]}; docsify merges entries "
                                           "that share one"))
                    else:
                        seen[href] = items[c]["line"]
            if it["href"] and (it["children"] or it["depth"] == 0) and \
                    re.match(r"^(#/|/)?(README(\.md)?)?\?(.*&)?id=", it["href"]):
                out.append(finding("LINT-04", src, it["line"],
                                   f"`{it['href']}` is a section on the home route, so it expands on every visit "
                                   "to the home page; give the section its own index page"))
        for it in items:
            if it["href"]:
                path = check_target(src, it["line"], it["href"], "")
                if path:
                    sidebar_targets.append(path)

    # Pages
    pages = {}
    for p in sorted(docs.rglob("*.md")):
        parts = p.relative_to(docs).parts
        if any(x in SKIP_DIRS or x.startswith(".") for x in parts[:-1]):
            continue
        pages[p.relative_to(docs).as_posix()] = p
    relative_ok = bool(has_config and re.search(r"relativePath\s*:\s*true", site_text))
    edges = {}
    for page_rel, p in pages.items():
        if p.name.startswith("_"):
            continue
        src = rel(p)
        page_dir = posixpath.dirname(page_rel)
        edges[page_rel] = []
        for line, target, image in links(p.read_text(encoding="utf-8", errors="ignore")):
            path = check_target(src, line, target, page_dir)
            if path:
                edges[page_rel].append(path)
            if (has_config and not relative_ok and not image and page_dir and path
                    and not target.startswith(("/", "#"))):
                out.append(finding("LINT-06", src, line,
                                   f"`{target}` is relative, but the site doesn't set `relativePath: true`, so "
                                   "docsify resolves it from the site root rather than this page"))

    # Config
    if has_config:
        m = re.search(r"subMaxLevel\s*:\s*(\d+)", site_text)
        if m and int(m.group(1)) > 0:
            line = site_text[: m.start()].count("\n") + 1
            out.append(finding("LINT-07", f"{docs_rel}/index.html", line,
                               f"`subMaxLevel: {m.group(1)}` adds each page's headings to the sidebar as children "
                               "of its entry; the page-contents rail is where a page's headings go"))

    # Reach: from the home page and the sidebar, through page links
    seen, todo = set(), ["README.md"] + sidebar_targets
    while todo:
        page = todo.pop()
        if page in seen:
            continue
        seen.add(page)
        todo.extend(edges.get(page, []))
    for page_rel in pages:
        if page_rel not in seen and not posixpath.basename(page_rel).startswith("_"):
            out.append(finding("LINT-08", f"{docs_rel}/{page_rel}", 1,
                               "no sidebar entry reaches this page, directly or through the pages it links"))

    if not (docs / "favicon.svg").is_file():
        out.append(finding("LINT-09", f"{docs_rel}/favicon.svg", 0,
                           "the site has no favicon.svg, its browser icon, sidebar logo, and home page icon"))
    return out


# ── Output ──────────────────────────────────────────────────

def print_report(report, findings, show_diff):
    print(f"Site:      {report['site']}")
    if "values" in report:
        v = report["values"]
        print(f"Stamp:     {report['stamp'] or 'none'}")
        print(f"Template:  {report['template']}")
        print(f"Values:    name {v['name']!r}, repo {v['url'] or '(none)'}, host {v['host']}, "
              f"Prism {', '.join(v['langs']) or '(none)'}, Mermaid {'on' if v['mermaid'] else 'off'}")
    if report.get("note"):
        print(f"Note:      {report['note']}")
    print()

    mode = report["mode"]
    if mode == "classified":
        entries = report["blocks"]
        if not entries:
            print("Template: every block matches the current template.")
        else:
            print("Template blocks that differ:")
            width = max(len(e["block"]) for e in entries)
            for e in entries:
                hint = f" (--resolve {e['block']}=site|template)" if e["status"] == "conflict" else ""
                print(f"  {e['status']:<13} {e['block']:<{width}}  {STATUS_TEXT[e['status']]}{hint}")
            for e in entries:
                if e["status"] == "conflict":
                    print(f"\n--- conflict in {e['block']}: what the template changed")
                    print(udiff(e["base"], e["current"], "template then", "template now") or "(nothing)\n", end="")
                    print(f"--- conflict in {e['block']}: what the site changed")
                    print(udiff(e["base"], e["site"], "template then", "site") or "(nothing)\n", end="")
                elif show_diff and e["status"] in CHANGES:
                    print(f"\n--- {e['status']}: {e['block']}")
                    print(udiff(e["site"], e["current"], "site", "current template"), end="")
    elif mode == "unclassified":
        if report["diff"]:
            print("Template: the site differs from the current template. Without a recorded stamp the "
                  "differences can't be told apart; read them against the template notes:")
            print(report["diff"], end="")
        else:
            print("Template: the site matches the current template" +
                  ("." if report["up_to_date"] else ", but carries no stamp; --apply --adopt adds one."))
    print()

    if findings:
        print("Findings:")
        for f in findings:
            where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            print(f"  {f['rule']}  {where}")
            print(f"      {f['message']}")
            print(f"      see {f['reference']}")
    else:
        print("Findings: none.")


def parse_resolutions(values):
    out = {}
    for v in values or []:
        m = re.match(r"^([a-z0-9#-]+)=(site|template)$", v)
        if not m:
            die(f"--resolve takes BLOCK=site or BLOCK=template (or all=...), not {v!r}")
        out[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser(description="Report, and on --apply carry in, what an existing docsify hub is missing.")
    ap.add_argument("repo", nargs="?", default=".", help="target repo path (default: .)")
    ap.add_argument("--docs", default="docs", help="the site's directory, relative to the repo (default: docs)")
    ap.add_argument("--diff", action="store_true", help="print the diff for each upstream change too")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when the template has moved on or there is any finding")
    ap.add_argument("--apply", action="store_true", help="write the merged template and stamp the site")
    ap.add_argument("--resolve", action="append", metavar="BLOCK=site|template",
                    help="with --apply: which side a conflicting block keeps (repeatable; all=... for every one)")
    ap.add_argument("--adopt", action="store_true",
                    help="with --apply on a site the template can't be classified against: replace "
                         "docs/index.html with the current template, rendered with the site's values")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not init.git(repo, "rev-parse", "--git-dir"):
        die(f"{repo} is not a git repository")
    owner = init.other_owner(repo)
    if owner:
        die(f"this repo's docs site is built by {owner}, not masthead; update it there.")
    docs = (repo / args.docs).resolve()
    index = docs / "index.html"
    if not index.is_file() or "docsify" not in index.read_text(encoding="utf-8", errors="ignore"):
        die(f"no docsify hub at {args.docs}/index.html. To stand one up, use /masthead:init-docs.")

    report, site, state = compare_template(repo, index)
    resolutions = parse_resolutions(args.resolve)

    if args.apply:
        if state is None:
            die(report["note"] + "; nothing to apply.")
        if report["mode"] == "classified":
            try:
                merged = merge(state["site_blocks"], state["current_blocks"], state["entries"], resolutions)
            except KeyError as e:
                die(f"the {e.args[0]} block conflicts; ask which to keep and pass "
                    f"--resolve {e.args[0]}=site or --resolve {e.args[0]}=template")
        else:
            if not args.adopt:
                die("the site can't be classified against the template, so --apply would replace it "
                    "outright. Carry its local edits across afterward, and pass --adopt to go ahead.")
            merged = state["current"]
        index.write_text(stamp(merged, state["generator"]), encoding="utf-8")
        report, site, state = compare_template(repo, index)
        report["applied"] = True

    findings = find_issues(repo, docs, site)
    if args.json:
        print(json.dumps({"template": report, "findings": findings}, indent=2))
    else:
        if report.get("applied"):
            print(f"Applied: {report['site']} now carries the current template ({report['template']}).\n")
        print_report(report, findings, args.diff)

    if args.check and (findings or (report["mode"] != "no-template" and not report["up_to_date"])):
        sys.exit(1)


if __name__ == "__main__":
    main()
