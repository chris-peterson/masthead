#!/usr/bin/env python3
"""Read a GitLab project's Pages settings, or turn its unique domain off.

GitLab gives a new project a unique Pages domain by default
(`<project>-<hash>.<pages-domain>`) and redirects the namespace URL
(`<group>.<pages-domain>/<project>/`) to it. Turning the unique domain off
serves the site at the namespace URL instead, which is predictable, and which
other sites in the group can link to.

    gitlab_pages.py status [--repo PATH] [--project GROUP/PROJECT] [--hostname HOST]
    gitlab_pages.py unique-domain off|on [--repo PATH] [--project ...] [--hostname ...]

The project and host default to the repo's origin remote. Both commands call
the API through `glab api`, so glab must be logged in to the host. Reading needs
access to the project; changing the setting needs the Maintainer or Owner role
(GitLab 17.9 and later; before that, administrator).
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.parse


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def origin_project(repo):
    """(hostname, project path) from the repo's origin remote, or (None, None)."""
    try:
        origin = subprocess.run(
            ["git", "-C", repo, "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
    for pattern in (
        r"git@([^:]+):(.+?)(?:\.git)?/?$",
        r"ssh://git@([^/:]+)(?::\d+)?/(.+?)(?:\.git)?/?$",
        r"https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?/?$",
    ):
        m = re.match(pattern, origin)
        if m:
            return m.group(1), m.group(2)
    return None, None


def glab_api(hostname, path, *fields, method=None):
    cmd = ["glab", "api", "--hostname", hostname, path]
    if method:
        cmd += ["--method", method]
    for field in fields:
        cmd += ["--raw-field", field]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        die("glab is not on PATH; install it and run `glab auth login`.")
    if out.returncode != 0:
        detail = (out.stderr or out.stdout).strip()
        if "403" in detail:
            die(f"GitLab refused ({detail}). Changing Pages settings needs the "
                "Maintainer or Owner role (GitLab 17.9+), or an administrator before that.")
        if "404" in detail:
            die(f"GitLab returned 404 ({detail}). Check the project path, and that "
                "Pages is enabled and the pages job has deployed at least once.")
        die(f"glab api {path} failed: {detail}")
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        die(f"glab api {path} returned something that isn't JSON: {out.stdout[:200]}")


def print_status(pages):
    print(f"Site URL:       {pages.get('url') or 'none yet'}")
    unique = pages.get("is_unique_domain_enabled")
    state = "on" if unique else "off" if unique is not None else "unknown"
    print(f"Unique domain:  {state}")
    primary = pages.get("primary_domain") or pages.get("pages_primary_domain")
    if primary:
        print(f"Primary domain: {primary}")
    deployments = pages.get("deployments") or []
    if deployments:
        print("Deployments:")
        for d in deployments:
            prefix = d.get("path_prefix") or "(live)"
            print(f"  {prefix:<16} {d.get('url')}")


def main():
    ap = argparse.ArgumentParser(description="Read or change a GitLab project's Pages domain settings.")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="print the site URL, unique-domain state, and deployments")
    ud = sub.add_parser("unique-domain", help="turn the project's unique Pages domain off or on")
    ud.add_argument("state", choices=["off", "on"])
    for p in sub.choices.values():
        p.add_argument("--repo", default=".", help="repo whose origin names the project (default: .)")
        p.add_argument("--project", help="GROUP/PROJECT path (default: from origin)")
        p.add_argument("--hostname", help="GitLab host (default: from origin)")
    args = ap.parse_args()

    host, project = origin_project(args.repo)
    host = args.hostname or host
    project = args.project or project
    if not host or not project:
        die("could not read the project from the origin remote; pass --hostname and --project.")
    path = f"projects/{urllib.parse.quote(project, safe='')}/pages"

    if args.command == "status":
        print_status(glab_api(host, path))
        return

    enabled = "true" if args.state == "on" else "false"
    pages = glab_api(host, path, f"pages_unique_domain_enabled={enabled}", method="PATCH")
    print(f"Unique domain turned {args.state} for {project}.")
    print_status(pages)
    print("The site URL above is the one to link and to check; a deployment "
          "made before the change may need the pages job to run again.")


if __name__ == "__main__":
    main()
