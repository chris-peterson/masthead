# Wiring the deploy into existing CI

Read this when the repo already has a CI workflow, so the scaffold script
declined to write a standalone one, or when you need to know where a deployed
site or a preview lands so you can check it. It covers GitHub Actions, GitLab
CI, where each host serves a site, and the one-time Pages setup each host needs.

The script writes a standalone CI file only when none exists. When a workflow is
already there it prints a note and leaves the wiring to you: matching the
pipeline's conventions, its change detection, and its action versions is
judgment, not a template.

## GitHub

Look for `.github/workflows/ci.yml` or similar. The shape below assumes a
`release-gate` job that runs `dorny/paths-filter`; adapt it to whatever gating
the workflow already does.

1. **Add a `force_publish_docs` input** to the `workflow_dispatch` trigger:

   ```yaml
   workflow_dispatch:
     inputs:
       force_publish_docs:
         description: 'Force publish docs (bypass change detection)'
         type: boolean
         default: false
   ```

2. **Add docs change detection** to the gate job's paths filter and outputs:

   ```yaml
   outputs:
     changes_in_docs: ${{ steps.changes.outputs.docs }}
   # ...in the filters block:
   filters: |
     docs:
       - 'docs/**'
   ```

   In a spec-driven repo, list the spec too (`- 'SPEC.md'`): it's copied into
   `docs/` at build time, so a change to it alone must still publish.

3. **Add a `publish-docs` job** that runs after the gate:

   ```yaml
   publish-docs:
     name: Publish documentation
     needs: release-gate
     if: needs.release-gate.outputs.changes_in_docs == 'true' || inputs.force_publish_docs == true
     runs-on: ubuntu-latest
     permissions:
       pages: write
       id-token: write
     environment:
       name: github-pages
       url: ${{ steps.deployment.outputs.page_url }}

     steps:
       - uses: actions/checkout@v6

       - name: Setup Pages
         uses: actions/configure-pages@v5

       - name: Upload artifact
         uses: actions/upload-pages-artifact@v4
         with:
           path: docs

       - name: Deploy to GitHub Pages
         id: deployment
         uses: actions/deploy-pages@v4
   ```

Match the action versions and patterns the existing workflow already uses. If
the repo is spec-driven, copy the spec into `docs/` before the upload step (see
[spec-driven repos](docsify.md#spec-driven-repos)).

## GitLab

If `.gitlab-ci.yml` already exists, append the `pages:` job and confirm a
`deploy` stage is declared:

```yaml
pages:
  stage: deploy
  script:
    - mkdir -p public
    - cp -r docs/* public/
  pages: true
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

## Branch previews

GitLab can publish each branch's docs beside the live site, under
`preview-<branch-slug>/`, using Pages parallel deployments. The prefix names the
branch, so a reader can tell which change a preview shows, and it's the
convention other repos' pages jobs already use. Each preview is a
`preview/<branch-slug>` environment, which an open merge request from that
branch links. It expires after a week; a later push publishes it again. The job sets the
week through a variable (GitLab's own default is 24 hours) and pins the live
site's expiry to `never`, since GitLab doesn't document whether `expire_in`
reaches the unprefixed deployment. A variable in `expire_in` needs GitLab 17.11
or later.

**Parallel deployments need GitLab Premium or Ultimate.** GitLab doesn't
document what a Free-tier project does with a `path_prefix`, and the failure
worth fearing is a branch's docs landing on the live site. So the script writes
previews only when passed `--previews`, and you pass it only after the user
confirms the project's tier.

With `--previews`, the `pages:` job (written, or printed for an existing
`.gitlab-ci.yml`) sets `pages.path_prefix` from a variable that is empty on the
default branch and `preview-$CI_COMMIT_REF_SLUG` on any other branch.
`$CI_COMMIT_REF_SLUG` is the branch name lowercased, with anything outside
`a-z0-9` turned into `-`, cut to 63 characters, so it's safe in a URL.

The preview rule matches branch pipelines (`$CI_COMMIT_BRANCH`), so it adds no
pipelines of its own. In a `.gitlab-ci.yml` whose `workflow: rules` allow only
merge request pipelines, `$CI_COMMIT_BRANCH` is empty there and no preview
runs; add a rule for them that sets the same variables, since
`$CI_COMMIT_REF_SLUG` names the source branch in a merge request pipeline too:

```yaml
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      variables:
        PAGES_PREFIX: preview-$CI_COMMIT_REF_SLUG
        PAGES_ENV: preview/$CI_COMMIT_REF_SLUG
        PAGES_EXPIRE: 1 week
```

GitHub Pages has no built-in previews. The third-party actions that add them
publish to a `gh-pages` branch, which doesn't fit the Actions-source deploy the
script writes, so the script refuses `--previews` on GitHub.

## Where the site lands

Each host serves a site at a URL set by the repo's name and place, and both
reserve a name that puts a site at the root of a domain. Check a deploy, or a
preview, at the URL its shape gives, not the one a project site would have.

| Repo | Site URL |
|------|----------|
| `<owner>/<repo>` on github.com | `https://<owner>.github.io/<repo>/` |
| `<owner>/<owner>.github.io` | `https://<owner>.github.io/` |
| A github.com repo with `docs/CNAME` | `https://<cname>/` |
| `<group>/<project>` on GitLab | `https://<group>.<pages-domain>/<project>/`, or a unique domain |
| `<group>/<sub>/<project>` on GitLab | `https://<group>.<pages-domain>/<sub>/<project>/`, or a unique domain |
| `<group>/<group>.<pages-domain>` on GitLab | `https://<group>.<pages-domain>/` |

- **GitLab's Pages domain is the instance's choice.** It's `gitlab.io` on
  gitlab.com and whatever the admin set elsewhere (`pages.example.com` for a
  `gitlab.example.com`). A namespace site's project name is its domain, so its
  URL is the one GitLab URL the script prints.
- **GitLab gives new projects a unique domain by default**; see
  [unique domains](#unique-domains-on-gitlab). The table's GitLab rows are the
  URLs with it off.
- **The site is hash-routed.** docsify routes after `#/`, so
  `https://<owner>.github.io/` and `https://<owner>.github.io/#/` are the same
  page. Check the path without the hash; the server never sees the hash.
- **A branch preview is the site URL plus `preview-<branch-slug>/`**, on
  whichever domain the site is served from. The `preview/<branch-slug>`
  environment's link is the URL to trust, and `$CI_PAGES_URL` carries the prefix on GitLab 17.9 and later.
  GitLab documents the prefix for project sites only; on a namespace site,
  check that the preview resolves before relying on it.
- **A namespace site shares its origin with the group's project sites** when
  unique domains are off (`<group>.<pages-domain>/` and
  `<group>.<pages-domain>/<project>/`), so anything stored per origin, such as
  docsify's search index, needs a per-site key (see
  [docsify recipes](docsify-recipes.md)).

### Unique domains on GitLab

GitLab gives a new project a unique Pages domain
(`<project>-<hash>.<pages-domain>`; a namespace site gets
`<group>-<domain-with-dashes>-<hash>.<pages-domain>`) and redirects the
namespace URL there with a 308, so that projects in a group don't share
cookies. The cost is a URL nobody can predict or remember, and previews under
it (`<unique>/preview-<branch-slug>/`). A docs hub has no cookies to keep apart, so it
usually wants the namespace URL.

`scripts/gitlab_pages.py` reads and changes the setting through `glab api`,
taking the project and host from the origin remote:

```bash
python3 skills/bootstrap/scripts/gitlab_pages.py status            # site URL, unique domain on/off, deployments
python3 skills/bootstrap/scripts/gitlab_pages.py unique-domain off  # serve at the namespace URL
```

- **Reading** is `GET /projects/:id/pages`, which returns `url`,
  `is_unique_domain_enabled`, and each deployment's `url` and `path_prefix`, so
  it lists the live site and every open preview. It answers 404 until the pages
  job has deployed once.
- **Changing** is `PATCH /projects/:id/pages` with
  `pages_unique_domain_enabled=false`. It needs the Maintainer or Owner role on
  GitLab 17.9 and later (administrator before). In the UI it's Deploy > Pages >
  "Use unique domain".
- **It's the user's call.** The setting is the project's, not the hub's, so
  change it only when they say to, and check the URL `status` prints afterward:
  a deployment made before the change may need the pages job to run again
  before the namespace URL serves it.

### Profile repos aren't project pages

A repo named after its owner holds the owner's profile, not a project:
`<owner>/<owner>` on GitHub renders its README at `github.com/<owner>`, and on
GitLab `<user>/<user>` renders on the user's profile and `<group>/gitlab-profile`
on the group's overview. Pages still serves a hub from one as a project site
(`https://<owner>.github.io/<owner>/`), but a docs link under the README's title
shows on the public profile. The script says when the repo is one; confirm with
the user before linking the hub there.

## One-time Pages setup

Once CI lands, tell the user about the setting each host needs (the script
prints the URL for GitHub):

- **GitHub:** Settings > Pages > Build and deployment > Source > GitHub Actions.
- **GitLab:** Settings > Pages. It is usually on by default once a `pages:` job
  has run.
