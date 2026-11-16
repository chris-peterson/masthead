#!/usr/bin/env python3
"""The docsify template as named blocks, and the history of every template a
released site may have been made from.

A marker comment (`<!-- masthead:block NAME -->`, `/* masthead:block NAME */`,
or `// masthead:block NAME`) starts a block, which runs to the next marker. The
lines before the first marker are the block named "document". Markers survive
into every generated site, so a site splits into the same blocks as the
template it came from.

A generated site is stamped with the version of masthead that wrote it and a
fingerprint of its template:

    <meta name="generator" content="masthead <semver>; template <fingerprint>">

template-history.json keeps every recorded template as its ordered list of
blocks, and each distinct block's raw text once. update.py renders the stamped
template's blocks with the site's own values to tell an upstream change (the
template moved on, the site's copy is untouched) from a local edit (someone
changed the site).

Any change to assets/docsify/index.html has to be recorded before it ships, or
a site made from it can't be updated block by block later:

    python3 template_blocks.py record     # add the current template (`just record-template`)
    python3 template_blocks.py check      # exit 1 if it isn't recorded (the tests run this)
    python3 template_blocks.py fingerprint
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "docsify"
TEMPLATE = ASSETS / "index.html"
HISTORY = ASSETS / "template-history.json"
PLUGIN_ROOT = Path(__file__).resolve().parents[4]

FIRST_BLOCK = "document"
MARKER_RE = re.compile(r"masthead:block ([a-z0-9-]+)")
# The stamp line, filled or still a placeholder. It changes on every release,
# so blocks are compared without it.
GENERATOR_LINE_RE = re.compile(r'^\s*<meta name="generator" content="(?:masthead[^"]*|\{\{GENERATOR\}\})">\s*$')
STAMP_RE = re.compile(r'<meta name="generator" content="masthead (\S+); template ([0-9a-f]{12})">')


def normalize(text):
    """The text blocks are compared on: LF line endings, no trailing spaces, no
    stamp line, no trailing blank lines."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [l.rstrip() for l in lines if not GENERATOR_LINE_RE.match(l)]
    return "\n".join(lines).rstrip("\n") + "\n"


def split_blocks(text):
    """Split template or site text into an ordered list of (name, text). A name
    repeated in the same text gets a #2, #3 suffix so each block stays distinct."""
    blocks, name, buf, seen = [], FIRST_BLOCK, [], {}
    for line in normalize(text).rstrip("\n").split("\n"):
        m = MARKER_RE.search(line)
        if m:
            if buf or name != FIRST_BLOCK:
                blocks.append((name, "\n".join(buf) + "\n"))
            name, buf = m.group(1), []
            seen[name] = seen.get(name, 0) + 1
            if seen[name] > 1:
                name = f"{name}#{seen[name]}"
        buf.append(line)
    blocks.append((name, "\n".join(buf) + "\n"))
    return blocks


def has_markers(text):
    return bool(MARKER_RE.search(text))


def _hash(text, n):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def fingerprint(template_text):
    return _hash(normalize(template_text), 12)


def block_hash(text):
    return _hash(text, 16)


def plugin_version():
    """The version of masthead this checkout or install is."""
    pj = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(pj.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        pass
    py = PLUGIN_ROOT / "plugin.yml"
    if py.is_file():
        m = re.search(r"^version:\s*(\S+)", py.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            return m.group(1)
    return "unknown"


def generator(template_text):
    """The stamp's content for a site rendered from template_text."""
    return f"masthead {plugin_version()}; template {fingerprint(template_text)}"


def read_stamp(site_text):
    """(masthead version, template fingerprint) from a site, or None."""
    m = STAMP_RE.search(site_text)
    return (m.group(1), m.group(2)) if m else None


def load_history(path=HISTORY):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"templates": {}, "blocks": {}}


def template_blocks(history, fp):
    """The raw blocks of a recorded template, as [(name, text)], or None."""
    entry = history["templates"].get(fp)
    if entry is None:
        return None
    return [(name, history["blocks"][h]) for name, h in entry["blocks"]]


def record(template_text, path=HISTORY):
    """Add a template to the history. Returns its fingerprint and whether it was new."""
    history = load_history(path)
    fp = fingerprint(template_text)
    if fp in history["templates"]:
        return fp, False
    entry = []
    for name, text in split_blocks(template_text):
        h = block_hash(text)
        history["blocks"].setdefault(h, text)
        entry.append([name, h])
    history["templates"][fp] = {"blocks": entry}
    path.write_text(json.dumps(history, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return fp, True


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    text = TEMPLATE.read_text(encoding="utf-8")
    fp = fingerprint(text)
    if cmd == "fingerprint":
        print(fp)
    elif cmd == "record":
        fp, new = record(text)
        print(f"template {fp} {'recorded' if new else 'already recorded'} in {HISTORY.name}")
    elif cmd == "check":
        if fp not in load_history()["templates"]:
            print(
                f"error: the current template ({fp}) isn't in {HISTORY.name}. Record it "
                "with `just record-template`, so sites made from it can be updated later.",
                file=sys.stderr,
            )
            return 1
        print(f"template {fp} is recorded")
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
