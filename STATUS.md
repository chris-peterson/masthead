# masthead spec coverage status

Tracking status of the requirements declared in [`SPEC.md`](SPEC.md).
Maintained by `/sextant:spec-status`.

**Last audit:** 2026-11-16
**Spec version:** unversioned
**Plugin version:** 0.2.0
**Coverage:** 75 Covered, 0 Partial, 0 Missing/Contradicts

The first 42 requirements were reverse-engineered from the code as it stood at
v0.1.0. SCAFFOLD-15 and PUBLISH-06 through PUBLISH-14 were added with the change
that implements them.

## Status by category

| Prefix | Count | Status | Notes |
|--------|------:|--------|-------|
| ENGINE-01..04 | 4 | All Covered | `skills/bootstrap/SKILL.md` (How this skill is split; 1. Pick the engine) |
| SCAFFOLD-01..15 | 15 | All Covered | `skills/bootstrap/scripts/docsify/bootstrap.py` (`main`, `other_owner`, `detect_host_and_url`, `render_index`, `detect_langs`, `uses_mermaid`, `seed_sidebar`, `seed_readme`, `ensure_justfile`, `detect_spec`, `ignore_spec_copy`); theme and site features in `skills/bootstrap/assets/docsify/index.html` |
| SCAFFOLD-16..17 | 2 | All Covered | `skills/bootstrap/scripts/docsify/template_blocks.py` (`generator`, `fingerprint`); `bootstrap.py` (`main`); the `page-toc` and `page-toc-style` blocks of `assets/docsify/index.html` |
| AUDIENCE-01..06 | 6 | All Covered | `skills/bootstrap/SKILL.md` (4. Sort the existing docs by audience) |
| EVENTS-01..03 | 3 | All Covered | `scripts/announce.sh`; `skills/bootstrap/SKILL.md` (step 4) |
| CONTENT-01..04 | 4 | All Covered | `skills/bootstrap/SKILL.md` (steps 5 to 8) |
| PUBLISH-01..14 | 14 | All Covered | `skills/bootstrap/scripts/docsify/bootstrap.py` (`write_ci`, `gitlab_pages_job`, `pages_links`, `gitlab_namespace_site`, `profile_page`, `main`); `skills/bootstrap/scripts/gitlab_pages.py`; `skills/bootstrap/references/ci-integration.md`; `skills/bootstrap/SKILL.md` (steps 3 and 9) |
| CHECK-01..04 | 4 | All Covered | `skills/bootstrap/SKILL.md` (10. Preview and verify); `skills/bootstrap/scripts/docsify/check-search.js`, `check-contrast.js` |
| MAINTAIN-01..02 | 2 | All Covered | `skills/bootstrap/scripts/docsify/bootstrap.py` (`main`, `--force`); `skills/bootstrap/SKILL.md` (When the hub needs changes later) |
| UPDATE-01..12 | 12 | All Covered | `skills/bootstrap/scripts/docsify/update.py` (`main`, `recover_values`, `compare_template`, `classify`, `merge`, `stamp`); `template_blocks.py` (`split_blocks`, `record`, `template_blocks`); `skills/update-docs/SKILL.md` (UPDATE-05's classification, UPDATE-06's choice, UPDATE-09 to UPDATE-12); `tests/test_update.py` |
| LINT-01..09 | 9 | All Covered | `skills/bootstrap/scripts/docsify/update.py` (`find_issues`, `parse_sidebar`, `resolve`, `exists_exact`, `links`); `tests/test_update.py` (`FindingsTest`) |

Requirements that SKILL.md carries (AUDIENCE, CONTENT, CHECK-01, CHECK-04,
PUBLISH-09, PUBLISH-10's README link, PUBLISH-12's confirmation,
PUBLISH-13, and UPDATE-05's classification, UPDATE-06's choice, and UPDATE-09 to
UPDATE-12) are instructions to the model running the skill. No test exercises them; they're Covered by the instruction being
there.

## How to use this file

When you implement a new requirement, change the row's status and add an
evidence pointer. When an audit reveals drift, update the row to **Partial**
or **Contradicts** with a one-line note.

Evidence pointers are the file plus its enclosing symbol by default. To use a
different granularity, add `**Evidence pointers:** line` (or `anchor`, `file`,
`directory`) to the metadata block above.

## Audit history

### 2026-11-16: Updating an existing hub

Added SCAFFOLD-16 (stamp the site with its template's version), SCAFFOLD-17 (a
page-contents rail in the template), and the UPDATE category for
`/masthead:update-docs`: bring an existing hub's template current while keeping
local edits; and the LINT category for the checks it runs on the sidebar and
pages against the engine reference's practices. SCAFFOLD-03 now names the new
skill in its refusal. All implemented alongside.

### 2026-11-13: Site URL shapes

PUBLISH-05 and PUBLISH-10 widened to print a GitLab namespace site's URL
(`<group>/<group>.<pages-domain>`), the one GitLab URL that follows from the
remote. Added PUBLISH-11 (say where a branch preview lands), PUBLISH-12 (flag a
profile repo), PUBLISH-13 (turn GitLab's unique domain off on the user's say),
and PUBLISH-14 (`gitlab_pages.py`), implemented alongside.

### 2026-11-12: Initial spec

Reverse-engineered 42 requirements from v0.1.0. Added SCAFFOLD-15 (ignore the
spec copy), PUBLISH-06 (a spec-only change redeploys on GitHub),
PUBLISH-07 to PUBLISH-09 (opt-in GitLab merge request previews), and
PUBLISH-10 (print no Pages URL that isn't certain), implemented alongside.
PUBLISH-05 narrowed from every GitHub host to the cases where the URL follows
from the remote.
